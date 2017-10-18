import re
from itertools import chain


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


def get_phase_name(choice):
    return choice if choice not in VARIANTS else VARIANTS[choice]


class Player:
    def __init__(self, name, homeworld, card_data):
        self.name = name
        # Each element of these lists represents a phase. Phase 0 is before
        # first round.
        self.placed = [[homeworld]]
        self.lost = [[]]
        self.explored = [0]
        self.hand = [[4]]
        # Unlike drawing cards, VP points are gained only once per turn.
        # Therefore no need for list.
        self.vp = [0]
        self.produced = [[]]
        self.last_msg = None

        self.card_data = card_data

    def add_new_phase(self):
        self.explored.append(0)
        self.placed.append([])
        self.lost.append([])
        self.hand.append([])
        self.vp.append(0)
        self.produced.append([])

    def tableau(self, phase_nr):
        # It would be tempting to just add and remove to a set, but that
        # would remove the ability to query for specific phases or ranges.
        tableau = [c for c in chain.from_iterable(self.placed[:phase_nr])]
        for l in chain.from_iterable(self.lost[:phase_nr]):
            tableau.remove(l)
        return tableau

    def get_hand(self, phase_nr=None):
        phase_nr = 1 if not phase_nr else phase_nr + 1
        return sum(chain.from_iterable(self.hand[:phase_nr]))

    def get_color(self):
        colors = ('red', 'green', 'yellow', 'cyan')
        color = self.name.lower() if self.name.lower() in colors else 'blue'
        return color

    def get_military(self, phase_nr):
        tmp = []

        always = extra = 0
        for card in self.tableau(phase_nr):
            always += self.card_data[card]['military']['normal']
            extra += self.card_data[card]['military']['potential_normal']
        tmp.append(('normal', always, always+extra))

        for card in self.tableau(phase_nr):
            for target in ('novelty', 'rare', 'gene', 'alien', 'rebel', 'xeno'):
                always = extra = 0
                always = self.card_data[card]['military'].get(target, 0)
                extra = self.card_data[card]['military'].get('potential_' + target, 0)
                if not (always or extra):
                    continue
                tmp.append((target, always + tmp[0][1], always+extra + tmp[0][2]))
        return tmp

    def raw_tableau_VP(self, phase_nr):
        '''Return total VP value of tableau without 6-devs'''
        return sum(self.card_data[card]['raw_VP'] for card in self.tableau(phase_nr))

    #TODO: begs for refactoring
    def vp_from_rewards(self, card, awards):
        ''' How many VP does a card get from a list of awards ? (6 devs...)'''
        for reqs, award in awards:
            if reqs <= self.card_data[card]['flags']:
                return award
            elif card in reqs:
                return award
        return 0

    # TODO: how about a new class ?
    def question_marks(self, card, tableau):
        '''Return the VP value for a variable VP card'''
        award_list = self.card_data[card]['?_VP']
        if not award_list:
            return 0
        total = 0
        for c in tableau:
            total += self.vp_from_rewards(c, award_list)
        for req, award in award_list:
            if req == {'THREE_VP'}:
                total += self.numbers['VP']//3
            elif req == {'TOTAL_MILITARY'}:
                total += self.get_military()[0][1]
            elif req == {'NEGATIVE_MILITARY'}:
                military = self.get_military()[0][1]
                total += abs(min(military, 0))
        return total

    def tableau_question_marks(self, phase_nr):
        '''Return the total VP for all variable VP cards in tableau.'''
        total = 0
        tableau = self.tableau(phase_nr)
        variable = [c for c in tableau if self.card_data[c]['?_VP']]
        return sum(self.question_marks(card, tableau) for card in tableau)


    def get_VP_bar(self, phase_nr):
        for_cards = self.raw_tableau_VP(phase_nr) * 'c'
        for_tokens = sum(self.vp[:phase_nr]) * 'v'
        for_variable = self.tableau_question_marks(phase_nr) * '?'
        return ''.join([for_cards, for_tokens, for_variable])

    def get_changes(self, phase_nr):
        '''Renders changes to player that happened within current round.'''
        content = ''

        expl = self.explored[phase_nr]
        expl = '' if not expl else str(expl)
        lost = ', '.join(self.lost[phase_nr]) if self.lost[phase_nr] else ''
        placed = ', '.join(self.placed[phase_nr]) if self.placed[phase_nr] else ''
        cards = sum(int(c) for c in self.hand[phase_nr] if int(c) > 0)
        cards = '' if not cards else '+%scards' % cards
        points = self.vp[phase_nr]
        points = '' if not points else '+%spoints' % points
        points = '' if expl else ''

        content += ' '.join([expl, cards, points]).strip()

        changes = {
                'lost': lost,
                'placed': placed,
                'content': content,
                'produced': [good[0] for good in self.produced[phase_nr]]
                }
        return changes
    
    def draw(self, howmany):
        self.hand[-1].append(int(howmany))

    def discard(self, howmany):
        self.draw(howmany * -1)

    def _parse_placement(self, msg):
        pattern = r'.+ places ([^.]+) at zero cost|.+ places (.+)\.'
        match = re.search(pattern, msg)
        placed = match.group(1) or match.group(2)
        self.placed[-1].append(placed)
        # Wormhole Prospectors places card from top of deck - no discard
        # But Terraforming Project uses the same message and FROM HAND!!
        worpro = '{0} flips {1}.'.format(self.name, placed)
        if 'at zero cost' not in msg:
            self.discard(1)
        elif self.last_msg and worpro not in self.last_msg:
            self.discard(1)
            
    def _parse_payment(self, msg):
        pattern = r'.+ pays (\d) (?:for|to conquer)'
        paid = int(re.search(pattern, msg).group(1))
        self.discard(paid)
    # TODO: find a way to display BOTH number of cards gained and lost
    # over the course of a phase.

    def _parse_production(self, msg):
        planet = re.search(r'.+ produces on (.+)\.', msg).group(1)
        produced = self.card_data[planet]['goods']
        self.produced[-1].append(produced)

    def _parse_card_and_point_gain(self, msg, phase_name):
        cards = points = 0
        if 'Explore' in msg:
            return
        # Sentient Robots, Scientific Cruisers are handled in
        # Produce and Consume summary lines.
        if 'from' in msg and phase_name not in ('Settle', 'Develop'):
            return
        elif phase_name in ('Develop', 'Settle'):
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
        self.draw(cards)
        self.vp[-1] = int(points)
    #TODO: solve the int/str issue once and for all

    def _parse_card_consumption(self, msg):
        pattern = r'.+ consumes (\d) cards? from hand using'
        consumed = int(re.search(pattern, msg).group(1))
        self.discard(consumed)

    def _parse_discard(self, msg):
        if 'good for extra military' in msg:
            pass
        elif 'at end of round' in msg:
            pattern = r'.+ discards (\d) cards? at end of round'
            discarded = int(re.search(pattern, msg).group(1))
            self.discard(discarded)
        elif 'to produce on' in msg:
            self.discard(1)
        else:
            # Cards discarded FROM TABLEAU (not from hand) can be
            # distinguished by *lack* of format in the message.
            lost = re.search(r'.+ discards ([^.]+).', msg).group(1)
            self.lost[-1].append(lost)

    def _parse_exploration(self, msg):
        pattern = r'.+ draws (\d+) and keeps (\d+).'
        explored, kept = re.search(pattern, msg).groups()
        self.explored[-1] = explored
        self.draw(kept)

    def update(self, msg, fmt, phase_name):
        # Wormhole Prospectors, e.g.
        # 'Green flips Replicant Robots.'
        # 'Green takes Replicant Robots into hand.'
        if msg.endswith('into hand.'):
            self.draw(1)
        # Gambling World:
        elif msg.startswith(self.name + ' keeps'):
            self.draw(1)
        elif 'keeps' in msg:
            self._parse_exploration(msg)
        elif 'places' in msg:
            self._parse_placement(msg)
        elif 'pays' in msg:
            self._parse_payment(msg)
        elif 'from hand' in msg:
            self._parse_card_consumption(msg)
        elif 'receives' in msg:
            self._parse_card_and_point_gain(msg, phase_name)
        elif 'produces on' in msg:
            self._parse_production(msg)
        elif 'discards' in msg and not fmt:
            self._parse_discard(msg)
        self.last_msg = msg


