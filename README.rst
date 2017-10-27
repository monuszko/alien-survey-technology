Alien Survey Technology
=======================

Log visualizer for the card game *Race for the Galaxy*.
Newest version of *AST* always at https://github.com/monuszko/alien-survey-technology
*Keldon AI* is a free implentation of RftG, and *AST* requires it to run. The game
can be downloaded from http://keldon.net/rftg/, or
https://boardgamegeek.com/thread/1424631/upgrade-keldons-ai-version-095 for
the newer version.

.. contents::

Requirements
------------

``Alien Survey Technology`` currently requires ``python3`` and ``yattag``.

Purpose
-------

*Keldon AI* is a very good application and computer opponents are merciless.
However, the interface leaves a bit to be desired. At times it's not clear
what's happening and why. The game could be clearer about who played which
action and who gained how much in each phase. This is something that you may
miss while playing the computer version.

*Alien Survey Technology* exists to answer these questions. Staring at *Keldon
AI* logs to understand what and why an opponent played gets old fast.

Installation
------------

1. Unzip *Alien Survey Technology* to a directory of your choice.
2. Open the *Keldon AI* settings and enable ``.xml`` exports. Set the game to
   save logs in the *Alien Survey Technology* dir.
3. Enable all verbose logging options.
4. Copy ``cards.txt`` from the *Keldon AI* directory to the *AST* directory.

Usage
-----

Run ``visualizer.py``. It will open the most recent .xml log file. It will
spawn a file called ``report.html``.

Each cell shows how much a player gained in that phase.

Colored table cells (other than the header) indicate the player played that
phase himself. It makes it easy to see who benefitted from somebody else's
action - who outwitted whom.

Bars at the end of each round show total victory points. ``c`` stands for card,
``v`` are victory *tokens*. 6 cost developments are currently not implemented.

Known issues
------------

No support for goals, takeovers, prestige and some other mechanics from the
first arc. It would be best if someone familiar with it sent a patch.

Future plans
------------

* more ``.svg`` symbols.
* more graphs
* more control over which log is opened and where reports are saved.
* aggregate summary of player bonuses for each round. For sum of ``I`` bonuses,
  ``II``, ``III``, ``IV`` and ``V`` bonuses from all cards in the tableau.


Contributing
------------

SVG Tutorial:
https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial

Icon System with SVG Sprites:
https://css-tricks.com/svg-sprites-use-better-icon-fonts/

Styling SVG <use> Content with CSS:
https://tympanus.net/codrops/2015/07/16/styling-svg-use-content-css/

Author
------

Marek Onuszko (marek dot onuszko at gmail dot com).
https://github.com/monuszko/

