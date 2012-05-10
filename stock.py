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
        self.spies = []
        # print "Playing at position %i." % (index)

    def reveal(self, spies):
        self.spies = spies
        # print "Spies are %s." % (spies)

    def select(self, players, count):
        # print "Selecting %i players from %s." % (count, players)
        me = [p for p in players if p.index == self.index]

        if self.spy:
            others = [p for p in players if p not in self.spies]
            return me + random.sample(others, count-1)
        else:
            others = [p for p in players if p.index != self.index]
            return me + random.sample(others, count-1)

    def vote(self, team, leader, tries): 
        # print "Voting for players %s selected by %s." % (team, leader)
        if self.spy:
            return len([p for p in team if p in self.spies])
        else:
            if tries >= 4:
                return True
            return random.choice([True, False])

    def sabotage(self):
        return self.spy

