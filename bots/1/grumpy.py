"""
@name: Grumpy Bot
@author: Chong-U Lim (MIT) 
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
"""

from player import Bot, Player
from game import State

import random

import logging
import logging.handlers

class BotPlan():

    def __init__(self):
        pass

    def init(self, game):
        self.game = game

    def load(self, rawPlan):

        # votes
        self.index = rawPlan[0]
        self.role = rawPlan[1]
        
        self.voteString = rawPlan[2:27]
        self.sabotageString = rawPlan[27:52]
        self.selectString = rawPlan[52:]

    def getVoteAction(self, missionId, attemptId):
        #print 'missionId:' + str(missionId)
        index = (missionId-1)*5 + (attemptId-1)
        #print 'index:' + str(index)
        actionId = self.voteString[index]
        return actionId == 1

    def getSabotageAction(self, missionId, attemptId):
        index = (missionId-1)*5 + (attemptId-1)
        actionId = self.sabotageString[index]
        return actionId == 1

    def getSelectAction(self, missionId, attemptId):
        index = (missionId-1)*5 + (attemptId-1)*5
        selection = self.selectString[index:index+5]

        playerIndex = 0
        players = []
        for n in selection:
            if n == 1:
                players = players + game.players[playerIndex]
            playerIndex = playerIndex + 1

        # print "selection:" + str(players)
        return players

class GrumpyBot(Bot):

    def __init__(self, game, index, spy):
        """Constructor called before a game starts.  It's recommended you don't
        override this function and instead use onGameRevealed() to perform
        setup for your AI.
        @param name     The public name of your bot.
        @param index    Your own index in the player list.
        @param spy      Are you supposed to play as a spy?
        """
        Player.__init__(self, self.__class__.__name__, index)
        self.game = game
        self.spy = spy

        self.spyplans = [  
                        "110000000000100000000000000100000000000000000000000000000000000000000000000000000000000000000000000000100010000000000000000000000000000000000000000000000000000000000000000000000"
        ]

        self.resplans = [
                        "100000010000000000000000000000000000000000000000000000000000000000000000000001101000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

        ]

        self.rawPlan = self.getPlansFor(index, spy)

        self.plan = BotPlan()
        self.plan.init(game)
        self.plan.load(self.rawPlan)

        self.log = logging.getLogger(str(self))
        if not self.log.handlers:
            try:
                output = logging.FileHandler(filename='logs/'+str(self)+'.xml')
                self.log.addHandler(output)
                self.log.setLevel(logging.DEBUG)
            except IOError:
                pass

    def getPlansFor(self, index, spy):

        if (spy):
            plans = self.spyplans
        else:
            plans = self.resplans

        candidates = [plan for plan in plans if plan.startswith(str(index))]
        
        if len(candidates) == 0:
            #print "random plan chosen"
            return random.choice(plans);
        else:
            #print "appropriate plan chosen"
            return random.choice(candidates)
    
    def onGameRevealed(self, players, spies):
        """This function will be called to list all the players, and if you're
        a spy, the spies too -- including others and yourself.
        @param players  List of all players in the game including you.
        @param spies    List of players that are spies, or an empty list.
        """
        
        role = "spy" if self.spy else "res"

        self.log.info("<Bot id=\"%d\" role=\"%s\">" %(self.index, role))
        # self.log.info("[%s] onGameRevealed()" %self)

    def onMissionAttempt(self, mission, tries, leader):
        """Callback function when a new turn begins, before the
        players are selected.
        @param mission  Integer representing the mission number (1..5).
        @param tries    Integer count for its number of tries (1..5).
        @param leader   A Player representing who's in charge.
        """
        #self.log.info("[%s] onMissionAttempt(), turn:%d, tries:%d, mission:%d, leader:%s" %(self, self.game.turn, self.game.tries, mission, leader))
       # self.log.info("<mission id=\"%d\" attempt=\"%d\" leader=\"%s\">" %(mission, tries, leader))

    def onMissionComplete(self, sabotaged):
        """Callback once the players have been chosen.
        @param selected     List of players that participated in the mission.
        @param sabotaged    Integer how many times the mission was sabotaged.
        """
        # self.log.info("[%s] onMissionComplete(), mission%d, tries:%d, sabotaged:%s" %(self, self.game.turn, self.game.tries, sabotaged))
        #self.log.info("</mission>")

    def select(self, players, count):
        """Pick a sub-group of players to go on the next mission.
        @param players  The list of all players in the game to pick from.
        @param count    The number of players you must now select.
        @return list    The players selected for the upcoming mission.
        """
        # self.log.info("[%s] select(), players:%s, count:%d" %(self, players, count))
        #others = random.sample(self.others(), count-1)
        #action = [self] + others
        #actionStr = [str(self.index) + "-" + self.name] + [p for p in others]
       
        action = self.plan.getSelectAction(self.game.turn, self.game.tries)
        if len(action) == 0:
            others = random.sample(self.others(), count-1)
            action = [self] + others
        
        #self.log.info("<select missionId=\"%d\" attemptId=\"%d\" count=\"%d\">%s</select>" %(self.game.turn, self.game.tries, count, actionStr))
        
        return action

    def onTeamSelected(self, leader, team):
        """Called immediately after the team is selected to go on a mission,
        and before the voting happens.
        @param leader   The leader in charge for this mission.
        @param team     The team that was selected by the current leader.
        """
        pass

    def vote(self, team): 
        """Given a selected team, decide whether the mission should proceed.
        @param team      List of players with index and name. 
        @return bool     Answer Yes/No.
        """ 
        # self.log.info("[%s] vote(), turn:%d, tries:%d, team:%s, res:%s" %(self, self.game.turn, self.game.tries, team, bool(self == self.game.leader)))
        # action = bool(self == self.game.leader)
        action = self.plan.getVoteAction(self.game.turn, self.game.tries)

        self.log.info("<vote missionId=\"%d\" attemptId=\"%d\" team=\"%s\">%s</vote>" %(self.game.turn, self.game.tries, team, action))
        return action

    def onVoteComplete(self, votes):
        """Callback once the whole team has voted.
        @param votes        Boolean votes for each player (ordered).
        """
        # self.log.info("[%s] onVoteComplete, turn:%d, tries:%d, votes:%s" %(self, self.game.turn, self.game.tries, votes))

    def sabotage(self):
        """Decide what to do on the mission once it has been approved.  This
        function is only called if you're a spy, otherwise you have no choice.
        @return bool        Yes to shoot down a mission.
        """
        #self.log.info("[%s] sabotage(), turn:%d, tries:%d, resWins:%d, spyWins:%d, team:%s" %(self, self.game.turn, self.game.tries, self.game.wins, self.game.losses, self.game.team ))
        #action = random.choice([True, False])
        action = self.plan.getSabotageAction(self.game.turn, self.game.tries)
        self.log.info("<sabotage missionId=\"%d\" attemptId=\"%d\">%s</sabotage>" %(self.game.turn, self.game.tries, action))
        return False 

    def onGameComplete(self, win, spies):
        """Callback once the game is complete, and everything is revealed.
        @param win          Boolean if the Resistance won.
        @param spies        List of only the spies in the game.
        """
        # self.log.info("[%s] onGameComplete(), turn:%d, tries:%d, win:%s, spies:%s" %(self, self.game.turn, self.game.tries, win, spies))
        winner = "res" if win else "spy"
        self.log.info("<winner>%s</winner>" %winner)
        self.log.info("</Bot>\n")
