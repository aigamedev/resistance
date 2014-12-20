"""
@name: Clymily Bot
@author: Tom Schaul <schaul@cims.nyu.edu>
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
"""

try:
    import cPickle as pickle #@UnusedImport
except:
    import pickle #@Reimport
    
from itertools import product
from collections import defaultdict
from util import Variable
from math import sqrt
import random

from player import Bot, Player

__all__ = ['Clymily']


def pickleDumpDict(name, d):
    """ pickle-dump a variable into a file """
    try:
        f = open(name + '.pickle', 'w')
        pickle.dump(d, f)
        f.close()
        return True
    except Exception, e:
        # print 'Error writing into', name, ':', str(e)
        return False


def pickleReadDict(name):
    """ pickle-read a (default: dictionary) variable from a file """
    try:
        f = open(name + '.pickle')
        val = pickle.load(f)
        f.close()
    except Exception, e:
        # print 'Nothing read from', name, ':', str(e)
        val = {}
    return val

def maskSome(tup, num):
    if num == 0:
        return [tup]
    pre = maskSome(tup, num-1)
    res = []
    for i in range(len(tup)):
        for p in pre:
            if p[i] is None:
                break
            res.append(p[:i]+[None]+p[i+1:])
    return res

class StatBase():
    
    name = 'logs/prob_db'
    
    delay = 50
    
    def __init__(self):
        # populate with dictionaries for all useful cases
        self._data = {}
        for l in [2,3]:
            # c, t-size
            self._data[('c', l)] = defaultdict(Variable)
            for numspies in [1,2]:
                for sabs in range(numspies+1):
                    # m, t-size, num-of-spies, num-of-sabotages
                    self._data[('m', l, numspies, sabs)] = defaultdict(Variable)            
            for isspy in [True, False]:
                for team in StatBase._allCanonical(l, isspy):
                    # v, isspy, (isonteam, t-size, numspies)                      
                    self._data[('v', isspy, team)] = defaultdict(Variable)
                    # s, isspy, (isonteam, t-size, numspies)                      
                    self._data[('s', isspy, team)] = defaultdict(Variable)
                
    def load(self):
        d1 = pickleReadDict(self.name)        
        d2 = pickleReadDict(self.name + '2')
        if len(d1) == 0:
            d1 = self._data
        if len(d2) == 0:
            d2 = self._data
        l1 = sum([len(x) for x in d1.values()])
        l2 = sum([len(x) for x in d2.values()])        
        if l1 < l2:
            self._data = d2
        else:
            self._data = d1
        if l1 == 0:
            self.store([0])
        if l2 == 0:
            self.store([1])
        
    def store(self, ticker=[0]):
        if ticker[0] % self.delay == 0:
            pickleDumpDict(self.name, self._data)
        if ticker[0] % self.delay == 1:
            pickleDumpDict(self.name + '2', self._data)
        ticker[0] += 1            
        
    def pprint(self):
        print "Player statistics on %s / %s topics." % (len(self._data), sum([len(x) for x in self._data.values()]))
        for n, d in sorted(self._data.items()):
            if len(d) > 0:
                print n
                for k, v in sorted(d.items()):
                    if v.total > 0 and v.samples > 0 and None not in k:
                        print k, v, v.samples
    
    @staticmethod                    
    def _canonical(team, subject, spies):
        """ Unique representation of team composition from one perspective """
        return (subject in team, len(team), len(spies.intersection(team)))
    
    @staticmethod
    def _allCanonical(size, leaderspy):
        for inteam in [True, False]:
            if leaderspy and inteam:
                minspies = 1
            else:
                minspies = 0
            if not leaderspy and inteam:
                maxspies = size-1
            else:
                maxspies = min(2, size)
            for ns in range(minspies, maxspies+1):
                yield (inteam, size, ns)
                
    def addSampleM(self, updown, output, tsize,
                   actors, greens):
        d = self._data[('m', tsize, len(actors), output)]
        if len(actors) == 1:
            for k in product([actors[0], None], [greens, None]):
                d[tuple(k)].sample(updown)
        else:
            for k in product([actors[0], None], [actors[1], None], [greens, None]):
                d[tuple(k)].sample(updown)
            
    def getProbM(self, output, tsize, actors, greens):
        d = self._data[('m', tsize, len(actors), output)]
        if len(actors) == 1:
            return self._estimateProb(d, (actors[0], greens))            
        else:
            return self._estimateProb(d, (actors[0], actors[1], greens))
            
    def addSampleV(self, updown, isspy, team,
                   actor, isleader, greens, vround):
        d = self._data[('v', isspy, team)]
        for k in product([actor, None], [isleader, None], [greens, None], [vround, None]):
            d[tuple(k)].sample(updown)
    
    def getProbV(self, isspy, team, actor, isleader, greens, vround):
        d = self._data[('v', isspy, team)]
        return self._estimateProb(d, (actor, isleader, greens, vround))            
        
    def addSampleC(self, updown, tsize,
                   actor, partner, isleader, greens):
        d = self._data[('c', tsize)]
        for k in product([actor, None],[partner, None], [isleader, None], [greens, None]):
            d[tuple(k)].sample(updown)
    
    def getProbC(self, tsize, actor, partner, isleader, greens):
        d = self._data[('c', tsize)]
        return self._estimateProb(d, (actor, partner, isleader, greens))                
        
    def addSampleS(self, updown, output, isspy,
                   actor, greens, vround):
        d = self._data[('s', isspy, output)]
        for k in product([actor, None], [greens, None], [vround, None]):
            d[tuple(k)].sample(updown)
    
    def getProbS(self, output, isspy, actor, greens, vround):
        d = self._data[('s', isspy, output)]
        return self._estimateProb(d, (actor, greens, vround))            
    
        
    def _estimateProb(self, dic, fullkey):
        """ If there is not enough info on the full scenario,
        gradually loosen the constraints to get at least a good prior. """        
        prior_params = {1: (50, 8),
                        2: (30, 4),
                        3: (20, 2),
                        4: (10, 1)}        
        v = Variable()        
        v.total = 0.5 + dic[fullkey].total   # uncertainty bias
        v.samples = 1 + dic[fullkey].samples
        for skipunits in range(1,len(fullkey)+1):
            bound, weight = prior_params[skipunits]
            if v.samples > bound:
                break
            for nkey in maskSome(list(fullkey), skipunits):
                if tuple(nkey) not in dic:
                    continue
                tmp = dic[tuple(nkey)]
                if tmp.samples == 0:
                    continue
                weight = min(weight, tmp.samples/float(skipunits))
                v.samples += weight
                v.total += weight*tmp.total/float(tmp.samples)                
        return v.total/float(v.samples)
                                    