class Phase:
    def __init__(self, msg, phase_nr, choices, card_data):
        self.name = re.search(r'--- (?:Second )?(\w+) phase ---', msg).group(1)
        # might be lower case - "Second settle phase" in 2 player advanced:
        self.name = self.name.title()
        self.nr = phase_nr


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

    def get_header(self, players):
        # This will be a list of table cells

        first_phase = self.phases[0]
        header = []

        for player in players:
            tab = '#' * len(player.tableau(first_phase.nr))
            # Split tableau into groups of 4 because humans can't naturally
            # perceive amounts higher than 4.
            choices = (ch[1] for ch in self.choices if ch[0] == player.name)
            choices = '/'.join(choices)
            tab = [tab[n:n+4] for n in range(0, len(tab), 4)]
            tab = ' '.join(tab)

            header.append(
                    (
                        player.get_color(),
                        (
                        '{0} ({1})'.format(player.name, choices),
                        tab,
                        'Hand: %s' % player.get_hand(first_phase.nr-1),
                        ),
                    )
                )

        return header


    # TODO: maybe a phase method?
    # Feature envy ?
    def phase_played_by(self, phase):
        '''Return list of player names who made this phase possible.'''
        names = []
        for ch in self.choices:
            if phase.name == get_phase_name(ch[1]):
                names.append(ch[0])
        return names
