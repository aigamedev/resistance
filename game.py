import itertools

from player import Player


class State(object):
    """Simple game state data-structure that's passed to bots to help reduce
    the amount of book-keeping required.  Your bots can access this via the
    `self.game` member variable.

    This data-structure is available in all the bot API functions, and gets
    updated automatically (in between API calls) once new information is
    available about the game."""


    PHASE_PREPARING = 0
    PHASE_SELECTION = 1
    PHASE_VOTING = 2
    PHASE_MISSION = 3
    PHASE_ANNOUNCING = 4


    def __init__(self):
        self.phase = 0                  # int (0..4): Current game phase.
        self.turn = 1                   # int (1..5): Mission number.
        self.tries = 1                  # int (1..5): Attempt number.
        self.wins = 0                   # int (0..3): Number of resistance wins.
        self.losses = 0                 # int (0..3): Number of spy victories.
        self.leader = None              # Player: Current mission leader.
        self.team = None                # set(Player): Set of players picked.
        self.players = None             # list[Player]: All players in a list.
        self.votes = None               # list[bool]: Votes for the mission.
        self.sabotages = None           # int (0..3): Number of sabotages.

    def clone(self):
        s = State()
        s.__dict__ = self.__dict__.copy()
        return s

    def __eq__(self, other):
        return \
                self.phase == other.phase           \
            and self.turn == other.turn             \
            and self.tries == other.tries           \
            and self.wins == other.wins             \
            and self.losses == other.losses         \
            and self.leader == other.leader         \
            and self.team == other.team             \
            and self.players == other.players       \
            and self.votes == other.votes           \
            and self.sabotages == other.sabotages

    def __repr__(self):
        output = "<State\n"
        for key in sorted(self.__dict__):
            value = self.__dict__[key]
            output += "\t- %s: %r\n" % (key, value)
        return output + ">"


class BaseGame(object):
    """Implementation of the core gameplay of THE RESISTANCE.  This class
    currently only supports games of 5 players."""

    MAX_TURNS = 5
    MAX_TRIES = 5
    NUM_WINS = 3
    NUM_LOSSES = 3


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

    def onMissionFailed(self, leader, team):
        pass

    def onAnnouncement(self, source, announcement):
        pass

    def onGameComplete(self, win, spies):
        pass


    def __init__(self, state=None):
        self.state = state or State()

        # Configuration for the game itself.
        self.participants = [2, 3, 2, 3, 3]

    def run(self):
        """Main entry point for the resistance game.  Once initialized call this to 
        simulate the game until it is complete."""

        # Repeat as long as the game hasn't hit the max number of missions.
        while not self.done:
            self.step()
        
        # Pass back the results to the bots so they can do some learning!
        spies = set([Player(p.name, p.index) for p in self.bots if p.spy])
        for p in self.bots:
            p.onGameComplete(self.state.wins >= self.NUM_WINS, spies)
        self.onGameComplete(self.state.wins >= self.NUM_WINS, spies)

    @property
    def done(self):
        # If there wasn't an agreement then the spies win.
        if self.state.tries > self.MAX_TRIES:
            return True
        # If this is the last turn that's it too!
        if self.state.turn > self.MAX_TURNS:
            return True
        # Otherwise it's fine to keep going until one side wins.
        return self.won or self.lost

    @property
    def won(self):
        return self.state.wins >= self.NUM_WINS

    @property
    def lost(self):
        return self.state.losses >= self.NUM_LOSSES

    def callback(self, name, *args):
        getattr(self, name)(*args)

    def next_leader(self):
        li = ((self.state.leader.index+1) % len(self.state.players)) if self.state.leader else 0
        return self.state.players[li]

    def get_selection(self, count):
        raise NotImplementedError

    def do_selection(self):
        """Phase 1) Pick the leader and ask for a selection of players on the team.
        """
        self.state.team = None
        self.state.votes = None
        self.state.sabotages = None

        self.callback('onMissionAttempt', self.state.turn, self.state.tries, self.state.leader)
        count = self.participants[self.state.turn-1]
        selected = self.get_selection(count)

        # Copy the list to make sure no internal data is leaked to the other bots!
        self.state.team = [Player(s.name, s.index) for s in selected]
        self.callback('onTeamSelected', self.state.leader, self.state.team)

        self.state.phase = State.PHASE_VOTING

    def get_votes(self):
        raise NotImplementedError

    def do_voting(self):
        """Phase 2) Notify other bots of the selection and ask for a vote."""

        votes = self.get_votes()
        
        self.state.votes = votes[:]
        self.callback('onVoteComplete', votes[:])

        score = sum([int(v) for v in self.state.votes])

        # Continue if there was a clear majority...
        if score > 2:
            self.state.phase = State.PHASE_MISSION
        else:
            self.callback('onMissionFailed', self.state.leader, self.state.team)
            self.state.tries += 1
            self.state.phase = State.PHASE_ANNOUNCING

    def get_sabotages(self):
        raise NotImplementedError

    def do_mission(self):
        """Phase 3) Run the mission and ask the bots if they want to help with
        the mission or sabotage!"""

        sabotaged = self.get_sabotages()
        if sabotaged == 0:
            self.state.wins += 1
        else:
            self.state.losses += 1
        self.state.sabotages = sabotaged

        self.onMissionComplete(sabotaged)

        self.state.phase = State.PHASE_ANNOUNCING
        self.state.turn += 1
        self.state.tries = 1

    def get_announcements(self):
        raise NotImplementedError

    def do_announcements(self):
        """Phase 4) Allow bots to publicly announce what they want about the game.
        """
        for source, ann in self.get_announcements():
            copy = {}
            assert type(ann) is dict, "Please return a dictionary from %s.announce(), not %s." % (p.name, type(ann))
            for k, v in ann.items():
                assert isinstance(k, Player), "Please use Player objects as dictionary key in %s.announce()." % (p.name)
                assert isinstance(v, float), "Please use floats as dictionary values in %s.announce()." % (p.name)
                copy[Player(k.name, k.index)] = v

            self.onAnnouncement(source, copy)

        self.state.leader = self.next_leader()
        self.state.phase = State.PHASE_SELECTION

    def do_preparation(self):
        self.onGameRevealed(self.state.players, self.spies)        
        self.state.phase = State.PHASE_SELECTION

    def step(self):
        """Single step/turn of the resistance game, which can fail if the voting
        does not have a clear majority."""

        if self.state.phase == State.PHASE_SELECTION:
            self.do_selection()
        elif self.state.phase == State.PHASE_VOTING:
            self.do_voting()
        elif self.state.phase == State.PHASE_MISSION:
            self.do_mission()
        elif self.state.phase == State.PHASE_ANNOUNCING:
            self.do_announcements()
        elif self.state.phase == State.PHASE_PREPARING:
            self.do_preparation()
        else:
            assert False, "Not expecting this game phase."


