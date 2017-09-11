#!/usr/bin/env python3

import os, re
from collections import OrderedDict, Counter

VARIANTS = {
        'Explore +1,+1': 'Explore',
        'Explore +5': 'Explore',
        'Consume-Trade': 'Consume',
        'Consume-x2': 'Consume',
        }

logs = [f for f in os.listdir('/tmp') if f.startswith('export_')]

log = max(logs)
print(log)

messages = []

with open('/tmp/' + log, 'r') as f:
    for line in f:
        message = re.search(r'.*<Message[^>]*>([^<]*)</Message>\n', line)
        if message:
            messages.append(message.group(1))


context = None
rounds = []
rnd = []
phase = {}
players = OrderedDict()
for msg in messages:
    if '===' in msg or '---' in msg:
        if 'Start of game' in msg:
            context = 'start'
        elif 'Round' in msg:
            context = re.search(r'=== Round (\d+) begins ===', msg).group(1)
            if phase:
                rnd.append(phase)
                rounds.append(rnd)
            rnd = []
            bonuses = {}
            phase = {}
        elif 'phase ---' in msg:
            context = 'phase'
            if phase:
                rnd.append(phase)

            phase = {'players': {}}
            for player in players.keys():
                phase['players'][player] = {}
                phase['players'][player]['placed'] = []
                phase['players'][player]['numbers'] = Counter()

    if context == 'start':
        if ' starts with ' in msg:
            player, homeworld = re.search(r'(.*) starts with (.*)\.', msg).groups()
            players[player] = homeworld

    if context and context.isdigit():
        if ' chooses ' in msg:
            player, action = re.search(r'(.*) chooses (.*)\.', msg).groups()
            phase_name = action if action not in VARIANTS else VARIANTS[action]
            variant = "" if action not in VARIANTS else action 

            if phase_name not in bonuses:
                bonuses[phase_name] = [(player, variant)]
            else:
                bonuses[phase_name].append((player, variant))
    if context and 'phase' in context:
        if 'phase ---' in msg:
            phase_name = re.search(r'--- ([A-Z][a-z]+) phase ---', msg).group(1)
            phase['name'] = phase_name
            phase['bonuses'] = bonuses[phase_name]
            continue

        if 'places' in msg:
            player, placed = re.search(r'([^ ]+) places ([^.]+).', msg).groups()
            phase['players'][player]['placed'].append(placed)

        



print('<h1> Players: </h1>')
print('<dl>')
for player, homeworld in players.items():
    print('<dt>{0}:</dt> <dd>{1}</dd>'.format(player, homeworld))
print('</dl>')

print()
print('<table>')
for round_number, rnd in enumerate(rounds, 1):
    for phase in rnd:
        if phase['name'] == rnd[0]['name']:
            print('<tr><td rowspan="%s">%s</td><td>%s ' % (len(rnd), round_number, phase['name']), end="")
        else:
            print('<tr><td>%s ' % phase['name'], end="")

        for player, variant in phase['bonuses']:
            print('%s: %s' % (player, variant), end='')
        print('</td>', end='')

        for player in players:
            pl = phase['players'][player]
            print('<td>', end="")
            line = ''
            line += ', '.join(pl['placed'])
            print(line, end='')
            print('</td>', end='')
        print('</tr>')

print('</table>')


