#!/usr/bin/env python3

import re
from collections import OrderedDict, Counter
from yattag import Doc, indent

from core import get_phase_name, Player, Phase
from load_data import get_card_data, get_messages


CARD_DATA = get_card_data()


PHASES = (
        'Explore',
        'Develop',
        'Settle',
        'Consume',
        'Produce'
        )


ROMAN = {
    'Explore': 'I',
    'Develop': 'II',
    'Settle': 'III',
    'Consume': 'IV',
    'Produce': 'V'
}


messages = get_messages()


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
                    line('li', 'Military %s' % player.get_military())


    # TODO: 6-devs
    def render_graphs(self):

        def by_bar_length(player):
            return len(player.get_VP_bar())

        players = self.phases[-1].players
        players = sorted(players, key=by_bar_length, reverse=True)
        with tag('ul', klass='bar-graph'):
            for player in players:
                klasses = '{0} {1}'.format(player.get_color(), 'moospace')
                with tag('li'):
                    with tag('span', klass=klasses):
                        text(player.get_VP_bar())

    # TODO: maybe a phase method?
    # Feature envy ?
    def phase_played_by(self, phase):
        '''Return list of player names who made this phase possible.'''
        names = []
        for ch in self.choices:
            if phase.name == get_phase_name(ch[1]):
                names.append(ch[0])
        return names




memory = OrderedDict()
msg = messages[0][0]
while 'Round' not in msg:
    if ' starts with ' in msg:
        player, homeworld = re.search(r'(.+) starts with (.*)\.', msg).groups()
        memory[player] = {}
        memory[player]['tableau'] = [homeworld]
        # TODO: Ancient Race
        memory[player]['hand'] = 4
        memory[player]['VP'] = 0
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
            rnd.phases.append(Phase(msg, rnd.choices, memory, CARD_DATA))
        else:
            rnd.phases[-1].update(msg, fmt, memory)
        msg, fmt = messages.pop(0)
    rounds.append(rnd)
    round_nr += 1


def render_changes(changes):
        with tag('ul'):
            if changes['lost']:
                line('li', changes['lost'], klass='strike')
            if changes['placed']:
                line('li', changes['placed'])
            if changes['content']:
                line('li', changes['content'])

        # TODO: kinds of goods sometimes have gaps between
        # them for no apparent reason.
        for kind in ('novelty', 'rare', 'gene', 'alien'):
            # Don't add empty spans to DOM tree
            if changes['produced'][kind]:
                with tag('span', klass=kind):
                    text(changes['produced'][kind])


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
                                render_changes(player.get_changes())
            rnd.render_graphs()


output = open('report.html', 'w')
print("Generating 'report.html' ...")
print(indent(doc.getvalue()), file=output)

