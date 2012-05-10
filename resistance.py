import random

class State:
    def __init__(self, index, name):
        self.index = index
        self.name = name

    def __repr__(self):
        return "<%s #%i>" % (self.name, self.index)


class Game:
    
    def __init__(self, players):
        roles = [True, True, False, False, False]
        random.shuffle(roles)

        self.players = [p(i, r) for p, r, i in zip(players, roles, range(0, len(players)))]
        
        self.states = [State(p.index, p.name) for p in self.players]
    
        self.participants = [2, 3, 2, 3, 3]

        self.wins = 0
        self.leader = 0

    def run(self):
        self.turn = 0

        spies = [self.states[p.index] for p in self.players if p.spy]
        for p in self.players:
            if p.spy:   
                p.reveal(spies)

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

        selected = l.select(self.states, self.participants[self.turn])

        votes = []
        score = 0
        for p in self.players:
            v = p.vote(selected, self.states[l.index])
            votes.append(v)
            if v:
                score += 1

        for p in self.players:
            p.onVoteComplete(selected, votes)

        if score <= 2:
            return False 

        sabotaged = False
        for s in selected:
            sabotaged = sabotaged or self.players[s.index].sabotage()

        if not sabotaged:
            self.wins += 1
            
        for p in self.players:
            p.onMissionComplete(selected, sabotaged)

        return True

