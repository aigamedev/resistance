import random
from collections import defaultdict

from player import Bot 


class Variable(object):
    def __init__(self):
        self.total = 0
        self.samples = 0

    def sample(self, value):
        self.total += value
        self.samples += 1

    def estimate(self):
        if self.samples > 0:
            return float(self.total) / float(self.samples)
        else:
            return 0.5

    def __repr__(self):
        if self.samples:
            return "%0.2f%% (%i)" % ((100.0 * float(self.total) / float(self.samples)), self.samples)
        else:
            return "UNKNOWN"


class GlobalStatistics(object):
    def __init__(self):
        self.spy_VotesForSpy = Variable()
        self.spy_VotesForRes = Variable()
        self.spy_PicksSpy = Variable()
        self.spy_PicksSelf = Variable()
        self.res_VotesForSpy = Variable()
        self.res_VotesForRes = Variable()
        self.res_PicksSpy = Variable()
        self.res_PicksSelf = Variable()
        self.spy_Sabotage = Variable()

    def __repr__(self):
        return """
As Spy, VOTES:  Spy %s  Res  %s
        PICKS:  Spy %s  Self %s
        SABOTAGE    %s
As Res, VOTES:  Spy %s  Res  %s
        PICKS:  Spy %s  Self %s
""" % (self.spy_VotesForSpy, self.spy_VotesForRes, self.spy_PicksSpy, self.spy_PicksSelf, self.spy_Sabotage, self.res_VotesForSpy, self.res_VotesForRes, self.res_PicksSpy, self.res_PicksSelf)


class LocalStatistics(object):
    def __init__(self):
        self.probability = Variable()
        # Chances of being one of the two spies out of the other four are 50%.
        self.probability.sample(0.5) 

    def update(self, probability):
        self.probability.sample(probability)


