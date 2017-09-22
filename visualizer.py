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


ROMAN = {
    'Explore': 'I',
    'Develop': 'II',
    'Settle': 'III',
    'Consume': 'IV',
    'Produce': 'V'
}


def get_color(player):
    colors = ('red', 'green', 'yellow', 'cyan')
    color = player.lower() if player.lower() in colors else 'blue'
    return color


logs = [f for f in os.listdir('/tmp') if f.startswith('export_')]
log = max(logs)
print('Processing {} ...'.format(log))


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


def get_phase_name(choice):
    return choice if choice not in VARIANTS else VARIANTS[choice]


def updated_choices(choices, msg):
    # TODO: 2 Player Advanced needs 2 choices per player.
    if ' chooses ' in msg:
        player_name, choice = re.search(r'(.+) chooses (.+)\.', msg).groups()
        # Split to support 2 Player Advanced:
        for ch in choice.split('/'):
            choices.append((player_name, ch))
    return choices


class Phase:
    ''' Stores information about game state at the start of the phase
    and about gains players made during the phase. '''
    def __init__(self, msg, choices, tableau):
        self.name = re.search(r'--- (?:Second )?(\w+) phase ---', msg).group(1)
        # might be lower case - "Second settle phase" in 2 player advanced:
        self.name = self.name.title()
        self.bonuses = []
        self.players = []
        for player_name in tableau:
            player = {
                    'name': player_name,
                    'placed': [],
                    'lost': [],
                    'numbers': Counter(),
                    'tableau': tableau[player_name].copy(),
                    }
            self.players.append(player)
        for player_name, choice in choices:
            if get_phase_name(choice) == self.name:
                self.bonuses.append((player_name, choice))

    def update(self, msg, fmt, tableau):
        ''' Update phase based on log message '''
        player = counter = None
        # Not checking 'split()[0] in line' because name might be
        # multi-word.
        for pl in self.players:
            if msg.startswith(pl['name']):
                player = pl
                counter = player['numbers']
                break
        if not player:
            return

        # exploration:
        if 'and keeps' in msg:
            pattern = r'.+ draws (\d+) and keeps (\d+).'
            explored, kept = re.search(pattern, msg).groups()
            counter['explored'] += int(explored)
            counter['kept'] += int(kept)

        # placement of cards:
        if 'places' in msg:
            pattern = r'.+ places ([^.]+) at zero cost|.+ places ([^.]+)'
            match = re.search(pattern, msg)
            placed = match.group(1) or match.group(2)
            player['placed'].append(placed)
            tableau[player['name']].append(placed)

        # Cards discarded FROM TABLEAU (not from hand) can be distinguished
        # by *lack* of format in the message.
        if 'discards' in msg and not fmt:
            if 'for extra military' in msg:
                pass
            elif 'at end of round' in msg:
                pass
            elif 'to produce on' in msg:
                pass
            else:
                lost = re.search(r'.+ discards ([^.]+).', msg).group(1)
                player['lost'].append(lost)
                tableau[player['name']].remove(lost)


        # cards and VPs gained:
        if 'receives' in msg:
            cards = points = 0
            if 'Explore' in msg:
                return
            # Sentient Robots, Scientific Cruisers are handled in
            # Produce and Consume summary lines.
            if 'from' in msg and self.name not in ('Settle', 'Develop'):
                return
            elif self.name in ('Develop', 'Settle'):
                cards = re.search(r'receives (\d+) cards? from', msg).group(1)
            elif 'VP' not in msg:
                pattern = r'receives (\d+) cards? for (Produce|Consume) phase'
                cards = re.search(pattern, msg).group(1)
            elif 'card' not in msg:
                pattern = r'.+ receives (\d+) VPs? for Consume phase.'
                points = re.search(pattern, msg).group(1)
            elif 'card' in msg and 'VP' in msg:
                pattern = r'.+ receives (\d+) cards? and (\d+) VPs?'
                cards, points = re.search(pattern, msg).groups()
            counter['cards'] += int(cards)
            counter['points'] += int(points)

        # production of goods:
        if 'produces on' in msg:
            planet = re.search(r'.+ produces on (.+)\.', msg).group(1)
            counter[PRODUCERS[planet]] += 1


def render_header(rnd):
    line('td', 'Actions')
    for player in rnd[0].players:
        tab = '#' * len(player['tableau'])
        # Split tableau into groups of 4 because humans can't naturally
        # perceive amounts higher than 4.
        tab = [tab[n:n+4] for n in range(0, len(tab), 4)]
        tab = ' '.join(tab)
        with tag('td', klass=get_color(player['name'])):
            with tag('ul'):
                line('li', player['name'])
                line('li', tab)


def render_gains(player):
    content = ''
    pl = player
    counter = player['numbers']

    explored = ''
    if  counter['explored']:
        explored = '+%s(%s)' % (counter['kept'], counter['explored'])

    lost = ', '.join(pl['lost'])
    placed = ', '.join(pl['placed'])

    cards = counter['cards']
    cards = '' if not cards else '+%scards' % cards
    points = counter['points']
    points = '' if not points else '+%spoints' % points

    content += ' '.join([explored, cards, points]).strip()

    if not (lost or placed or content):
        return

    with tag('ul'):
        if lost:
            line('li', lost, klass='strike')
        if placed:
            line('li', placed)
        if content:
            line('li', content)

    # TODO: kinds of goods sometimes have gaps between
    # them for no apparent reason.
    for kind in ('novelty', 'rare', 'gene', 'alien'):
        # Don't add empty spans to DOM tree
        if counter[kind]:
            with tag('span', klass=kind):
                text('#' * counter[kind])


tableau = OrderedDict()
msg = messages[0][0]
while 'Round' not in msg:
    if ' starts with ' in msg:
        player, homeworld = re.search(r'(.+) starts with (.*)\.', msg).groups()
        tableau[player] = [homeworld]
    msg = messages.pop(0)[0]


rounds = []
while 'End of game' not in msg:
    choices = []
    rnd = []
    while 'phase ---' not in msg:
        # Between Round and Phase
        choices = updated_choices(choices, msg)
        msg, fmt = messages.pop(0)
    while '===' not in msg:
        if 'phase ---' in msg:
            rnd.append(Phase(msg, choices, tableau))
        else:
            rnd[-1].update(msg, fmt, tableau)
        msg, fmt = messages.pop(0)
    rounds.append(rnd)


doc, tag, text, line= Doc().ttl()
with tag('html'):
    with tag('meta'):
        doc.stag('link', rel="stylesheet", href="style.css")
    with tag('body'):
        for round_number, rnd in enumerate(rounds, 1):
            line('h2', 'Round %s' % round_number)
            with tag('table'):
                with tag('tr'):
                    render_header(rnd)
                for phase in rnd:
                    with tag('tr'):
                        line('td', ROMAN[phase.name])
                        for player in phase.players:
                            klass = ''
                            if player['name'] in (b[0] for b in phase.bonuses):
                                klass = get_color(player['name'])
                            with tag('td', klass=klass):
                                render_gains(player)


output = open('report.html', 'w')
print("Generating 'report.html' ...")
print(indent(doc.getvalue()), file=output)

