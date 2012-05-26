import random

from player import Bot 


class Paranoid(Bot):
    """An AI bot that tends to vote everything down!"""

    def select(self, players, count):
        return [self] + random.sample(self.others(), count - 1)

    def vote(self, team): 
        return bool(self == self.game.leader)

    def sabotage(self, team):
        return True 


class Hippie(Bot):
    """An AI bot that's OK with everything!"""

    def select(self, players, count):
        return [self] + random.sample(self.others(), count - 1)

    def vote(self, team): 
        return True

    def sabotage(self, team):
        return True


class RandomBot(Bot):
    """An AI bot that's perhaps never played before and doesn't
    understand the rules very well!"""

    def select(self, players, count):
        return random.sample(players, count)

    def vote(self, team): 
        return random.choice([True, False])

    def sabotage(self, team):
        return random.choice([True, False])


class Deceiver(Bot):
    """A tricky bot that's good at pretending being resistance as a spy."""

    def onGameRevealed(self, players, spies):
        self.spies = spies

    def select(self, players, count):
        return [self] + random.sample(self.others(), count - 1)

    def vote(self, team): 
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
        return len(team) > 2


class RuleFollower(Bot):
    """Rule-based AI that does a pretty good job of capturing
    common sense play rules for THE RESISTANCE."""

    def onGameRevealed(self, players, spies):
        self.spies = spies

    def select(self, players, count):
        return [self] + random.sample(self.others(), count - 1)

    def vote(self, team): 
        # Both types of factions have constant behavior on the last try.
        if self.game.tries == 5:
            return not self.spy
        # Spies select any mission with one or more spies on it.
        if self.spy:
            return len([p for p in team if p in self.spies]) > 0
        # If I'm not on the team, and it's a team of 3...
        if len(team) == 3 and not self in team:
            return False
        return True

    def sabotage(self, team):
        return True

