import random

from player import Player

class SoreLooser(Player):

    me = {}
    accomplice = {}
    
    good = {}

    lastVote = False
	
    def __init__(self, index, spy):
        Player.__init__(self, "SoreLooser", index, spy)
        
        # This information is local and stored for one game only.
        self.local_statistics = {}

    def reveal(self, players, spies):
        me = [p for p in players if p.index == self.index]
        
        self.players = players
        self.spies = spies
        self.me = [p for p in players if p.index == self.index]
        
        self.good = {}
        
        # create good
        for p in players:
            self.good.update({p:0})
          
        self.good.update({p:100})

        if (self.spy):
            for p in spies:
                if p.index<>self.me.index:
                    self.accomplice = p                    
        pass


    def select(self, players, count):
        # who am i
        me = [p for p in players if p.index == self.index]
        
        # As a spy, pick myself and others who are not spies.
        if self.spy:
            others = [p for p in players if p not in self.spies]
            return me + random.sample(others, count-1)
        # As resistance, pick myself also and others randomly.
        else:
#             ORIGINAL CODE
#            others = [p for p in players if p.index != self.index]
#            return me + random.sample(others, count-1)
            sgood = sorted(self.good, key=self.good.__getitem__, reverse=True)	    	
            return sgood[0:count] 

    def vote(self, team, leader, tries): 
        # As a spy, vote for all missions that include a spy!
        if self.spy:
            return len([p for p in team if p in self.spies]) > 0

        # As resistance, always pass the fifth try.
        if tries >= 4:
            self.lastVote = True
            return True
            
        # If I'm not on the team and it's a team of 3!
        if len(team) == 3 and not self.index in [p.index for p in team]:
            self.lastVote = False
            return False

        #print "CHIAMA LA NOSTRA"
        sel = 0
        for s in team:        	
            sel = sel + self.good[s]
        sel = sel/len(team)            
            
        all = 0
        for s in self.good:
            all = all + self.good[s]
        all = all/5
            
        self.lastRound = team

        if (sel>all):
            self.lastVote = True
            return True
        else:
            self.lastVote = False
            return False
            
        # Otherwise, just approve the team and get more information. 
        self.lastVote = True
        return True

    def onVoteComplete(self, players, votes, team):
        # Remember this team for future reference!
        self.team = team
        
        if (not self.spy):
            i = 0
            for p in players:
               if (p<>self.me):
                  if (votes[i]==self.lastVote):
                      self.good[p] += 50
                  else:
                      self.good[p] -= 25
               i = i + 1

        
    def onMissionComplete(self, team, sabotaged):
        # Forget this failed team so we don't pick it!
        if sabotaged or self.spy:
            self.team = None

        if (not self.spy):
            for p in team:
                if sabotaged:
                    if (self.me<>p):
                        self.good.update({p:self.good[p]-100})
                else:
                    self.good.update({p:self.good[p]+100})
        pass

    def sabotage(self, team):
    
        if not self.spy:
            return False
        
        if len(team) == 2:
            #return random.choice([True, False])
            return False
            
        if len(team) == 3:
            if (self.accomplice in team and self.accomplice.index>self.me.index):
                return False
            else:
                return True
                                            
        return True

    def onGameComplete(self, players, spies):
        """Callback once the game is complete, and everything is revealed.
        @param players      List of all players in the game.
        @param spies        List of only the spies in the game."""
        
        me = [p for p in players if p.index == self.index]
        
        pass
