# -*- coding: utf8 -*-
import random
import sys

from game import Game
from util import Variable
from bots import RandomBot, RuleFollower, Paranoid, Hippie, Deceiver
from aigd import LogicalBot, Statistician 

competitors = [RuleFollower, LogicalBot, Statistician, Deceiver, Paranoid, Hippie, RandomBot]

statistics = {}


class Statistic:
    def __init__(self):
        self.resWins = Variable()
        self.spyWins = Variable()
        self.votesRes = Variable()
        self.votesSpy = Variable()
        self.selections = Variable()

    def total(self):
        return Variable(self.resWins.total + self.spyWins.total, self.resWins.samples)


class CompetitionRound(Game):
    
    def onPlayerVoted(self, player, vote, leader, team):
        global statistics
        if player.spy:
            return

        spies = [t for t in team if t.spy]
        s = statistics[player.name]
        # When there are no spies, we expect support.
        if not spies:    
            s.votesRes.sample(int(vote))
        # For missions with spies, we expect down vote.
        else:
            s.votesSpy.sample(int(not vote))
   
    def onPlayerSelected(self, player, team):
        global statistics
        if player.spy:
            return

        spies = [t for t in team if t.spy]
        statistics[player.name].selections.sample(int(len(spies) == 0))


GAMES = 10000

for i in range(1,GAMES+1):
    if i % 2500 == 0: print >>sys.stderr, 'o'
    elif i % 500 == 0: print >>sys.stderr, '.',

    players = [random.choice(competitors) for x in range(0,5)]
    # players = random.sample(competitors, 5)
    g = CompetitionRound(players)
    for p in g.bots:
        statistics.setdefault(p.name, Statistic())

    g.run()

    win = bool(g.state.wins >= 3)
    for p in g.bots:
        s = statistics.get(p.name, Statistic())

        s.spyWins.sample(int(p.spy and not win))
        s.resWins.sample(int(not p.spy and win))


print "\nSPIES" 
for s in sorted(statistics.items(), key = lambda x: -x[1].spyWins.estimate()):
    print " ", s[0], "\t", s[1].spyWins

print "\nRESISTANCE\t\t\t(vote,\t\tselect)" 
for s in sorted(statistics.items(), key = lambda x: -x[1].resWins.estimate()):
    print " ", s[0], "\t", s[1].resWins, "\t\t", s[1].votesRes, s[1].votesSpy, "\t", s[1].selections

print "\nTOTAL" 
for s in sorted(statistics.items(), key = lambda x: -x[1].total().estimate()):
    print " ", s[0], "\t", s[1].total()

