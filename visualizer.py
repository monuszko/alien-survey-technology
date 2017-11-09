#!/usr/bin/env python3

import re
from collections import OrderedDict, Counter

from core import get_phase_name, Player, Phase, Round, Game
from load_data import get_data, get_card_data
from render import produce_report


input_data = get_data()
messages = input_data['messages']
CARD_DATA = get_card_data(input_data['expansion_code'])


game = Game()


msg = messages[0][0]
while 'Round' not in msg:
    if ' starts with ' in msg:
        name, homeworld = re.search(r'(.+) starts with (.*)\.', msg).groups()
        game.players.append(Player(name, homeworld, CARD_DATA))
        # Unfortunately, cards discarded at start of the game are not logged
        # except for the human player.
        if homeworld == 'Ancient Race':
            game.players[-1].hand[-1].append(-1)
    msg = messages.pop(0)[0]


round_nr = 1
phase_nr = 1
while 'End of game' not in msg:
    rnd = Round(round_nr)
    while 'phase ---' not in msg:
        # Between Round and Phase
        rnd.update_choices(msg)
        msg, fmt = messages.pop(0)
    while '===' not in msg:
        if 'phase ---' in msg:
            phase = Phase(msg, phase_nr, rnd.choices, CARD_DATA)
            rnd.phases.append(phase)
            phase_nr += 1
            game.prepare_players()
        else:
            game.update_player(msg, fmt, phase.name)
        msg, fmt = messages.pop(0)
    game.rounds.append(rnd)
    round_nr += 1


while 'Game information' not in msg:
    msg = messages.pop(0)[0]

for x in range(3):
    game.information.append(messages.pop(0)[0])


produce_report(game)

