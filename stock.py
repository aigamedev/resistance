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


class SimplePlayer(Player):

    # This information is global and used accross multiple games.
    global_statistics = {}    

    def __init__(self, index, spy):
        Player.__init__(self, "Simple", index, spy)
        
        # This information is local and stored for one game only.
        self.local_statistics = {}

    def reveal(self, players, spies):
        self.players = players
        self.spies = [s for s in spies if s.index != self.index]

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
        # As a spy, vote for all missions that include a spy!
        if self.spy:
            return len([p for p in team if p in self.spies]) > 0

        # As resistance, always pass the fifth try.
        if tries >= 4:
            return True
        # If I'm not on the team and it's a team of 3!
        if len(team) == 3 and not self.index in [p.index for p in team]:
            return False
        # Otherwise, just approve the team and get more information. 
        return True

    def onVoteComplete(self, players, votes, team):
        # Remember this team for future reference!
        self.team = team
    
    def onMissionComplete(self, team, sabotaged):
        # Forget this failed team so we don't pick it!
        if sabotaged or self.spy:
            self.team = None

    def sabotage(self, team):
        if not self.spy:
            return False
        
        if len(team) == 2:
            return random.choice([True, False])
        else:
            return True

    def onGameComplete(self, players, spies):
        # Set the default value for global stats.
        for p in players:
            self.global_statistics.setdefault(p.name, 0)
        # Update it only for the spies.
        for p in spies:
            self.global_statistics[p.name] += 1

