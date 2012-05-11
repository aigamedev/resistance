import random

from player import Player


class RandomPlayer(Player):

    def __init__(self, index, spy):
        Player.__init__(self, "Random", index, spy)

    def select(self, players, count):
        return random.sample(players, count)

    def vote(self, team, leader, tries): 
        return random.choice([True, False])

    def sabotage(self, team):
        if self.spy:
            return random.choice([True, False])
        else:
            return False


class RuleFollower(Player):

    def __init__(self, index, spy):
        Player.__init__(self, "RuleFollower", index, spy)

    def reveal(self, players, spies):
        self.spies = spies

    def select(self, players, count):
        me = [p for p in players if p.index == self.index]
        others = [p for p in players if p.index != self.index]
        return me + random.sample(others, count - 1)

    def vote(self, team, leader, tries): 
        # Spies select any mission with one or more spies on it.
        if self.spy:
            return len([p for p in team if p in self.spies]) > 0
        # As resistance, always pass the fifth try.
        if tries >= 4:
            return True
        # If I'm not on the team, and it's a team of 3...
        if len(team) == 3 and not self.index in [p.index for p in team]:
            return False
        return True

    def sabotage(self, team):
        return self.spy
 

class LogicReasoner(Player):

    def __init__(self, index, spy):
        Player.__init__(self, "LogicReasoner", index, spy)
        self.team = None
        
    def reveal(self, players, spies):
        self.players = players
        self.spies = spies

    def select(self, players, count):
        me = [p for p in players if p.index == self.index]

        # As a spy, pick myself and others who are not spies.
        if self.spy:
            others = [p for p in players if p not in self.spies]
            return me + random.sample(others, count-1)
        # As resistance...
        else:
            team = []
            # If there was a previously selected successfull team, pick it! 
            if self.team:
                team = [p for p in self.team if p.index != self.index and p not in self.spies]
            # If the previous team did not include me, reduce it by one.
            if len(team) > count-1:
                team = random.sample(team, count-1)
            # If there are not enough people still, pick another randomly.
            if len(team) < count-1:
                others = [p for p in players if p.index != self.index and p not in (team+self.spies)]
                team.extend(random.sample(others, count-1-len(team)))
            return me + team
        # TODO: As resistance there are subteams that must be filtered out
        # even if we don't know who the spies are 100%.

    def vote(self, team, leader, tries): 
        # As a spy, vote for all missions that include one spy!
        if self.spy:
            return len([p for p in team if p in self.spies]) > 0

        # As resistance, always pass the fifth try.
        if tries >= 4:
            return True
        # If there's a known spy on the team.
        if set(team).intersection(set(self.spies)):
            return False
        # If I'm not on the team and it's a team of 3!
        if len(team) == 3 and not self.index in [p.index for p in team]:
            return False
        # Otherwise, just approve the team and get more information. 
        return True

    def onVoteComplete(self, players, votes, team):
        self.team = None
    
    def onMissionComplete(self, team, sabotaged):
        if self.spy:
            return

        # Forget this failed team so we don't pick it!
        if not sabotaged:
            self.team = team
            return

        suspects = [p for p in team if p not in self.spies and p != self]
        spies = [p for p in team if p in self.spies]
        # We have more thumbs down than suspects and spies!
        if sabotaged >= len(suspects) + len(spies):
            for spy in [s for s in suspects if s not in self.spies]:
                self.spies.append(spy)

    def sabotage(self, team):
        return self.spy


class Variable(object):
    def __init__(self):
        self.total = 0
        self.samples = 0

    def sample(self, value):
        self.total += value
        self.samples += 1

    def __repr__(self):
        if self.samples:
            return "%0.2f%%" % (100.0 * float(self.total) / float(self.samples))
        else:
            return "UNKNOWN"


class GlobalStatistics(object):
    def __init__(self):
        self.spy_VotesForSpy = Variable()
        self.res_VotesForSpy = Variable()
        self.spy_VotesForRes = Variable()
        self.res_VotesForRes = Variable()
        self.spy_Sabotage = Variable()

    def __repr__(self):
        return str([self.spy_VotesForSpy, self.res_VotesForSpy,
                    self.spy_VotesForRes, self.res_VotesForRes, 
                    self.spy_Sabotage])


class LocalStatistics(object):
    def __init__(self):
        self.probability = 0.4

    def update(self, prob):
        self.probability = self.probability * 0.5 + prob * 0.5


class Statistician(Player):

    global_statistics = {}

    def __init__(self, index, spy):
        Player.__init__(self, "Statistician", index, spy)
        self.missions = []
        self.local_statistics = {}

    def reveal(self, players, spies):
        self.spies = spies
        # Set the default value for global stats.
        for p in players:
            self.global_statistics.setdefault(p.name, GlobalStatistics())
            self.local_statistics.setdefault(p.name, LocalStatistics())

    def select(self, players, count):
        # TODO: The probability of each player depends on the team chosen.
        # As you pick players assuming they are not spies, the probabilities
        # must be updated here.
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

    def vote(self, team, leader, tries): 
        probability = sum([self._estimate(p) for p in team])
        return (probability / float(len(team))) < 0.5

    def _estimate(self, player):
        return self.local_statistics[player.name].probability

    def sabotage(self, team):
        return self.spy

    def onMissionComplete(self, team, sabotaged):
        # Store this information for later once we know the spies.
        self.missions.append((team, sabotaged))
        if self.spy:
            return

        # Update probabilities for this current game...
        probability = float(sabotaged) / float(len(team))
        for p in team:
            self.local_statistics[p.name].update(probability)
    
    def onVoteComplete(self, players, votes, team):
        # We don't know enough, don't update statistics.
        if len(self.spies) != 2:
            return

        spied = len([p for p in team if p in self.spies]) > 0
        for p, v in zip(players, votes):
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

    def onGameComplete(self, players, spies):
        for team, sabotaged in self.missions:
            suspects = [p for p in team if p in spies]
            # No spies on this mission to update statistics.
            if len(suspects) == 0:
                continue

            # This mission passed despite spies, very suspicious...
            for p in suspects:
                self.store(p, 'spy_Sabotage', float(sabotaged) / float(len(suspects)))

    def store(self, player, attribute, value):
        self.global_statistics[player.name].__dict__[attribute].sample(value)

