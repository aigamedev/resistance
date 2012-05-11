import random

class State:
    def __init__(self, index, name):
        self.index = index
        self.name = name

    def __repr__(self):
        return "<%s #%i>" % (self.name, self.index)

    def __eq__(self, other):
        return self.index == other.index and self.name == other.name

    def __ne__(self, other):
        return self.index != other.index or self.name != other.name

    def __hash__(self):
        return hash(self.index) ^ hash(self.name)


class Game:

    NUM_TURNS = 5
    NUM_WINS = 3
    NUM_LOSSES = 3
   
    def __init__(self, players):
        roles = [True, True, False, False, False]
        random.shuffle(roles)

        self.players = [p(i, r) for p, r, i in zip(players, roles, range(0, len(players)))]
        
        self.states = [State(p.index, p.name) for p in self.players]
    
        self.participants = [2, 3, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]

        self.wins = 0
        self.leader = 0

    def run(self):
        self.turn = 0
        self.tries = 0

        spies = [self.states[p.index] for p in self.players if p.spy]
        for p in self.players:
            if p.spy:   
                p.reveal(self.states[:], spies[:])
            else:
                p.reveal(self.states[:], [])

        while self.turn < self.NUM_TURNS:
            if self.step():
                self.turn += 1
                self.tries = 0
            else:
                self.tries += 1

            if self.tries >= 5:
                self.wins = 0
                break

            if self.wins >= self.NUM_WINS:
                break
            if self.turn - self.wins >= self.NUM_LOSSES:
                break
        
        for p in self.players:
            p.onGameComplete(self.states[:], spies)

    def step(self):
        l = self.players[self.leader]
        self.leader += 1
        if self.leader >= len(self.players):
            self.leader = 0 

        count = self.participants[self.turn]
        selected = l.select(self.states[:], count)
        assert type(selected) is list, "Expecting a list as a return value of select()."
        assert len(set(selected)) == count, "The list returned by select() is of the wrong size!"
        for s in selected: assert isinstance(s, State), "Please return objects from the list passed to select()."

        votes = []
        score = 0
        for p in self.players:
            v = p.vote(selected[:], self.states[l.index], self.tries)
            assert type(v) is bool, "Please return a boolean from vote()."
            votes.append(v)
            if v:
                score += 1

        for p in self.players:
            p.onVoteComplete(self.states[:], votes, selected[:])

        if score <= 2:
            return False 

        sabotaged = 0
        for s in selected:
            p = self.players[s.index]
            result = p.sabotage(selected[:])
            if not p.spy: assert result == False, "The function sabotage() cannot return True for Resistance fighters."
            sabotaged += int(result)

        if sabotaged == 0:
            self.wins += 1
            
        for p in self.players:
            p.onMissionComplete(selected[:], sabotaged)

        return True

