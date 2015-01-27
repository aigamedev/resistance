THE RESISTANCE AI
=================

Python framework for THE RESISTANCE board & card game, along with various AI bots submitted for the 2012 competition at the Game/AI Conference.

|Build Status|

----

Running Competitions
--------------------

Launch a competition with bots from a relative path as follows:
    python competition.py 1000 bots/beginners.py

Run a competition from a python module, assuming the path is set:
    PYTHONPATH=bots python competition.py 1000 beginners.Hippie beginners.Paranoid

These standalone competitions run without dependencies, and also run with PyPy_ for additional performance.

.. image:: docs/competition.png

The script outputs ranking tables with scores for resistance and spies separately as percentage of wins, then below they are combined.  The two `vote` columns track correct up-votes and correct down-votes, depending on whether it's spy or or resistance.  The `voted` column shows how often others supported a team including this player.  The `selected` column shown how often the player was selected, and `selection` tracks the picking of teams with or without spies (depending on role).


.. |Build Status| image:: https://travis-ci.org/aigamedev/resistance.png?branch=master
   :target: https://travis-ci.org/aigamedev/resistance

.. _PyPy: http://pypy.org/