class Game(BaseGame):

    def __init__(self, bots, roles, state=None):
        super(Game, self).__init__(state=state)

        # Create Bot instances based on the constructor passed in.
        self.bots = [p(self.state, i, r) for p, r, i in zip(bots, roles, range(0, len(bots)))]
        self.spies = set([Player(p.name, p.index) for p in self.bots if p.spy])
        
        # Maintain a copy of players that includes minimal data, for passing to other bots.
        self.state.players = [Player(p.name, p.index) for p in self.bots]
        self.state.leader = self.next_leader()

    def onPlayerSelected(self, player, team):
        pass

    def onPlayerVoted(self, player, vote, leader, team):
        pass

    def callback(self, name, *args):
        for p in self.bots:
            getattr(p, name)(*args)
        getattr(self, name)(*args)

    def onGameRevealed(self, players, spies):
        # Tell the bots who the spies are if they are allowed to know.        
        for p in self.bots:
            p.onGameRevealed(self.state.players, spies if p.spy else set())

    def get_selection(self, count):
        leader = self.bots[self.state.leader.index]
        selected = leader.select(self.state.players, count)

        # Check the data returned by the bots is in the expected format!
        assert type(selected) in [list, set, tuple], "Expecting a list|set|tuple as a return value of select(), not %s." % type(selected)
        assert len(set(selected)) == len(selected), "There were duplicate players returned in the list by %s.select()." % (leader.name)
        assert len(selected) == count, "The list returned by %s.select() is of the wrong size!  Expecting %i was %i." % (leader.name, count, len(selected))
        for s in selected:
            assert isinstance(s, Player), "Please return Player objects in the list from %s.select()." % (leader.name)
            assert s in self.state.players, "The specified Player does not exist in this game: %r." % (s)

        # Make an internal callback, e.g. to track statistics about selection.
        self.onPlayerSelected(leader, [b for b in self.bots if b in selected])
        return selected

    def get_votes(self):
        votes = []
        for p in self.bots:
            v = p.vote(self.state.team)
            assert type(v) is bool, "Please return a boolean from %s.vote() instead of %s." % (p.name, type(v))
            self.onPlayerVoted(p, v, self.state.leader, [b for b in self.bots if b in self.state.team])
            votes.append(v)
        return votes

    def onMissionComplete(self, sabotaged):
        # Pass back the results of the mission to the bots.
        # Process the team first to make sure any timing of the result
        # is the same for all player roles, specifically over IRC.
        for s in self.state.team:
            p = self.bots[s.index]
            p.onMissionComplete(sabotaged)

        # Now, with delays taken into account, all other results can be
        # passed back safely without divulging Spy/Resistance identities.
        for p in [b for b in self.bots if b not in self.state.team]:
            p.onMissionComplete(sabotaged)
        
    def get_sabotages(self):
        sabotaged = 0
        for s in self.state.team:
            p = self.bots[s.index]
            result = False
            if p.spy:
                result = p.sabotage()
                assert type(result) is bool, "Please return a boolean from %s.sabotage(), not %s." % (p.name, type(result))
            sabotaged += int(result)
        return sabotaged

    def onAnnouncement(self, player, announcement):
        for other in [o for o in self.bots if o != player]:
            other.onAnnouncement(player, announcement)

    def get_announcements(self):
        return [(p, ann) for p, ann in [(Player(p.name, p.index), p.announce()) for p in self.bots] if ann]
