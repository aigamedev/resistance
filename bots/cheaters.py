import random
import inspect
import itertools

from player import Bot
from intermediate import Simpleton


__all__ = ['RandomCheater', 'LogicalCheater']


# RES_CHEAT_RATIO = 0.7
RES_CORRECT_DOWNVOTE = 0.7
RES_CORRECT_UPVOTE = 0.7
RES_CORRECT_SELECTION = 0.7

SPY_CHEAT_RATIO = 0.7


def permutations(config):
    """Returns unique elements from a list of permutations."""
    return list(set(itertools.permutations(config)))


class RandomCheater(Bot):
    """An AI that can hack the current game implementation and cheat
    randomly a specified percentage of the time."""

    @classmethod
    def cheat_SetRate(cls, res, spy):
        global RES_CHEAT_RATIO 
        RES_CHEAT_RATIO = res
        global SPY_CHEAT_RATIO 
        SPY_CHEAT_RATIO = spy

    def cheat_GetSpies(self):
        """Grab the game state from the stack, and lookup the spies using the
        inspection module.  This code was adapted from Tom Schaul's tests."""
        spies = []
        f = inspect.stack()[2]
        for game in [v for v in f[0].f_locals.values() if hasattr(v, 'bots')]:
            for b in game.bots:
                spies.extend([p for p in self.players if b == p and b.spy])
            break
        del f
        return set(spies)

    def onGameRevealed(self, players, spies):
        self.players = players
        self.spies = spies or self.cheat_GetSpies()

    def getSpies(self, config):
        return set([player for player, spy in zip(self.others(), config) if spy])

    def getResistance(self, config):
        return [player for player, spy in zip(self.others(), config) if not spy]

    def correct(self):
        return random.random() <= (SPY_CHEAT_RATIO if self.spy else RES_CHEAT_RATIO)

    def cheat_Select(self, spied, count):
        if not spied:
            # Pick either one or two spies for the mission.
            team = random.sample(list(self.spies), random.choice([1,2]))
        else:
            team = []
        # Then fill the rest with random operatives. 
        operatives = set(self.players) - self.spies
        team.extend(random.sample(list(operatives), count - len(team)))
        return team

    def select(self, players, count):
        """A spy selects a team with spies CHEAT_RATIO of the time, and a
        resistance selects no spies CHEAT_RATIO of the time."""

        return self.cheat_Select(self.correct(), count)

    def cheat_Vote(self, spied):
        if self.correct():
            self.log.info("Voting %s, the correct decision." % (not spied))
            return not spied
        else:
            self.log.info("Voting %s, the incorrect decision." % (spied))
            return spied

    def vote(self, team): 
        """A spy votes up teams with spies CHEAT_RATIO of the time, a resistance
        votes down teams without spies CHEAT_RATIO of the time."""

        spied = set(team) & self.spies
        return self.cheat_Vote(bool(spied))

    def sabotage(self):
        return True 


class LogicalCheater(Simpleton):

    cheat           = RandomCheater.__dict__['correct']
    cheat_Select    = RandomCheater.__dict__['cheat_Select']
    cheat_Vote      = RandomCheater.__dict__['cheat_Vote']
    cheat_GetSpies  = RandomCheater.__dict__['cheat_GetSpies']

    def onGameRevealed(self, players, spies):
        super(LogicalCheater, self).onGameRevealed(players, spies)
        self.spies = spies or self.cheat_GetSpies()

    def _vote(self, team):
        """Let the logical reasoning of Simpleton filter out the clearly bad
        choices, then make a randomly cheating vote if necessary."""
        return RandomCheater.__dict__['vote'](self, team) 

    def select(self, players, count):
        while True:
            team = RandomCheater.__dict__['select'](self, players, count)
            if self._acceptable(team):
                break
        return team

