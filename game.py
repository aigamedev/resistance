import itertools

from player import Player


class State(object):
    """Simple game state data-structure that's passed to bots to help reduce
    the amount of book-keeping required.  Your bots can access this via the
    self.game member variable.

    This data-structure is available in all the bot API functions, and gets
    updated automatically (in between API calls) once new information is
    available about the game."""

    def __init__(self):
        self.turn = 1                   # int (1..5): Mission number.
        self.tries = 1                  # int (1..5): Attempt number.
        self.wins = 0                   # int (1..3): Number of resistance wins.
        self.losses = 0                 # int (1..3): Number of spy victories.
        self.leader = None              # Player: Current mission leader.
        self.team = None                # set(Player): Set of players picked.
        self.players = None             # list[Player]: All players in a list.


class Game(object):
    """Implementation of the core gameplay of THE RESISTANCE.  This class
    currently only supports games of 5 players."""

    NUM_TURNS = 5
    NUM_WINS = 3
    NUM_LOSSES = 3

    def onPlayerVoted(self, player, vote, leader, team):
        pass
   
    def onPlayerSelected(self, player, team):
        pass


    def onGameRevealed(self, players, spies):
        pass

    def onMissionAttempt(self, mission, tries, leader):
        pass

    def onTeamSelected(self, leader, team):
        pass

    def onVoteComplete(self, votes):
        pass

    def onMissionComplete(self, sabotaged):
        pass

    def onAnnouncement(self, source, announcement):
        pass

    def onGameComplete(self, win, spies):
        pass


    def __init__(self, bots, roles):
        self.state = State()        

        # Create Bot instances based on the constructor passed in.
        self.bots = [p(self.state, i, r) for p, r, i in zip(bots, roles, range(1, len(bots)+1))]
        
        # Maintain a copy of players that includes minimal data, for passing to other bots.
        self.state.players = [Player(p.name, p.index) for p in self.bots]
    
        # Configuration for the game itself.
        self.participants = [2, 3, 2, 3, 3]
        self.leader = itertools.cycle(self.state.players) 

    def run(self):
        """Main entry point for the resistance game.  Once initialized call this to 
        simulate the game until it is complete."""

        # Tell the bots who the spies are if they are allowed to know.
        spies = set([Player(p.name, p.index) for p in self.bots if p.spy])
        for p in self.bots:
            p.onGameRevealed(self.state.players, spies if p.spy else set())
        self.onGameRevealed(self.state.players, spies)

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
            if self.won:
                break
            if self.lost:
                break
        
        # Pass back the results to the bots so they can do some learning!
        for p in self.bots:
            p.onGameComplete(self.state.wins >= self.NUM_WINS, spies)
        self.onGameComplete(self.state.wins >= self.NUM_WINS, spies)

    @property
    def won(self):
        return self.state.wins >= self.NUM_WINS

    @property
    def lost(self):
        return self.state.losses >= self.NUM_LOSSES

    def callback(self, name, *args):
        for p in self.bots:
            getattr(p, name)(*args)
        getattr(self, name)(*args)

    def step(self):
        """Single step/turn of the resistance game, which can fail if the voting
        does not have a clear majority."""

        # Step 1) Pick the leader and ask for a selection of players on the team.
        self.state.leader = next(self.leader)
        self.state.team = None
        l = self.bots[self.state.leader.index-1]
        self.callback('onMissionAttempt', self.state.turn, self.state.tries, self.state.leader)

        count = self.participants[self.state.turn-1]
        selected = l.select(self.state.players, count)

        # Check the data returned by the bots is in the expected format!
        assert type(selected) is list or type(selected) is set, "Expecting a list as a return value of select()."
        assert len(set(selected)) == count, "The list returned by %s.select() is of the wrong size!" % (l.name)
        for s in selected:
            assert isinstance(s, Player), "Please return Player objects in the list from %s.select()." % (l.name)

        # Make an internal callback, e.g. to track statistics about selection.
        self.onPlayerSelected(l, [b for b in self.bots if b in selected])
        # Copy the list to make sure no internal data is leaked to the other bots!
        selected = [Player(s.name, s.index) for s in selected]
        self.state.team = set(selected)
        self.callback('onTeamSelected', self.state.leader, selected)

        # Step 2) Notify other bots of the selection and ask for a vote.
        votes = []
        score = 0
        for p in self.bots:
            v = p.vote(selected[:])
            self.onPlayerVoted(p, v, l, [b for b in self.bots if b in selected])
            assert type(v) is bool, "Please return a boolean from %s.vote() instead of %s." % (p.name, type(v))

            votes.append(v)
            score += int(v)
    
        # Step 3) Notify players of the vote result.
        self.callback('onVoteComplete', votes[:])

        # Continue if there was a clear majority...
        if score > 2:
            # Step 4) In this case, run the mission and ask the bots if they want
            # to go through with the mission or sabotage!
            sabotaged = 0
            for s in selected:
                p = self.bots[s.index-1]
                result = False
                if p.spy:
                    result = p.sabotage()
                    assert type(result) is bool, "Please return a boolean from %s.sabotage(), not %s." % (p.name, type(result))
                sabotaged += int(result)

            if sabotaged == 0:
                self.state.wins += 1
            else:
                self.state.losses += 1
                
            # Step 5) Pass back the results of the mission to the bots.
            # Process the team first to make sure any timing of the result
            # is the same for all player roles, specifically over IRC.
            for s in selected:
                p = self.bots[s.index-1]
                p.onMissionComplete(sabotaged)
            # Now, with delays taken into account, all other results can be
            # passed back safely without divulging Spy/Resistance identities.
            for p in [b for b in self.bots if b not in selected]:
                p.onMissionComplete(sabotaged)
            self.onMissionComplete(sabotaged)

        for p in self.bots:
            ann = p.announce()
            if not ann: continue

            copy = {}
            assert type(ann) is dict, "Please return a dictionary from %s.announce(), not %s." % (p.name, type(ann))
            for k, v in ann.items():
                assert isinstance(k, Player), "Please use Player objects as dictionary key in %s.announce()." % (p.name)
                assert isinstance(v, float), "Please use floats as dictionary values in %s.announce()." % (p.name)
                copy[Player(k.name, k.index)] = v

            source = Player(p.name, p.index)
            for other in [o for o in self.bots if o != p]:
                other.onAnnouncement(source, copy)
            self.onAnnouncement(source, copy)

        return score > 2
