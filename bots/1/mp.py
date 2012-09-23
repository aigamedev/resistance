"""
@name: Magi Bot
@author: Marcos Perez
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
"""

from player import Bot, Player
from game import State
import random


class MissionedTeam:
    
    def __init__(self,team,sabotages):
        self.team=team
        self.sabotages=sabotages


class Statistic:
    def __init__(self,defaultVal=0.0,minSucesos=1):
        self.ocurrences=0.0
        self.totalSucesos=0.0
        self.defaultVal=defaultVal
        self.minSucesos=minSucesos
    def ocurrence(self):
        self.ocurrences=self.ocurrences+1
        self.totalSucesos+=1
    def notOcurrence(self):
        self.totalSucesos+=1
    def update(self,ocurence):
        if ocurence:
            self.ocurrence()
        else:
            self.notOcurrence()
    def probability(self):
        if self.totalSucesos>=self.minSucesos:
            return self.ocurrences/self.totalSucesos
        else:
            return self.defaultVal
    def hasEnoughtSamples(self,minSucesos):
        return self.totalSucesos>=minSucesos
    def copy(self):
        myCopy=Statistic()
        myCopy.ocurrences=self.ocurrences
        myCopy.totalSucesos=self.totalSucesos
        myCopy.defaultVal=self.defaultVal
        myCopy.minSucesos=self.minSucesos
        return myCopy    
                
class PlayerStats:
    def __init__(self):
        self.playersStats={}
    def registerPlayer(self,player):
        if player.name not in self.playersStats:
            self.playersStats[player.name]={}
    def ocurence(self,suceso,player,state):
        self.update(suceso, player, True, state)
    def notOcurrence(self,suceso,player,state):
        self.update(suceso, player, False, state)
    def probabilityInternal(self,suceso,player):
        self.registerPlayer(player)
        playerStats=self.playersStats[player.name]
        if suceso not in playerStats:
            playerStats[suceso]=Statistic()
        return playerStats[suceso].probability()
    def enoughtData(self,suceso,player,minSamples):
        self.registerPlayer(player)
        playerStats=self.playersStats[player.name]
        if suceso not in playerStats:
            playerStats[suceso]=Statistic()
        return playerStats[suceso].hasEnoughtSamples(minSamples)    
    def probability(self,suceso,player,defaultValue=0.0,minSamples=1,hierachicalProbability=False,gameState=None):
        if gameState is not None and hierachicalProbability:
            if self.enoughtData(suceso+str(gameState.turn)+"-"+str(gameState.tries), player,minSamples):
                return self.probabilityInternal(suceso+str(gameState.turn)+"-"+str(gameState.tries), player)
            elif self.enoughtData(suceso+str(gameState.turn), player,minSamples):
                return self.probabilityInternal(suceso+str(gameState.turn), player)
        if self.enoughtData(suceso, player,minSamples):
            return self.probabilityInternal(suceso, player) 
        else:
            return defaultValue
    def update(self,suceso,player,ocurrence,gameState=None):
        self.updInternal(suceso, player, ocurrence)
        if gameState is not None:
            self.updInternal(suceso+str(gameState.turn), player, ocurrence)
            self.updInternal(suceso+str(gameState.turn)+"-"+str(gameState.tries), player, ocurrence)
            #self.updInternal(suceso+str(gameState.leader), player, ocurrence)
            
    def updInternal(self,suceso,player,ocurrence):
        self.registerPlayer(player)
        playerStats=self.playersStats[player.name]
        if suceso not in playerStats:
            playerStats[suceso]=Statistic()
        playerStats[suceso].update(ocurrence)        
    def copy(self):
        myCopy=PlayerStats()
        for playerName in self.playersStats:
            myCopy.playersStats[playerName]={}
            for suceso in self.playersStats[playerName]:
                myCopy.playersStats[playerName][suceso]=self.playersStats[playerName][suceso].copy()
        return myCopy

class GameState:
    
    def __init__(self,players):
        self.leader=None
        self.tries=1
        self.turn=1
        self.players=players
        self.votes=[]
        self.selectedTeams=[]
        self.lostTurns=0
        self.team=[]
        self.missionedTeams=[]
        self.selectionResults=[]
    def voteComplete(self,votes):
        self.selectedTeams.append(self.team)
        self.votes.append(votes)
