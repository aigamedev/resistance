"""
@name: Bot5Players
@author: Daniel Marquez Quintanilla 
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
@since: 05.09.2012
"""

from player import Bot
from game import *
import random

class Bot5Players(Bot):

    def onGameRevealed(self, players, spies):
        """This function will be called to list all the players, and if you're
        a spy, the spies too -- including others and yourself.
        @param players  List of all players in the game including you.
        @param spies    List of players that are spies, or an empty list.
        """
        self.memory = Memory(self, players, spies)
        self.entries = TeamEntries(players)
        if not self.spy:
            self.initialTrust = 1000
            self.entries.addTrust(self, self.initialTrust)
        self.log.info("Building behaviors")
        self.behavior = Bot5PlayersBehavior(self.game, self)



    def onMissionAttempt(self, mission, tries, leader):
        """Callback function when a new turn begins, before the
        players are selected.
        @param mission  Integer representing the mission number (1..5).
        @param tries    Integer count for its number of tries (1..5).
        @param leader   A Player representing who's in charge.
        """
        self.memory.currentMission = mission
        self.currentLeader = leader
        self.behavior.process(self.game, self, GamePhase.onMissionAttempt)

    def select(self, players, count):
        """Pick a sub-group of players to go on the next mission.
        @param players  The list of all players in the game to pick from.
        @param count    The number of players you must now select.
        @return list    The players selected for the upcoming mission.
        """
        self.memory.selectionCount = count
        return self.behavior.process(self.game, self, GamePhase.select)

    def onTeamSelected(self, leader, team):
        """Called immediately after the team is selected to go on a mission,
        and before the voting happens.
        @param leader   The leader in charge for this mission.
        @param team     The team that was selected by the current leader.
        """
        self.memory.currentTeam = list(team)
        self.memory.currentLeader = leader
        self.behavior.process(self.game, self, GamePhase.onTeamSelected)

    def vote(self, team):
        """Given a selected team, decide whether the mission should proceed.
        @param team      List of players with index and name.
        @return bool     Answer Yes/No.
        """
        self.memory.currentTeam = list(team)
        return self.behavior.process(self.game, self, GamePhase.vote)

    def onVoteComplete(self, votes):
        """Callback once the whole team has voted.
        @param votes        Boolean votes for each player (ordered).
        """
        self.memory.votes = votes
        self.behavior.process(self.game, self, GamePhase.onVoteComplete)

    def sabotage(self):
        """Decide what to do on the mission once it has been approved.  This
        function is only called if you're a spy, otherwise you have no choice.
        @return bool        Yes to shoot down a mission.
        """
        return self.behavior.process(self.game, self, GamePhase.sabotage)


    def onMissionComplete(self, sabotaged):
        """Callback once the players have been chosen.
        @param selected     List of players that participated in the mission.
        @param sabotaged    Integer how many times the mission was sabotaged.
        """
        self.memory.lastSabotage = sabotaged
        self.behavior.process(self.game, self, GamePhase.onMissionComplete)

    def onGameComplete(self, win, spies):
        """Callback once the game is complete, and everything is revealed.
        @param win          Boolean if the Resistance won.
        @param spies        List of only the spies in the game.
        """
        #have we found some patterns?
        self.behavior.process(self.game, self, GamePhase.onGameComplete)
#
#
#
class TeamEntry:
    def __init__(self, player):
        self.player = player
        self.count = 0


class TeamEntries:
    """Histogram filter"""
    def __init__(self, players):
        self.entries = dict()
        for p in players:
            self.entries[p] = 0

    def addTrust(self, player, value):
        self.entries[player] += value

class RuleStatistics:
    """Just like team entries, but used for get the most used rules"""
    def __init__(self):
        self.entries = dict()
        self.total = 0

    def ruleFired(self, ruleFired):
        if self.entries.has_key(ruleFired):
            self.entries[ruleFired] += 1
        else:
            self.entries[ruleFired] = 1
        self.total += 1

    def __repr__(self):
        result = "TOTAL RULES FIRED %i\n" % (self.total)
        for key, value in sorted(self.entries.iteritems(), key=lambda (k,v): (v,k)):
            result += "RULE: %s  TIMES:  %s\n" % (key, value)
        return result

rulesStatistics = RuleStatistics()

#
#===========
# BEHAVIORS
#===========
#

class ResistanceBaseBehavior:
    """The base class for all behaviors"""
    def __init__(self, game, owner, priority = 0):
        self.owner = owner
        self.game = game
        self.priority = priority

    def process(self, game, owner, phase):
        return (False, None)

    def __cmp__(self, other):
        assert isinstance(other, ResistanceBaseBehavior)
        if self.priority < other.priority:
            return -1
        elif self.priority < other.priority:
            return 1
        else:
            return 0

class ResistanceDelegateBehaviour(ResistanceBaseBehavior):
    """A behavior whose process function delegates the calculation to the function given"""
    def __init__(self, game, owner, priority = 0, delegateFunction=None):
        ResistanceBaseBehavior.__init__(self, game, owner, priority)
        self.delegateFunction = delegateFunction

    def process(self, game, owner, phase):
        if self.delegateFunction:
            return self.delegateFunction(game, owner, phase)
        return (False, None)

class ResistanceCompositeBaseBehavior(ResistanceBaseBehavior):
    """Base class for behaviors that are composed for other more simple behaviors"""
    def __init__(self, game, owner, priority = 0, children=[]):
        ResistanceBaseBehavior.__init__(self, game, owner, priority)
        self.children = children
        self.children.sort()


    def process(self, game, owner, phase):
        for behaviour in self.children:
            output = behaviour.process(game,owner,phase)
            if output[0]:
                rulesStatistics.ruleFired(behaviour.__class__.__name__)
                return output

        return (False, None)

class TrueBehavior(ResistanceBaseBehavior):
    def process(self, game, owner, phase):
        return (True, True)

