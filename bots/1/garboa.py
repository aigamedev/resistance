"""
@name: GarboA Bot
@author: Alberto Uriarte and Josep Valls-Vargas (Drexel University)
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
"""

import random

from player import Bot
import itertools
import logging
import collections
        
class GarboA(Bot):
    def onGameRevealed(self, players, spies):
        self.spies = spies
        self.players = players
        self.suspicion = {}
        self.missions_done = {}
        for player in players:
            self.suspicion[player]=0
            self.missions_done[player]=0
        self.me = [p for p in players if p.index == self.index][0]
        self.others = [p for p in players if not p.index == self.index]
        
        self.log2 = self.log
        def nolog(params):
            pass
        if self.spy:
            self.log.debug = nolog
        self.log.debug("---GAME %s---" % str(self.me))
        self.log.debug(spies)
    def select(self, players, count):
        if(self.spy):
            # spy with lowest suspicion + resistance with lowest suspicion
            return [sorted(list(self.spies),key=lambda i:self.suspicion[i])[0]] + sorted([i for i in players if i not in self.spies],key=lambda i:self.suspicion[i])[0:count-1]
        else:
            # if we have to pick 3 players, we should include ourselves to minimize having a spy
            # if we are among the least suspicious players, we include ourselves
            if count > 2 or (self.me in sorted(self.suspicion.items(),key=lambda i:i[1])[0:2]):
                # myself + the least supicious of the remaining players 
                return [self.me] + sorted(self.others,key=lambda i:self.suspicion[i])[0:count-1]
            else:
                # least suspicious players 
                return sorted(self.game.players,key=lambda i:self.suspicion[i])[0:count]

    def onMissionComplete(self, sabotaged):
        # fact spy = 1000
        # fact res= -1000
        # suspicion ~100
        team = self.game.team
        no_team = [p for p in self.game.players if p not in self.game.team]
        for p in self.game.team:
            self.missions_done[p] += 1
        if sabotaged:
            # the team is suspicious
            if self.me not in self.game.team:
                if len(team)==2 and sabotaged==2:            
                    for p in team:
                        self.suspicion[p] += 1000
                    for p in no_team:
                        self.suspicion[p] -= 1000
                if len(team)==2 and sabotaged==1:
                    for p in team:
                        self.suspicion[p] += 50
                if len(team)==3 and sabotaged==2:
                    for p in team:
                        self.suspicion[p] += 100
                    for p in no_team:
                        self.suspicion[p] -= 1000
                if len(team)==3 and sabotaged==1:
                    for p in team:
                        self.suspicion[p] += 25
            else:
                if len(team)==2 and sabotaged==1:
                    for p in [p for p in team if not p==self.me]:
                        self.suspicion[p] += 1000
                    self.suspicion[self.me] += 50
                if len(team)==3 and sabotaged==2:
                    for p in [p for p in team if not p==self.me]:
                        self.suspicion[p] += 1000
                    self.suspicion[self.me] += 100
                    for p in no_team:
                        self.suspicion[p] -= 1000
                if len(team)==3 and sabotaged==1:
                    for p in [p for p in team if not p==self.me]:
                        self.suspicion[p] += 50
                    self.suspicion[self.me] += 25
            # the leader and voters are suspicious
            self.voterPenalites(team)
        else:
            if len(team)==2:
                for p in team:
                    self.suspicion[p] -= 50
            else:
                for p in team:
                    self.suspicion[p] -= 25   
        self.log.debug("---ROUND %d %s ---" % (self.game.turn,str(self.me)))
        self.log.debug(sabotaged)
        self.log.debug(self.game.team)
        self.log.debug(self.suspicion)
    def voterPenalites(self,team):
            if self.game.turn>1 and max([self.suspicion[i] for i in team])>=100:
                self.suspicion[self.game.leader] += 40
                for p in filter(lambda i:self.last_votes[i.index] and not i==self.game.leader, self.game.players):
                    self.suspicion[p]+=20
            if len(team)==3 and max([self.suspicion[i] for i in team])>=50:
                for i in [i for i in self.players if i not in team and self.last_votes[i.index]]:
                    self.suspicion[i] += 700 
    def onGameComplete(self, win, spies):
        self.log.debug("---END %s ---" % str(self.me))
        self.log.debug(self)
        self.log.debug(spies)
        self.log.debug(self.suspicion) 
    def sabotage(self):
        return self.spy 
    def vote(self, team):
        self.log.debug("---VOTING %d %s ---" % (self.game.tries,str(self.me)))
        self.log.debug(self.game.leader)
        self.log.debug(team)
        if self.game.tries == 5: return True
        suspects = sorted(self.game.players,key=lambda i:self.suspicion[i])
        suspects2 = [p for p in suspects if not p==self.me]
        if self.spy:
            return len([p for p in team if p in self.spies])>0
        else:
            # We need data
            if self.game.turn == 1: return True 
            if suspects[-1] in team: return False
            if len(team)==2:
                if self.me in team and suspects[-2] in team: return False    
            elif len(team)==3:
                # There is going to be a spy if it is not all resistance members, we want in
                if self.me not in team:
                    return False
                elif suspects2[-1] in team or suspects[-2] in team:
                    return False
        return True  
    def onVoteComplete(self, votes):
        our = votes[self.index]
        if self.game.turn>1 and self.game.tries<5:
            for i in self.game.players:
                if not votes[i.index]==our:
                    self.suspicion[i]+=8
            team = self.game.team
            team_filtered = filter(lambda i:self.suspicion[i]<750,team)
            if self.me not in team and len(team)==3 and len(team_filtered)<3:              
                not_team_voted_true = [i for i in self.game.players if i not in team and votes[i.index]]
                for i in not_team_voted_true:
                    self.suspicion[i]+=500
            if self.me not in team and len(team)==3:
                for i in [i for i in self.game.players if i not in team and votes[i.index]]:
                    self.suspicion[i]+=400
            # When there there is a spy NOT in the team, voting AGAINST the team, let's assume there are no spies on the team
            if len(filter(lambda i:self.suspicion[i]>750 and i not in team and not votes[i.index],self.game.players))>0:
                for i in self.game.team:  
                    self.suspicion[i]-=600
            
        self.last_votes = votes
        self.log.debug("---VOTES %s ---" % str(self.me))
        self.log.debug(votes)