#["Sabotear","VotarAFavorDeUnSpia","VotarEnContraDeUnSpia","SeleccionarSaboteo","SeleccionarOk","NoSabotear"]
class PlayerAsignment:
    
    
    def __init__(self,resistance,spies):
        self.resistance=resistance
        self.spies=spies
        self.playersStats={}
        self.sabotages=[]
        self.isValid=False
        #there are 6 posible player asignments given the fact that i'm from resistance
        self.probability=1.0/6.0
    def isPosible(self):
        return self.probability>0
    def alwaysTrue(self):
        return self.probability==1

class Rule:
    def __init__(self,spyStats,rsStats):
        self.spyStats=spyStats
        self.rsStats=rsStats
        self.init()
        pass
    def init(self):
        pass
    def applies(self,state,action,data,asignments):
        return False
    def updateModel(self,asignments,state, action,data):
        if self.applies(state, action, data,asignments):
            return self.upd(asignments,state, action,data)
            
    def upd(self,asignments,state, action,data):
        pass
    def spyProbability(self,asignments,p):
        pSpy=0
        for a in asignments:
            if p in a.spies:
                pSpy+=a.probability
        return pSpy
        
class Actions:
    SABOTAGE="Sabotage"
    VOTE="Vote"
    ACCOMPLISHED="Acomplished"
    SELECT="Select"

class Probabilities:
    VOTE_ON_TEAMS_WITH_SPIES="VoteOnTeamWithSpies"
    SELECT_SPY_TEAMS="SelectSpyTeams"
    VOTE_ON_HE="VoteOnHe"
    VOTE_ON_OTHER_SPIES="VOTE_ON_OTHER_SPIES"
    VOTE_ON_SPIES="VOTE_ON_SPIES"
    VOTE_ON_RESISTENCE="VoteSuccessfull"
    VOTE_ON_TWOSPY_TEAM="VoteOnTwoSpyTeam"
    SABOTAGE="Sabotage"
    SELECT_HIMSELF="SELECTHIMSELF"
    SELECT_SPIES="SELECT_SPIES"
    SABOTAGE_ON_TWO_SPIE_TEAM="SABOTAGE_ON_TWO_SPIE_TEAM"
    VOTE_ON_THREETEAMS_WHEREHE_ISNT="VOTE_ON_THREETEAMS_WHEREHE_ISNT"

        

class SabotageRule(Rule):
    def applies(self, state, action,data,asignments):
        return action==Actions.SABOTAGE and data>=0
    def upd(self, asignments, state, action, sabotages):
        probSum=0
        for a in asignments:
            spiesOnTeam=0
            for p in state.team:
                if p in a.spies:
                    spiesOnTeam=spiesOnTeam+1
            if spiesOnTeam<sabotages:
                a.probability = 0
            if spiesOnTeam==2 and sabotages==1:
                a.probability=min(a.probability,
                                  (self.spyStats.probability(Probabilities.SABOTAGE_ON_TWO_SPIE_TEAM,a.spies[1],0.0,5)+
                                  self.spyStats.probability(Probabilities.SABOTAGE_ON_TWO_SPIE_TEAM,a.spies[0],0.0,5))*0.5)    
            probSum += a.probability
        
        if probSum>0:
            adjustCoef=1/probSum
            for a in asignments:
                a.probability=a.probability*adjustCoef
        return state.team


class VoteAgainsMissionLeader(Rule):
    def init(self):
        self.checkVotes=[]
    def applies(self, state, action, data,asignments):
        if action== Actions.SABOTAGE:
                self.checkVotes.append(state.team)
        if len(state.team)==2 and action==Actions.VOTE and not data.vote and state.lostTurns>0:
            if data.player in state.team and data.player!=state.leader:
                for t in self.checkVotes:
                    if data.player in t and state.leader in t:
                        return True
        
        return False
    def upd(self, asignments, state, action, data):
        pSpy=self.spyProbability(asignments, data.player)
        if pSpy>0 and pSpy<1:
            pRes=1-pSpy
            pVotoEnContraLuegoSaboteoSpia=0.1
            pVotoEnContraLuegoSaboteoRs=1.0
            denominator=(pSpy*(pVotoEnContraLuegoSaboteoSpia-pVotoEnContraLuegoSaboteoRs)+pVotoEnContraLuegoSaboteoRs)
            if denominator>0:
                newPSpy=(pVotoEnContraLuegoSaboteoSpia*pSpy)/denominator
                newPRs=1-newPSpy
                for a in asignments:
                    if data.player in a.spies:
                        a.probability=a.probability*(newPSpy/pSpy)
                    else:
                        a.probability=a.probability*(newPRs/pRes)

