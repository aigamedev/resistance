import random
from player import Player


class Game:
    """Implementation of the core gameplay of THE RESISTANCE.  This class currently
    only supports games of 5 players."""

    NUM_TURNS = 5
    NUM_WINS = 3
    NUM_LOSSES = 3

    def onPlayerVoted(self, player, vote, leader, team):
        pass
   
    def onPlayerSelected(self, player, team):
        pass
   
    def __init__(self, bots):
        # Randomly assign the roles based on the player index.
        roles = [True, True, False, False, False]
        random.shuffle(roles)

        # Create Bot instances based on the constructor passed in.
        self.bots = [p(i, r) for p, r, i in zip(bots, roles, range(0, len(bots)))]
        
        # Maintaina copy of players that includes minimal data, for passing to other bots.
        self.players = [Player(p.name, p.index) for p in self.bots]
    
        # Configuration for the game itself.
        self.participants = [2, 3, 2, 3, 3]
        self.wins = 0
        self.leader = 0

    def run(self):
        """Main entry point for the resistance game.  Once initialized call this to 
        simulate the game until it is complete."""

        self.turn = 0
        self.tries = 0

        # Tell the bots who the spies are if they are allowed to know.
        spies = [self.players[p.index] for p in self.bots if p.spy]
        for p in self.bots:
            if p.spy:
                p.onGameRevealed(self.players[:], spies[:])
            else:
                p.onGameRevealed(self.players[:], [])

        # Repeat as long as the game hasn't hit the max number of missions.
        while self.turn < self.NUM_TURNS:
            
            # Some missions will take multiple turns... 
            if self.step():
                self.turn += 1
                self.tries = 0
            else:
                self.tries += 1

            # If there wasn't an agreement then the spies win.
            if self.tries >= 5:
                self.wins = 0
                break

            # Determine if either side has won already.
            if self.wins >= self.NUM_WINS:
                break
            if self.turn - self.wins >= self.NUM_LOSSES:
                break
        
        # Pass back the results to the bots so they can do some learning!
        for p in self.bots:
            p.onGameComplete(self.players[:], spies)

    def step(self):
        """Single step/turn of the resistance game, which can fail if the voting
        does not have a clear majority."""

        # Step 1) Pick the leader and ask for a selection of players on the team.
        l = self.bots[self.leader]
        self.leader += 1
        if self.leader >= len(self.bots):
            self.leader = 0 

        count = self.participants[self.turn]
        selected = l.select(self.players[:], count)
        assert type(selected) is list, "Expecting a list as a return value of select()."
        assert len(set(selected)) == count, "The list returned by %s.select() is of the wrong size!" % (l.name)
        for s in selected: assert isinstance(s, Player), "Please return Player objects in the list from select()."
        self.onPlayerSelected(l, [b for b in self.bots if b in selected])
        selected = [Player(s.name, s.index) for s in selected]        

        # Step 2) Notify other bots of the selection and ask for a vote.
        votes = []
        score = 0
        for p in self.bots:
            v = p.vote(selected[:], self.players[l.index], self.tries)
            self.onPlayerVoted(p, v, l, [b for b in self.bots if b in selected])
            assert type(v) is bool, "Please return a boolean from vote()."
            votes.append(v)
            if v:
                score += 1
        
        # Step 3) Notify players of the vote result.
        for p in self.bots:
            p.onVoteComplete(self.players[:], votes, selected[:])

        # Bail out if there was no clear majority...
        if score <= 2:
            return False 

        # Step 4) In this case, run the mission and ask the bots if they want
        # to go through with the mission or sabotage!
        sabotaged = 0
        for s in selected:
            p = self.bots[s.index]
            result = p.sabotage(selected[:])
            if not p.spy: assert result == False, "The function sabotage() cannot return True for Resistance fighters."
            sabotaged += int(result)

        if sabotaged == 0:
            self.wins += 1
            
        # Step 5) Pass back the results of the mission to the bots.
        for p in self.bots:
            p.onMissionComplete(selected[:], sabotaged)

        return True

