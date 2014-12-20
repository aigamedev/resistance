"""
@name: PandSBot
@author: Pavel Raliuk and Alex Paklonski
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
"""

import random
import math

from player import Bot 



class PandSBot(Bot):

    def onGameRevealed(self, players, spies):
        self.players = players
        self.spies = spies
        self.team = None        
        self.friends = [[Probability(0.4) for x in range(5)] for y in range(5)]
        self.suspects = [Probability(0.0) for x in range(5)]
        self.supportSuspects = [Variable(0.4, 1.0) for x in range(5)]
        self.suspeciousActions = [Variable(0,0) for x in range(5)] #player not in team, team == 3, votes
        self.possibleGoodActions = [Variable(0,0) for x in range(5)] #player in team, votes against team
        self.suspectsPair = [[(x,y),0] for x in range(5) for y in range(5) if x < y]

    def _updateSuspectsPair(self):

        for x in self.suspectsPair:
            spy1 = x[0][0]
            spy2 = x[0][1]
            #calculate how suspicious x[0] pair (spy1 friend for spy2, spy2 friend for spy1, and etc)
            estimate = self.suspects[spy1].estimate() * self.suspects[spy2].estimate();
            if estimate < 0.99:                 
                v = (0.50 + 0.50 * self.friends[spy1][spy2].estimate() * self.friends[spy2][spy1].estimate())
                v *= (0.75 + 0.25 * self.supportSuspects[spy1].estimate() * self.supportSuspects[spy2].estimate())
                v *= estimate
                v *= 0.4 + 0.6 * (self.suspeciousActions[spy1].estimate() + self.suspeciousActions[spy2].estimate())/2
                v *= 1 - 0.1 * (self.possibleGoodActions[spy1].estimate() + self.possibleGoodActions[spy2].estimate())/2
                x[1] = v
                #x[1] =(random.uniform(0.98, 1.0))*x[1]
            else:
                x[1] = estimate

    def _getSuspicious(self, spy1):
        v = (0.75 + 0.25 * self.supportSuspects[spy1].estimate())
        v *= self.suspects[spy1].estimate()
        v *= 0.4 + 0.6 * (self.suspeciousActions[spy1].estimate())
        v *= 1 - 0.1 * (self.possibleGoodActions[spy1].estimate())
        return v

    def _getBadPair(self):
        #get the most suspicious pair
        tmp = [x for x in self.suspectsPair if self.index not in x[0]]
        result = max(tmp, key=lambda p: (random.uniform(0.9, 1.0))*p[1])
        #result = tmp
        if result[0] > 0:#random.uniform(0, 0.5):-------------------------------------------
            return result[0],result[1]
        else:
            return []

    def _getGood(self):
        #get all players that is not in badPair
        bad, v = self._getBadPair()
        if v > 0:
            t = set(self._othersIndexes())-set(bad)
            result = sorted(t, key=lambda p: self._getSuspicious(p))
        else:
            result = sorted(self._othersIndexes(), key=lambda p: (p - self.game.leader.index + len(self.game.players))%len(self.game.players))
            
        return result


    def _othersIndexes(self):
        #all players indexes [1,2,...] except users
        return [x.index for x in self.others() ]

    def _playersIndexes(self):
        #all players indexes [1,2,...]
        return [x.index for x in self.game.players ]

    def _maybeLastTurn(self):
        return (self.game.losses == 2) or (self.game.wins == 2)

    def select(self, players, count):
        
        goodPlayers = self._getGood();
        badPair, v = self._getBadPair();

        #always include myself
        me = [p for p in players if p.index == self.index]

        
        #other variants from reliable players
        #variants = [p for p in players if p.index in goodPair and p not in self.spies]
        #num = min(len(variants), count - 1)
        #result = list(set( me + random.sample(variants, num)))
        result = me + [x for x in players if x.index in goodPlayers[0: count-1]]

        #if not enough add random
        if (len(result)<count):
            #self._getSortedGood()
            if not self.spy:
                self.log.info("get random=(")
            others = [p for p in players if p not in result]
            result += random.sample(others, count-len(result))
        return result

    def vote(self, team): 
        othersPeople = set(self.game.players)-set(team);

        #always vote for own team
        if self.game.leader == self:
            return True
        if self.game.turn==1 and self.game.tries == 1:
            return True
        
        badPair,v = self._getBadPair()

        teamIndexes = set([x.index for x in team])

        #As a spy, vote for all missions that include one spy!
        if self.spy:            
            spiesCount = len([p for p in team if p in self.spies])
            if spiesCount > 0: # or (spiesCount > 0 and self._maybeLastTurn()):
                return True
            return False

        # As resistance, always pass the fifth try.
        if self.game.tries == 5:
            return True
        # If I'm not on the team and it's a team of 3!
        if len(team) == 3 and not self.index in [p.index for p in team]:
            return False

        ## first round vote, because we do not have any information
        #if self.game.losses == 0:
        #    return True
        #do not vote for most suspicious pair
        if teamIndexes.intersection(badPair):
            return False
        if self.game.leader.index not in teamIndexes:
            return False  
        # Otherwise, just approve the team and get more information. 
        return True

    def onVoteComplete(self, votes):
        me = [p for p in self.game.players if p.index == self.index]
        votes = votes
        self.votes = votes;#to work properly votes[p.index]
        
        team = [p.index for p in set(self.game.team)-set(me)]
        notTeam = [p.index for p in set(self.game.players)-set(self.game.team)-set(me)];

        #leader didn't choose himself
        self.suspeciousActions[self.game.leader.index].sampleBool(self.game.leader.index not in team)

        for p1 in self._othersIndexes():

            # if 1st round, 1st try and player against - suspicious ----------------------------------
            self.suspeciousActions[p1].sampleBool( not self.votes[p1] and self.game.turn==1 and self.game.tries==1)

            # if 5th tries and player against - suspicious ----------------------------------
            self.suspeciousActions[p1].sampleBool( not self.votes[p1] and self.game.tries==5)

                
            #player out of team of 3 person, but vote, maybe he is spy (or stupid)
            self.suspeciousActions[p1].sampleBool( self.votes[p1] and len(self.game.team)==3 and p1 not in team)

            #player in team, but votes againts, possible he is good (or stupid=))
            self.possibleGoodActions[p1].sampleBool( not self.votes[p1] and p1 in team)

            if p1 == self.game.leader.index:
                #spy doesnot choose second spy in team
                for p2 in notTeam:
                    self.friends[p1][p2].sampleExt(1, len(notTeam))
            else:
                #anyone vote for team where he is, so more intrested in team without
                if p1 not in team:
                    # for all players that voted,  team are possible friends
                    if (self.votes[p1]):                        
                        for p2 in team:
                            self.friends[p1][p2].sampleExt(1, len(team))
                    else:
                        for p2 in notTeam:
                            self.friends[p1][p2].sampleExt(1, len(notTeam))                    
                    
        self._updateSuspectsPair()        
        self.team = None
    
    def _getIndexes(self, players):
        return [p.index for p in players]

    def onMissionComplete(self, sabotaged):

        #update possibility to be a spy
        maxSpies = 2

        team = [p.index for p in self.game.team if p.index != self.index]
        other = [p.index for p in self.game.players if p.index != self.index and p.index not in team]

        if sabotaged>0:
            for i in team:    
                self.suspects[i].sampleExt(sabotaged, len(team))

        if sabotaged<maxSpies:
            for i in other:    
                self.suspects[i].sampleExt(maxSpies-sabotaged, len(other))
      
        if self.game.turn > 1:
            for p in other:#[p.index for p in self.game.players if p.index != self.index]:
                val = int((self.votes[p] and sabotaged>0) or (not self.votes[p] and sabotaged==0))
                self.supportSuspects[p].sampleExt(val,1)

        self._updateSuspectsPair()        

    def sabotage(self):
        #return self.spy
        #sabotage only if one spy or last turn
        spiesCount = len([p for p in self.game.team if p in self.spies])
        return spiesCount == 1 or self._maybeLastTurn() or (spiesCount==2 and self.game.leader.index != self.index)
    
    def onGameComplete(self, win, spies):
        pass
        #if self.spy:
        #    return
        #if not win:
        #    opinion = (self._getBadPair())
        #    good = len(set(opinion) - set([p.index for p in spies]))==0;
        #    if not good:
        #        print "Fail=("
        #        print "Turn %s"%self.game.turn
        #        print "%s (%s)"%( good, spies)
        #        for pair in self.suspectsPair:
        #            if self.index not in pair[0]:
        #                s1 = pair[0][0]
        #                s2 = pair[0][1]
        #                print "%s : %0.2f (%s * %s)=%0.2f; (%s %s) (%s %s)"%((s1, s2), pair[1], self.friends[s1][s2], self.friends[s2][s1], self.friends[s1][s2].estimate() * self.friends[s2][s1].estimate() ,self.supportSuspects[s1],self.supportSuspects[s2], self.suspects[s1], self.suspects[s2])
        #        print "Suspects:"
        #        print self.suspects
        #        print "Support:"
        #        print self.supportSuspects
        #        print "Friends:"
        #        for x in self.friends:
        #            print x
        #        print "PossibleGoodAction: "
        #        print self.possibleGoodActions
        #        print "Suspicious Action:"
        #        print self.suspeciousActions

        #        #print "Friends delta:"
        #        #for x in self.friendsExclusive:
        #        #    print ["%0.2f%%"%(f*100) for f in x]
        #        print self.game.players
        #        print "(%s, %s)"%(opinion[0], opinion[1])
        #        pass
        #    else:
        #        print "OK=)"
        #else:
        #    print "OK=)"



