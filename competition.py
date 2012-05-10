import random

from resistance import Game
from stock import RandomPlayer, SimplePlayer


competitors = [RandomPlayer, SimplePlayer]
statistics = {}


class Statistic:
    def __init__(self):
        self.resistance = 0
        self.spies = 0
        self.plays = 0

    def __repr__(self):
        return "(RESISTANCE %0.1f%%, SPY %0.1f%%)" % (float(self.resistance) * 100.0 / float(self.plays), float(self.spies) * 100.0 / float(self.plays))

GAMES = 10000

for i in range(0,GAMES):
    players = [random.choice(competitors) for x in range(0,5)]
    g = Game(players)
    g.run()

    win = bool(g.wins >= 3)
    for p in g.players:
        s = statistics.get(p.name, Statistic())
        s.plays += 1
        statistics[p.name] = s

        if p.spy and not win:
            s = statistics.get(p.name, Statistic())
            s.spies += 1
            statistics[p.name] = s
        if not p.spy and win:
            s = statistics.get(p.name, Statistic())
            s.resistance += 1
            statistics[p.name] = s

print statistics
