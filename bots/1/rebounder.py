"""
@name: Rebounder Bot
@author: Peter Cowling (The University of York) 
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
"""

import random

from player import Bot


__all__ = ['Rebounder']

def intersection(*lists):
    """ Return the intersection of all of the lists presented as arguments.
    """
    if len(lists) == 0: return []
    ilist = lists[0]
    for i in range (1,len(lists)):
        ilist = [x for x in ilist if x in lists[i]]
    return ilist

def nonempty_intersection(*lists):
    """ Find the first list that is nonempty (lists[i]). 
        Then find the intersection(lists[i],lists[i+1],...) sequentially,
        but ignore lists whose intersection with previous intersections leads to an empty set,
    """
    i = 0
    while i < len(lists) and len(lists[i]) == 0: i += 1
    if i == len(lists): return []

    nelist = lists[i]
    for j in range (i+1, len(lists)):
        templist = [x for x in nelist if x in lists[j]]
        if templist != []: nelist = templist
    return nelist

class Rebounder(Bot):

    def onGameRevealed(self, players, spies):
        self.spies = spies
        # logging.debug("Revealed: " + str(players))

        if self.spy: 
            self.strong_configs = self.weak_configs = self.vote_configs = self.select_configs = [] # modelling opponents irrelevant for spies
        else: 
            # each of these configs corresponds to a possible arrangement of spies among the other players
            # strong_configs is a lower bound - it assumes spies always defect
            # weak_configs is an upper bound (and always true) - it assumes spies may or may not defect
            # vote_configs assumes a spy will vote against any team that does not contain a spy
            # select_configs assumes a spy will always choose a team consisting of himself plus non-spies
            self.strong_configs = range(6)
            self.weak_configs = range(6)
            self.vote_configs = range(6)
            self.select_configs = range(6)

    def configs_to_string(self, configs):
        """ Return the possible spy pairs for the given list of configs (from the point of view of self) 
        """
        outstr = ""
        for c in configs:
            for s in self.get_spies(c):
                outstr += str(s)
            outstr += " "
        return outstr

    def get_spies(self, v):
        """ Get the list of spy indices corresponding to config[v]
            Never includes me. Not used if I am a spy.
        """
        notme = [p for p in range(5) if p != self.index]
        if v==0:   return [notme[0], notme[1]]
        elif v==1: return [notme[0], notme[2]]
        elif v==2: return [notme[0], notme[3]]
        elif v==3: return [notme[1], notme[2]]
        elif v==4: return [notme[1], notme[3]]
        elif v==5: return [notme[2], notme[3]]
        else: assert(False)

    def get_resistance(self,v):
        """ Get the list of resistance indices corresponding to config[v]. 
            Never includes me. Not used if I am a spy.
        """
        notme = [p for p in range(5) if p != self.index]
        return [p for p in notme if p not in self.get_spies(v)]

    def select(self, players, count):
        """ Select players for a mission I will lead.
        """
        if self.spy:
            # return me plus (count-1) non-spies
            resistance = [p for p in players if p != self and p not in self.spies]
            return [self] + random.sample(resistance, count-1)
                #random.sample([p for p in players if p.index != self.index], count-1)
        else:
            assert len(self.get_select_configs()) > 0
            indices = random.sample(self.get_resistance(random.choice(self.get_select_configs())), count-1) + [self.index]
            return [p for p in players if p.index in indices]

    def get_select_configs(self):
        return nonempty_intersection(self.weak_configs, self.strong_configs, self.select_configs, self.vote_configs)

    def vote(self, team):
        """ Vote for a mission team proposed by leader (given a number of tries to date).
        """
        if self.spy:
            if self.game.tries == 5:
                return False
            else:
                return len([p for p in team if p in self.spies]) > 0 # Vote yes if spy on team, no otherwise
        else:
            if self.game.leader.index == self.index: return True
            if self.game.tries == 5:
                return True
            self.select_configs = [c for c in self.select_configs if self.select_compatible(c,team,self.game.leader)] 
            ti = [p.index for p in team]
            # Is the team compatible with a config which contains no spy?
            if len(self.strong_configs) == 0:
                vote = len([c for c in self.weak_configs if self.compatible(c,ti,0,False)]) > 0
            else:
                vote = len([c for c in self.strong_configs if self.compatible(c,ti,0,True)]) > 0
            if vote: votestring = "for"
            else: votestring = "against" 
            # logging.debug("Me: " + str(self.index) + ". Try: " + str(self.game.tries) + ". Vote " + votestring + " Team: " + str(ti) \
            #    + ". Possible strong configs: " + self.configs_to_string([c for c in self.strong_configs if self.compatible(c,ti,0,True)]) \
            #    + ". Possible weak configs: " + self.configs_to_string([c for c in self.weak_configs if self.compatible(c,ti,0,False)]))
            return vote

    def onVoteComplete(self, votes):
        self.vote_configs = [c for c in self.vote_configs if self.vote_compatible(c,self.game.players,votes,self.game.team)]
        # if not self.spy: logging.debug("Votes: " + str(votes))

    def vote_compatible(self, config, players, votes, team):
        """ Is config compatible with the voting assuming a spy will vote against any team that does not contain a spy?
            Also assume that all spies will vote against any team on the 4th try and any resistace will vote for.
        """
        forids = [players[i].index for i in range(5) if votes[i] == True] 
        num_selected_spies = len([s for s in team if s.index in self.get_spies(config)])
        num_spyvotesfor = len([p for p in self.get_spies(config) if p in forids])
        return (num_selected_spies > 0 or self.game.tries == 5) and num_spyvotesfor == 2 \
            or num_selected_spies == 0 and num_spyvotesfor == 0

    def select_compatible(self, config, team, leader):
        """ Is config compatible with the selection assuming a spy will 
            always propose a team consisting of himself plus non-spies
        """
        num_selected_spies = len([s for s in team if s.index in self.get_spies(config)])
        return leader.index in [p.index for p in team] and \
            leader.index in self.get_spies(config) and \
            num_selected_spies == 1

    def compatible(self, config, selectedplayerindices, sabotage, strong):
        """ Is config compatible with the mission result assuming spies always lie (strong == True)
            or assuming spies may or may not lie (strong == False)
        """
        num_selected_spies = len([s for s in selectedplayerindices if s in self.get_spies(config)])
        if strong: 
            return num_selected_spies == sabotage
        else:
            return num_selected_spies >= sabotage            

    def onMissionComplete(self, sabotaged):
        """ Update legal strong and weak configs given a mission result.
        """
        if not self.spy:
            spi = [p.index for p in self.game.team]
            self.strong_configs = [c for c in self.strong_configs if self.compatible(c,spi,sabotaged,True)] 
            self.weak_configs = [c for c in self.weak_configs if self.compatible(c,spi,sabotaged,False)] 
            # logging.debug("Me: " + str(self.index) + ". Mission result: " + str(sabotaged) + " for team " + str(spi) +\
            #    ". Possible strong configs: " + self.configs_to_string(self.strong_configs) + \
            #    ". Possible weak configs: " + self.configs_to_string(self.weak_configs) + \
            #    ". Possible vote configs: " + self.configs_to_string(self.vote_configs) + \
            #    ". Possible select configs: " + self.configs_to_string(self.select_configs) + "\n")

    def sabotage(self):
        """ Sabotage if I am the only spy in the team, or if the other spy on the team is random,
            or if it is two of me as spies and I have the lower index.
        """
        if self.spy:
            other_spy = [s for s in self.spies if s.index != self.index][0]
            if other_spy.index not in [p.index for p in self.game.team] or \
                other_spy.name == "Random" or \
                (other_spy.name == self.name and self.index < other_spy.index):
                return True
        return False

    def onGameComplete(self, players, spies):
        # logging.debug("-----------------------------------------------\n")
        pass


class RebounderWStSeV(Rebounder):
    def get_select_configs(self):
        return nonempty_intersection(self.weak_configs, self.strong_configs, self.select_configs, self.vote_configs)

class RebounderWStVSe(Rebounder):
    def get_select_configs(self):
        return nonempty_intersection(self.weak_configs, self.strong_configs, self.vote_configs, self.select_configs)

class RebounderWSeVSt(Rebounder):
    def get_select_configs(self):
        return nonempty_intersection(self.weak_configs, self.select_configs, self.vote_configs, self.strong_configs)

class RebounderWVSeSt(Rebounder):
    def get_select_configs(self):
        return nonempty_intersection(self.weak_configs, self.vote_configs, self.select_configs, self.strong_configs)

