import os, re
from collections import Counter


def get_card_data():
    military_targets = (
        ' NOVELTY',
        ' RARE',
        ' GENE',
        ' ALIEN',
        ' AGAINST_REBEL',
        ' XENO',
        )
    card_data = {}
    with open('cards.txt', 'r') as card_file:
        card = None
        for line in card_file:
            if line.startswith('N:'):
                card_name = line[2:].strip()
                card_data[card_name] = {
                        'military': Counter(),
                        'flags': set(),
                        '?_VP': [],
                        }
                card = card_data[card_name]
            elif line.startswith('T:'):
                card_type, cost, vp = line.split(':')[1:]
                cost, vp = int(cost), int(vp)
                card['raw_VP'] = vp
                card['cost'] = cost
                card['flags'].add('WORLD' if card_type == '1' else 'DEVEL')
                if card['cost'] == 6:
                    card['flags'].add('SIX')
            elif line.startswith('G:'):
                goods = line.split(':')[1].strip()
                card['goods'] = goods.lower()
                # This assumes too much, but you can't know for sure without
                # reading the optional F: (flags) line, which comes *later*.
                card['flags'] |= {goods, 'PRODUCTION', 'NONMILITARY'}
            elif line.startswith('F:'):
                flags = line[2:].split('|')
                card['flags'] |= {flag.strip() for flag in flags}
                if card['flags'] & {'WORLD', 'MILITARY'} == {'WORLD'}:
                    card['flags'].add('NONMILITARY')
                if 'WINDFALL' in card['flags']:
                    card['flags'].remove('PRODUCTION')
            elif line.startswith('P:3') and 'EXTRA_MILITARY' in line:
                line = line[4:-3]
                bonus = int(line.split(':')[1])
                potential = False
                if 'CONSUME' in line or 'DISCARD' in line:
                    potential = True
                for target in military_targets:
                    if target in line:
                        target = target.strip().lower()
                        break
                    target = 'normal'
                target = target if target != 'against_rebel' else 'rebel'
                key = ('' if not potential else 'potential_') + target
                card['military'][key] = bonus
            elif line.startswith('V:'):
                vp, code, name = line.split(':')[1:]
                code = code.replace('_FLAG', '')
                if code in ('ALIEN_TECHNOLOGY', 'ALIEN_SCIENCE', 'ALIEN_UPLIFT'):
                    continue;
                elif code == 'NAME':
                    code = {name.strip()}
                elif code in ('THREE_VP', 'NEGATIVE_MILITARY', 'TOTAL_MILITARY'):
                    code = {code}
                elif code.startswith('ANTI_XENO'):
                    a = 'ANTI_XENO'
                    code = {w.lstrip('_') for w in code.partition(a) if w}
                else:
                    code = set(code.split('_'))
                card['?_VP'].append((code, int(vp)))
    return card_data


logs = [f for f in os.listdir('.') if f.startswith('export_')]

log = max(logs)
print('Processing {} ...'.format(log))


def get_messages():
    messages = []
    with open(log, 'r') as log_file:
        # Note to future self:
        # (?:) is an optional non-capturing group
        # which may contain a normal group.
        pattern = r'.*<Message(?: format="(\w+)")?>([^<]*)<\/Message>\n'
        for line in log_file:
            match = re.search(pattern, line)
            if match:
                fmt, message = match.groups()
                messages.append((message, fmt))
    return messages
