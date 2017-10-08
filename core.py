import re
from collections import Counter


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
    def __init__(self, name, memory, card_data):
        self.name = name
        self.placed = []
        self.lost = []
        self.numbers = Counter()
        self.numbers['hand'] = memory[self.name]['hand']
        self.numbers['VP'] = memory[self.name]['VP']
        # TODO: display individual cards to show what factored into player's
        # decision when choosing action.
        self.tableau = memory[self.name]['tableau'].copy()

        self.card_data = card_data

    def get_color(self):
        colors = ('red', 'green', 'yellow', 'cyan')
        color = self.name.lower() if self.name.lower() in colors else 'blue'
        return color

    def get_military(self):
        tmp = []

        always = extra = 0
        for card in self.tableau:
            always += self.card_data[card]['military']['normal']
            extra += self.card_data[card]['military']['potential_normal']
        tmp.append(('normal', always, always+extra))

        for card in self.tableau:
            for target in ('novelty', 'rare', 'gene', 'alien', 'rebel', 'xeno'):
                always = extra = 0
                always = self.card_data[card]['military'].get(target, 0)
                extra = self.card_data[card]['military'].get('potential_' + target, 0)
                if not (always or extra):
                    continue
                tmp.append((target, always + tmp[0][1], always+extra + tmp[0][2]))
        return tmp

    def raw_tableau_VP(self):
        '''Return total VP value of tableau without 6-devs'''
        return sum(self.card_data[card]['raw_VP'] for card in self.tableau)

    #TODO: begs for refactoring
    def vp_from_rewards(self, card, awards):
        ''' How many VP does a card get from a list of awards ? (6 devs...)'''
        #TODO: NEGATIVE_MILITARY
        #TODO: TOTAL_MILITARY
        for reqs, award in awards:
            if reqs <= self.card_data[card]['flags']:
                return award
            elif card in reqs:
                return award
        return 0

    # TODO: how about a new class ?
    def question_marks(self, card):
        '''Return the VP value for a variable VP card'''
        award_list = self.card_data[card]['?_VP']
        if not award_list:
            return 0
        total = 0
        for c in self.tableau:
            gain = self.vp_from_rewards(c, award_list)
            total += gain
            for req, award in award_list:
                if req == {'THREE_VP'}:
                    total += self.numbers['VP']//3
        return total

    def tableau_question_marks(self):
        '''Return the total VP for all variable VP cards in tableau.'''
        total = 0
        variable = [c for c in self.tableau if self.card_data[c]['?_VP']]
        return sum(self.question_marks(card) for card in self.tableau)


    def get_VP_bar(self):
        for_cards = self.raw_tableau_VP() * 'c' 
        for_tokens = self.numbers['VP'] * 'v'
        for_variable = self.tableau_question_marks() * '?'
        return ''.join([for_cards, for_tokens, for_variable])

    def get_changes(self):
        '''Renders changes to player that happened within current round.'''
        content = ''
        counter = self.numbers

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

        changes = {
                'lost': lost,
                'placed': placed,
                'content': content,
                'produced': []
                }
        for kind in ('novelty', 'rare', 'gene', 'alien'):
            if counter[kind]:
                changes['produced'].append(kind[0] * counter[kind])
        return changes

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
            pattern = r'.+ places ([^.]+) at zero cost|.+ places (.+)\.'
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
            memory[self.name]['VP'] += int(points)

        # production of goods:
        if 'produces on' in msg:
            planet = re.search(r'.+ produces on (.+)\.', msg).group(1)
            counter[self.card_data[planet]['goods']] += 1


class Phase:
    ''' Stores information about game state at the start of the phase
    and about gains players made during the phase. '''
    def __init__(self, msg, choices, memory, card_data):
        self.name = re.search(r'--- (?:Second )?(\w+) phase ---', msg).group(1)
        # might be lower case - "Second settle phase" in 2 player advanced:
        self.name = self.name.title()
        self.players = []
        for player_name in memory:
            self.players.append(Player(player_name, memory, card_data))

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

    def get_header(self):
        # This will be a list of table cells
        header = []

        for player in self.phases[0].players:
            tab = '#' * len(player.tableau)
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
                        'Hand: %s' % player.numbers['hand'],
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