class AcomplishedRule(Rule):
    def applies(self, state, action,data,asignments):
        return action==Actions.ACCOMPLISHED
    def upd(self, asignments, state, action, sabotages):
        for p in state.team:
            pSpy=self.spyProbability(asignments, p)
            if pSpy>0 and pSpy<1:
                pRes=1-pSpy
                pNoSaboteoSiendoSpia=1-self.spyStats.probability(Probabilities.SABOTAGE,p,1.0,40)
                #assert pNoSaboteoSiendoSpia<0.5,p.name+str(pNoSaboteoSiendoSpia)
                pNoSaboteoSiendoResistencia=1.0
                denominator=(pRes*(pNoSaboteoSiendoResistencia-pNoSaboteoSiendoSpia)+pNoSaboteoSiendoSpia)
                if denominator>0:
                    newPRs=(pNoSaboteoSiendoResistencia*pRes)/denominator
                    newPSpy=1-newPRs
                    for a in asignments:
                        if p in a.resistance:
                            a.probability=a.probability*(newPRs/pRes)
                        else:
                            a.probability=a.probability*(newPSpy/pSpy)

class LastTryVote(Rule):
    def applies(self, state, action, data,asignments):
        return state.tries==5 and action==Actions.VOTE and not data.vote
    def upd(self, asignments, state, action, data):
        probSum=0
        for a in asignments:
            spiesOnTeam=0
            if data.player in a.spies:
                spiesOnTeam=spiesOnTeam+1
            if spiesOnTeam==0:
                a.probability = 0
            probSum += a.probability
        
        if probSum>0:
            adjustCoef=1/probSum
            for a in asignments:
                a.probability=a.probability*adjustCoef                

class NoVoteOnSuccessfullTeamTeams(Rule):
    def init(self):
        self.accomplishedPlayers=[]
    def applies(self, state, action, data,asignments):
        if action==Actions.ACCOMPLISHED:
            for p in state.team:
                self.accomplishedPlayers.append(p)
        elif action==Actions.SABOTAGE:
            for p in state.team:
                if p in self.accomplishedPlayers:
                    self.accomplishedPlayers.remove(p)
        if action==Actions.VOTE and not data.vote:
            for p in state.team:
                if p not in self.accomplishedPlayers:
                    return False
            return True
        else:
            return False
                
    def upd(self, asignments, state, action, data):
        pSpy=self.spyProbability(asignments, data.player)
        if pSpy>0 and pSpy<1:
            pRes=1-pSpy
            pVotoEnContraLuegoSaboteoSpia=1.0
            pVotoEnContraLuegoSaboteoRs=0.2
            denominator=(pSpy*(pVotoEnContraLuegoSaboteoSpia-pVotoEnContraLuegoSaboteoRs)+pVotoEnContraLuegoSaboteoRs)
            if denominator>0:
                newPSpy=(pVotoEnContraLuegoSaboteoSpia*pSpy)/denominator
                newPRs=1-newPSpy
                for a in asignments:
                    if data.player in a.spies:
                        a.probability=a.probability*(newPSpy/pSpy)
                    else:
                        a.probability=a.probability*(newPRs/pRes)         

