import os, re
from collections import Counter


MILITARY_TARGETS = (
    ' NOVELTY',
    ' RARE',
    ' GENE',
    ' ALIEN',
    ' AGAINST_REBEL',
    ' XENO',
    )


def get_card_data():
    card_data = {}
    with open('cards.txt', 'r') as card_file:
        for line in card_file:
            if line.startswith('N:'):
                card_name = line[2:].strip()
                card_data[card_name] = {'military': Counter()}
            elif line.startswith('T:'):
                card_data[card_name]['raw_VP'] = int(line.split(':')[-1])
            elif line.startswith('G:'):
                card_data[card_name]['goods'] = line.split(':')[1].lower().strip()
            elif line.startswith('P:3') and 'EXTRA_MILITARY' in line:
                # Cut the phase identifier and the last number I don't understand.
                line = line[4:-3]
                bonus = int(line.split(':')[1])
                potential = False
                if 'CONSUME' in line or 'DISCARD' in line:
                    potential = True
                specialized = False
                for target in MILITARY_TARGETS:
                    if target in line:
                        target = target.strip().lower()
                        break
                    target = 'normal'
                target = target if target != 'against_rebel' else 'rebel'
                key = ('' if not potential else 'potential_') + target
                card_data[card_name]['military'][key] = bonus
    return card_data


logs = [f for f in os.listdir('/tmp') if f.startswith('export_')]
log = max(logs)
print('Processing {} ...'.format(log))


def get_messages():
    messages = []
    with open('/tmp/' + log, 'r') as log_file:
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
