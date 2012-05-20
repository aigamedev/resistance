import random
import itertools
from player import Player


class State:
    """Simple game state data-structure that's passed to bots to help reduce
    the amount of book-keeping required."""

    def __init__(self):
        self.turn = 1 
        self.tries = 1
        self.wins = 0
    
    def losses(self):
        """How many games the resistance lost, or the spies won."""
        return self.turn - self.wins - 1


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
        self.state = State()        

        # Randomly assign the roles based on the player index.
        roles = [True, True, False, False, False]
        random.shuffle(roles)

        # Create Bot instances based on the constructor passed in.
        self.bots = [p(self.state, i, r) for p, r, i in zip(bots, roles, range(0, len(bots)))]
        
        # Maintaina copy of players that includes minimal data, for passing to other bots.
        self.players = [Player(p.name, p.index) for p in self.bots]
    
        # Configuration for the game itself.
        self.participants = [2, 3, 2, 3, 3]
        self.leader = itertools.cycle(self.bots) 

    def run(self):
        """Main entry point for the resistance game.  Once initialized call this to 
        simulate the game until it is complete."""

        # Tell the bots who the spies are if they are allowed to know.
        spies = [self.players[p.index] for p in self.bots if p.spy]
        for p in self.bots:
            if p.spy:
                p.onGameRevealed(self.players[:], spies[:])
            else:
                p.onGameRevealed(self.players[:], [])

        # Repeat as long as the game hasn't hit the max number of missions.
        while self.state.turn <= self.NUM_TURNS:
            
            # Some missions will take multiple turns... 
            if self.step():
                self.state.turn += 1
                self.state.tries = 1
            else:
                self.state.tries += 1

            # If there wasn't an agreement then the spies win.
            if self.state.tries > 5:
                self.state.turn = self.NUM_TURNS+1
                break

            # Determine if either side has won already.
            if self.state.wins >= self.NUM_WINS:
                break
            if self.state.losses() >= self.NUM_LOSSES:
                break
        
        # Pass back the results to the bots so they can do some learning!
        for p in self.bots:
            p.onGameComplete(self.state.wins >= self.NUM_WINS, self.players[:], spies)

    def step(self):
        """Single step/turn of the resistance game, which can fail if the voting
        does not have a clear majority."""

        # Step 1) Pick the leader and ask for a selection of players on the team.
        l = self.leader.next()

        count = self.participants[self.state.turn-1]
        selected = l.select(self.players[:], count)

        # Check the data returned by the bots is in the expected format!
        assert type(selected) is list or type(selected) is set, "Expecting a list as a return value of select()."
        assert len(set(selected)) == count, "The list returned by %s.select() is of the wrong size!" % (l.name)
        for s in selected: assert isinstance(s, Player), "Please return Player objects in the list from select()."

        # Make an internal callback, e.g. to track statistics about selection.
        self.onPlayerSelected(l, [b for b in self.bots if b in selected])
        # Copy the list to make sure no internal data is leaked to the other bots!
        selected = [Player(s.name, s.index) for s in selected]        

        # Step 2) Notify other bots of the selection and ask for a vote.
        votes = []
        score = 0
        for p in self.bots:
            v = p.vote(selected[:], self.players[l.index])
            self.onPlayerVoted(p, v, l, [b for b in self.bots if b in selected])
            assert type(v) is bool, "Please return a boolean from vote()."

            votes.append(v)
            score += int(v)
    
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
            self.state.wins += 1
            
        # Step 5) Pass back the results of the mission to the bots.
        for p in self.bots:
            p.onMissionComplete(selected[:], sabotaged)

        return True