class FalseBehavior(ResistanceBaseBehavior):
    def process(self, game, owner, phase):
        return (True, False)

#
# SELECTION BEHAVIORS
#
class RandomSelectionBehaviour(ResistanceBaseBehavior):
    """Just selects a team randomly"""
    def process(self, game, owner, phase):
        owner.log.info("A completely random selection.")
        return (True, random.sample(game.players, owner.memory.selectionCount))

class MeAndRandomSelectionBehaviour(ResistanceBaseBehavior):
    """Just selects me and the others randomly"""
    def process(self, game, owner, phase):
        return (True, [owner] + random.sample(owner.others(),  owner.memory.selectionCount - 1))

class OneSpyRandomSelectionBehavior(ResistanceBaseBehavior):
    """Selects one of the two spies randomly"""
    def process(self, game, owner, phase):
        others = owner.memory.others - owner.memory.spies
        return (True, random.sample(owner.memory.spies,1) + random.sample(others,  owner.memory.selectionCount - 1))

class OneSpySelectionBehavior(ResistanceBaseBehavior):
    """Selects one of the two spies randomly"""
    def process(self, game, owner, phase):
        spies = list(owner.memory.spies)
        sorted_by_trust = []
        for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
            if not(key in spies):
                sorted_by_trust.append((key, value))
        sorted_by_trust.reverse()

        less_suspicious = spies[0]
        if owner.entries.entries[less_suspicious] < owner.entries.entries[spies[0]]:
            less_suspicious = spies[1]
        team = [less_suspicious]

        for i in range(owner.memory.selectionCount - 1):
            team.append(sorted_by_trust[i][0])
        return (True, team)

class OneSpyLessSuspiciousSelectionBehavior(ResistanceBaseBehavior):
    """Selects the spy less suspicious or not played yet"""
    def process(self, game, owner, phase):
        if game.turns > 1 and game.wins == 0:
            spies = list(owner.memory.spies)
            sorted_by_trust = []
            for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
                if not(key in spies):
                    sorted_by_trust.append((key, value))
            sorted_by_trust.reverse()

            index1 = spies[0].index
            index2 = spies[1].index
            plays1 = 0
            plays2 = 0
            for i in range(game.turn-1):
                if (i+1) == 2 or (i+1) == 4 or (i+1) == 5:
                    plays1 += 0.5 * owner.memory.selections.value[i][index1]
                    plays2 += 0.5 * owner.memory.selections.value[i][index2]
                else:
                    plays1 += owner.memory.selections.value[i][index1]
                    plays2 += owner.memory.selections.value[i][index2]

            less_suspicious = spies[0]
            if plays2 < plays1:
                less_suspicious = spies[1]
            team = [less_suspicious]

            for i in range(owner.memory.selectionCount - 1):
                team.append(sorted_by_trust[i][0])
            return (True, team)
        else:
            return(False, None)

class SpySelectionBehavior(ResistanceCompositeBaseBehavior):
    def __init__(self, game, owner, priority = 0, children=[]):
        ResistanceCompositeBaseBehavior.__init__(self, game, owner, priority,children)
        self.children = [OneSpySelectionBehavior(game, owner, 1),
                        OneSpyLessSuspiciousSelectionBehavior(game, owner, 0)]


class MeAndOnlyResitanceRandomSelectionBehaviour(ResistanceBaseBehavior):
    """Just selects me and the others resistance members randomly"""
    def process(self, game, owner, phase):
        if len(owner.memory.resistance) >= owner.memory.selectionCount - 1:
            return (True, [owner] + random.sample(owner.memory.resistance,  owner.memory.selectionCount - 1))
        else:
            return(False, None)

class OnlyResitanceRandomSelectionBehaviour(ResistanceBaseBehavior):
    """resistance members randomly"""
    def process(self, game, owner, phase):
        team = owner.memory.resistance | set([owner])
        if len(team) >= owner.memory.selectionCount:
            return (True, random.sample(team,  owner.memory.selectionCount))
        else:
            return(False, None)

class MeAndLessSuspiciousSelectionBehaviour(ResistanceBaseBehavior):
    """We haven't got enough info, me, resistance and others that might be not spies"""
    def process(self, game, owner, phase):
        others = owner.memory.others - owner.memory.resistance - owner.memory.spies
        if len(others) + len(owner.memory.resistance) >= owner.memory.selectionCount-1:
            return (True, [owner] + list(owner.memory.resistance) + random.sample(others,  owner.memory.selectionCount - 1 - len(owner.memory.resistance)))
        else:
            return(False, None)

class ResistanceSelectionWorstCase(ResistanceBaseBehavior):
    """Just selects me and the others randomly"""
    def process(self, game, owner, phase):
        others = owner.memory.others - owner.memory.resistance - owner.memory.spies
        return (True, [owner] + list(owner.memory.resistance) + list(others) + random.sample(owner.memory.spies, owner.memory.selectionCount - 1 - len(owner.memory.resistance) - len(others)))

class LessSuspiciousSelectionBehaviour(ResistanceBaseBehavior):
    """We haven't got enough info, me, resistance and others that might be not spies"""
    def process(self, game, owner, phase):
        sorted_by_trust = []
        for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
            if key != owner:
                sorted_by_trust.append((key, value))
        sorted_by_trust.reverse()
        #Do I trust on the second one?
        if sorted_by_trust[1][1] > 0 and game.losses < Game.NUM_LOSSES - 1:
            return (True, random.sample([owner, sorted_by_trust[0][0], sorted_by_trust[1][0]], owner.memory.selectionCount))
        else:
            #ok, me first then follow my feelings
            team = [owner]
            for i in range(owner.memory.selectionCount-1):
                team.append(sorted_by_trust[i][0])
            return (True, team)

