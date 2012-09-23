"""
@name: HartBot
@author: Jonas Hartmann <jonasharty@gmail.com>
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
@since: 02.08.2012
"""

from __future__ import division
from game import State
from genericpath import exists
from player import Bot
from token import EQUAL
import random

class HartBot(Bot):
    threshold = 0.1
    increaseValue = 0.35
    decreaseValue = 0.25
    initialSuspection = 0.5
        
    '''
    This bot was created by Jonas Hartmann for the RESISTANCE competition
    realized by the AiGameDev.com for the GameAiConference in Vienna 2012
    '''
    def onGameRevealed(self, players, spies):
        self._logInfo("Game was revealed for me -> " + str(self))
        
        # initialize variables
        self.team = None
        self.suspection = self._createSuspectionDict(players, spies)
        self._logSuspection()
        self.players = players
        # save only the other spies        
        self.spies = [p for p in spies if p.index not in [self.index]]
        
        if self.spy:
            self._logInfo("Other spies: ")
            for player in self.spies:
                self._logInfo(player)
       
        self._logInfo("Other players in this game: ")
        for player in self.others():
            self._logInfo(player)

        pass
    
    def select(self, players, count):
        """Pick a sub-group of players to go on the next mission.
        @param players  The list of all players in the game to pick from.
        @param count    The number of players you must now select.
        @return list    The players selected for the upcoming mission.
        """
        # As a spy, pick myself and others who are not spies.
        if self.spy:
            self._logInfo("[TEAM SELECTION] Me and resistance team...")
            others = [p for p in self.others() if p not in self.spies]
            return [self] + random.sample(others, count - 1)
            
        # As a resistance, I will choose a team which I could trust
        self._logInfo("[TEAM SELECTION] selecting the most trusted...")
        return self._selectMostTrustableTeam(count)
        
    def vote(self, team):
        """Given a selected team, decide whether the mission should proceed.
        @param team      List of players with index and name. 
        @return bool     Answer Yes/No.
        """
        # Always approve our own missions.
        if self.game.leader == self:
            self._logInfo ("Approving our own mission...")
            return True

        # Both types of factions have constant behavior on the last try.
        if self.game.tries == 5:
            self._logInfo ("This mission must pass or not pass! Returning " + str(not self.spy))
            return not self.spy
        
        # As a spy, only approve if there is a spy in the mission  
        if self.spy:      
            self._logInfo ("Approving mission only if there is a spy")
            if self in team:
                return True
            return len([sp for sp in team if sp in self.spies]) > 0

        # If I'm not on the team and it's a team of 3, there is a spy in the team!
        if len(team) == 3 and not self.index in [p.index for p in team]:
            self._logInfo("Not approving mission")
            return False        
        
        # Do not vote for suspicious teams
        for p in team:
            if self.suspection[p.index] > self.threshold:
                self._logInfo("Not approving mission, he is probably a spy -> " + str(p))
                return False
        
        self._logInfo("Approving mission")
        return True
    
    def sabotage(self):
        """Decide what to do on the mission once it has been approved.  This
        function is only called if you're a spy, otherwise you have no choice.
        @return bool        Yes to shoot down a mission.
        """
        # Always take the chance to sabotage the mission
        self._logInfo("Sabotage!!")
        return self.spy

    def onMissionComplete(self, sabotaged):
        self._adjustSuspection(self.team, sabotaged)
        self._logSuspection()
        
        self._logInfo("Mission completed")
        if sabotaged:
            self._logInfo("Mission was sabotaged " + str(sabotaged) + " times")
        else:
            self._logInfo("Mission succeeded")
        
        self._logInfo("Mission team: " + str(self.team))
        self._logInfo("-----------------------------")
        
        pass
    
    
    def onMissionAttempt(self, mission, tries, leader):
        """Callback function when a new turn begins, before the
        players are selected.
        @param mission  Integer representing the mission number (1..5).
        @param tries    Integer count for its number of tries (1..5).
        @param leader   A Player representing who's in charge.
        """
        pass
    
    def onTeamSelected(self, leader, team):
        """Called immediately after the team is selected to go on a mission,
        and before the voting happens.
        @param leader   The leader in charge for this mission.
        @param team     The team that was selected by the current leader.
        """
        self.team = team
        self._logInfo("Selected mission team: " + str(self.team))
        
        return
    
    def onVoteComplete(self, votes):
        """Callback once the whole team has voted.
        @param votes        Boolean votes for each player (ordered).
        """
        pass
    
    def onGameComplete(self, win, spies):
        """Callback once the game is complete, and everything is revealed.
        @param win          Boolean if the Resistance won.
        @param spies        List of only the spies in the game.
        """
        if win:
            self._logInfo("GAME COMPLETE! RESISTANCE WON!")
        else:
            self._logInfo("GAME COMPLETE! SPIES WON!")
        
        self.team = None
        self.suspection = None
        pass
    
    ''' =================== '''
    '''  Private functions  '''
    ''' =================== '''
    
    def _selectMostTrustableTeam(self, count):
        """ Select the players which have the lowest suspicious value
        @param count The number of players you must select
        @return list The players selected
        """
        sortedSuspection = sorted(self.suspection.items(), key=lambda t : t[1])
        sortedIndexes = [k for k, v in sortedSuspection]
        return [p for p in self.players if p.index in sortedIndexes[0:count]]
    
    def _createSuspectionDict(self, players, spies):
        """
        @return: dictionary
        """
        if self.spy:
            # As a spy I already know everything
            sdict = {}
            for player in players:
                if player in spies:
                    sdict[player.index] = 1.0
                else:
                    sdict[player.index] = 0.0
            return sdict
            
        # As a resistance...
        sdict = {}
        for p in players:
            if p.index == self.index:
                sdict[p.index] = 0.0
            else:
                sdict[p.index] = self.initialSuspection
        return sdict
        
    def _increaseSuspection(self, player, teamSize):
        # ignore myself
        if self.index == player.index:
            return
        
        index = player.index
        self._logInfo("Increasing suspection of player: " + str(player))
        self.suspection[index] = self.suspection[index] + self.increaseValue
            
    def _decreaseSuspection(self, player):
        # ignore myself
        if self.index == player.index:
            return
        
        index = player.index
        self._logInfo("Decreasing suspection of player: " + str(player))
        self.suspection[index] = self.suspection[index] - self.decreaseValue
        if (self.suspection[index] < 0):
            self.suspection[index] = 0.0

    def _adjustSuspection(self, team, sabotaged):
        """ Will be called after each mission to adjust the way I 
        think about the other players
        """
        if self.spy:
            # As a spy I already know everything, so I just move on
            return
        
        
        # As a resistance...
        
        # If the mission was not sabotaged, trust a little more in the team
        if not sabotaged:
            self._logInfo("(THOUGHT) They seem to be nice guys...")
            for p in team:
                self._decreaseSuspection(p)
            return
       
        # If everyone in the team sabotaged the mission, then they are for sure spies
        if sabotaged == len(team):
            self._logInfo("(THOUGHT) They are all spies!!!")
            for p in team:
                self.suspection[p.index] = 10.0
            return
            
        # The mission was sabotaged and there were only 2 in the mission and I was one of them
        if len(team) == 2 and (self.index in [p.index for p in team]):
            self._logInfo("(THOUGHT) The other is a spy!")
            other = [p for p in team if p.index != self.index]
            self.suspection[other[0].index] = 10.0
            return
        
        # The mission was sabotaged and we were part of a big team, so don't trust the others
        if len(team) > 2 and (self.index in [p.index for p in team]):
            self._logInfo("(THOUGHT) One of the others is a spy!")
            others = [p for p in team if p.index not in [self.index]]
            for p in others:
                self._increaseSuspection(p, len(team) - 1)
            return
        
        # The mission was sabotaged but we don't exactly who, so don't trust the whole team
        self._logInfo("(THOUGHT) Someone is a spy...")
        for p in team:
            self._increaseSuspection(p, len(team))
        
        return

    def _logSuspection(self):
        self._logInfo("Suspection: " + str(self.suspection))
        pass
    
    def _logInfo(self, message):
        self.log.info(str(self) + ": " + str(message))
        pass