class Statistics(object):
    """ Keep track during a game and update values at the end, when the 
    ground truth is known. """
        
    def reset(self, players):
        self.players = players
        self.votes = []
        self.selections = []
        self.missions = []
        self.cooperations = []
            
    def _name(self, index):
        return [p.name for p in self.players if p.index==index][0]
            
    def resolve(self, spies):        
        for t, s, g, lname in self.missions:
            spynames = tuple(sorted([self._name(p) for p in spies.intersection(t)]))             
            if len(spynames) > 0:
                for sval in range(len(spynames)+1):
                    allPlayerStats.addSampleM(updown=(sval==s), output=sval, tsize=len(t),
                                              actors=spynames, greens=g)  
            if s==2:
                allPlayerStats.addSampleC(updown=True, tsize=len(t), actor=spynames[0], 
                                          partner=spynames[1], isleader=(spynames[0]==lname), greens=g)
                allPlayerStats.addSampleC(updown=True, tsize=len(t), actor=spynames[1], 
                                          partner=spynames[0], isleader=(spynames[1]==lname), greens=g)
            elif s==0 and len(spynames)==2:
                allPlayerStats.addSampleC(updown=False, tsize=len(t), actor=spynames[0], 
                                          partner=spynames[1], isleader=(spynames[0]==lname), greens=g)
                allPlayerStats.addSampleC(updown=False, tsize=len(t), actor=spynames[1], 
                                          partner=spynames[0], isleader=(spynames[1]==lname), greens=g)
        
                        
        for n1, n2, tl, g, leader, sab in self.cooperations:
            allPlayerStats.addSampleC(updown=sab, tsize=tl, actor=n1, 
                                      partner=n2, isleader=leader, greens=g)
        
        for t, l, v, vote, g, r in self.votes:
            ct = StatBase._canonical(t, v, spies)
            allPlayerStats.addSampleV(updown=vote, team=ct, isspy=(v in spies),
                                      actor=self._name(v), isleader=(l==v), 
                                      greens=g, vround=r)  
                        
        for t, l, g, r in self.selections:
            ct = StatBase._canonical(t, l, spies)
            for oteam in StatBase._allCanonical(len(t), l in spies):
                allPlayerStats.addSampleS(updown=(oteam==ct), output=oteam, isspy=(l in spies),
                                          actor=self._name(l), greens=g, vround=r)
                    
        allPlayerStats.store()                



    def hypothesis(self, spies, me, verbose=False):
        """ Compute the likelihood of this set of spies, given
        the currently accumulated evidence. """
        totprob = 1.
        if verbose:
            print '\nHypothesis', spies
        
        # TODO: normalize by alternatives! This is all incorrect?
        for t, s, g, _ in self.missions:
            spynames = sorted([self._name(p) for p in spies.intersection(t)])             
            if len(t)==2 and s==2 and len(spies.intersection(t)) == 2:
                if verbose:
                    print '  obvious bad:', t, s
                return 1e50
            elif len(spynames) < s:
                if verbose:
                    print '  obvious not bad:', t, s, spynames
                return 1e-50
            elif len(spynames) > 0:
                prob = allPlayerStats.getProbM(s, len(t), spynames, g)
                if verbose:
                    print '   mission', t, s, g, '\t',spynames, '\t', round(prob,4)                    
                totprob *= prob            
                
        for t, l, g, r in self.selections:
            if l == me:
                # no recursive evidence from my own actions.
                continue
            ct = StatBase._canonical(t, l, spies)
            prob = allPlayerStats.getProbS(ct, l in spies, self._name(l), g, r)
            if verbose:
                print '    select',  t, '\t', l,self._name(l),  g, ct, '\t', round(prob,4)                
            totprob *= sqrt(prob)
        
        for t, l, vt, vote, g, r in self.votes:
            if vt == me:
                continue
            ct = StatBase._canonical(t, vt, spies)
            prob = allPlayerStats.getProbV(vt in spies, ct, self._name(vt), l==vt, g, r)
            if verbose:
                print '     vote', t, l, '\t', vt, self._name(vt), vote, g, '\t', ct, '\t', round(prob,4)                
            if vote:
                totprob *= sqrt(sqrt(prob))
            else:
                totprob *= sqrt(sqrt(1-prob))
        
        if verbose:
            print "  Result:", totprob
            print
        return totprob
                            