class NotSelectedSelectionBehaviour(ResistanceBaseBehavior):
    """We cant afford lose, me with one of the group of three"""
    def process(self, game, owner, phase):
        #use this method if we haven't won any round
        if game.turn == 3 and game.wins == 0:
            sorted_by_trust = []
            for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
                if key != owner:
                    sorted_by_trust.append((key, value))
            sorted_by_trust.reverse()
            if sorted_by_trust[0][1] <= 0.5:
                #I have no clue, anyone who hasn't been selected yet
                player = - 1
                trust = -999999
                for j in range(5):
                    for i in range(game.turn-1):
                        if owner.memory.selections.value[i][j] > 0 or j==owner.index:
                            break
                    if i == game.turn-1  and  owner.entries[game.players[j]] > trust:
                        player = j
                        trust = owner.entries[game.players[j]]

                if player >= 0:
                    return(True, [owner, game.players[player]])
                else:
                    #if all players have participated already, I'll select the most trusted one
                    return (False, None)
            else:
                #we have enough info to select the best ones
                return (False, None)
        else:
            return (False, None)

##class NotSelectedSelectionBehaviour(ResistanceBaseBehavior):
##    """We cant afford lose, me with one of the group of three"""
##    def process(self, game, owner, phase):
##        #use this method if we haven't won any round
##        if game.turn == 3 and game.wins == 0:
##            sorted_by_trust = []
##            for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
##                if key != owner:
##                    sorted_by_trust.append((key, value))
##            sorted_by_trust.reverse()
##            if sorted_by_trust[0][1] <= 0.5:
##                #I have no clue, anyone who hasn't been selected yet
##                player = - 1
##                trust = -999999
##                for j in range(5):
##                    if owner.memory.selections.value[1][j] == 1 and j != owner.index-1 and owner.entries[game.players[j]] > trust:
##                        player = j
##                        trust = owner.entries[game.players[j]]
##
##                if player >= 0:
##                    return(True, [owner, game.players[player]])
##                else:
##                    #if all players have participated already, I'll select the most trusted one
##                    return (False, None)
##            else:
##                #we have enough info to select the best ones
##                return (False, None)
##        else:
##            return (False, None)

class MostUntrustedSelectionBehaviour(ResistanceBaseBehavior):
    """let's put the most suspicious together with the members that haven't played"""
    def process(self, game, owner, phase):
        #use this method if we haven't won any round
        if game.turn == 2 and game.wins == 0:
            sorted_by_trust = []
            for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
                if key != owner:
                    sorted_by_trust.append((key, value))
            sorted_by_trust.reverse()
            #we could have lost but te result was two sabotages
            if sorted_by_trust[0][1] <= 0.5:
                #I have no clue, most suspicious together with others  who hasn't played
                all_players = set(game.players)
                players = set([])
                for j in range(5):
                    for i in range(game.turn-1):
                        if owner.memory.selections.value[i][j] > 0 or j==owner.index:
                            break
                    if i == game.turn-1:
                        players.add(game.players[j])

                diff = all_players - players
                if owner in diff:
                    diff.remove(owner)
                    team = random.sample(diff,  1) + random.sample(players,  2)
                else:
                    players.remove(owner)
                    team = random.sample(diff,  1) + random.sample(players,  2)
                return (True, team)
            else:
                #we have enough info to select the best ones
                return (False, None)
        else:
            return (False, None)


class ResistanceMemberSelectionBehavior(ResistanceCompositeBaseBehavior):
    """High-level behavior for resistance members"""
    def __init__(self, game, owner, priority = 0, children=[]):
        ResistanceCompositeBaseBehavior.__init__(self, game, owner, priority,children)
        self.children = [LessSuspiciousSelectionBehaviour(game, owner, 1),
                        MostUntrustedSelectionBehaviour(game, owner, 0),
                        #NotSelectedSelectionBehaviour(game, owner, 0)
                        ]

#
# VOTING BEHAVIORS
#
class RandomVotingBehaviour(ResistanceBaseBehavior):
    """Just returns true or false randomly"""
    def process(self, game, owner, phase):
        return (True, random.choice([True, False]))


class VotingBCResistanceMemberBehaviour(ResistanceBaseBehavior):
    """
    If it's the last try accept the team.
    Resistance members will accept the team, and spies could be easily spotted
    if the reject it
    """
    def process(self, game, owner, phase):
        # Base case, accept the mission anyway
        # a spy should be easily spotted if  it rejects the team
        # We are supposing resistance players have somekind of rationality
        if game.tries == Game.MAX_TURNS:
            return (True, True)
        else:
            return (False, None)


class JustOneSpyBehavior(ResistanceBaseBehavior):
    """Better avoid to have a team consisting only in spies"""
    def process(self, game, owner, phase):
        if len([p for p in owner.memory.currentTeam if p in owner.memory.spies]) == len(owner.memory.currentTeam):
            return (True, random.choice([True, False]))
        else:
            return (False, None)

class AtLeastOneSpyVotingBehavior(ResistanceBaseBehavior):
    def process(self, game, owner, phase):
        return (True, len([p for p in owner.memory.currentTeam if p in owner.memory.spies]) > 0)

class SpyVotingBCBehavior(ResistanceBaseBehavior):
    """I don't care with the number of spies (at least one) if it's our last mission"""
    def process(self, game, owner, phase):
        if game.losses == Game.NUM_LOSSES -1:
            return (True, len([p for p in owner.memory.currentTeam if p in owner.memory.spies]) > 0)
        else:
            return (False, None)

class SpyVotingBC2Behavior(ResistanceBaseBehavior):
    """First mission, first round and no spies-> coin flip"""
    def process(self, game, owner, phase):
        if game.tries == 1 and game.turn == 1 and len([p for p in owner.memory.currentTeam if p in owner.memory.spies]) == 0:
            return (True, random.choice([True, False]))
        else:
            return (False, None)

