# -*- coding: utf8 -*-
import random

from game import Game
from bots import RandomBot, RuleFollower, ParanoidBot, HippieBot, Deceiver
from aigd import LogicalBot, Statistician 

competitors = [RuleFollower, LogicalBot, Statistician, Deceiver, ParanoidBot, HippieBot, RandomBot]

statistics = {}


class Statistic:
    def __init__(self):
        self._resistance = 0
        self._spies = 0
        self.plays = 0

    def total(self):
        return float(self._resistance + self._spies) / float(self.plays)

    def spies(self):
        return float(self._spies) / float(self.plays)

    def resistance(self):
        return float(self._resistance) / float(self.plays)


GAMES = 50000

for i in range(1,GAMES):
    if i % 10000 == 0: print 'o'
    elif i % 2500 == 0: print '.',

    players = [random.choice(competitors) for x in range(0,5)]
    # players = random.sample(competitors, 5)
    g = Game(players)
    g.run()

    win = bool(g.wins >= 3)
    for p in g.bots:
        s = statistics.get(p.name, Statistic())
        s.plays += 1
        statistics[p.name] = s

        if p.spy and not win:
            s = statistics.get(p.name, Statistic())
            s._spies += 1
            statistics[p.name] = s
        if not p.spy and win:
            s = statistics.get(p.name, Statistic())
            s._resistance += 1
            statistics[p.name] = s


print "\nSPIES" 
for s in sorted(statistics.items(), key = lambda x: -x[1].spies()):
    print " ", s[0], "\t", s[1].spies() * 100.0

print "\nRESISTANCE" 
for s in sorted(statistics.items(), key = lambda x: -x[1].resistance()):
    print " ", s[0], "\t", s[1].resistance() * 100.0

print "\nTOTAL" 
for s in sorted(statistics.items(), key = lambda x: -x[1].total()):
    print " ", s[0], "\t", s[1].total() * 100.0