# global variable initialized here
allPlayerStats = StatBase()
allPlayerStats.load()




def nod(*_):
    return True

def nay(*_):
    return False


class SubsumptionBot(Bot):
    """ Actual strategy is composed from a collection of (priority, condition, action) tuples.
    Behaviors with the same priority, and condition that holds, are picked from randomly. """

    @property
    def _otherspy(self):
        return [s for s in self.spies if s != self][0]
    
    @property
    def _me(self):
        return Player(self.name, self.index)        



    def _amIOnTeam(self, team):
        return self.index in [p.index for p in team]
    
    def _isSpyOnTeam(self, team):
        return len(self.spies.intersection(team)) > 0
    
    def _isExactlyOneSpyTeam(self, team):
        return len(self.spies.intersection(team)) == 1
    
    def _isMySelection(self, team):
        return self.game.leader == self
    
    # when a resistance bot sometimes knows the spies
    def _perfectTeam(self, players, count):
        return random.sample(set(players).difference(self.spies), count)
        
    
    
    def _randomTeam(self, players, count):
        return random.sample(players, count)
        
    def _teamWithMe(self, players, count):        
        return [self._me] + random.sample(self.others(), count-1)
        
    def _teamWithMeAndRes(self, players, count):
        otherres = [p for p in players if p not in self.spies]
        return [self._me] + random.sample(otherres, count-1)
    
    def _teamWithMeAndSpy(self, players, count):               
        otherres = [p for p in players if p not in self.spies]
        return list(self.spies) + random.sample(otherres, count-2)
    
    def _teamWithMeAndOneRes(self, players, count):
        if count == 2:
            return self._teamWithMeAndRes(players, count)
        else:
            return self._teamWithMeAndSpy(players, count)
        
    def _teamWithMeNotTaboo(self, players, count):
        for _ in range(100):
            team = self._teamWithMe(players, count)
            if not self._isTaboo(team):
                return team
        # back-up, as this may not terminate if I'm an obvious spy
        return self._teamWithMe(players, count)          
    
    def _teamWithSpyNotTaboo(self, players, count):
        for _ in range(200):
            team = self._randomTeam(players, count)
            if not self._isTaboo(team) and self._isExactlyOneSpyTeam(team):
                return team
        return self._teamWithMe(players, count)     

    def _teamNotTaboo(self, players, count):
        while True:
            team = self._randomTeam(players, count)
            if not self._isTaboo(team):
                return team

    def _teamWithMeAndGood(self, players, count):
        """ Preferably pick members from the last good team """
        if not self.lastgoodteam:
            return self._teamWithMeNotTaboo(players, count)    
        if len(self.lastgoodteam) >= count-1:    
            return [self._me] + random.sample(self.lastgoodteam, count-1)
        else:
            # we need one more unvalidated player
            for p in set(self.others()):
                if p in self.lastgoodteam:
                    continue
                team = [p, self._me]+self.lastgoodteam
                if not self._isTaboo(team):
                    break
            return team
        
    def _isTaboo(self, team):
        self.taboo.sort()
        for t in self.taboo:
            if set(t).issubset(set(team)):
                return True
        return False

    def _tabooTeam(self, team, sabotaged):
        if len(team) <= sabotaged:
            self.taboo.extend([[p] for p in team])
            if not self.spy:
                self.spies.update(team)
            if len(team) < sabotaged:
                # any logical deduction finds me guilty.
                self.burned_spy = True
        elif len(team) == 3 and sabotaged == 2:
            # all subsets must contain a spy
            self.taboo.extend([team[:-1], team[1:], [team[0], team[-1]]])            
        else:
            self.taboo.append(team)
                
    
            
    def _action(self, dic, *args):
        res = []
        pmax = -1 
        for p, c, a in dic:
            if p < pmax:
                break
            if c(self):
                pmax = p
                res.append(a(*args))    
        return random.choice(res) 
    
    def sabotage(self):
        self.mylastplay = self._action(self.sabotage_behaviors)
        return self.mylastplay
    
    def vote(self, team):
        if self.spy:
            return self._action(self.spy_vote_behaviors, team)
        else:
            return self._action(self.res_vote_behaviors, team)

    def select(self, players, count):
        if self.spy:
            res = self._action(self.spy_select_behaviors, players, count)            
        else:
            res = self._action(self.res_select_behaviors, players, count)
        random.shuffle(res)
        return res


    def onMissionComplete(self, sabotaged):
        if sabotaged:
            if self.spy:     
                # even if I'm a spy, I have to pretend?
                self._tabooTeam(list(self.game.team), sabotaged)
            else:
                self._tabooTeam([p for p in self.game.team if p != self], sabotaged)
            if self.lastgoodteam:
                if self._isTaboo(self.lastgoodteam):
                    self.lastgoodteam = None
        else:
            self.lastgoodteam = [p for p in self.game.team if p != self]
    
    def onGameRevealed(self, players, spies):
        self.players = players
        self.spies = spies
        self.safe = set([self])
        self.taboo = []
        self.burned_spy = False
        self.lastgoodteam = None
        
        self.sabotage_behaviors = [(1e10, lambda s: (s.game.losses == 2), nod),
                                   (0, nod, nod)]     
        self.spy_vote_behaviors = [(1e10, lambda s: (s.game.tries == 5 and s.game.losses == 2), nay), 
                                   (0, nod, nod)]
        self.res_vote_behaviors = [(1e10, lambda s: (s.game.tries == 5), nod), 
                                   (0, nod, nod)]    
        self.spy_select_behaviors = [(0, nod, self._teamWithMe)]    
        self.res_select_behaviors = [(0, nod, self._teamWithMe)]

        self._addBehaviors()
        for blist in [self.sabotage_behaviors, self.spy_vote_behaviors, self.res_vote_behaviors, 
                      self.spy_select_behaviors, self.res_select_behaviors]:
            blist.sort(key=lambda e: -e[0])
        
    def _addBehaviors(self):
        """ For subclasses. """