class NoVoteOnTeamsOfThreeWhereHeIsNot(Rule):
    def applies(self, state, action, data,asignments):
        return action==Actions.VOTE and len(state.team)==3 and data.player not in state.team
    
    def upd(self, asignments, state, action, data):
        pSpy=self.spyProbability(asignments, data.player)
        if pSpy>0 and pSpy<1:
            pRes=1-pSpy
            pVotoEnContraLuegoSaboteoSpia=self.spyStats.probability(Probabilities.VOTE_ON_THREETEAMS_WHEREHE_ISNT,data.player,0.9,5)
            pVotoEnContraLuegoSaboteoRs=self.rsStats.probability(Probabilities.VOTE_ON_THREETEAMS_WHEREHE_ISNT,data.player,0.0,5)
            if not data.vote:
                pVotoEnContraLuegoSaboteoSpia=1-self.spyStats.probability(Probabilities.VOTE_ON_THREETEAMS_WHEREHE_ISNT,data.player,0.9,5)
                pVotoEnContraLuegoSaboteoRs=1-self.rsStats.probability(Probabilities.VOTE_ON_THREETEAMS_WHEREHE_ISNT,data.player,0.0,5)
                
            denominator=(pSpy*(pVotoEnContraLuegoSaboteoSpia-pVotoEnContraLuegoSaboteoRs)+pVotoEnContraLuegoSaboteoRs)
            if denominator>0:
                newPSpy=(pVotoEnContraLuegoSaboteoSpia*pSpy)/denominator
                newPRs=1-newPSpy
                for a in asignments:
                    if data.player in a.spies:
                        a.probability=a.probability*(newPSpy/pSpy)
                    else:
                        a.probability=a.probability*(newPRs/pRes)     
class VoteOnSpies(Rule):
    def init(self):
        self.accomplishedPlayers=[]
    def applies(self, state, action, data, asignments):
        if action==Actions.VOTE and data.vote and state.tries<4:
            for p in state.team:
                pSpy=self.spyProbability(asignments, p)
                if pSpy>0.8:
                    return True
            return False
        else:
            return False
                
    def upd(self, asignments, state, action, data):
        pSpy=self.spyProbability(asignments, data.player)
        if pSpy>0 and pSpy<1:
            pRes=1-pSpy
            pVotoEnContraLuegoSaboteoSpia=self.spyStats.probability(Probabilities.VOTE_ON_SPIES,data.player,1.0,50)
            pVotoEnContraLuegoSaboteoRs=self.rsStats.probability(Probabilities.VOTE_ON_SPIES,data.player,0.1,50)
            denominator=(pSpy*(pVotoEnContraLuegoSaboteoSpia-pVotoEnContraLuegoSaboteoRs)+pVotoEnContraLuegoSaboteoRs)
            if denominator>0:
                newPSpy=(pVotoEnContraLuegoSaboteoSpia*pSpy)/denominator
                newPRs=1-newPSpy
                for a in asignments:
                    if data.player in a.spies:
                        a.probability=a.probability*(newPSpy/pSpy)
                    else:
                        a.probability=a.probability*(newPRs/pRes)
class SelectSpies(Rule):
    def init(self):
        self.accomplishedPlayers=[]
    def applies(self, state, action, data, asignments):
        if action==Actions.SELECT and data.vote and state.lostTurns>=1:
            for p in data.team:
                pSpy=self.spyProbability(asignments, p)
                if pSpy>0.7:
                    return True
            return False
        else:
            return False
                
    def upd(self, asignments, state, action, data):
        pSpy=self.spyProbability(asignments, data.player)
        if pSpy>0 and pSpy<1:
            pRes=1-pSpy
            pVotoEnContraLuegoSaboteoSpia=self.spyStats.probability(Probabilities.VOTE_ON_TEAMS_WITH_SPIES,data.player,1.0,50)
            pVotoEnContraLuegoSaboteoRs=self.rsStats.probability(Probabilities.VOTE_ON_TEAMS_WITH_SPIES,data.player,0.2,50)
            denominator=(pSpy*(pVotoEnContraLuegoSaboteoSpia-pVotoEnContraLuegoSaboteoRs)+pVotoEnContraLuegoSaboteoRs)
            if denominator>0:
                newPSpy=(pVotoEnContraLuegoSaboteoSpia*pSpy)/denominator
                newPRs=1-newPSpy
                for a in asignments:
                    if data.player in a.spies:
                        a.probability=a.probability*(newPSpy/pSpy)
                    else:
                        a.probability=a.probability*(newPRs/pRes)


    
 