class SpyVotingBehavior(ResistanceCompositeBaseBehavior):
    """High-level behavior for voting as a spy"""
    def __init__(self, game, owner, priority = 0, children=[]):
        ResistanceCompositeBaseBehavior.__init__(self, game, owner, priority,children)
        self.children = [AtLeastOneSpyVotingBehavior(game, owner, 5),
                        JustOneSpyBehavior(game, owner, 4),
                        SpyVotingBCBehavior(game, owner, 0),
                        SpyVotingBC2Behavior(game, owner, 2),
                    VotingBCResistanceMemberBehaviour(game, owner, 1)]
        self.children.sort()

class ResistanceMemberBasicVoting(ResistanceBaseBehavior):
    """
    Just make sure the team doesn't have any bot who might be a spy
    (from my point of view)
    """
    def process(self, game, owner, phase):

        #how much i trust you
        leader_trust = owner.entries.entries[owner.memory.currentLeader]

        sorted_by_trust = []

        for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
            if key != owner:
                sorted_by_trust.append((key, value))

        if leader_trust < 0 and (( sorted_by_trust[0][0] ==  owner.memory.currentLeader ) or ( sorted_by_trust[1][0] ==  owner.memory.currentLeader )):
            #I don't trust you at all
            return (True, False )

        sorted_by_trust.reverse()

        #best fit (without me)
        max_trust = sorted_by_trust[0][1] + sorted_by_trust[1][1]

        trust = 0
        for member in owner.memory.currentTeam:
            if member != owner:
                trust += owner.entries.entries[member]


##      return (True, trust >= max_trust)
##        return (True, trust >= max_trust or trust >= 0)

        best_fit = set([owner, sorted_by_trust[0][0], sorted_by_trust[1][0]])

        #FIX. the magic number 2.5 is just because the maximum penalization for a mission failed is 5
        tolerance = 2.5
        return (True, set(owner.memory.currentTeam).issubset(best_fit) or abs(max_trust - trust) < tolerance)

class NotSelectedOnVotingBehaviour(ResistanceBaseBehavior):
    """We haven't won any round and not any clue, approve "new" pairs"""
    def process(self, game, owner, phase):
        #use this method if we haven't won any round
        if game.turn == 3 and game.wins == 0:
            sorted_by_trust = []
            for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
                if key != owner:
                    sorted_by_trust.append((key, value))
            #sorted_by_trust.reverse()
            #if sorted_by_trust[0][1] <= 0.5:
            if owner.entries.entries[owner.memory.currentLeader] >= -3.5:
                v1 = owner.memory.selections.take([0,1,2,3,4],[owner.memory.currentTeam[0].index])
                v2 = owner.memory.selections.take([0,1,2,3,4],[owner.memory.currentTeam[1].index])
                #let's try this team if it has never selected before
                res = v1.transpose() * v2
                return (True, res.value[0][0] == 0)
##                if res.value[0][0] == 0:
##                    return (True, True)
##                else:
##                    return (False, None)
            else:
                #we have enough info to select the best ones
                return (False, None)
        else:
            return (False, None)

##class NotSelectedOnVotingBehaviour(ResistanceBaseBehavior):
##    """We haven't won any round and not any clue, approve "new" pairs"""
##    def process(self, game, owner, phase):
##        #use this method if we haven't won any round
##        if game.turn == 3 and game.wins == 0:
##            sorted_by_trust = []
##
##            for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
##                if key != owner:
##                    sorted_by_trust.append((key, value))
##
##            sorted_by_trust.reverse()
##
##            best_fit = set([owner, sorted_by_trust[0][0], sorted_by_trust[1][0]])
##
##            return (True, set(owner.memory.currentTeam).issubset(best_fit))
##        else:
##            return(False, None)

class NotSelected3OnVotingBehaviour(ResistanceBaseBehavior):
    """I can't afford to lose, me with someone of the previous team"""
    def process(self, game, owner, phase):
        #use this method if we haven't won any round
        if game.turn == 3 and game.wins == 0:
            sorted_by_trust = []
            for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
                if key != owner:
                    sorted_by_trust.append((key, value))
            sorted_by_trust.reverse()
            if sorted_by_trust[0][1] <= 0.5:
                players = set([])
                for j in range(5):
                    if owner.memory.selections.value[1][j] == 1 and owner.memory.selections.value[0][j] == 0  and j != owner.index:
                        players.add(game.players[j])
                    if (owner in owner.memory.currentTeam) and len(set(owner.memory.currentTeam).intersection(players))==1:
                    #or len(set(owner.memory.currentTeam).intersection(players))==2:
                        return(True, True)
                    else:
                        return(True, False)
            else:
                #we have enough info to select the best ones
                return (False, None)
        else:
            return (False, None)


class NotSelected2OnVotingBehaviour(ResistanceBaseBehavior):
    """second round, approve the most suspicious together"""
    def process(self, game, owner, phase):
        #use this method if we haven't won any round
        if game.turn == 2 and game.wins == 0:
            sorted_by_trust = []
            for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
                if key != owner:
                    sorted_by_trust.append((key, value))
            sorted_by_trust.reverse()
            if sorted_by_trust[0][1] <= 0.5:
                #I have no clue, most suspicious together with others  who hasn't played
                diff = set([])
                players = set([])
                for j in range(5):
                    if owner.memory.selections.value[0][j] == 0:
                        players.add(game.players[j])
                    else:
                        diff.add(game.players[j])

                inteam = owner in owner.memory.currentTeam
                indiff = owner in diff
                if inteam and indiff:
                    return (True, len(players.intersection(owner.memory.currentTeam)) == 2)
                elif inteam and not indiff:
                    players.remove(owner)
                    return (True, len(diff.intersection(owner.memory.currentTeam)) == 1)
                else:
                    return (True, len(diff.intersection(owner.memory.currentTeam)) == 1 and len(players.intersection(owner.memory.currentTeam)) == 2)
            else:
                #we have enough info to select the best ones
                return (False, None)
        else:
            return (False, None)

