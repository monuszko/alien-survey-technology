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
            line('li', changes['lost'], klass='strike')
        if changes['placed']:
            line('li', changes['placed'])
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


def render_military(player, phase_nr):
    for l in player.get_military(player.get_tableau(phase_nr)):
        target, always, potential = l
        always = str(always)
        potential = str(potential)
        with tag('span', klass='military ' + target):
            sign = '+' if int(always) > 0 else '-'
            tmp = '({0}{1})'.format(sign, always)
            if potential > always:
                tmp = tmp.replace(always, always + '/' + potential)
            text(tmp)


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
                                render_military(pl, rnd.phases[0].nr)
                    for phase in rnd.phases:
                        with tag('tr'):
                            line('td', ROMAN[phase.name])
                            for player in game.players:
                                klass = ''
                                if player.name in rnd.phase_played_by(phase):
                                    klass = player.get_color()
                                with tag('td', klass=klass):
                                    render_changes(player.get_changes(phase.nr))
                render_bar_graph(game.players, phase.nr + 1)
                vp_taken = 0
                for player in game.players:
                    vp_taken += len(player.get_VP_bar(phase.nr).strip('c?'))
                vp_left = 12 * len(game.players) - vp_taken
                text('Tokens left: {0}'.format(vp_left))


    output = open('report.html', 'w')
    print("Generating 'report.html' ...")
    print(indent(doc.getvalue()), file=output)

