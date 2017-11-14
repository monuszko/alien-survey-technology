from yattag import Doc, indent

doc, tag, text, line = Doc().ttl()


ROMAN = {
    'Explore': 'I',
    'Develop': 'II',
    'Settle': 'III',
    'Consume': 'IV',
    'Produce': 'V'
}


def render_cells(cells):
    ''' Render a list of table cells. Each cell is a tuple:
    (cell_html_class, tuple_of_contents)

    if tuple_of_contents is length 1, it is inserted into
    cell directly. Otherwise, it is rendered as an unorderd list.
    '''
    for cell in cells:
        kl = cell[0]
        if len(cell[1]) == 1:
            line('td', cell[1][0], klass=kl)
        else:
            with tag('td', klass=kl):
                with tag('ul'):
                    for row in cell[1]:
                        line('li', row)


def as_tokens(points):
    tokens = []
    points = int(points)
    while points:
        for token in (10, 5, 1):
            if token <= points:
                tokens.append(token)
                points -= token
                break
    return tokens


def colored(card_name):
    '''Returns the card name with certain keywords wrapped in a <span>'''
    keywords = (
            'Alien',
            'Uplift',
            'Rebel',
            'Terraforming',
            'Anti-Xeno',
            'Xeno',
            'Imperium',
            )

    present = set()
    for kw in keywords:
        if kw in card_name and not any(kw in p for p in present):
            present.add(kw)
            card_name = card_name.replace(kw,
                '<span class="colored {0}">{1}</span>'.format(kw.lower(), kw))

    return card_name


def render_changes(changes):
    if not any(changes.values()):
        return

    with tag('ul'):
        if changes['explored']:
            with tag('svg', klass="long-icon"):
                with tag('g', transform="scale(0.75)"):
                    doc.stag('use', ('xlink:href', '#explore'))
                    text_id = '#number-%s' % changes['explored']
                    doc.stag('use', ('xlink:href', text_id))

                    doc.stag('use', ('xlink:href', '#card'), x=23)
                    text_id = '#number-%s' % changes['cards']
                    doc.stag('use', ('xlink:href', text_id), x=23)
        if changes['lost']:
            with tag('li'):
                doc.asis(colored(changes['lost']))
        if changes['placed']:
            with tag('li'):
                doc.asis(colored(changes['placed']))
        if changes['points']:
            for token in as_tokens(changes['points']):
                with tag('svg', klass="icon"):
                    symbol_id = 'hexagon-%s' % token
                    doc.stag('use', ('xlink:href', '#hexagon'), klass=symbol_id)
        if changes['cards'] and not changes['explored']:
            with tag('svg', klass="icon"):
                doc.stag('use', ('xlink:href', '#card'))
                doc.stag('use', ('xlink:href', '#number-%s' % changes['cards']),
                        )

    # Putting a couple of icons inside a single <svg> tag is more trouble than
    # it's worth. Probably the cleanest way is --icon-width CSS variable
    # and using translate on subsequent icons.
    if changes['produced']:
        for good in changes['produced']:
            with tag('svg', klass="icon"):
                doc.stag('use', ('xlink:href', '#good'), klass=good)


#BUG: displays info from the start of the used phase, not end of round
def render_bar_graph(players, phase_nr):
    with tag('ul', klass='bar-graph'):
        for player in reversed(sorted(players, key=lambda x: len(x.get_VP_bar(phase_nr)))):
            with tag('li'):
                total = ' {0}'.format(str(len(player.get_VP_bar(phase_nr))))
                line('span', player.get_VP_bar(phase_nr), klass=player.get_color())
                text(total)



def render_military_circle(content, klass):
    with tag('svg', klass="icon"):
        doc.stag('use', ('xlink:href', '#military'), klass=klass)

        plus = '+' if int(content) >= 0 else ''
        with tag('text', ('text-anchor', 'middle'), x="9", y="17", fill="red"):
            text(plus + content)


def render_military(player, phase_nr):
    for l in player.get_military(player.get_tableau(phase_nr)):
        target, min_str, max_str = l
        if target != 'normal':
            text('/')
        min_str = str(min_str)
        max_str = str(max_str)

        render_military_circle(min_str, target)
        if max_str > min_str:
            text('-')
            render_military_circle(max_str, target)


def render_settle_discounts(player, phase_nr):
    for l in player.get_settle_discounts(player.get_tableau(phase_nr)):
        reduced, power = l
        if not power:
            continue
        with tag('svg', klass="icon"):
            doc.stag('use', ('xlink:href', '#settle-discount'), klass=reduced)
            with tag('text', ('text-anchor', 'middle'), x="9", y="17", fill="black"):
                text('-{0}'.format(power))


def render_settle_bonuses(player, phase_number):
    with tag('ul'):
        with tag('li'):
            render_military(player, phase_number)
        with tag('li'):
            render_settle_discounts(player, phase_number)



def produce_report(game):
    with tag('html'):
        with tag('meta'):
            doc.stag('link', rel="stylesheet", href="style.css")
        with tag('body'):
            doc.asis('\n'.join(open('defs.svg', 'r').readlines()))
            with tag('ul'):
                for message in game.information:
                    line('li', message)
            for rnd in game.rounds:
                title_id = 'title-{0}'.format(rnd.number)
                line('h2', 'Round %s' % rnd.number, target=title_id)
                parent_id = 'table-{0}'.format(rnd.number)
                with tag('table', id=parent_id):
                    with tag('tr'):
                        with tag('td'):
                            line('a', 'Show bonuses', href='#' + parent_id)
                            line('a', 'Hide bonuses', klass='hidden', href='#' + title_id)
                        render_cells(rnd.get_header(game.players))
                    with tag('tr', klass='hidden'):
                        line('td', 'phase bonuses')
                        for pl in game.players:
                            with tag('td'):
                                render_settle_bonuses(pl, rnd.phases[0].nr)
                    for phase in rnd.phases:
                        with tag('tr'):
                            line('td', ROMAN[phase.name])
                            for player in game.players:
                                klass = ''
                                if player.name in rnd.phase_played_by(phase):
                                    klass = player.get_color()
                                with tag('td', klass=klass):
                                    render_changes(player.get_changes(phase.nr))
                render_bar_graph(game.players, phase.nr)
                vp_taken = 0
                for player in game.players:
                    vp_taken += len(player.get_VP_bar(phase.nr).strip('c?'))
                vp_left = 12 * len(game.players) - vp_taken
                text('Tokens left: {0}'.format(vp_left))


    output = open('report.html', 'w')
    print("Generating 'report.html' ...")
    print(indent(doc.getvalue()), file=output)