class VotingBCBehavior(ResistanceBaseBehavior):
    """Approve if I'm the leader"""
    def process(self, game, owner, phase):
        if owner == owner.memory.currentLeader:
            return (True, True)
        else:
            return (False, None)

class ResistanceMemberBCTeamMembers(ResistanceBaseBehavior):
    """
    If the team size is equal to the number of resistance members and I'm not
    part of team reject it
    """
    def process(self, game, owner, phase):
        sorted_by_trust = []
        for key, value in sorted(owner.entries.entries.iteritems(), key=lambda (k,v): (v,k)):
            if key != owner:
                sorted_by_trust.append((key, value))
        sorted_by_trust.reverse()
        if sorted_by_trust[0][1] > 0.5 or game.wins > 0:
            if len(owner.memory.currentTeam) == 3 and  (not (owner in owner.memory.currentTeam)):
                return (True, False)
            else:
                return (False, None)
        else:
            return (False, None)

##class ResistanceMemberBCTeamMembers(ResistanceBaseBehavior):
##    """
##    If the team size is equal to the number of resistance members and I'm not
##    part of team reject it
##    """
##    def process(self, game, owner, phase):
##        if len(owner.memory.currentTeam) == 3 and  (not (owner in owner.memory.currentTeam)):
##            return (True, False)
##        else:
##            return (False, None)

class ResistanceMemberVotingBehavior(ResistanceCompositeBaseBehavior):
    """High-level behavior for voting as a resistance member"""
    def __init__(self, game, owner, priority = 0, children=[]):
        ResistanceCompositeBaseBehavior.__init__(self, game, owner, priority,children)
        self.children = [TrueBehavior(game, owner, 10),
                        ResistanceMemberBasicVoting(game, owner, 4),
                        NotSelectedOnVotingBehaviour(game, owner, 3),
                        #NotSelected3OnVotingBehaviour(game, owner, 2),
                        NotSelected2OnVotingBehaviour(game, owner, 2),
                        ResistanceMemberBCTeamMembers(game, owner, 1),
                        VotingBCBehavior(game, owner, 1),
                        VotingBCResistanceMemberBehaviour(game, owner, 0)]
        self.children.sort()

#
# ONVOTECOMPLETED BEHAVIORS
#

class ResistanceMemberOnVotingBaseCase(ResistanceBaseBehavior):
    """
    Just a basic reasoning. If it was the last votation attempt,
    all the ones who have rejected the team could possibly be spies!
    """
    def process(self, game, owner, phase):
        # base case: see if any bot has rejected the team, they must be spies
        if game.tries == Game.MAX_TURNS and game.losses < Game.NUM_LOSSES:
            for i in range(len(owner.memory.votes)):
                if not owner.memory.votes[i]:
                     owner.entries.addTrust(game.players[i], -1)
        #the phase after the voting is mostly for reasoning, so we don't need stop other types of them
        return (False, None)


class ResistanceMemberOnVotingFirstTime(ResistanceBaseBehavior):
    """
    Why reject a team in the first place? Suspicious...
    """
    def process(self, game, owner, phase):
        # do you know something i dont?
        rejecteds = owner.memory.votes.count(False)
        if game.tries == 1 and game.turn == 1 and  rejecteds > 0 and rejecteds < 4:
            for i in range(len(owner.memory.votes)):
                if not owner.memory.votes[i]:
                     owner.entries.addTrust(game.players[i], -1)
        #the phase after the voting is mostly for reasoning, so we don't need stop other types of them
        return (False, None)

class ResistanceMemberOnVotingBehavior(ResistanceCompositeBaseBehavior):
    """Highest-level behavior for on vote completed"""
    def __init__(self, game, owner, priority = 0, children=[]):
        ResistanceCompositeBaseBehavior.__init__(self, game, owner, priority,children)
        self.children = [ResistanceMemberOnVotingBaseCase(game, owner, 0),
                         ResistanceMemberOnVotingFirstTime(game, owner, 0)]

#
# SABOTAGING BEHAVIORS
#
class ResistanceMemberSabotagingBehaviour(ResistanceBaseBehavior):
    """Just like FalseBehavior, and it's here just to have one behavior per game phase"""
    def process(self, game, owner, phase):
        #Resistance memebers never sabotage a mission
        return (True, False)

class SpySabotagingBehavior(ResistanceCompositeBaseBehavior):
    """Highest-level behavior for sabotaging"""
    def __init__(self, game, owner, priority = 0, children=[]):
        ResistanceCompositeBaseBehavior.__init__(self, game, owner, priority,children)
        self.children = [TrueBehavior(game, owner, 3),
                        TwoSpiesSabotagingBehavior(game, owner, 2),
                        OnlyTwoSpiesSabotagingBehavior(game, owner, 1),
                        SpySabotageBaseCaseBehavior(game, owner, 0)]
##        self.children = [TrueBehavior(game, owner, 0)]
        self.children.sort()

class SpySabotageBaseCaseBehavior(ResistanceBaseBehavior):
    """Spy base case for sabotaging. Sabotage the mission if it leads to an immediat victory"""
    def process(self, game, owner, phase):
        if game.losses == Game.NUM_LOSSES-1:
            return (True,True)
        else:
            return(False, None)

class OnlyTwoSpiesSabotagingBehavior(ResistanceBaseBehavior):
    """The team is composed only by spies!"""
    def process(self, game, owner, phase):
        if len([p for p in game.team if p in owner.memory.spies]) == len(game.team)  and game.wins < Game.NUM_WINS-1:
            #people won't trust me if I sabotage the mission
            return (True, False)
        else:
            return (False,None)

