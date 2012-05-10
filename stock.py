import random

from resistance import Player


class RandomPlayer(Player):

    def __init__(self, spy):
        Player.__init__(self, "Random", spy)

    def select(self, players, count):
        return random.sample(players, count)

    def vote(self, players): 
        return random.choice([True, False])

    def sabotage(self):
        if self.spy:
            return random.choice([True, False])
        else:
            return False


class SimplePlayer(Player):
    
    def __init__(self, spy):
        Player.__init__(self, "Simple", spy)

    def select(self, players, count):
        return random.sample(players, count)

    def vote(self, players): 
        return random.choice([True, False])

    def sabotage(self):
        return self.spy

