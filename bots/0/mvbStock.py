import random

from player import Player

class Rogue(Player):
    # This information is global and used across multiple games.
    global_statistics = {}    

    def __init__(self, index, spy):
        Player.__init__(self, "Rogue", index, spy)
        self.spy = spy
        self.index = index
        pass

    def reveal(self, players, spies):
# If you're a spy, this function will be called to list the spies, including others and yourself.
        self.iSabotaged = False
        self.players = players
        self.spies = spies
        self.numPlayers = len(players)
        self.numSpies = 2 #len(spies)
        self.me = [p for p in self.players if p.index == self.index][0]

        self.wasInMission = [0 for x in players]
        ns = self.numSpies
        if self.spy :
            ns -= 1
        self.spyProbPlayer = [ns/(self.numPlayers-1.) for x in players]
        if self.spy : 
            self.spyProbPlayer[self.index] = 1;
        else:
            self.spyProbPlayer[self.index] = 0;

        self.missionSucceeded = [0, 0, 0, 0, 0]
        self.numMissionsSucceeded = 0
        self.numMissionsPlayed = 0
       
        pass
 
    def select(self, players, count):
        """Pick a sub-group of players to go on the next mission.
        @return list    The players selected."""
        myTeam = []
        index = 0
        max = 0
        min = 1
        for p in players:
            if p != self.me:
                if self.spyProbPlayer[p.index] > max:
                    max = self.spyProbPlayer[p.index]
                if self.spyProbPlayer[p.index] < min:
                    min = self.spyProbPlayer[p.index]
                
        if self.spy == True: # Spy Strategy
            if random.random() < .99:
                myTeam.append(self.me)
            while len(myTeam) < count:
                p = players[index]
                if not (p in myTeam):
                    if max == 0:
                        if random.random() < 1. / (self.numPlayers-1):
                            myTeam.append(p)
                    else:
                        if random.random() < self.spyProbPlayer[p.index]:
                            myTeam.append(p)
                        elif random.random() < .01:
                            myTeam.append(p)
                index += 1
                if index >= len(players):
                    index = 0
        else:
            if random.random() < .99:
                myTeam.append(self.me)
            while len(myTeam) < count:
                p = players[index]
                if not (p in myTeam):
                    if random.random() > self.spyProbPlayer[p.index]:
                        myTeam.append(p)
                index += 1
                if index >= len(players):
                    index = 0
        return myTeam

    def vote(self, team, leader, tries):
        """Given a selected team, decide whether the mission should proceed.
        @param team      List of players with index and .
        @param leader    Single player that chose this team.
        @param tries     Number of attempts for this vote.
        @return bool     Answer Yes/No.""" 
        pSuccess = 1;
        inTeam = False
        for x in team:
            pSuccess *= (1-self.spyProbPlayer[x.index])
            if x.index == self.index:
                inTeam = True

        if self.spy == True:
            if inTeam:
                return True
            return random.random() > pSuccess
        else:
            if inTeam:
                return True
            return random.random() < pSuccess


    def onVoteComplete(self, players, votes, team):
        """Callback once the whole team has voted.
        @param players      List of all the players in the game.
        @param votes        Boolean votes for each player (ordered).
        @param team         The team that was chosen for this vote."""
        
        pass

    def sabotage(self, team):
        """Decide what to do on the mission once it has been approved.
        @return bool        Yes to shoot down a mission."""
        if self.spy:
            self.iSabotaged = True
            return True #random.choice([True, False])
        else:
            self.iSabotaged = False
            return False

    def onMissionComplete(self, team, sabotaged):
        """Callback once the players have been chosen.
        @param team     List of players that participated in the mission.
        @param sabotaged    Integer how many times the mission was sabotaged."""
        numOthersInTeam = len(team)
        numOthersSabotaged = sabotaged
        if self.me in team:
            numOthersInTeam -= 1
            if self.iSabotaged == True:
                numOthersSabotaged -= 1
        if numOthersSabotaged == 0:
            self.numMissionsSucceeded += 1
            for p in team:
                if p != self.me:
                    self.spyProbPlayer[p.index] *= 0 #(1.-1./numOthersInTeam)
        else:
            for p in team:
                if p!= self.me:
                    self.spyProbPlayer[p.index] += (1.-self.spyProbPlayer[p.index])/(1.+sabotaged);        
        
        pass

    def __repr__(self):
        """Built-in function to support pretty-printing."""
        type = {True: "SPY", False: "RESISTANCE"}
        return "<%s #%i %s>" % (self.name, self.index, type[self.spy])

    def onGameComplete(self, players, spies):
        # Set the default value for global stats.
        for p in players:
            self.global_statistics.setdefault(p.name, 0)
        # Update it only for the spies.
        for p in spies:
            self.global_statistics[p.name] += 1

    
        