class TwoSpiesSabotagingBehavior(ResistanceBaseBehavior):
    """Two spies in a team of three. How suspicious am I?"""
    def process(self, game, owner, phase):
        otherSpy = list(owner.memory.spies - set([owner]))
        if len([p for p in game.team if p in owner.memory.spies]) == 2 and game.wins < Game.NUM_WINS-1:

            index1 = owner.index
            index2 = otherSpy[0].index
            plays1 = 0
            plays2 = 0
            for i in range(game.turn-1):
                if (i+1) == 2 or (i+1) == 4 or (i+1) == 5:
                    plays1 += 0.5 * owner.memory.selections.value[i][index1]
                    plays2 += 0.5 * owner.memory.selections.value[i][index2]
                else:
                    plays1 += owner.memory.selections.value[i][index1]
                    plays2 += owner.memory.selections.value[i][index2]

            #only sabotage if i'm more suspicious
            return (True, (plays1 > plays2) or (plays1==plays2 and owner.entries.entries[owner] < owner.entries.entries[otherSpy[0]]) or (random.choice([True, False])))
        else:
            return (False,None)

#
# ONMISSIONCOMPLETED BEHAVIORS
#

class OnMissionCompletedResistanceFailBCBehavior(ResistanceBaseBehavior):
    """Two members, two sabotages->two spies the most easy one"""
    def process(self, game, owner, phase):
        if owner.memory.lastSabotage == len(owner.memory.currentTeam):
            others = owner.memory.others - set(owner.memory.currentTeam)
            for member in owner.memory.currentTeam:
                owner.entries.addTrust(member, -5)
                #get the selections
                owner.memory.selections.value[game.turn - 1][member.index] = 1
            for member in others:
                owner.entries.addTrust(member, 5)
            return(True, None)
        return (False, None)


class OnMissionCompletedResistanceFailBC2Behavior(ResistanceBaseBehavior):
    """Me with spies!"""
    def process(self, game, owner, phase):
        if owner.memory.lastSabotage == (len(owner.memory.currentTeam)-1) and (owner in owner.memory.currentTeam):
            for member in owner.memory.currentTeam:
                owner.entries.addTrust(member, -5)
                #get the selections
                owner.memory.selections.value[game.turn - 1][member.index] = 1
            owner.entries.addTrust(owner.memory.currentLeader, -0.5)
            return(True, None)
        return (False, None)

class OnMissionCompletedResistanceFailBehavior(ResistanceBaseBehavior):
    """One spy in the team"""
    def process(self, game, owner, phase):
        if owner.memory.lastSabotage > 0:
            im_in_the_team = (owner in owner.memory.currentTeam)
            #im_in_the_team = 0
            for member in owner.memory.currentTeam:
                owner.entries.addTrust(member, -2/len(owner.memory.currentTeam) - im_in_the_team/3 )
                #get the selections
                owner.memory.selections.value[game.turn - 1][member.index] = 1
            owner.entries.addTrust(owner.memory.currentLeader, -0.5)

            for i in range(len(owner.memory.votes)):
                if owner.memory.votes[i]:
                    owner.entries.addTrust(game.players[i], -0.5)
                else:
                    owner.entries.addTrust(game.players[i], 0.5)
            return (True, None)
        return (False, None)

class OnMissionCompletedResistanceFail2Behavior(ResistanceBaseBehavior):
    """Three members (not me), two sabotages->two spies"""
    def process(self, game, owner, phase):
        if owner.memory.lastSabotage == 2:
            others = owner.memory.others - set(owner.memory.currentTeam)
            for member in owner.memory.currentTeam:
                #penalize a little bit more
                owner.entries.addTrust(member, -2)
                #get the selections
                owner.memory.selections.value[game.turn - 1][member.index] = 1
            for member in others:
                owner.entries.addTrust(member, 5)
            return(True, None)
        return (False, None)

class OnMissionCompletedResistanceBCBehavior(ResistanceBaseBehavior):
    """We won with this team, infer something!"""
    def process(self, game, owner, phase):
        if owner.memory.lastSabotage == 0:

            for member in owner.memory.currentTeam:
                owner.entries.addTrust(member, 4)
                #get the selections
                owner.memory.selections.value[game.turn - 1][member.index] = 1

            if not (owner.memory.currentLeader in owner.memory.currentTeam) and owner.memory.currentLeader!= owner:
                owner.entries.addTrust(owner.memory.currentLeader, 0.5)

            if len(owner.memory.currentTeam) == 3:
                others = owner.memory.others - set(owner.memory.currentTeam)
                for member in others:
                    owner.entries.addTrust(member, -4)

            for i in range(len(owner.memory.votes)):
                if owner.memory.votes[i]:
                    owner.entries.addTrust(game.players[i], 0.5)
                else:
                    owner.entries.addTrust(game.players[i], -0.5)
            return (True, None)
        return (False, None)

class OnMissionCompletedResistanceBehavior(ResistanceCompositeBaseBehavior):
    """High-level"""
    def __init__(self, game, owner, priority = 0, children=[]):
        ResistanceCompositeBaseBehavior.__init__(self, game, owner, priority,children)
        self.children = [OnMissionCompletedResistanceFailBehavior(game, owner, 5),
                        OnMissionCompletedResistanceFail2Behavior(game, owner, 1),
                        OnMissionCompletedResistanceFailBC2Behavior(game, owner, 0),
                        OnMissionCompletedResistanceFailBCBehavior(game, owner, 0),
                        OnMissionCompletedResistanceBCBehavior(game, owner, 0),]
        self.children.sort()








class OnMissionCompletedSpyBehavior(ResistanceCompositeBaseBehavior):
    """High-level  behavior for spies"""
    def __init__(self, game, owner, priority = 0, children=[]):
        ResistanceCompositeBaseBehavior.__init__(self, game, owner, priority,children)
        self.children = [OnMissionCompletedResistanceFailBehavior(game, owner, 1),
                        OnMissionCompletedResistanceFailBCBehavior(game, owner, 0),
                        OnMissionCompletedResistanceBCBehavior(game, owner, 0),]
        self.children.sort()


