'''
@author: Tom
'''

from player import Player
import random


class OpponentType(object):
    """ A place to hold history information, and 
    some estimated characteristics. """
    
    
    def __init__(self, name):
        self.name = name
        self.accDiffs = 0.
        self.count = 0
        
    def accAccurateness(self, wasspy, spyness):
        self.count += 1
        spyness /= (self.accFactor()+0.0001)
        if wasspy:
            self.accDiffs += 1-spyness
        else:
            self.accDiffs += spyness
        
    def accFactor(self):
        if self.name == "Random":
            return 0
        #print self.accDiffs, self.count, (self.count - self.accDiffs*2.) / (self.count+1.)
        return (self.count - self.accDiffs*2.) / (self.count+1.)
    
class Opponent(object):
    
    
    def __init__(self, oppclass=None):
        self.oppclass = oppclass
        
        self.firstsafeteammemberships = 0
        self.nextsafeteammemberships = 0
        self.firstspyteammemberships = 0
        self.nextspyteammemberships = 0
        
        self.votedforspymission = 0
        self.unvotedgoodmission = 0
        self.unvotedforspymission = 0
        self.votedgoodmission = 0
        
    def spyness(self, turn=0):
        """ What is the current estimate for this player to be a spy?"""
        evidence = (self.firstsafeteammemberships + self.firstspyteammemberships) * 0.6
        N = (self.firstsafeteammemberships - self.firstspyteammemberships) * 0.6  
        
        evidence += (self.nextsafeteammemberships + self.nextspyteammemberships) 
        N += (self.nextsafeteammemberships - self.nextspyteammemberships)  
        
        evidence += (self.votedforspymission + self.votedgoodmission) * 0.1
        N += (self.unvotedforspymission - self.votedforspymission) * 0.1
        evidence += (self.votedforspymission + self.votedgoodmission) * 0.05
        N += (self.votedgoodmission - self.unvotedgoodmission) * 0.05
        
        N *= self.oppclass.accFactor()
        
        if evidence == 0:
            return 0.5
        else:
            #print (evidence-N)/(2*evidence+0.001)
            return (evidence-N)/(2*evidence+0.001)
    
    def wasAmongSpies(self, L, turn, wturns):
        if turn == 0:
            self.firstspyteammemberships += 1./L
        else:
            self.nextspyteammemberships += 1./L
            
    def wasSafe(self, L, turn, wturns):
        if turn == 0:
            self.firstsafeteammemberships += 1./L
        else:
            self.nextsafeteammemberships += 1./L
        
    def votedForSpies(self, L, inteam, turn, wturns):        
        self.votedforspymission += 1
        
    def unvotedForSpies(self, L, inteam, turn, wturns):
        self.unvotedforspymission += 1
        
    def votedForGood(self, L, inteam, turn, wturns):
        self.votedgoodmission += 1
        
    def unvotedForGood(self, L, inteam, turn, wturns):
        self.unvotedgoodmission += 1     
        
    def accAccurateness(self, wasspy, spyness):
        self.oppclass.accAccurateness(wasspy, spyness)
    
    
        
class Goodie(Opponent):
    def spyness(self):
        return 0
    
    def accAccurateness(self, wasspy, spyness):
        pass
    
class Turn(object):
    leaderid = None
    chosenteam = None
    votelist = None
    votesuccess = None
    # if the vote succeeded
    spycards = None

        
oppmemory = {}


