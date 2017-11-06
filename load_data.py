import os, re
from collections import Counter


def _get_fresh_card():
            card = {
            'military': Counter(),
            'flags': set(),
            '?_VP': [],
            }
            return card


def _parse_card_header(line, card):
    card_type, cost, vp = line.split(':')[1:]
    cost, vp = int(cost), int(vp)
    card['raw_VP'] = vp
    card['cost'] = cost
    card['flags'].add('WORLD' if card_type == '1' else 'DEVEL')
    if 'WORLD' in card['flags']:
        card['flags'].add('NONMILITARY')
    if card['cost'] == 6:
        card['flags'].add('SIX')


def _parse_goods(line, card):
    goods = line.split(':')[1].strip()
    card['goods'] = goods.lower()
    # This assumes too much, but you can't know for sure without
    # reading the optional F: (flags) line, which comes *later*.
    card['flags'] |= {goods, 'PRODUCTION', 'NONMILITARY'}


def _parse_flags(line, card):
    flags = line[2:].split('|')
    card['flags'] |= {flag.strip() for flag in flags}
    if 'MILITARY' in card['flags']:
        card['flags'].remove('NONMILITARY')
    if 'WINDFALL' in card['flags']:
        card['flags'].remove('PRODUCTION')


def _parse_explore_phase(line, card):
    if 'ORB_MOVEMENT' not in line:
        card['flags'].add('EXPLORE')


def _parse_settle_phase(line, card):
    if 'EXTRA_MILITARY' not in line:
        return
    military_targets = (
        ' NOVELTY',
        ' RARE',
        ' GENE',
        ' ALIEN',
        ' AGAINST_REBEL',
        ' XENO',
        )
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


def _parse_consume_phase(line, card):
    if 'TRADE_ACTION' in line or 'TRADE' not in line:
        card['flags'].add('CONSUME')
    else:
        card['flags'].add('TRADE')


def _parse_conditions(line, card):
    vp, code, name = line.split(':')[1:]
    code = code.replace('_FLAG', '')
    if code in ('ALIEN_TECHNOLOGY', 'ALIEN_SCIENCE', 'ALIEN_UPLIFT'):
        return;
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


def get_card_data():
    card_data = {}
    with open('cards.txt', 'r') as card_file:
        card = None
        for line in card_file:
            if line.startswith('N:'):
                card_name = line[2:].strip()
                card = card_data[card_name] = _get_fresh_card()
            elif line.startswith('T:'):
                _parse_card_header(line, card)
            elif line.startswith('G:'):
                _parse_goods(line, card)
            elif line.startswith('F:'):
                _parse_flags(line, card)
            elif line.startswith('P:1'):
                _parse_explore_phase(line, card)
            elif line.startswith('P:3'):
                _parse_settle_phase(line, card)
            elif line.startswith('P:4'):
                _parse_consume_phase(line, card)
            elif line.startswith('V:'):
                _parse_conditions(line, card)
    return card_data


def get_messages():
    log = max(f for f in os.listdir('.') if f.startswith('export_'))
    print('Processing {} ...'.format(log))
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