#
# HIGHEST-LEVEL ONE
#
class Bot5PlayersBehavior(ResistanceCompositeBaseBehavior):
    """The highest level behavior"""
    def __init__(self, game, owner, priority = 0, children=[]):
        ResistanceCompositeBaseBehavior.__init__(self, game, owner, priority,children)
        #init sub-behaviors depending on being a spy or not
        if self.owner.spy:
            self.children = [ResistanceBaseBehavior(game, owner, GamePhase.onGameRevealed),
                            ResistanceBaseBehavior(game, owner, GamePhase.onMissionAttempt),
                            #OneSpyRandomSelectionBehavior(game, owner, GamePhase.select),
                            #OneSpySelectionBehavior(game, owner, GamePhase.select),
                            SpySelectionBehavior(game, owner, GamePhase.select),
                            ResistanceBaseBehavior(game, owner, GamePhase.onTeamSelected),
                            SpyVotingBehavior(game, owner, GamePhase.vote),
                            ResistanceBaseBehavior(game, owner, GamePhase.onVoteComplete),
                            SpySabotagingBehavior(game, owner, GamePhase.sabotage),
                            #ResistanceBaseBehavior(game, owner, GamePhase.onGameComplete),
                            OnMissionCompletedSpyBehavior(game, owner, GamePhase.onMissionComplete),
                            ResistanceBaseBehavior(game, owner, GamePhase.onGameComplete)]
        else:
            self.children = [ResistanceBaseBehavior(game, owner, GamePhase.onGameRevealed),
                            ResistanceBaseBehavior(game, owner, GamePhase.onMissionAttempt),
                            ResistanceMemberSelectionBehavior(game, owner, GamePhase.select),
                            ResistanceBaseBehavior(game, owner, GamePhase.onTeamSelected),
                            ResistanceMemberVotingBehavior(game, owner, GamePhase.vote),
                            ResistanceMemberOnVotingBehavior(game, owner, GamePhase.onVoteComplete),
                            FalseBehavior(game, owner, GamePhase.sabotage),
                            OnMissionCompletedResistanceBehavior(game, owner, GamePhase.onMissionComplete),
                            ResistanceBaseBehavior(game, owner, GamePhase.onGameComplete)]

    def process(self, game, owner, phase):
        return self.children[phase].process(game,owner,phase)[1]



class GamePhase:
    PHASES = 9
    onGameRevealed=0
    onMissionAttempt=1
    select=2
    onTeamSelected=3
    vote=4
    onVoteComplete=5
    sabotage=6
    onMissionComplete=7
    onGameComplete=8

class Memory:
    """Or should I say BlackBoard system"""
    _currentLeader = None
    _currentTeam = None
    _currentMission = None
    _selectionCount = None
    _votes = None
    _lastSabotage = None

    def __init__(self, owner, players, spies):
        self.players = players
        self.spies = spies
        self.spiesIndex = [spy.index for spy in spies]
        self.others = set(owner.others())
        self.resistance = set()
        self.selections = matrix()
        self.selections.zero(5,5)

    @property
    def currentLeader(self):
        return self._currentLeader

    @currentLeader.setter
    def currentLeader(self, value):
        self._currentLeader = value

    @property
    def currentTeam(self):
        return self._currentTeam

    @currentTeam.setter
    def currentTeam(self, value):
        self._currentTeam = value

    @property
    def currentMission(self):
        return self._currentMission

    @currentMission.setter
    def currentMission(self, value):
        self._currentMission = value

    @property
    def selectionCount(self):
        return self._selectionCount

    @selectionCount.setter
    def selectionCount(self, value):
        self._selectionCount = value

    @property
    def votes(self):
        return self._votes

    @votes.setter
    def votes(self, value):
        self._votes = value

    @property
    def lastSabotage(self):
        return self._lastSabotage

    @lastSabotage.setter
    def lastSabotage(self, value):
        self._lastSabotage

class BehaviorsStatistics:
    """See the most-used behaviors"""
    def __init__(self):
        self.total = 0
        self.entries = dict()

