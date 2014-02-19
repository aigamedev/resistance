import random
import operator

from player import Player

class IAmNotASpyPlayer(Player):
    
    def __init__(self, index, spy):
        self.round=1
        self.blues = 0
        self.red = 0
        Player.__init__(self, "IAmNotASpy", index, spy)
        
    def onVoteComplete(self, players, votes, team):
        self.team = team
            
    def onMissionComplete(self, selectedPlayers, sabotaged):
        #print "Round ", self.round, " sabotaged ", sabotaged        
        self.round = self.round+1
        if sabotaged:
            self.blues+=1
        else:
            self.red+=1
        if self.round>5:
            self.round=1
        
        for p in selectedPlayers:
            self.stats[p.index] += sabotaged*sabotaged;
        #print self.stats    
            
    def reveal(self, players, spies):
        self.players = players
        self.spies = spies
        self.stats = [0]*len(players)
        
    def isSpy(self, player):
        for s in self.spies:
            if (player.index == s.index):
                return True
        return False 


    def select(self, players, count):
        me = [p for p in players if p.index == self.index]

        # As a spy, pick myself and others who are not spies.
        if self.spy:
            others = [p for p in players if p not in self.spies]
            return me + random.sample(others, count-1)
        # As resistance, pick myself also and others randomly.
        else:                    
            couples = zip(self.stats, [p.index for p in players])
            #print "c:  ", couples
            #print "sc: ", sorted(couples)
            others=[]
            k=0
            for s,i in sorted(couples):
                #print "s=",s," i=", i
                if (self.index!=i):
                    others += [p for p in players if p.index == i]
                    k +=1
                if k==count-1:
                    break 
                      
            #others = [p for p in players if p.index != self.index]
            return me + others
    
    def vote(self, team, leader, tries): 
        if self.spy:
            if  len([p for p in team if p in self.spies])<1:
                return False
            elif len([p for p in team if p in self.spies])==1:
                return True
            elif len([p for p in team if p in self.spies])>1 and self.red==2:
                return True
            else: #TODO: Deal with this case: more spies and not last turn 
                return random.choice([True, False, False])
        else: #TODO: Better voting strategy for resistance
            if tries >= 3:
                return True
            #return False
            sumStat=0
            for p in team:
                sumStat += self.stats[p.index]
            if sumStat <= self.round:
                return True
            else:
                return False
            #return random.choice([True, False])
 
    def sabotage(self,team):
        if not self.spy:
            return False
        else: 
            return True
                
            