class Variable(object):
    def __init__(self, v0, n0):
        self.total = v0
        self.samples = n0

    def sample(self, value):
        self.sampleExt(value, 1)

    def sampleBool(self, value):
        self.sampleExt(int(value), 1)

    def sampleExt(self, value, n):
        self.total += value
        self.samples += n

    def estimate(self):
        if self.samples > 0:
            return float(self.total) / float(self.samples)
        else:
            return 0.0
    def error(self):
            # We're dealing with potential results at 0% or 100%, so
            # use an Agresti-Coull interval (can't do a normal
            # Clopper-Pearson without requiring the numpy library, and
            # can't use the central limit theorem too close to the
            # extremes). Note this is still degenerate when the number
            # of samples is very small, and may give an upper bound >
            # 100%.
            n_prime = self.samples + 3.84 # 95% confidence interval
            value = (self.total + (3.84 * 0.5)) / n_prime
            error = 1.96 * math.sqrt(value * (1.0 - value) / n_prime)
            return error

    def estimateWithError(self):
        return self.estimate()-self.error()*0.25

    def estimateWithErrorRnd(self):
        val = self.estimate()-self.error()*random.uniform(0.0, 0.2)
        val = max(0, min(val,1))
        return val

    def __repr__(self):
        if self.samples:
            #return "%0.2f%% (%i)" % ((100.0 * float(self.total) / float(self.samples)), self.samples)
            return "%0.2f%% " % ((100.0 * float(self.total) / float(self.samples)))
        else:
            return "UNKNOWN"


class Probability(object):
    def __init__(self, v0):
        self.value = v0
        self.n = 0

    def sample(self, value):
        self.sampleExt(value, 1)

    def sampleExt(self, value, n):
        self.value = 1 - (1 - self.value)*(1 - float(value) / float(n))
        self.n += n
        
    def sampleExtNeg(self, value, n):
        self.value *= (1- float(value) / float(n))

    def estimate(self):
        return self.value

    def __repr__(self):
        #return "%0.2f%% (%i)" % (100.0 * float(self.value), self.n)
        return "%0.2f%% " % (100.0 * float(self.value))