class StatBot(SubsumptionBot):
    """ A stats-collecting bot. """
    
    def onGameRevealed(self, players, spies):
        super(StatBot, self).onGameRevealed(players, spies)
        self.stats = Statistics()
        self.stats.reset(players)
        self.greens = 0
        self.vround=1
            
    def onTeamSelected(self, leader, team):
        super(StatBot, self).onTeamSelected(leader, team)
        self.lastteam = [p.index for p in team]
        self.stats.selections.append((self.lastteam, leader.index, self.greens, self.vround))
                    
    def onVoteComplete(self, votes):
        super(StatBot, self).onVoteComplete(votes)
        li = self.game.leader.index
        for i, voted in enumerate(votes):
            voter = i
            self.stats.votes.append((self.lastteam, li==voter, voter, voted, self.greens, self.vround))
        self.vround += 1
            
    def onMissionComplete(self, sabotaged):
        super(StatBot, self).onMissionComplete(sabotaged)
        self.stats.missions.append((self.lastteam, sabotaged, self.greens, self.game.leader.name))
        if self.spy:
            missionspies = [s for s in self.spies if s.index in self.lastteam]
            if len(missionspies) == 2:
                # what did I play? What did the other play?
                hisname = self._otherspy.name
                if self.mylastplay:
                    hisplay = (sabotaged==2)
                else:
                    hisplay = (sabotaged==1)
                self.stats.cooperations.append((self.name, hisname, len(self.lastteam), 
                                               self.greens, self.index==self.game.leader.index, self.mylastplay))
                self.stats.cooperations.append((hisname, self.name, len(self.lastteam), 
                                               self.greens, self.index==self.game.leader.index, hisplay))
        if sabotaged == 0:
            self.greens += 1
        self.vround = 1
            
    def onGameComplete(self, win, spies):
        self.stats.resolve(set([s.index for s in spies]))
        
        

