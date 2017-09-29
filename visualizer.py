#!/usr/bin/env python3

import re
from collections import OrderedDict, Counter

from core import get_phase_name, Player, Phase, Round
from load_data import get_card_data, get_messages
from render import produce_report


CARD_DATA = get_card_data()
messages = get_messages()


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


produce_report(rounds)

