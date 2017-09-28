import re
from collections import Counter


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
        '''Stub'''
        always = potential = 0
        for card in self.tableau:
            always += self.card_data[card]['military']['normal']
            potential += self.card_data[card]['military']['potential_normal']

        return '{0}({1})'.format(
                always,
                always + potential
                )

    def raw_tableau_VP(self):
        '''Return total VP value of tableau without 6-devs'''
        return sum(self.card_data[card]['raw_VP'] for card in self.tableau)

    def get_VP_bar(self):
        return self.raw_tableau_VP()*'c' +  self.numbers['VP']*'v'


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
                'produced': {}
                }
        for kind in ('novelty', 'rare', 'gene', 'alien'):
            changes['produced'][kind] = '#' * counter[kind]
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
