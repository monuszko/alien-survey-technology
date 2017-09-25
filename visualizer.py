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


class Round():
    def __init__(self, number):
        self.phases = []
        self.number = number
        self.choices = []

    def update_choices(self, msg):

        def phase_order(choice):
            return PHASES.index(get_phase_name(choice[1]))

        if ' chooses ' in msg:
            player_name, choice = re.search(r'(.+) chooses (.+)\.', msg).groups()
            # Split to support 2 Player Advanced:
            for ch in choice.split('/'):
                self.choices.append((player_name, ch))
        choices = sorted(self.choices, key=phase_order)

    def render_header(self):
        line('td', 'Actions')
        #TODO: Do Players really belong inside Phase ? Think of pros and cons.
        for player in self.phases[0].players:
            tab = '#' * len(player.tableau)
            # Split tableau into groups of 4 because humans can't naturally
            # perceive amounts higher than 4.
            choices = (ch[1] for ch in self.choices if ch[0] == player.name)
            choices = '/'.join(choices)
            tab = [tab[n:n+4] for n in range(0, len(tab), 4)]
            tab = ' '.join(tab)
            with tag('td', klass=player.get_color()):
                with tag('ul'):
                    line('li', '{0} ({1})'.format(player.name, choices))
                    line('li', tab)
                    line('li', 'Hand: %s' % player.numbers['hand'])

    # TODO: maybe a phase method?
    # Feature envy ?
    def phase_played_by(self, phase):
        '''Return list of player names who made this phase possible.'''
        names = []
        for ch in self.choices:
            if phase.name == get_phase_name(ch[1]):
                names.append(ch[0])
        return names


class Player:
    def __init__(self, name, memory):
        self.name = name
        self.placed = []
        self.lost = []
        self.numbers = Counter()
        self.numbers['hand'] = memory[self.name]['hand']
        # TODO: display individual cards to show what factored into player's
        # decision when choosing action.
        self.tableau = memory[self.name]['tableau'].copy()

    def get_color(self):
        colors = ('red', 'green', 'yellow', 'cyan')
        color = self.name.lower() if self.name.lower() in colors else 'blue'
        return color

    def render_changes(self):
        '''Renders changes to player that happened within current round.'''
        content = ''
        counter = player.numbers

        explored = ''
        if  counter['explored']:
            explored = '+%s(%s)' % (counter['kept'], counter['explored'])

        lost = ', '.join(self.lost)
        placed = ', '.join(self.placed)

        cards = counter['cards']
        cards = '' if not cards else '+%scards' % cards
        points = counter['points']
        points = '' if not points else '+%spoints' % points

        content += ' '.join([explored, cards, points]).strip()

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

    def update(self, msg, fmt, memory, phase):
        counter = self.numbers

        # exploration:
        if 'and keeps' in msg:
            pattern = r'.+ draws (\d+) and keeps (\d+).'
            explored, kept = re.search(pattern, msg).groups()
            counter['explored'] += int(explored)
            counter['kept'] += int(kept)
            memory[self.name]['hand'] += int(kept)

        # placement of cards:
        if 'places' in msg:
            pattern = r'.+ places ([^.]+) at zero cost|.+ places ([^.]+)'
            match = re.search(pattern, msg)
            placed = match.group(1) or match.group(2)
            self.placed.append(placed)
            memory[self.name]['tableau'].append(placed)
            memory[self.name]['hand'] -= 1

        if 'pays' in msg:
            paid = int(re.search(r'.+ pays (\d) for', msg).group(1))
            self.numbers['discarded'] += paid
            memory[self.name]['hand'] -= paid

        # TODO: find a way to display BOTH number of cards gained and lost
        # over the course of a phase.
        if 'from hand' in msg:
            pattern = r'.+ consumes (\d) cards? from hand using'
            consumed = int(re.search(pattern, msg).group(1))
            self.numbers['discarded'] += consumed
            memory[self.name]['hand'] -= consumed

        # Cards discarded FROM TABLEAU (not from hand) can be distinguished
        # by *lack* of format in the message.
        if 'discards' in msg and not fmt:
            if 'good for extra military' in msg:
                pass
            elif 'at end of round' in msg:
                pattern = r'.+ discards (\d) cards? at end of round'
                discarded = int(re.search(pattern, msg).group(1))
                self.numbers['discarded'] += discarded
                memory[self.name]['hand'] -= discarded
            elif 'to produce on' in msg:
                self.numbers['discarded'] += 1
                memory[self.name]['hand'] -= 1
            else:
                lost = re.search(r'.+ discards ([^.]+).', msg).group(1)
                self.lost.append(lost)
                memory[self.name]['tableau'].remove(lost)

        # Wormhole Prospectors, e.g.
        # 'Green flips Replicant Robots.'
        # 'Green takes Replicant Robots into hand.'
        if msg.endswith('into hand.'):
            counter['cards'] += 1
            memory[self.name]['hand'] += 1

        # cards and VPs gained:
        if 'receives' in msg:
            cards = points = 0
            if 'Explore' in msg:
                return
            # Sentient Robots, Scientific Cruisers are handled in
            # Produce and Consume summary lines.
            if 'from' in msg and phase not in ('Settle', 'Develop'):
                return
            elif phase in ('Develop', 'Settle'):
                # Handles on-Settle bonus including Terraforming Robots,
                # powers that make you draw on Develop, etc.
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
            memory[self.name]['hand'] += int(cards)

        # production of goods:
        if 'produces on' in msg:
            planet = re.search(r'.+ produces on (.+)\.', msg).group(1)
            counter[PRODUCERS[planet]] += 1


