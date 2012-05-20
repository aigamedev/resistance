import random

from player import Bot 


class Paranoid(Bot):

    def select(self, players, count):
        others = [p for p in players if p != self]
        return [self] + random.sample(others, count - 1)

    def vote(self, team, leader): 
        return bool(self == leader)

    def sabotage(self, team):
        return self.spy 


class Hippie(Bot):

    def select(self, players, count):
        others = [p for p in players if p != self]
        return [self] + random.sample(others, count - 1)

    def vote(self, team, leader): 
        return True

    def sabotage(self, team):
        return self.spy


class RandomBot(Bot):

    def select(self, players, count):
        return random.sample(players, count)

    def vote(self, team, leader): 
        return random.choice([True, False])

    def sabotage(self, team):
        if self.spy:
            return random.choice([True, False])
        else:
            return False


class Deceiver(Bot):

    def onGameRevealed(self, players, spies):
        self.spies = spies

    def select(self, players, count):
        others = [p for p in players if p != self]
        return [self] + random.sample(others, count - 1)

    def vote(self, team, leader): 
        # Since a resistance would vote up the last mission...
        if self.game.tries == 5:
            return True
        # Spies select any mission with only one spy on it.
        if self.spy and len(team) == 2:
            return len([p for p in team if p in self.spies]) == 1
        # If I'm not on the team, and it's a team of 3...
        if len(team) == 3 and not self in team: 
            return False
        return True

    def sabotage(self, team):
        # Shoot down only missions with more than another person.
        if self.spy:
            return len(team) > 2
        return False


class RuleFollower(Bot):

    def onGameRevealed(self, players, spies):
        self.spies = spies

    def select(self, players, count):
        others = [p for p in players if p != self]
        return [self] + random.sample(others, count - 1)

    def vote(self, team, leader): 
        # Both types of factions have constant behavior on the last try.
        if self.game.tries == 5:
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

