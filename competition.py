#!/usr/bin/env python
# -*- coding: utf-8 -*-
import importlib
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
        self.spyVoted = Variable()
        self.spySelected = Variable()
        self.selections = Variable()

    def total(self):
        return Variable(
            self.resWins.total + self.spyWins.total,
            self.resWins.samples + self.spyWins.samples
            )


class CompetitionRound(Game):

    def onPlayerVoted(self, player, vote, leader, team):
        global statistics
        if player.spy:
            return

        spies = [t for t in team if t.spy]

        statistics.setdefault(player.name, CompetitionStatistics())
        s = statistics[player.name]
        # When there are no spies, we expect support.
        if not spies:    
            s.votesRes.sample(int(vote))
        # For missions with spies, we expect down vote.
        else:
            s.votesSpy.sample(int(not vote))

        # Spies on the mission hope to be not detected.
        for spy in spies:
            statistics.setdefault(spy.name, CompetitionStatistics())
            s = statistics[spy.name]
            s.spyVoted.sample(int(vote))
   
    def onPlayerSelected(self, player, team):
        global statistics
        if player.spy:
            return

        spies = [t for t in team if t.spy]
        statistics.setdefault(player.name, CompetitionStatistics())
        statistics[player.name].selections.sample(int(len(spies) == 0))

        for bot in self.bots:
            statistics.setdefault(bot.name, CompetitionStatistics())
            s = statistics[bot.name]
            if bot.spy:
                s.spySelected.sample(int(bot in team))


class CompetitionRunner(object):

    def __init__(self, competitors, rounds = 10000):
        self.competitors = competitors
        self.rounds = rounds
        self.games = [] 

    def pickPlayersForRound(self):
        # Only one instance of each bot per game, assumes more than five.
        # return random.sample(self.competitors, 5)
        
        # Multiple possible bot instances per game, works for any number.
        return [random.choice(self.competitors) for x in range(0,5)] 

    def main(self):
        names = [bot.__name__ for bot in self.competitors]
        for bot in self.competitors:
            if hasattr(bot, 'onCompetitionStarting'):
                bot.onCompetitionStarting(names)

        for i in range(1,self.rounds+1):
            if i % 2000 == 0: print >>sys.stderr, 'o'
            elif i % 50 == 0: print >>sys.stderr, '.',

            self.play(CompetitionRound, self.pickPlayersForRound())

    def play(self, GameType, players, channel = None):
        g = GameType(players)
        g.channel = channel
        self.games.append(g)
        g.run()
        self.games.remove(g)

        for b in g.bots:
            statistics.setdefault(b.name, CompetitionStatistics())
            s = statistics.get(b.name)
            if b.spy:
                s.spyWins.sample(int(not g.won))
            else:
                s.resWins.sample(int(g.won))
        return g

    def echo(self, *args):
        print ' '.join([str(a) for a in args])

    def show(self):
        global statistics

        print "\n",
        for bot in self.competitors:
            if hasattr(bot, 'onCompetitionFinished'):
                bot.onCompetitionFinished()

        if len(statistics) == 0:
            return

        self.echo("SPIES\t\t\t\t(voted,\t\tselected)")
        for s in sorted(statistics.items(), key = lambda x: x[1].spyWins.estimate(), reverse = True):
            self.echo(" ", '{0:<16s}'.format(s[0]), s[1].spyWins, "\t", s[1].spyVoted, "\t", s[1].spySelected)

        self.echo("RESISTANCE\t\t\t(vote,\t\tselect)")
        for s in sorted(statistics.items(), key = lambda x: x[1].resWins.estimate(), reverse = True):
            self.echo(" ", '{0:<16s}'.format(s[0]), s[1].resWins, "\t", s[1].votesRes, s[1].votesSpy, "\t", s[1].selections)

        self.echo("TOTAL")
        for s in sorted(statistics.items(), key = lambda x: x[1].total().estimate(), reverse = True):
            self.echo(" ", '{0:<16s}'.format(s[0]), s[1].total())
        self.echo("")

        statistics = {}


def getCompetitors(argv):
    competitors = []
    for request in argv:
        if '.' in request:
            filename, classname = request.split('.')
        else:
            filename, classname = request, None

        module = importlib.import_module(filename)
        if classname:
            competitors.append(getattr(module, classname))
        else:
            for b in dir(module):
                if b.startswith('__') or b == 'Bot': continue
                cls = getattr(module, b)
                if hasattr(cls, 'sabotage'):
                    competitors.append(cls)
    return competitors

if __name__ == '__main__':
    if len(sys.argv) <= 2:
        print 'USAGE: competition.py 10000 file.BotName [...]'
        sys.exit(-1)

    competitors = getCompetitors(sys.argv[2:])
    runner = CompetitionRunner(competitors, int(sys.argv[1]))
    try:
        runner.main()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        runner.show()

