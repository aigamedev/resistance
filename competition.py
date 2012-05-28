# -*- coding: utf8 -*-
import random
import sys

from game import Game
from util import Variable

statistics = {}


class CompetitionStatistics:
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


class CompetitionRunner(object):

    def __init__(self, competitors, rounds = 10000):
        self.competitors = competitors
        self.rounds = rounds

    def pickPlayersForRound(self):
        # Only one instance of each bot per game, assumes more than five.
        # return players = random.sample(competitors, 5)
        
        # Multiple possible bot instances per game, works for any number.
        return [random.choice(self.competitors) for x in range(0,5)] 

    def main(self):
        for i in range(1,self.rounds+1):
            if i % 2500 == 0: print >>sys.stderr, 'o'
            elif i % 500 == 0: print >>sys.stderr, '.',

            g = CompetitionRound(self.pickPlayersForRound())
            for b in g.bots:
                statistics.setdefault(b.name, CompetitionStatistics())

            g.run()
            for b in g.bots:
                s = statistics.get(b.name)

                s.spyWins.sample(int(b.spy and not g.won))
                s.resWins.sample(int(not b.spy and g.won))

    def show(self):
        print "\nSPIES"
        for s in sorted(statistics.items(), key = lambda x: -x[1].spyWins.estimate()):
            print " ", s[0], "\t", s[1].spyWins

        print "\nRESISTANCE\t\t\t(vote,\t\tselect)" 
        for s in sorted(statistics.items(), key = lambda x: -x[1].resWins.estimate()):
            print " ", s[0], "\t", s[1].resWins, "\t\t", s[1].votesRes, s[1].votesSpy, "\t", s[1].selections

        print "\nTOTAL" 
        for s in sorted(statistics.items(), key = lambda x: -x[1].total().estimate()):
            print " ", s[0], "\t", s[1].total()


if __name__ == '__main__':
    import importlib
    
    if len(sys.argv) <= 2:
        print 'USAGE: competition.py 10000 file.BotName [...]'
        sys.exit(-1)

    competitors = []
    for filename, classname in [s.split('.') for s in sys.argv[2:]]:
        module = importlib.import_module(filename)
        competitors.append(getattr(module, classname))

    runner = CompetitionRunner(competitors, int(sys.argv[1]))
    runner.main()
    runner.show()

