import random

from player import Bot 


class Bounder(Bot):

    def __init__(self, index, spy):
        Bot.__init__(self, "Bounder", index, spy)
        self.index = index
        self.spy = spy
        # logging.basicConfig(filename='Bounder.log',filemode = 'w',level=logging.ERROR)
        if spy: 
            self.strong_configs = self.weak_configs = [] # modelling opponents irrelevant for spies
        else: 
            # each of these configs corresponds to a possible arrangement of spies among the other players
            # strong configs is a lower bound - it assumes spies always defect
            # weak configs is an upper bound - it assumes spies may or may not defect
            self.strong_configs = range(6)
            self.weak_configs = range(6)

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
            Never includes me.
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
            Never includes me.
        """
        notme = [p for p in range(5) if p != self.index]
        return [p for p in notme if p not in self.get_spies(v)]

    def onGameRevealed(self, players, spies):
        """ Update data at the start of the game once I know players (and spies if I am a spy).
        """
        self.spies = [p.index for p in spies]

    def select(self, players, count):
        """ Select players for a mission I will lead.
        """
        if self.spy:
            # return me plus (count-1) non-spies
            return [p for p in players if p.index == self.index] + \
                random.sample([p for p in players if p.index != self.index and p.index not in self.spies], count-1)
        else:
            if len(self.strong_configs) > 0:
                #Choose a random strong configuration which includes me
                indices = random.sample(self.get_resistance(random.choice(self.strong_configs)), count-1) + [self.index]
                return [p for p in players if p.index in indices]
            else:
                #Choose a random weak configuration which includes me
                indices = random.sample(self.get_resistance(random.choice(self.weak_configs)), count-1) + [self.index]
                return [p for p in players if p.index in indices]

    def vote(self, team, leader, tries):
        """ Vote for a mission team proposed by leader (given a number of tries to date).
        """
        if self.spy:
            if tries == 4:
                return False
            else:
                return len([p for p in team if p.index in self.spies]) > 0 # Vote yes if spy on team, no otherwise
        else:
            if tries == 4:
                return True
            ti = [p.index for p in team]
            # Is the team compatible with a config which contains no spy?
            if len(self.strong_configs) == 0:
                vote = len([c for c in self.weak_configs if self.compatible(c,ti,0,False)]) > 0
            else:
                vote = len([c for c in self.strong_configs if self.compatible(c,ti,0,True)]) > 0
            if vote: votestring = "for"
            else: votestring = "against" 
            # logging.debug("Me: " + str(self.index) + ". Try: " + str(tries) + ". Vote " + votestring + " Team: " + str(ti) \
            #    + ". Possible strong configs: " + self.configs_to_string([c for c in self.strong_configs if self.compatible(c,ti,0,True)]) \
            #    + ". Possible weak configs: " + self.configs_to_string([c for c in self.weak_configs if self.compatible(c,ti,0,False)]))
            return vote

    def onVoteComplete(self, players, votes, team):
        pass

    def compatible(self, config, selectedplayerindices, sabotage, strong):
        """ Is config compatible with the mission result assuming spies always lie (strong == True)
            or assuming spies may or may not lie (strong == False)
        """
        num_selected_spies = len([s for s in selectedplayerindices if s in self.get_spies(config)])
        if strong: 
            return num_selected_spies == sabotage
        else:
            return num_selected_spies >= sabotage            

    def onMissionComplete(self, selectedPlayers, sabotaged):
        """ Update legal strong and weak configs give a mission result.
        """
        if not self.spy:
            spi = [p.index for p in selectedPlayers]
            self.strong_configs = [c for c in self.strong_configs if self.compatible(c,spi,sabotaged,True)] 
            self.weak_configs = [c for c in self.weak_configs if self.compatible(c,spi,sabotaged,False)] 
            # logging.debug("Me: " + str(self.index) + ". Mission result: " + str(sabotaged) + " for team " + str(spi) +\
            #    ". Possible strong configs: " + self.configs_to_string(self.strong_configs) + \
            #    ". Possible weak configs: " + self.configs_to_string(self.weak_configs) + "\n")

    def sabotage(self, team):
        return self.spy

    def onGameComplete(self, players, spies):
        # logging.debug("-----------------------------------------------\n")
        pass
