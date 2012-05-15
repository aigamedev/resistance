import random

from player import Bot 


class ParanoidBot(Bot):

    def __init__(self, index, spy):
        Bot.__init__(self, "Paranoid", index, spy)

    def select(self, players, count):
        me = [p for p in players if p.index == self.index]
        others = [p for p in players if p.index != self.index]
        return me + random.sample(others, count - 1)

    def vote(self, team, leader, tries): 
        return bool(self == leader)

    def sabotage(self, team):
        return self.spy 


class RandomBot(Bot):

    def __init__(self, index, spy):
        Bot.__init__(self, "Random", index, spy)

    def select(self, players, count):
        return random.sample(players, count)

    def vote(self, team, leader, tries): 
        return random.choice([True, False])

    def sabotage(self, team):
        if self.spy:
            return random.choice([True, False])
        else:
            return False


class RuleFollower(Bot):

    def __init__(self, index, spy):
        Bot.__init__(self, "RuleFollower", index, spy)

    def onGameRevealed(self, players, spies):
        self.spies = spies

    def select(self, players, count):
        others = [p for p in players if p != self]
        return [self] + random.sample(others, count - 1)

    def vote(self, team, leader, tries): 
        # Both types of factions have constant behavior on the last try.
        if tries >= 4:
            return not self.spy
        # Spies select any mission with one or more spies on it.
        if self.spy:
            return len([p for p in team if p in self.spies]) > 0
        # If I'm not on the team, and it's a team of 3...
        if len(team) == 3 and not self.index in [p.index for p in team]:
            return False
        return True

    def sabotage(self, team):
        return self.spy

