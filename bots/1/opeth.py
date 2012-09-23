"""
@name: Opeth Bot
@author: Daniel Rodriguez
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
"""

from player import Bot
from game import State
import random


class Opeth(Bot):
    """Opeth is a melancholic bot."""

    # List of spies. We only get this info if we are a spy.
    spy_spies = None

    # My interpretation of the world. This is dict where keys are Player objects
    # and values are confidence scores for each player. Confidence scores start
    # at 0 and get higher if I believe that player is not a spy.
    # We do not use any additional info granted to us if we are a spy to update
    # this.
    my_guess = dict()

    # This is like my_guess except we update it based on information that other
    # resistance members have. It is not as accurate as my_guess but will
    # provide an insight on what other bots think about the world.
    their_guess = dict()

    # List of players that I am sure are spies.
    spies_for_sure = set()

    def onGameRevealed(self, players, spies):
        """This function will be called to list all the players, and if you're
        a spy, the spies too -- including others and yourself.
        @param players  List of all players in the game including you.
        @param spies    List of players that are spies, or an empty list.
        """
        self.spy_spies = spies

        self.my_guess = dict(zip(players, [0] * 5))
        self.their_guess = dict(zip(players, [0] * 5))

    def onMissionAttempt(self, mission, tries, leader):
        """Callback function when a new turn begins, before the
        players are selected.
        @param mission  Integer representing the mission number (1..5).
        @param tries    Integer count for its number of tries (1..5).
        @param leader   A Player representing who's in charge.
        """
        pass

    def select(self, players, count):
        """Pick a sub-group of players to go on the next mission.
        @param players  The list of all players in the game to pick from.
        @param count    The number of players you must now select.
        @return list    The players selected for the upcoming mission.
        """
        me = [p for p in players if p.index == self.index]

        # As a spy, pick myself and others who are not spies.
        # if self.spy:
        #    others = [p for p in players if p not in self.spy_spies]
        #    return me + random.sample(others, count-1)

        # It makes a lot of sense to be part of the team so we will always propose ourselves.

        if not self.spy:
            # I am not a spy. Select myself and the people I trust the most.
            team = self.getPlayersITrust(count)
        else:
            # I am a spy. Select myself and the people I think they trust the most.
            team = self.getPlayersTheyTrust(count)

        # If I am not on that list, replace the last element
        if me[0] not in team:
            team.pop()
            team = team + me

        return team

    def onTeamSelected(self, leader, team):
        """Called immediately after the team is selected to go on a mission,
        and before the voting happens.
        @param leader   The leader in charge for this mission.
        @param team     The team that was selected by the current leader.
        """

        # Because we are bots and there is no conversation involved, there is no
        # point in not selecting yourself as part of the team. If they didn't
        # do it, that is suspicious.
        if leader not in team:
            self.my_guess[leader] -= 5
            self.their_guess[leader] -= 5

        pass

    def vote(self, team):
        """Given a selected team, decide whether the mission should proceed.
        @param team      List of players with index and name.
        @return bool     Answer Yes/No.
        """

        self.log.debug("Voting for:")
        self.log.debug(team)

        # Approve my own team.
        if self.index == self.game.leader.index:
            self.log.debug("Yup. I am the leader.")
            return True

        # Both types of factions have constant behavior on the last try.
        if self.game.tries == 5:
            self.log.debug("Last try!")
            return not self.spy

        # Spies select any mission with one or more spies on it.
        if self.spy:
            self.log.debug("Yup. I am a spy and there is at least one spy on the team.")
            return len([p for p in team if p in self.spy_spies]) > 0
    
        # I am resistance. Vote against teams that have at least one of 2 most untrustested players
        worst = self.getPlayersITrust(2, True)
        for player in worst:
            if player in team and self.my_guess[player] < 0:
                self.log.debug("Nope. I don't trust these guys:")
                self.log.debug(worst)
                self.log.debug(team)
                return False
    
        #If I'm not on the team, and it's a team of 3...
        if len(team) == 3 and not self in team:
            self.log.debug("Nope. It's a a team of 3 and I am not in it:")
            self.log.debug(team)
            return False    

        return True

    def onVoteComplete(self, votes):
        """Callback once the whole team has voted.
        @param votes        Boolean votes for each player (ordered).
        """
        if votes > 3:
            self.log.debug("* Team approved!")
        else:
            self.log.debug("* Team rejected!")
        pass

    def sabotage(self):
        """Decide what to do on the mission once it has been approved.  This
        function is only called if you're a spy, otherwise you have no choice.
        @return bool        Yes to shoot down a mission.
        """

        spies = [s for s in self.game.team if s in self.spy_spies]

        # Special cases:

        # Sabotage to win (spies won 2 times already)
        if self.game.losses == 2:
            self.log.debug("Sabotaging because spies have won 2 missions")
            return True

        # Sabotage to not loose (resistance won 2 times already). 
        # Only do it if there is at least a non spy on the team.
        if self.game.wins == 2 and len(spies) < len(self.game.team):
            self.log.debug("Sabotaging because resistance has won 2 missions")
            return True

        # If I am the only spy
        if len(spies) == 1:
            return True
            if (len(self.game.team) == 3):
                self.log.debug("Sabotaging because I am the only spy on a team of 3.")
                return True

            if (len(self.game.team) == 2):
                # We will confuse them only if they haven't won anything.
                self.log.debug("Sabotaging: " + str(self.game.wins != 0) + " because I am the only spy and the number of wins is " + str(self.game.wins))
                return self.game.wins != 0
            return True

        if len(spies) > 1:
            if self.index == self.game.leader.index:
                self.log.debug("Sabotaging. There is more than one spy in the team but I am the leader")
                return True

            if self.game.leader in spies:
                self.log.debug("Not sabotaging. There is more than one spy but I am not the leader.")
                return False

            # More than one spy and non of us is the leader. 
            # Make this decision based on the number of wins.
            self.log.debug("Sabotaging: " + str(self.game.wins > 1) + " because I am not the only spy and the number of wins is " + str(self.game.wins))
            return self.game.wins > 1

        return True

    def onMissionComplete(self, sabotaged):
        """Callback once the players have been chosen.
        @param selected     List of players that participated in the mission.
        @param sabotaged    Integer how many times the mission was sabotaged.
        """

        # Can we know for sure if the whole team are spies?
        if len(self.game.team) == sabotaged:
            for spy in self.game.team:
                if spy.index != self.index:
                    self.my_guess[spy] -= 100
                    self.spies_for_sure.add(spy)
                self.their_guess[spy] -= 100

        # Can we know for sure if the rest of the team is a spy?
        # 3 conditions: I am not a spy, I am in the team,
        # and the number of sabotaged votes is equal to the
        # team size minus one (my vote)
        if not self.spy and self in self.game.team and sabotaged == len(self.game.team) - 1:
            for spy in self.game.team:
                if spy.index != self.index:
                    self.my_guess[spy] -= 100
                    self.spies_for_sure.add(spy)

        # If this mission failed, that team gets penalized (according to the number of times the mission was sabotaged),
        # otherwise we gain confidence in them.
        for player in self.game.team:
            if sabotaged:
                if player.index != self.index:
                    self.my_guess[player] -= sabotaged
                self.their_guess[player] -= sabotaged
            else:
                self.my_guess[player] += 2
                self.their_guess[player] += 2

        # If the leader is not in the team but the mission succeded, restore confidence in him, I guess.
        if self.game.leader not in self.game.team:
            if sabotaged == 0:
                self.my_guess[self.game.leader] += 5
                self.their_guess[self.game.leader] += 5
            else:
                # If the mission was sabottaged, punish him further.
                self.my_guess[self.game.leader] -= sabotaged
                self.their_guess[self.game.leader] -= sabotaged

        # Print stats
        if sabotaged == 0:
            self.log.debug("*** SUCCEDED ***")
        else:
            self.log.debug("*** SABOTAGED *** " + str(sabotaged) + " times.")
        self.log.debug("Leader: " + self.game.leader.name);

        self.log.debug("--- Team:")
        for player in self.game.team:
            self.log.debug(player.name + ": " +  str(self.my_guess[player]))

        self.log.debug("--- The rest:")
        for player in self.game.players:
            if player in self.game.team: 
                continue
            self.log.debug(player.name + ": " +  str(self.my_guess[player]))


        self.log.debug("---------------------------------------------------")


    def onGameComplete(self, win, spies):
        """Callback once the game is complete, and everything is revealed.
        @param win          Boolean if the Resistance won.
        @param spies        List of only the spies in the game.
        """

        self.log.debug("*************************** GAME RESULTS ***************************")
        self.log.debug("Am I as spy? " + str(self.spy))
        if self.spy:
            self.log.debug("--- Actual spies:")
            for player in self.spy_spies:
                self.log.debug(player.name)
        self.log.debug("--- My guess:")
        for player in self.game.players:
            self.log.debug(player.name + ": " +  str(self.my_guess[player]))
        self.log.debug("--- What I think is their guess:")
        for player in self.game.players:
            self.log.debug(player.name + ": " +  str(self.my_guess[player]))
        self.log.debug("******************************* DONE *******************************")
        self.log.debug(self.my_guess)

        pass

    def getPlayersITrust(self, number_players, reversed=False):
        """Returns a sorted list of the number_players more trustworthy players.
        @param number_players How many players do you want?
        """
        sorted_list = sorted(self.game.players, key=lambda player: self.my_guess[player], reverse=not reversed)
        sorted_list.remove(self)
        return sorted_list[:number_players]

    def getPlayersTheyTrust(self, number_players, reversed=False):
        sorted_list = sorted(self.game.players, key=lambda player: self.their_guess[player], reverse=not reversed)
        return sorted_list[:number_players]
