import random
import itertools

from player import Bot


def permutations(config):
    """Returns unique elements from a list of permutations."""
    return list(set(itertools.permutations(config)))


class Suspicious(Bot):
    """Simplification of Invalidator, one of the strongest AIs against bots from
    the 2012 competition.
    """

    def oracle_selection(self, config):
        """Rate teams chosen by the leader, assuming a particular configuration.
        Zero means the selection is not suspicious, and positive values indicate
        higher suspicion levels."""

        all_spies = self.getSpies(config)
        team_spies = [s for s in self.game.team if s in all_spies]
        if self.game.leader in all_spies and len(team_spies) == 0:
            return 1.0, [(1.0, "%s, assuming a spy, did not pick a mission with spies.")] 
        if len(team_spies) >= 2:
            return 0.5, [(0.5, "%s, assuming a spy, picked a mission with two spies!")]
        return 0.0, []

    def oracle_voting(self, config, votes):
        """Assess the votes of a player, assuming a particular configuration.
        Zero means no suspicious activity and positive values indicate high
        suspicion levels."""

        all_spies = self.getSpies(config)
        team_spies = [s for s in self.game.team if s in all_spies]

        score, factors = 0.0, []        
        for p, v in zip(self.game.players, votes):            
            if p in all_spies and v and not team_spies:
                score += 1.0
                factors.append((1.0, "%s, assuming a spy, voted for a mission that had no assumed spies." % (p.name)))
            if p in all_spies and not v and len(team_spies) == 1:
                score += 1.0
                factors.append((1.0, "%s, assuming a spy, did not vote a mission that had an assumed spy." % (p.name)))
            if p in all_spies and v and len(team_spies) > 1:
                score += 0.5
                factors.append((0.5, "%s, assuming a spy, voted a mission with multiple assumed spy." % (p.name)))
            if self.game.tries == 5 and p not in all_spies and not v:
                score += 2.0
                factors.append((2.0, "%s, assuming resistance, did not approve the final try!" % (p.name)))
            if p not in all_spies and len(self.game.team) == 3 and p not in self.game.team and v:
                score += 2.0
                factors.append((2.0, "%s, assuming a resistance, voted for a mission without self!" % (p.name)))
        return score, factors

    def oracle_sabotages(self, config, sabotaged):
        spies = [s for s in self.game.team if s in self.getSpies(config)]
        score = max(0, sabotaged - len(spies)) * 100.0
        if score > 0.0:
            return score, [(score, "%s participated in a mission that had %i sabotages." % (self.game.team, sabotaged))]
        else:
            return 0.0, []

    def adviser_vote(self, team):
        if self.spy:
            spies = [s for s in team if s in self.spies]
            if len(spies) > 0 and (self.game.losses == 2 or self.game.wins == 2):
                self.log.debug("Taking a risk since the game could finish.")
                return True
            if self.game.tries == 5:
                self.log.debug("Voting up the last mission because Resistance would.")
                return False
            if len(team) == 3:
                self.log.debug("Voting strongly about this team because it's size 3!")
                return self in team
        else:
            if self.game.leader == self:
                self.log.debug("Approving my own mission selection.")
                return True
            if self.game.tries == 5:
                self.log.debug("Voting up the last mission to avoid failure.")
                return True
        return None

    def onGameRevealed(self, players, spies):
        self.spies = spies

        # Count the number of times each configuration was apparently invalidated.
        self.invalidations = {k: 0.0 for k in permutations([True, True, False, False])}
        # This is used to help justify decisions in hybrid human/bot matches.
        self.factors = {k: [] for k in permutations([True, True, False, False])}

    def likeliest(self):
        ranked = sorted(self.invalidations.keys(), key = lambda c: self.invalidations[c])
        invalidations = self.invalidations[ranked[0]]
        return [r for r in ranked if self.invalidations[r] == invalidations]

    def select(self, players, count):
        likely = self.likeliest()
        config = random.choice(likely)
        return [self] + random.sample(self.getResistance(config), count-1)

    def onTeamSelected(self, leader, team):
        for config in self.invalidations:
            score, factors = self.oracle_selection(config)
            self.invalidations[config] += score
            self.factors[config].extend(factors)

    def vote(self, team): 
        advice = self.adviser_vote(team)
        if advice:
            return advice

        # Count the scores of configurations where no spies are selected. 
        scores, matches = [], []
        for config in self.invalidations:
            if len([s for s in team if s in self.getSpies(config)]) == 0:
                scores.append(self.invalidations[config])
                matches.append(config)
        if not scores:
            return False

        # Establish whether this meets the criteria for selection...
        threshold = min(self.invalidations.values())
        return min(scores) <= threshold

    def onVoteComplete(self, votes):
        for config in self.invalidations:
            score, factors = self.oracle_voting(config, votes)
            self.invalidations[config] += score
            self.factors[config].extend(factors)

    def getSpies(self, config):
        assert len(config) == 4
        assert all([type(c) is bool for c in config])
        return set([player for player, spy in zip(self.others(), config) if spy])

    def getResistance(self, config):
        assert len(config) == 4
        assert all([type(c) is bool for c in config])
        return set([player for player, spy in zip(self.others(), config) if not spy])

    def onMissionComplete(self, sabotaged):
        for config in self.invalidations:
            score, factors = self.oracle_sabotages(config, sabotaged)
            self.invalidations[config] += score
            self.factors[config].extend(factors)

    def sabotage(self):
        if self.game.wins == 2 or self.game.losses == 2:
            self.log.debug("Sabotaging since there's a chance of winning or losing.")
            return True

        if len(self.game.team) == 2 and self.game.turn == 1:
            self.log.debug("Missions of size two are too risky...")
            return False

        spies = [s for s in self.game.team if s in self.spies]
        if len(spies) > 1:
            self.log.debug("Too many spies, can't coordinate!")
            return False

        self.log.debug("Other checks failed, why not sabotage since I'm a spy?")
        return True
