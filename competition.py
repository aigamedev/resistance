import random

from resistance import Game
from stock import RandomPlayer, SimplePlayer


competitors = [RandomPlayer, SimplePlayer]
statistics = {}


# Only one game being run currently!
for i in range(0,1):
    players = [random.choice(competitors) for x in range(0,5)]
    g = Game(players)
    g.run()

    if g.wins >= 3:
        print "\nRESISTANCE WINS!"
    else:
        print "\nSPIES WIN."

