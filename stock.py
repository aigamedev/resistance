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

    def reveal(self, players, spies):
        self.players = players
        self.spies = spies

    def select(self, players, count):
        me = [p for p in players if p.index == self.index]

        # As a spy, pick myself and others who are not spies.
        if self.spy:
            others = [p for p in players if p not in self.spies]
            return me + random.sample(others, count-1)
        # As resistance, pick myself also and others randomly.
        else:
            others = [p for p in players if p.index != self.index]
            return me + random.sample(others, count-1)

    def vote(self, team, leader, tries): 
        if self.spy:
            return len([p for p in team if p in self.spies])
        else:
            if tries >= 4:
                return True
            return random.choice([True, False])

    def onVoteComplete(self, players, votes, team):
        self.team = team
    
    def onMissionComplete(self, team, sabotaged):
        # Forget this failed team so we don't pick it!
        if sabotaged or self.spy:
            self.team = None

    def sabotage(self):
        if not self.spy:
            return False
        
        if len(self.team) == 2:
            return random.choice([True, False])
        else:
            return True

