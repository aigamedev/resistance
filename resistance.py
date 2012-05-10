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

    def sabotage(self):
        """Decide what to do on the mission once it has been approved.
        @return bool"""
        raise NotImplemented

    def onMissionComplete(self, selected, sabotaged):
        pass        


class RandomPlayer(Player):

    def __init__(self, spy):
        Player.__init__(self, "Random", spy)

    def select(self, players, count):
        return random.sample(players, count)

    def vote(self, players): 
        return random.choice([True, False])

    def sabotage(self):
        if self.spy:
            return random.choice([True, False])
        else:
            return False


class Game:
    
    def __init__(self):
        self.players = [RandomPlayer(True), RandomPlayer(True), RandomPlayer(True),
                        RandomPlayer(False), RandomPlayer(False)]
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

        score = 0
        for p in self.players:
            if p.vote(selected):
                score += 1

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


resistance = 0
spies = 0
average = 0

for i in xrange(0,10000):
    g = Game()
    g.run()
    if g.wins > 2:
        resistance += 1
    else:
        spies += 1
    average += g.turn

print 'SPIES wins: ', spies
print 'RESISTANCE wins: ', resistance
print 'TURNS average: ', float(average) / 10000.0

