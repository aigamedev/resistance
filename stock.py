import random

from player import Player


class RandomPlayer(Player):

    def __init__(self, index, spy):
        Player.__init__(self, "Random", index, spy)

    def select(self, players, count):
        return random.sample(players, count)

    def vote(self, team, leader, tries): 
        return random.choice([True, False])

    def sabotage(self):
        if self.spy:
            return random.choice([True, False])
        else:
            return False


class SimplePlayer(Player):
    
    def __init__(self, index, spy):
        Player.__init__(self, "Simple", index, spy)
        # print "Playing at position %i." % (index)

    def reveal(self, spies):
        # print "Spies are %s." % (spies)
        pass

    def select(self, players, count):
        # print "Selecting %i players from %s." % (count, players)
        return random.sample(players, count)

    def vote(self, team, leader, tries): 
        # print "Voting for players %s selected by %s." % (team, leader)
        return random.choice([True, False])

    def sabotage(self):
        return self.spy

