class Player(object):
    """A player in the game of resistance, identified by a unique index as the position
       at the table (random), and a name that identifies this player across multiple
       games (constant).
       
       When you build a Bot for resistance, you'll be given lists of players to manipulate
       in the form of instances of this Player class.  You can use it as follows:
        
            for player in players:
                print player.name, player.index

       NOTE: You can ignore the implementation of this class and simply skip to the details
       of the Bot class below if you want to write your own AI.
    """

    def __init__(self, name, index):
        self.name = name
        self.index = index

    def __repr__(self):
        return "<%s #%i>" % (self.name, self.index)

    def __eq__(self, other):
        return self.index == other.index and self.name == other.name

    def __ne__(self, other):
        return self.index != other.index or self.name != other.name

    def __hash__(self):
        return hash(self.index) ^ hash(self.name)


class Bot(Player):
    """This is the base class for your AI.  To get started:
        1) Derive this class.  See stock.py for examples.
        2) Implement callback functions below; you must re-implement the
           ones that raise exceptions. 
         
        All player data passed to your AI is done as a data-structure, for
        example to list other players:

            for p in players:
                if p.index != self.index:
                    print p.name
        
        See the SimplePlayer in stock.py for more examples. 
    """

    def reveal(self, players, spies):
        """If you're a spy, this function will be called to list the spies,
        including others and yourself.
        @param players  List of all players in the game.
        @param spies    List of players that are spies."""
        pass

    def select(self, players, count):
        """Pick a sub-group of players to go on the next mission.
        @return list    The players selected."""
        raise NotImplemented

    def vote(self, team, leader, tries):
        """Given a selected team, decide whether the mission should proceed.
        @param team      List of players with index and .
        @param leader    Single player that chose this team.
        @param tries     Number of attemps for this vote.
        @return bool     Answer Yes/No.""" 
        raise NotImplemented

    def onVoteComplete(self, players, votes, team):
        """Callback once the whole team has voted.
        @param players      List of all the players in the game.
        @param votes        Boolean votes for each player (ordered).
        @param team         The team that was chosen for this vote."""
        pass

    def sabotage(self, team):
        """Decide what to do on the mission once it has been approved.
        @return bool        Yes to shoot down a mission."""
        raise NotImplemented

    def onMissionComplete(self, team, sabotaged):
        """Callback once the players have been chosen.
        @param selected     List of players that participated in the mission.
        @param sabotaged    Integer how many times the mission was sabotaged."""
        pass

    def onGameComplete(self, players, spies):
        """Callback once the game is complete, and everything is revealed.
        @param players      List of all players in the game.
        @param spies        List of only the spies in the game."""
        pass

    def __init__(self, name, index, spy):
        """Constructor called before a game starts.
        @param name     The public name of your bot.
        @param index    Your own index in the player list.
        @param spy      Are you supposed to play as a spy?"""
        Player.__init__(self, name, index)
        self.spy = spy

    def __repr__(self):
        """Built-in function to support pretty-printing."""
        type = {True: "SPY", False: "RESISTANCE"}
        return "<%s #%i %s>" % (self.name, self.index, type[self.spy])

