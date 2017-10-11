#!/usr/bin/env python3

import re
from collections import OrderedDict, Counter

from core import get_phase_name, Player, Phase, Round
from load_data import get_card_data, get_messages
from render import produce_report


CARD_DATA = get_card_data()
messages = get_messages()

game = {
    'players': [],
    'rounds': [],
    }

msg = messages[0][0]
while 'Round' not in msg:
    if ' starts with ' in msg:
        name, homeworld = re.search(r'(.+) starts with (.*)\.', msg).groups()
        game['players'].append(Player(name, homeworld, CARD_DATA))
        # Unfortunately, cards discarded at start of the game are not logged
        # except for the human player.
        if homeworld == 'Ancient Race':
            game['players'][-1].hand[-1].append(-1)
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
            for player in game['players']:
                player.add_new_phase()
        else:
            for player in game['players']:
                if msg.startswith(player.name):
                    player.update(msg, fmt, phase)
                    break
        msg, fmt = messages.pop(0)
    game['rounds'].append(rnd)
    round_nr += 1


produce_report(game)