class VoteData:
    def __init__(self,player,vote):
        self.player=player
        self.vote=vote                                                          
class SelectData:
    def __init__(self,player,team):
        self.player=player
        self.team=team

class SelectedTeam:
    def __init__(self,leader,team):
        self.leader=leader
        self.team=team
class Magi(Bot):
    """This is the base class for your AI in THE RESISTANCE.  To get started:
         1) Derive this class from a new file that will contain your AI.  See
            bots.py for simple stock AI examples.

         2) Implement mandatory API functions below; you must re-implement
            those that raise exceptions (i.e. vote, select, sabotage).

         3) If you need any of the optional callback API functions, implement
            them (i.e. all functions named on*() are callbacks).

       Aside from parameters passed as arguments to the functions below, you 
       can also access the game state via the self.game variable, which contains
       a State class defined in game.py.

       For debugging, it's recommended you use the self.log variable, which
       contains a python logging object on which you can call .info() .debug()
       or warn() for instance.  The output is stored in a file in the #/logs/
       folder, named according to your bot. 
    """
    
    globalSpyPlayerStats=PlayerStats()
    globalResistancePlayerStats=PlayerStats()
   
    lastSelected=None
    sabotageIdx=0
    selectSabotageIdx=3
    noSabotearIdx=5
    noSelSabotearIdx=4
    definitiveSpies=[]
    baseModelsPerName={}
    def onGameRevealed(self, players, spies):
        """This function will be called to list all the players, and if you're
        a spy, the spies too -- including others and yourself.
        @param players  List of all players in the game including you.
        @param spies    List of players that are spies, or an empty list.
        """
        self.gatheringInfo=False
        self.spies=spies
        self.updSpyStats=self.globalSpyPlayerStats.copy()
        self.updResistanceStats=self.globalResistancePlayerStats.copy()
        self.gameState=GameState(players)
        self.deceives=[]
        self.trusts={}
        self.definitiveSpies=[]
        self.playerStats={}
        self.hmms=[]
        self.otherPlayers=self.others()
        a=self.otherPlayers[0]
        b=self.otherPlayers[1]
        c=self.otherPlayers[2]
        d=self.otherPlayers[3]
        abCDModel=PlayerAsignment([a,b],[c,d])
        acBDModel=PlayerAsignment([a,c],[b,d])
        adBCModel=PlayerAsignment([a,d],[b,c])
        bcadModel=PlayerAsignment([b,c],[a,d])
        bdacModel=PlayerAsignment([b,d],[a,c])
        cdabModel=PlayerAsignment([c,d],[a,b])
        self.players=players
        self.hmms.append(abCDModel)
        self.hmms.append(acBDModel)
        self.hmms.append(adBCModel)
        self.hmms.append(bcadModel)
        self.hmms.append(bdacModel)
        self.hmms.append(cdabModel)
        self.changed= True
        self.gameState.lostTurns=0
        self.bestModel=None
        self.rules=[]
        spyStats=self.globalSpyPlayerStats
        rsStats=self.globalResistancePlayerStats
        
        self.rules.append(SabotageRule(spyStats,rsStats))
        self.rules.append(VoteAgainsMissionLeader(spyStats,rsStats))
        self.rules.append(AcomplishedRule(spyStats,rsStats))
        self.rules.append(LastTryVote(spyStats,rsStats))
        self.rules.append(NoVoteOnSuccessfullTeamTeams(spyStats,rsStats))
        self.rules.append(VoteOnSpies(spyStats,rsStats))
        self.rules.append(SelectSpies(spyStats,rsStats))
        self.rules.append(NoVoteOnTeamsOfThreeWhereHeIsNot(spyStats,rsStats))
        self.burned=False
        self.otherBurned=False
        self.otherSelected=False
        pass
    def bestPrediction(self):
        if self.changed:
            bestModels=[]
            bestIdx=1000
            for md in self.hmms:
                tstIdx=0.0
                for md2 in self.hmms:
                    if md2!=md:
                        for p in md2.spies:
                            if p not in md.spies:
                                tstIdx+=md2.probability*self.updSpyStats.probability(Probabilities.SABOTAGE,p,1.0,30)
                                
                if tstIdx<bestIdx:
                    bestModels=[md]
                    bestIdx=tstIdx
                elif tstIdx==bestIdx:
                    bestModels.append(md)
            self.bestModel=bestModels[0]  
            self.changed=False
            #if bestIdx<=0.1:
                #assert False
                            
        return self.bestModel
    def bestPredictionB(self):
        if self.changed:
            self.bestModel=None
            bestIdx=-1
            for md in self.hmms:
                tstIdx=md.probability
                if tstIdx>bestIdx:
                    self.bestModel=md
                    bestIdx=tstIdx
            self.changed=False
            #if bestIdx<=0.1:
                #assert False
                            
        return self.bestModel
    def onMissionAttempt(self, mission, tries, leader):
        """Callback function when a new turn begins, before the
        players are selected.
        @param mission  Integer representing the mission number (1..5).
        @param tries    Integer count for its number of tries (1..5).
        @param leader   A Player representing who's in charge.
        """
        self.gameState.tries=tries
        self.gameState.turn=mission
        self.gameState.leader=leader
        pass

    def select(self, players, count):
        """Pick a sub-group of players to go on the next mission.
        @param players  The list of all players in the game to pick from.
        @param count    The number of players you must now select.
        @return list    The players selected for the upcoming mission.
        """
        others=[p for p in self.others() if p not in self.spies]
        
        if self.spy:                    
            if self.burned:
                return [self]+ random.sample(others,count-1)
            elif self.otherBurned and not self.otherSelected:
                return [p for p in self.spies if p != self]+ random.sample(others,count-1)
            elif not self.otherBurned and not self.otherSelected:
                return [p for p in self.spies if p != self]+ random.sample(others,count-1)
            else:
                return random.sample(self.spies,1)+ random.sample(others,count-1)
        
            
        otherResistanceMembers=self.predictedResistance()
        #random.shuffle(otherResistanceMembers)
        assert otherResistanceMembers[1] is not None,"error en la ressitencia"
       
        if count==3:                    
            return [self,otherResistanceMembers[0],otherResistanceMembers[1]]
        else:
            return [self,otherResistanceMembers[0]]

    def onTeamSelected(self, leader, team):
        """Called immediately after the team is selected to go on a mission,
        and before the voting happens.
        @param leader   The leader in charge for this mission.
        @param team     The team that was selected by the current leader.
        """
        self.lastLeader=leader
        self.lastSelected=team
        self.gameState.team=team
        self.gameState.leader=leader
        self.updResistanceStats.update(Probabilities.SELECT_HIMSELF,leader,leader in team,self.gameState)
        self.gameState.selectionResults.append(SelectedTeam(leader,team))
        if leader!=self and leader in self.spies:
            self.otherSelected=True
        pass
    def predictedSpies(self):
        return self.bestPrediction().spies
    def predictedResistance(self):
        return self.bestPrediction().resistance
    def vote(self, team):
        """Given a selected team, decide whether the mission should proceed.
        @param team      List of players with index and name. 
        @return bool     Answer Yes/No.
        """
       
        if self.game.tries == 5:
            return True
        if self==self.game.leader:
            return True
        if self.spy and len(team) == 3 and len([p for p in team if p in self.spies])>0:
            return True
        elif self.spy and len(team)==3:
            return False
        
        if len(team) == 3 and not self.index in [p.index for p in team]:
            return False
        
        if self.spy and not self in team:
            return random.random()>0.5
        
        if self.gameState.lostTurns>0:
            for p in team:
                if p in self.predictedSpies():
                    return False            
                
        return True    
    def onVoteComplete(self, votes):
        """Callback once the whole team has voted.
        @param votes        Boolean votes for each player (ordered).
        """
        self.gameState.voteComplete(votes)
        
        for i,p in enumerate(self.players):
            vote=votes[i]
            if p not in self.gameState.team:
                self.updSpyStats.update(Probabilities.VOTE_ON_THREETEAMS_WHEREHE_ISNT,p,vote,self.gameState)
            for r in self.rules:
                r.updateModel(self.hmms,self.gameState,Actions.VOTE,VoteData(p,vote))
        
        self.changed=True
        
        pass

    def sabotage(self):
        """Decide what to do on the mission once it has been approved.  This
        function is only called if you're a spy, otherwise you have no choice.
        @return bool        Yes to shoot down a mission.
        """
        self.burned=True
        return self.spy and not len([p for p in self.gameState.team if p in self.spies]) > 1

    def onMissionComplete(self, sabotaged):
        """Callback once the players have been chosen.
        @param selected     List of players that participated in the mission.
        @param sabotaged    Integer how many times the mission was sabotaged.
        """
        
        for p in self.gameState.team:
            self.updSpyStats.update(Probabilities.SABOTAGE,p,sabotaged>0,self.gameState)
        
        self.gameState.missionedTeams.append(MissionedTeam(self.gameState.team,sabotaged))
        self.gameState.turn=self.game.turn
        for r in self.rules:
            if sabotaged>0:
                r.updateModel(self.hmms,self.gameState,Actions.SABOTAGE,sabotaged)
            else:
                r.updateModel(self.hmms,self.gameState,Actions.ACCOMPLISHED,sabotaged)
        self.changed=True
        if sabotaged>0:
            self.gameState.lostTurns+=1
        
        if self in self.gameState.team:
            self.burned=True
        for p in self.spies:
            if p!=self and p in self.gameState.team:
                self.otherBurned=True
        
        pass

    def onGameComplete(self, win, spies):
        """Callback once the game is complete, and everything is revealed.
        @param win          Boolean if the Resistance won.
        @param spies        List of only the spies in the game.
        """
        
        for i,votes in enumerate(self.gameState.votes):
            votedTeam=self.gameState.selectedTeams[i]
            spiesInTeam=len([s for s in votedTeam if s in spies])
            
            for j,vote in enumerate(votes):
                player=self.gameState.players[j]
                spyInTeam=player in spies
                
                if spiesInTeam==0:
                    self.updSpyStats.update(Probabilities.VOTE_ON_RESISTENCE,player,vote,None)
                    self.updResistanceStats.update(Probabilities.VOTE_ON_RESISTENCE,player,vote,None)
                elif spiesInTeam>=1:
                    if spyInTeam:
                        self.updSpyStats.update(Probabilities.VOTE_ON_HE,player,vote,None)
                        self.updResistanceStats.update(Probabilities.VOTE_ON_HE,player,vote,None)
                    else:
                        self.updSpyStats.update(Probabilities.VOTE_ON_OTHER_SPIES,player,vote,None)
                        self.updResistanceStats.update(Probabilities.VOTE_ON_OTHER_SPIES,player,None)
                    self.updSpyStats.update(Probabilities.VOTE_ON_SPIES,player,vote,self.gameState)
                    self.updResistanceStats.update(Probabilities.VOTE_ON_SPIES,player,vote,None)    
                    if spiesInTeam>1:
                        self.updSpyStats.update(Probabilities.VOTE_ON_TWOSPY_TEAM,player,vote,None)
                        self.updResistanceStats.update(Probabilities.VOTE_ON_TWOSPY_TEAM,player,vote,None)
        for ms in self.gameState.missionedTeams:
            #ms=MissionedTeam()
            spiesOnTeam=len([s for s in ms.team if s in spies])
            if spiesOnTeam>1:
                for p in ms.team:
                    self.updSpyStats.update(Probabilities.SABOTAGE_ON_TWO_SPIE_TEAM,p,spiesOnTeam<ms.sabotages,None)
                
        for sel in self.gameState.selectionResults:
            #sel=SelectedTeam()
            spiesInTeam=len([s for s in sel.team if s in spies])
            self.updSpyStats.update(Probabilities.SELECT_SPIES,sel.leader,spiesInTeam>0,self.gameState)
            self.updResistanceStats.update(Probabilities.SELECT_SPIES,sel.leader,spiesInTeam>0,self.gameState)
        for p in self.game.players:
            if p in spies and p.name in self.updSpyStats.playersStats:
                self.globalSpyPlayerStats.playersStats[p.name]=self.updSpyStats.playersStats[p.name]
            elif p.name in self.updResistanceStats.playersStats:
                self.globalResistancePlayerStats.playersStats[p.name]=self.updResistanceStats.playersStats[p.name]       
        
                
         
        pass
