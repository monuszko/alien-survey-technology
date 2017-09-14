#!/usr/bin/env python3

import os, re
from collections import OrderedDict, Counter
from yattag import Doc, indent


PRODUCERS = {}
with open('cards.txt', 'r') as card_file:
    for line in card_file:
        if line.startswith('N:'):
            card_name = ' '.join(line.split(':')[1:]).strip()
        elif line.startswith('G:'):
            PRODUCERS[card_name] = line.split(':')[1].lower().strip()

PHASES = (
        'Explore',
        'Develop',
        'Settle',
        'Consume',
        'Produce'
        )

VARIANTS = {
        'Explore +1,+1': 'Explore',
        'Explore +5': 'Explore',
        'Consume-Trade': 'Consume',
        'Consume-x2': 'Consume',
        }


def get_color(player):
    colors = ('red', 'green', 'yellow', 'cyan')
    color = player.lower() if player.lower() in colors else 'blue'
    return color


logs = [f for f in os.listdir('/tmp') if f.startswith('export_')]

log = max(logs)
print('Processing {}...'.format(log))

messages = []

with open('/tmp/' + log, 'r') as log_file:
    for line in log_file:
        message = re.search(r'.*<Message[^>]*>([^<]*)</Message>\n', line)
        if message:
            messages.append(message.group(1))


def get_phase_template():
    phase = {'players': {}}
    for player in players.keys():
        phase['players'][player] = {}
        phase['players'][player]['placed'] = []
        phase['players'][player]['numbers'] = Counter()
        phase_name = context
        phase['name'] = phase_name
        phase['bonuses'] = bonuses[phase_name]
    return phase


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
        elif 'phase ---' in msg:
            context = re.search(r'--- (\w+) phase ---', msg).group(1)
            if phase:
                rnd.append(phase)
            phase = get_phase_template()
        continue

    # Collect initial game information:
    if context == 'start':
        if ' starts with ' in msg:
            player, homeworld = re.search(r'(.+) starts with (.*)\.', msg).groups()
            players[player] = homeworld

    # Collect round start information:
    if context and context.isdigit():
        if ' chooses ' in msg:
            player, action = re.search(r'(.+) chooses (.+)\.', msg).groups()
            phase_name = action if action not in VARIANTS else VARIANTS[action]
            variant = "" if action not in VARIANTS else action 

            if phase_name not in bonuses:
                bonuses[phase_name] = [(player, variant)]
            else:
                bonuses[phase_name].append((player, variant))

    # Collect info about phase:
    if context in PHASES:
        player = counter = None
        first = msg.split()[0]
        if first in players:
            player, counter = first, phase['players'][first]['numbers']

        # exploration:
        if 'keeps' in msg:
            pattern = r'.+ draws (\d+) and keeps (\d+).'
            explored, kept = re.search(pattern, msg).groups()
            counter['explored'] += int(explored)
            counter['kept'] += int(kept)

        # placement of cards:
        if 'places' in msg:
            player, placed = re.search(r'(.+) places ([^.]+).', msg).groups()
            phase['players'][player]['placed'].append(placed)

        # cards and VPs gained:
        cards = points = 0
        pattern = r'(.+) receives (\d+) cards? for \w phase.'

        if 'for Consume phase' in msg:
            if 'card' in msg and 'VP' in msg:
                pattern = r'(.+) receives (\d+) cards? and (\d+) VPs?'
                player, cards, points = re.search(pattern, msg).groups()
            elif 'VP' in msg:
                pattern = r'(.+) receives (\d+) VPs? for Consume phase.'
                player, points = re.search(pattern, msg).groups()
            else:
                pattern = r'(.+) receives (\d+) cards? for Consume phase.'
                player, cards = re.search(pattern, msg).groups()
            counter['cards'] += int(cards)
            counter['points'] += int(points) 
        elif 'for Produce phase' in msg:
            pattern = r'(.+) receives (\d+) cards? for Produce phase.'

        # production of goods:
        if 'produces on' in msg:
            planet = re.search(r'.+ produces on (.+)\.', msg).group(1)
            counter[PRODUCERS[planet]] += 1


doc, tag, text, line= Doc().ttl()


def render_actions(phase):
    for player, variant in phase['bonuses']:
        action = variant if variant in VARIANTS else phase['name']
        line('li', action, klass=get_color(player))


def render_gains(phase):
    content = ''
    pl = phase['players'][player]
    counter = pl['numbers']

    explored = ''
    if  counter['explored']:
        explored = '+%s(%s)' % (counter['kept'], counter['explored'])

    placed = ', '.join(pl['placed'])

    cards = counter['cards']
    cards = '' if not cards else '+%scards' % cards
    points = counter['points']
    points = '' if not points else '+%spoints' % points 

    content += ' '.join([explored, placed, cards, points])
    text(content)

    for kind in ('novelty', 'rare', 'gene', 'alien'):
        with tag('span', klass=kind):
            text('#' * counter[kind])


with tag('html'):
    with tag('meta'):
        doc.stag('link', rel="stylesheet", href="style.css")
    with tag('body'):
        for round_number, rnd in enumerate(rounds, 1):
            line('h2', 'Round %s' % round_number)
            with tag('table'):
                for phase in rnd:
                    with tag('tr'):
                        with tag('td', klass='action'):
                            render_actions(phase)
                        for player in players:
                            with tag('td'):
                                render_gains(phase)


output = open('report.html', 'w')
print("Generating 'report.html'...")
print(indent(doc.getvalue()), file=output)