class Trusty(Player):
    
    stochasticity = 0.0
    
    goodenoughleader = 0.25
    
    initsabotageprob = 0.5
    
    def __init__(self, index, spy):
        """Constructor called before a game starts.
        @param name     The public name of your bot.
        @param index    Your own index in the player list.
        @param spy      Are you supposed to play as a spy?"""
        Player.__init__(self, "Trusty", index, spy)
        self.leader = 0
        self.players = {}
        self.turnhistory = []
        self.spies = []
        self.turn = 0
        self.winturns = 0
        #print 'me', self.index
    
    @property
    def minturnsleft(self):
        return 3-self.turn+self.winturns
    
    @property
    def risklimit(self):
        if self.turn == 0: 
            return 1.
        else:
            return 0.2 * (self.minturnsleft-1)
        
    def reveal(self, players, spies):
        """If you're a spy, this function will be called to list the spies,
        including others and yourself.
        @param spies    List of players that are spies."""
        if len(self.players) > 0:
            return
        for p in players:
            if p.index == self.index:
                self.players[p.index] = Goodie()
                continue 
            if p.name not in oppmemory:
                oppmemory[p.name] = OpponentType(p.name)             
            self.players[p.index] = Opponent(oppmemory[p.name])
        self.spies = spies        

    def select(self, players, count):
        """Pick a sub-group of players to go on the next mission.
        @return list    The players selected."""
        me = [p for p in players if p.index == self.index]
                    
        if self.spy:
            if random.random() < self.stochasticity:
                others = [p for p in players if p.index != self.index]
            else:
                others = [p for p in players if p not in self.spies]
            res = random.sample(others, count-1)
        else:
            if random.random() < self.stochasticity:
                others = [p for p in players if p.index != self.index]
                res = random.sample(others, count-1)
            else:
                others = [(self.players[p.index].spyness(), p) 
                          for p in players if p.index != self.index]
                others.sort()
                res = [p for (_, p) in others][:count-1]
        return me+ res

    def vote(self, team, leader, tries):
        """Given a selected team, decide whether the mission should proceed.
        @param team      List of players with index and .
        @param leader    Single player that chose this team.
        @param tries     Number of attemps for this vote.
        @return bool     Answer Yes/No.""" 
        if self.spy:
            if random.random() < self.stochasticity:
                return random.choice([True, False])
            else:
                return len([p for p in team if p in self.spies]) > 0
        else:
            if tries >= 4:
                return True
            # If I'm not on the team and it's a team of 3!
            if len(team) == 3 and not self.index in [p.index for p in team]:
                return False
                    
            if random.random() < self.stochasticity:
                return random.choice([True, False])            
            if leader.index==self.index:
                return True
            if self.players[leader.index].spyness() > self.goodenoughleader:
                #print self.players.keys()
                #print [p.index for p in team], self.index
                totalrisk = sum([self.players[p.index].spyness() for p in team])
                if totalrisk > self.risklimit:
                    return False
                else:
                    return True 
            else:
                return False

    def onVoteComplete(self, players, votes, team):
        """Callback once the whole team has voted.
        @param players      List of all the players in the game.
        @param votes        Boolean votes for each player (ordered).
        @param team         The team that was chosen for this vote."""
        self.lastvotes = votes

    def sabotage(self, team):
        """Decide what to do on the mission once it has been approved.
        @return bool        Yes to shoot down a mission."""
        if not self.spy:
            return False
        else:
            if random.random() < self.initsabotageprob * (self.minturnsleft-1):
                return True
            else:
                return False

    def onMissionComplete(self, selectedPlayers, sabotaged):
        """Callback once the players have been chosen.
        @param selected     List of players that participated in the mission.
        @param sabotaged    Boolean whether the misison was sabotaged or not."""
        self.turn += 1
        if self.spy and sabotaged: 
            self.winturns += 1
        if not self.spy and not sabotaged: 
            self.winturns += 1
        
        if not self.spy:
            for p in selectedPlayers:
                if sabotaged:
                    self.players[p.index].wasAmongSpies(len(selectedPlayers), 
                                                        self.turn, self.winturns)                    
                else:
                    self.players[p.index].wasSafe(len(selectedPlayers), 
                                                  self.turn, self.winturns)
                    
            for pin in range(5):
                inteam = pin in [x.index for x in selectedPlayers]                    
                if sabotaged:
                    if self.lastvotes[pin]:
                        self.players[pin].votedForSpies(len(selectedPlayers), inteam, 
                                                            self.turn, self.winturns)
                    else:
                        self.players[pin].unvotedForSpies(len(selectedPlayers), inteam,
                                                            self.turn, self.winturns)
                    
                else:
                    if self.lastvotes[pin]:
                        self.players[pin].unvotedForGood(len(selectedPlayers), inteam,
                                                         self.turn, self.winturns)
                    else:
                        self.players[pin].votedForGood(len(selectedPlayers), inteam,
                                                       self.turn, self.winturns)

    def onGameComplete(self, players, spies):
        """Callback once the game is complete, and everything is revealed.
        @param players      List of all players in the game.
        @param spies        List of only the spies in the game."""
        for p in players:
            self.players[p.index].accAccurateness(p in spies, self.players[p.index].spyness())
        