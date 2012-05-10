import random


class Player:

    def __init__(self, name, spy):
        self.name = name
        self.spy = spy

    def select(self, players, count):
        """Pick a sub-group of players to go on the next mission.
        @return list    The players selected."""
        raise NotImplemented

    def vote(self, players):
        """Given a list of players, decide whether the mission should proceed.
        @return bool     Answer Yes/No.""" 
        raise NotImplemented

    def onVoteComplete(self, players, votes):
        """Callback once the whole team has voted.
        @param players      List of all the players in the game.
        @param votes        Boolean votes ."""
        pass

    def sabotage(self):
        """Decide what to do on the mission once it has been approved.
        @return bool        Yes to shoot down a mission."""
        raise NotImplemented

    def onMissionComplete(self, selectedPlayers, sabotaged):
        """Callback once the players have been chosen.
        @param selected     List of players that participated in the mission.
        @param sabotaged    Boolean whether the misison was sabotaged or not."""
        pass        


class Game:
    
    def __init__(self, players):
        roles = [True, True, False, False, False]
        random.shuffle(roles)

        self.players = [p(r) for p, r in zip(players, roles)]
        random.shuffle(self.players)
    
        self.participants = [2, 3, 2, 3, 3]

        self.wins = 0
        self.leader = 0

    def run(self):
        self.turn = 0

        while self.turn < 5:
            if self.step():
                self.turn += 1

            if self.wins >= 3:
                break
            if self.turn - self.wins >= 3:
                break

    def step(self):
        l = self.players[self.leader]
        self.leader += 1
        if self.leader >= len(self.players):
            self.leader = 0 

        selected = l.select(self.players, self.participants[self.turn])

        votes = []
        score = 0
        for p in self.players:
            v = p.vote(selected)
            votes.append(v)
            if v:
                score += 1

        for p in self.players:
            p.onVoteComplete(self.players, votes)

        if score <= 2:
            return False 

        sabotaged = False
        for s in selected:
            sabotaged = sabotaged or s.sabotage()

        if not sabotaged:
            self.wins += 1
            
        for p in self.players:
            p.onMissionComplete(selected, sabotaged)

        return True