class Phase:
    ''' Stores information about game state at the start of the phase
    and about gains players made during the phase. '''
    def __init__(self, msg, choices, memory):
        self.name = re.search(r'--- (?:Second )?(\w+) phase ---', msg).group(1)
        # might be lower case - "Second settle phase" in 2 player advanced:
        self.name = self.name.title()
        self.players = []
        for player_name in memory:
            self.players.append(Player(player_name, memory))

    def update(self, msg, fmt, memory):
        '''Determine the player and delegate updating data to it'''
        player = counter = None
        # Not checking 'split()[0] in line' because name might be
        # multi-word.
        for pl in self.players:
            if msg.startswith(pl.name):
                player = pl
                break
        if not player:
            return
        player.update(msg, fmt, memory, self.name)


memory = OrderedDict()
msg = messages[0][0]
while 'Round' not in msg:
    if ' starts with ' in msg:
        player, homeworld = re.search(r'(.+) starts with (.*)\.', msg).groups()
        memory[player] = {}
        memory[player]['tableau'] = [homeworld]
        # TODO: Ancient Race
        memory[player]['hand'] = 4
    msg = messages.pop(0)[0]


rounds = []
round_nr = 1
while 'End of game' not in msg:
    rnd = Round(round_nr)
    while 'phase ---' not in msg:
        # Between Round and Phase
        rnd.update_choices(msg)
        msg, fmt = messages.pop(0)
    while '===' not in msg:
        if 'phase ---' in msg:
            rnd.phases.append(Phase(msg, rnd.choices, memory))
        else:
            rnd.phases[-1].update(msg, fmt, memory)
        msg, fmt = messages.pop(0)
    rounds.append(rnd)
    round_nr += 1


doc, tag, text, line= Doc().ttl()
with tag('html'):
    with tag('meta'):
        doc.stag('link', rel="stylesheet", href="style.css")
    with tag('body'):
        for rnd in rounds:
            line('h2', 'Round %s' % rnd.number)
            with tag('table'):
                with tag('tr'):
                    rnd.render_header()
                for phase in rnd.phases:
                    with tag('tr'):
                        line('td', ROMAN[phase.name])
                        for player in phase.players:
                            klass = ''
                            if player.name in rnd.phase_played_by(phase):
                                klass = player.get_color()
                            with tag('td', klass=klass):
                                player.render_changes()


output = open('report.html', 'w')
print("Generating 'report.html' ...")
print(indent(doc.getvalue()), file=output)