#============
# UTILS
#============
#---------------------------------------
# Matrix class from Sebastrian Thrun's Udacity course (self-driving car)
#
class matrix:

    # implements basic operations of a matrix class

    # ------------
    #
    # initialization - can be called with an initial matrix
    #

    def __init__(self, value = [[]]):
        self.value = value
        self.dimx  = len(value)
        self.dimy  = len(value[0])
        if value == [[]]:
            self.dimx = 0

    # ------------
    #
    # makes matrix of a certain size and sets each element to zero
    #

    def zero(self, dimx, dimy):
        if dimy == 0:
            dimy = dimx
        # check if valid dimensions
        if dimx < 1 or dimy < 1:
            raise ValueError, "Invalid size of matrix"
        else:
            self.dimx  = dimx
            self.dimy  = dimy
            self.value = [[0.0 for row in range(dimy)] for col in range(dimx)]

    # ------------
    #
    # makes matrix of a certain (square) size and turns matrix into identity matrix
    #

    def identity(self, dim):
        # check if valid dimension
        if dim < 1:
            raise ValueError, "Invalid size of matrix"
        else:
            self.dimx  = dim
            self.dimy  = dim
            self.value = [[0.0 for row in range(dim)] for col in range(dim)]
            for i in range(dim):
                self.value[i][i] = 1.0
    # ------------
    #
    # prints out values of matrix
    #

    def show(self, txt = ''):
        for i in range(len(self.value)):
            print txt + '['+ ', '.join('%.3f'%x for x in self.value[i]) + ']'
        print ' '

    # ------------
    #
    # defines elmement-wise matrix addition. Both matrices must be of equal dimensions
    #

    def __add__(self, other):
        # check if correct dimensions
        if self.dimx != other.dimx or self.dimx != other.dimx:
            raise ValueError, "Matrices must be of equal dimension to add"
        else:
            # add if correct dimensions
            res = matrix()
            res.zero(self.dimx, self.dimy)
            for i in range(self.dimx):
                for j in range(self.dimy):
                    res.value[i][j] = self.value[i][j] + other.value[i][j]
            return res

    # ------------
    #
    # defines elmement-wise matrix subtraction. Both matrices must be of equal dimensions
    #

    def __sub__(self, other):
        # check if correct dimensions
        if self.dimx != other.dimx or self.dimx != other.dimx:
            raise ValueError, "Matrices must be of equal dimension to subtract"
        else:
            # subtract if correct dimensions
            res = matrix()
            res.zero(self.dimx, self.dimy)
            for i in range(self.dimx):
                for j in range(self.dimy):
                    res.value[i][j] = self.value[i][j] - other.value[i][j]
            return res

    # ------------
    #
    # defines multiplication. Both matrices must be of fitting dimensions
    #

    def __mul__(self, other):
        # check if correct dimensions
        if self.dimy != other.dimx:
            raise ValueError, "Matrices must be m*n and n*p to multiply"
        else:
            # multiply if correct dimensions
            res = matrix()
            res.zero(self.dimx, other.dimy)
            for i in range(self.dimx):
                for j in range(other.dimy):
                    for k in range(self.dimy):
                        res.value[i][j] += self.value[i][k] * other.value[k][j]
        return res


    # ------------
    #
    # returns a matrix transpose
    #

    def transpose(self):
        # compute transpose
        res = matrix()
        res.zero(self.dimy, self.dimx)
        for i in range(self.dimx):
            for j in range(self.dimy):
                res.value[j][i] = self.value[i][j]
        return res

    # ------------
    #
    # creates a new matrix from the existing matrix elements.
    #
    # Example:
    #       l = matrix([[ 1,  2,  3,  4,  5],
    #                   [ 6,  7,  8,  9, 10],
    #                   [11, 12, 13, 14, 15]])
    #
    #       l.take([0, 2], [0, 2, 3])
    #
    # results in:
    #
    #       [[1, 3, 4],
    #        [11, 13, 14]]
    #
    #
    # take is used to remove rows and columns from existing matrices
    # list1/list2 define a sequence of rows/columns that shall be taken
    # is no list2 is provided, then list2 is set to list1 (good for
    # symmetric matrices)
    #

    def take(self, list1, list2 = []):
        if list2 == []:
            list2 = list1
        if len(list1) > self.dimx or len(list2) > self.dimy:
            raise ValueError, "list invalid in take()"

        res = matrix()
        res.zero(len(list1), len(list2))
        for i in range(len(list1)):
            for j in range(len(list2)):
                res.value[i][j] = self.value[list1[i]][list2[j]]
        return res

    # ------------
    #
    # creates a new matrix from the existing matrix elements.
    #
    # Example:
    #       l = matrix([[1, 2, 3],
    #                  [4, 5, 6]])
    #
    #       l.expand(3, 5, [0, 2], [0, 2, 3])
    #
    # results in:
    #
    #       [[1, 0, 2, 3, 0],
    #        [0, 0, 0, 0, 0],
    #        [4, 0, 5, 6, 0]]
    #
    # expand is used to introduce new rows and columns into an existing matrix
    # list1/list2 are the new indexes of row/columns in which the matrix
    # elements are being mapped. Elements for rows and columns
    # that are not listed in list1/list2
    # will be initialized by 0.0.
    #

    def expand(self, dimx, dimy, list1, list2 = []):
        if list2 == []:
            list2 = list1
        if len(list1) > self.dimx or len(list2) > self.dimy:
            raise ValueError, "list invalid in expand()"

        res = matrix()
        res.zero(dimx, dimy)
        for i in range(len(list1)):
            for j in range(len(list2)):
                res.value[list1[i]][list2[j]] = self.value[i][j]
        return res

    # ------------
    #
    # Computes the upper triangular Cholesky factorization of
    # a positive definite matrix.
    # This code is based on http://adorio-research.org/wordpress/?p=4560
    #

    def Cholesky(self, ztol= 1.0e-5):

        res = matrix()
        res.zero(self.dimx, self.dimx)

        for i in range(self.dimx):
            S = sum([(res.value[k][i])**2 for k in range(i)])
            d = self.value[i][i] - S
            if abs(d) < ztol:
                res.value[i][i] = 0.0
            else:
                if d < 0.0:
                    raise ValueError, "Matrix not positive-definite"
                res.value[i][i] = sqrt(d)
            for j in range(i+1, self.dimx):
                S = sum([res.value[k][i] * res.value[k][j] for k in range(i)])
                if abs(S) < ztol:
                    S = 0.0
                res.value[i][j] = (self.value[i][j] - S)/res.value[i][i]
        return res

    # ------------
    #
    # Computes inverse of matrix given its Cholesky upper Triangular
    # decomposition of matrix.
    # This code is based on http://adorio-research.org/wordpress/?p=4560
    #

    def CholeskyInverse(self):

        res = matrix()
        res.zero(self.dimx, self.dimx)

        # Backward step for inverse.
        for j in reversed(range(self.dimx)):
            tjj = self.value[j][j]
            S = sum([self.value[j][k]*res.value[j][k] for k in range(j+1, self.dimx)])
            res.value[j][j] = 1.0/ tjj**2 - S/ tjj
            for i in reversed(range(j)):
                res.value[j][i] = res.value[i][j] = \
                    -sum([self.value[i][k]*res.value[k][j] for k in \
                              range(i+1,self.dimx)])/self.value[i][i]
        return res

    # ------------
    #
    # comutes and returns the inverse of a square matrix
    #
    def inverse(self):
        aux = self.Cholesky()
        res = aux.CholeskyInverse()
        return res

    # ------------
    #
    # prints matrix (needs work!)
    #
    def __repr__(self):
        return repr(self.value)


def main():
    pass


if __name__ == '__main__':
    main()
