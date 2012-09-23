import random
import itertools

from player import Bot


def permutations(config):
    """Returns unique elements from a list of permutations."""
    return list(set(itertools.permutations(config)))


class Bounder(Bot):
    """Idea of upper and lower bounds shamelessly stolen from Peter Cowling. :-)
       This is an implementation of his bot for comparison and modeling."""

    def onGameRevealed(self, players, spies):
        self.players = players
        self.spies = spies

        # The set of possible assignments around the table, for:
        #   - PESSIMISTIC: All teams except those 100% proven to be spies.
        self.pessimistic = permutations([True, True, False, False])
        #   - OPTIMISTIC: The teams we don't suspect to be spies without guarantees.
        self.optimistic = permutations([True, True, False, False])

    def select(self, players, count):
        if self.optimistic:
            config = random.choice(self.optimistic)
        else:
            assert len(self.pessimistic) > 0
            config = random.choice(self.pessimistic)
        return [self] + random.sample(self.getResistance(config), count-1)
    
    def vote(self, team): 
        # As a spy, vote for all missions that include one spy!
        # TODO: Vote up as long as we're compatible with one or
        # more configurations?
        # if self.spy:
        #    return len([p for p in team if p in self.spies]) > 0

        # Then determine if this is an acceptable thing to vote for...
        def acceptable(configurations, optimistic):
            current = [c for c in configurations if self._validate(c, team, 0, optimistic)]
            return bool(len(current) > 0)

        # Try our best-case options first, otherwise fall back...
        if self.optimistic:
            return acceptable(self.optimistic, True)
        elif self.pessimistic:
            return acceptable(self.pessimistic, False)
        else:
            return random.choice([True, False])

    def onVoteComplete(self, votes):
        # Speculation about votes does not guarantee anything, so we exclude
        # it here. See git history for details, or other bots like Invalidator.
        pass

    def getSpies(self, config):
        return [player for player, spy in zip(self.others(), config) if spy]

    def getResistance(self, config):
        return [player for player, spy in zip(self.others(), config) if not spy]

    def _validate(self, config, team, sabotaged, optimistic):
        spies = [s for s in team if s in self.getSpies(config)]
        if optimistic:
            return len(spies) == sabotaged
        else:
            return len(spies) >= sabotaged

    def onMissionComplete(self, sabotaged):
        if self.spy:
            return

        self.optimistic = [c for c in self.optimistic if self._validate(c, self.game.team, sabotaged, True)]
        self.pessimistic = [c for c in self.pessimistic if self._validate(c, self.game.team, sabotaged, False)]

    def sabotage(self):
        return True 