class LogicalClone(SubsumptionBot):
    
    def _addBehaviors(self):
        self.spy_vote_behaviors.append((10, nod, self._isSpyOnTeam))
        self.res_vote_behaviors.append((15, self._isMySelection, nod))
        self.res_vote_behaviors.append((10, lambda s: s._isTaboo(s.game.team), nay))
        self.res_vote_behaviors.append((5,  lambda s: (len(s.game.team) == 3 
                                                       and not s._amIOnTeam(s.game.team)), nay))
        self.spy_select_behaviors.append((10, nod, self._teamWithMeAndRes))
        self.res_select_behaviors.append((10, nod, self._teamWithMeAndGood))


 
class InferenceBot(StatBot):
    """ Does inference on who the spies are. """
    
    certaintyThreshold = 0.99999
    
    verbose= False
    
    def onGameRevealed(self, players, spies):
        super(InferenceBot, self).onGameRevealed(players, spies)
        self._hypotheses = self._allpairs() 
        self.hprobs = defaultdict(float)   
        self.sprobs = defaultdict(float)
        
    def onMissionComplete(self, sabotaged):
        super(InferenceBot, self).onMissionComplete(sabotaged)
        if self.game.wins <3 and self.game.losses <3:
            self.inferSpies()
    
    def onTeamSelected(self, leader, team):
        super(InferenceBot, self).onTeamSelected(leader, team)
        self.inferSpies()
        
    def onGameComplete(self, win, spies):
        super(InferenceBot, self).onGameComplete(win, spies)
        # DEBUG
        for s in self.spies:
            if not s in spies:
                print self, self.spy, self.spies, spies
                print self.sprobs
                print self.hprobs
                self.verbose = True
                self.inferSpies()
                #raise
    
    def _allpairs(self):
        """ All possible pairs. """
        res = []
        others = sorted([p for p in self.players if p.index!=self.index]) 
        for ii, i in enumerate(others):
            for j in others[ii+1:]:
                res.append((i,j))
        return res
            
    def inferSpies(self):
        if self.spy:# or len(self.spies)==2:
            if self.verbose:
                print 'Done', self
        else:
            for h in self._hypotheses:
                self.hprobs[h] = self.stats.hypothesis(set([s.index for s in h]), self.index, self.verbose)
            tot = sum(self.hprobs.values())
            for k in self.hprobs:
                self.hprobs[k] /= tot
                if self.verbose:
                    print "The pair %s are the spies with prob %s" %(k, round(self.hprobs[k],3))
            for p in self.players:
                if p.index == self.index:
                    continue
                self.sprobs[p] = 0
                for k in self.hprobs:
                    if p in k:
                        self.sprobs[p] += self.hprobs[k]
                if self.sprobs[p] > self.certaintyThreshold:
                    self.spies.add(p)
                if self.sprobs[p] < (1- self.certaintyThreshold):
                    self.safe.add(p)
            if self.verbose:
                for p in self.sprobs:
                    print "The player %s is a spy with prob %s" %(p, round(self.sprobs[p],3))
        
        #DEBUG
        if len(self.spies) > 2 and not self.verbose:
            self.verbose = True
            print self.players, self.spies
            self.inferSpies()
            self.verbose = False
                
            
    def _inHammerPos(self):
        """ Am I in the position that will propose the fifth team selection? """
        triesUntilLeader = (self.index - self.game.leader.index) % 5
        return (5-self.game.tries) == triesUntilLeader
        
    def _notTooSpyish(self, team):
        spyprob = max([self.sprobs[p] for p in team if p.index!=self.index])
        return spyprob < self._threshold()
            
    def _threshold(self):
        triesUntilLeader = (self.index - self.game.leader.index) % 5
        threshold = 0.2*self.game.tries
        if (5-self.game.tries) > triesUntilLeader:
            threshold /= 2.
        if triesUntilLeader == 0:
            threshold += 0.5
        return threshold            
        
    def _leastSpyish(self, players, count):
        team = sorted([(self.sprobs[p], p) for p in players 
                       if (p not in self.spies and p not in self.safe)])
        s = list(self.safe)
        if len(s) >= count:
            return s[:count]
        else:
            return s + [p for (_,p) in team][:count-len(s)]

    def _myVoteIrrelevant(self, threshold=0.01):
        """ Estimate whether it's likely that 3 others will take the decision on the team already """
        self._estimateVote()
        vs = sorted(self.yesvote)
        return (vs[2] < threshold or vs[1] > (1-threshold)) 
        
    def _estimateVote(self):
        self.yesvote = [0,0,0,0]
        if self.spy:
            cases = [(self.spies, 1)]
        else:
            cases = self.hprobs.items()
        for h, prob in cases:
            for i, p in enumerate(self.others()):
                ct = StatBase._canonical(self.game.team, p, h)
                nodprob = allPlayerStats.getProbV(p in h, ct, p.name, self.game.leader==p, 
                                                  self.greens, self.vround)
                self.yesvote[i] += prob * nodprob
        
    def _otherSpyWillSabotage(self, threshold=0.05):
        if not self._otherspy in self.game.team:
            return False
        prob = allPlayerStats.getProbC(len(self.game.team), self._otherspy.name, self.name, 
                                       self._otherspy==self.game.leader, self.greens)
        return prob > (1-threshold)
        
        
    scambleprob = 0.01
    
    def _addScrambles(self):
        self.sabotage_behaviors.append((25, lambda *_:random.random()<self.scambleprob, nod))
        self.sabotage_behaviors.append((25, lambda *_:random.random()<self.scambleprob, nay))
        self.spy_vote_behaviors.append((25, lambda *_:random.random()<self.scambleprob, nod))
        self.spy_vote_behaviors.append((25, lambda *_:random.random()<self.scambleprob, nay))
        self.spy_select_behaviors.append((25, lambda *_:random.random()<(self.scambleprob*2), self._teamWithMe))
    
        
        
        
class Clymily(InferenceBot, LogicalClone):
    def _addBehaviors(self):
        LogicalClone._addBehaviors(self)
        self.res_vote_behaviors.append((100, lambda s: len(s.spies)==2, 
                                        lambda team: len(set(team).intersection(self.spies))==0))
        self.res_vote_behaviors.append((90, lambda s: len(s.safe)>1, 
                                        lambda team: len(set(team).intersection(self.safe))==len(team)))
        self.res_select_behaviors.append((100, lambda s: len(s.spies)==2, self._perfectTeam))
        self.res_vote_behaviors.append((40, nod, self._notTooSpyish))
        self.res_select_behaviors.append((40, lambda s: nod, self._leastSpyish))

        self.spy_vote_behaviors.append((20, InferenceBot._myVoteIrrelevant, 
                                        lambda team: len(set(team).intersection(self.spies))==0))
        self.sabotage_behaviors.append((20, InferenceBot._otherSpyWillSabotage, nay))
        self._addScrambles()







        
