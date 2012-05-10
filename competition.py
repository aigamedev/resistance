import random

from resistance import Game
from stock import RandomPlayer, SimplePlayer


competitors = [RandomPlayer, SimplePlayer]
statistics = {}


for i in xrange(0,10000):
    players = [random.choice(competitors) for x in xrange(0,5)]
    g = Game(players)
    g.run()   

