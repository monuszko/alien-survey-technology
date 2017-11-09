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
    if card_type == '1':
        card['flags'] |= {'WORLD', 'NONMILITARY'}
    else:
        card['flags'].add('DEVEL')
    if card['cost'] == 6:
        card['flags'].add('SIX')


def _parse_goods(line, card):
    goods = line.split(':')[1].strip()
    card['goods'] = goods.lower()
    # This assumes too much, but you can't know for sure without
    # reading the optional F: (flags) line, which comes *later*.
    card['flags'] |= {goods, 'PRODUCTION'}


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
    if target not in card['military']:
        card['military'][target] = [0, 0]
    if not potential:
        card['military'][target][0] += bonus
    else:
        card['military'][target][1] += bonus


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


# Some cards (like Rebel Resistance) have identical name but differ in function.
# Such cards never appear in the same expansion, and while it's technically
# possible to mix ALL of them in, official rules don't allow it.
# So instead of enabling the use of ALL of them simultaneously and mucking with
# internal card ID's, this application simply prevents loading
# (and overwriting) cards from non-matching expansions.
USED_EXPANSIONS = {
            # Base game only:
            '0': {'0'},
            # Base and The Gathering Storm:
            '1': {'0', '1'},
            # Base, TGS and Rebel vs Imperium:
            '2': {'0', '1', '2'},
            # Base, TGS, RvI and Brink of War:
            '3': {'0', '1', '2', '3'},
            # Base and Alien Artifacts:
            '4': {'0', '4'},
            # Base and Xeno Invasion:
            '5': {'0', '5'},
            # Base and Rebel vs Imperium:
            '6': {'0', '6'},
        }


def get_card_data(expansion_code):
    card_data = {}
    with open('cards.txt', 'r') as card_file:
        card = None
        for line in card_file:
            if line.startswith('N:'):
                card_name = line[2:].strip()
                card = _get_fresh_card()
            elif line.startswith('T:'):
                _parse_card_header(line, card)
            elif line.startswith('E@'):
                card_expansion = line[2]
                if card_expansion in USED_EXPANSIONS[expansion_code]:
                    card_data[card_name] = card
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


def get_data():
    log = max(f for f in os.listdir('.') if f.startswith('export_'))
    print('Processing {} ...'.format(log))
    messages = []
    with open(log, 'r') as log_file:
        # Note to future self:
        # (?:) is an optional non-capturing group
        # which may contain a normal group.
        pattern = r'.*<Message(?: format="(\w+)")?>([^<]*)<\/Message>\n'
        for line in log_file:
            if '<Expansion id="' in line:
                expansion_code = line.split('"')[1]
                continue
            match = re.search(pattern, line)
            if match:
                fmt, message = match.groups()
                messages.append((message, fmt))
    return {
            'messages': messages,
            'expansion_code': expansion_code,
            }
    return messages