class Statistician(Bot):

    global_statistics = defaultdict(GlobalStatistics)

    def onGameRevealed(self, players, spies):
        self.spies = spies
        self.players = players

        self.missions = []
        self.selections = []
        self.votes = []
        self.local_statistics = defaultdict(LocalStatistics)

    def select(self, players, count):
        # NOTE: The probability of each player depends on the team chosen.
        # As you pick players assuming they are not spies, the probabilities
        # should be updated here.
        team = [p for p in players if p.index == self.index]
        while len(team) < count:
            candidates = [p for p in players if p not in team]
            team.append(self._roulette(zip(candidates, [1.0 - self._estimate(p) for p in candidates])))
        return team

    def _roulette(self, candidates):
        total = sum([c[1] for c in candidates])
        current = 0.0
        threshold = random.uniform(0.0, total)
        for c in candidates:
            current += c[1]
            if current >= threshold:
                return c[0]
        assert False, "Could not perform roulete wheel selection."

    def vote(self, team):
        # Store this for later once we know the spies.
        self.selections.append((self.game.leader, team))

        # Hard coded if spy, could use statistics to check what to do best!
        if self.spy:
            return len([p for p in team if p in self.spies]) > 0

        total = sum([self._estimate(p) for p in team if p != self])
        alternate = sum([self._estimate(p) for p in self.players if p != self and p not in team])
        return bool(total <= alternate)

    def _estimate(self, player):
        return self.local_statistics[player.name].probability.estimate()

    def sabotage(self):
        return self.spy

    def onMissionComplete(self, sabotaged):
        # Store this information for later once we know the spies.
        self.missions.append((self.game.team[:], sabotaged))
        if self.spy:
            return

        # Update probabilities for this current game...
        others = [p for p in self.game.team if p != self]
        probability = float(sabotaged) / float(len(others))
        for p in others:
            self.local_statistics[p.name].update(probability)

        probability = 1.0 - float(sabotaged) / float(4 - len(others))
        for p in [p for p in self.players if p not in self.game.team]:
            self.local_statistics[p.name].update(probability)
    
    def onVoteComplete(self, votes):
        # Step 2) Store.
        self.votes.append((votes, self.game.team[:]))

        # Based on the voting, we can do many things:
        #   - Infer the probability of spies being on the team.
        #   - Infer the probability of spies being the voters.

        # Step 1) As resistance, run a bunch of predictions.
        # According to Bayes' Theorem:
        #   P(A|B) = P(B|A)  * P(A) / P(B)
        spied = bool(len([p for p in self.game.team if p in self.spies]) > 0)
                # or self._discard(team)
        if spied:
            for player, vote in zip(self.game.players, votes):
                p = self.local_statistics[player.name].probability.estimate()

                # In this case with:
                #   - A is the probability of 'player' being a spy. 
                #   - B is the probability of 'player' voting for suspects.
                if vote:
                    spy_Vote = self.fetch(player, ['spy_VotesForSpy'])
                    probability = spy_Vote * p # / 1.0 
                else:
                    res_Vote = self.fetch(player, ['res_VotesForSpy'])
                    probability = 1.0 - res_Vote * p # / 1.0 

                self.local_statistics[player.name].update(probability)
        elif False:
            # NOTE: If we had more information we could determine if a team excluded spies
            # for sure!  In this case, we could run more accurate predictions...
            for player, vote in zip(self.game.players, votes):
                spy_Vote = self.fetch(player, ['spy_VotesForSpy', 'spy_VotesForRes'])
                res_Vote = self.fetch(player, ['res_VotesForSpy', 'res_VotesForRes'])
                p = self.local_statistics[player.name].probability.estimate()

                # In this case with:
                #   - A is the probability of 'player' being a spy. 
                #   - B is the probability of 'player' voting true.
                if vote:
                    probability = spy_Vote * p # / 1.0 
                else:
                    probability = 1.0 - res_Vote * p # / 1.0 

                self.local_statistics[player.name].update(probability)

        for player, vote in zip(self.game.players, votes):
            p = self.local_statistics[player.name].probability.estimate()
            spy_Vote = self.fetch(player, ['spy_VotesForSpy']) * (0.0 + p) \
                     + self.fetch(player, ['res_VotesForSpy']) * (1.0 - p)
            res_Vote = self.fetch(player, ['spy_VotesForRes']) * (0.0 + p) \
                     + self.fetch(player, ['res_VotesForRes']) * (1.0 - p)

            for member in self.game.team:
                # In this case, Bayes' Theorem with:
                #   - A is the probability of team 'member' being a spy.
                #   - B is the probability of 'player' voting true.
                t = self.local_statistics[member.name].probability.estimate()
                
                if vote:
                    probability = spy_Vote * t # / 1.0
                else:
                    probability = 1.0 - res_Vote * t # / 1.0

                # NOTE: This reduces overall estimate quality...
                # self.local_statistics[member.name].update(probability)


    def onGameComplete(self, win, spies):
        for team, sabotaged in self.missions:
            suspects = [p for p in team if p in spies]
            # No spies on this mission to update statistics.
            if len(suspects) == 0:
                continue

            # This mission passed despite spies, very suspicious...
            for p in suspects:
                self.store(p, 'spy_Sabotage', float(sabotaged) / float(len(suspects)))

        for leader, team in self.selections:
            suspects = [p for p in team if p in spies]
            if leader in spies:
                self.store(leader, 'spy_PicksSpy', int(len(suspects) > 0))
                self.store(leader, 'spy_PicksSelf', int(leader in team))
            else:
                self.store(leader, 'res_PicksSpy', int(len(suspects) > 0))
                self.store(leader, 'res_PicksSelf', int(leader in team))

        for votes, team in self.votes:
            spied = len([p for p in team if p in spies]) > 0
            for p, v in zip(self.game.players, votes):
                if spied:
                    if p in self.spies:
                        self.store(p, 'spy_VotesForSpy', int(v))
                    else:
                        self.store(p, 'res_VotesForSpy', int(v))
                else:
                    if p in self.spies:
                        self.store(p, 'spy_VotesForRes', int(v))
                    else:
                        self.store(p, 'res_VotesForRes', int(v))

    def store(self, player, attribute, value):
        self.global_statistics[player.name].__dict__[attribute].sample(value)

    def fetch(self, player, attributes):
        result = 0.0
        for a in attributes:
            result += self.global_statistics[player.name].__dict__[a].estimate()
        return result / float(len(attributes))

