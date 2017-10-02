from yattag import Doc, indent


doc, tag, text, line= Doc().ttl()


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


def render_changes(changes):
    # TODO: maybe empty strings wasn't a bright idea ?
    changes1 = any(changes[ch] for ch in ('lost', 'placed', 'content'))
    changes2 = any(ch for ch in changes['produced'].values())
    if not changes1 and not changes2:
        return

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


def render_bar_graph(bars):
    with tag('ul', klass='bar-graph'):
        for bar in bars:
            with tag('li'):
                line('span', bar[1], klass=bar[0])


def produce_report(rounds):
    with tag('html'):
        with tag('meta'):
            doc.stag('link', rel="stylesheet", href="style.css")
        with tag('body'):
            for rnd in rounds:
                title_id = 'title-{0}'.format(rnd.number)
                line('h2', 'Round %s' % rnd.number, target=title_id)
                parent_id = 'table-{0}'.format(rnd.number)
                with tag('table', id=parent_id):
                    with tag('tr'):
                        with tag('td'):
                            line('a', 'Show bonuses', href='#' + parent_id)
                            line('a', 'Hide bonuses', klass='hidden', href='#' + title_id)
                        render_cells(rnd.get_header())
                    with tag('tr', klass='hidden'):
                        line('td', 'phase bonuses')
                        for pl in rnd.phases[0].players:
                            line('td', pl.get_military())
                    for phase in rnd.phases:
                        with tag('tr'):
                            line('td', ROMAN[phase.name])
                            for player in phase.players:
                                klass = ''
                                if player.name in rnd.phase_played_by(phase):
                                    klass = player.get_color()
                                with tag('td', klass=klass):
                                    render_changes(player.get_changes())
                bars = rnd.get_bars()
                render_bar_graph(bars)
                vp_taken = sum(b[1].count('v') for b in bars)
                vp_left = 12 * len(phase.players) - vp_taken
                text('Tokens left: {0}'.format(vp_left))


    output = open('report.html', 'w')
    print("Generating 'report.html' ...")
    print(indent(doc.getvalue()), file=output)

