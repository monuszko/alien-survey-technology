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
                line('h2', 'Round %s' % rnd.number)
                with tag('table'):
                    with tag('tr'):
                        render_cells(rnd.get_header())
                    for phase in rnd.phases:
                        with tag('tr'):
                            line('td', ROMAN[phase.name])
                            for player in phase.players:
                                klass = ''
                                if player.name in rnd.phase_played_by(phase):
                                    klass = player.get_color()
                                with tag('td', klass=klass):
                                    render_changes(player.get_changes())
                render_bar_graph(rnd.get_bars())


    output = open('report.html', 'w')
    print("Generating 'report.html' ...")
    print(indent(doc.getvalue()), file=output)

