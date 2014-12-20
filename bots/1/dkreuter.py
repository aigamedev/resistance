# coding: utf-8
"""
@name: Kreuter Bot
@author: Daniel Kreuter
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
"""

from __future__ import print_function, division, unicode_literals

# Variable names are for losers.

# rst: trick spies into revealing themselves

from player import Bot
from game import State, Game
from functools import partial as inf
from itertools import combinations, compress
from pprint import pprint
from copy import copy as shallow_copy
import collections

fprint = rprint = print
pprint = rprint = \
print = lambda *a, **kw: None

class Log:
    Sab = object()
    Vote = object()

def copy(game):
    game = shallow_copy(game)
    game.players = tuple(game.players)
    game.team = game.team and frozenset(game.team)
    return game

class Var:
    __slots__ = ["a"]

    def __init__(self):
        self.a = {}

    def put(self, v, success, prob):
        k = self.a.setdefault(v, [0, 0])
        k[1-success] += 1-prob
        k[0+success] += prob

    def __repr__(self):
        return repr(self.a)

def consistency(hyp):
    c = 1.0
    for pred in hyp:
        c *= pred.consistency()
    return c

def m_out_of_n(v, a=(1, 0)):
    # compute the probability of M-out-of-N events
    # returns len(v)+1 elements
    a = (1, 0)
    for u in v:
        w = 1-u
        a = tuple(a[j]*w+a[j-1]*u for j in range(len(a)))+(0,)
    return a[:-2]

def majority(la):
    return la//2+1

def majority_vote(a):
    """ Usage: majority_vote(m_out_of_n(voters)) """
    return sum(a[len(a)//2+1:])

def weighted(f, a):
    b = map(f, a)
    c = sum(b)
    for d, e in zip(b, a):
        yield d/c, e

def o(i, e):
    if e: return (0, 1)
    else: return (i,)

def probsum(f):
    a = b = 1.0
    for x, y in f:
        s = float(x+y)
        if s==0: continue
        k = 2*min(x,y)/s
        if x > y: a *= k
        else:     b *= k
    A = a+b-a*b
    if A==0.0: return [0, 1, 0]
    return ((1-a)*b/A, a*b/A, (1-b)*a/A)

def probsum2(g):
    return probsum(var.a.get(input, [0, 0]) for var, input in g)

class GlobalStats:

    def __init__(self):
        # Statistics about sabotage behaviour
        self.spy_sab_alw = Var() # Always.
        self.spy_sab_inf = Var() # Lowest id? y/n
        self.spy_sab_sup = Var() # Highest id? y/n
        self.spy_sab_trn = Var() # Turn number? 1..5
        self.spy_sab_ldr = Var() # Am I leader? y/n
        self.spy_sab_lda = Var() # Leaders team? Resistance/Spy
        self.spy_sab_sze = Var() # Team size? ?..?
        self.spy_sab_nsp = Var() # Numer of spies on the team? 0..?
        # Statistics about voting behaviour (Spies)
        self.spy_vte_alw = Var() # Always.
        self.spy_vte_mem = Var() # Am I team member? y/n
        self.spy_vte_ldr = Var() # Am I team leader? y/n
        self.spy_vte_sze = Var() # Team size? ?..?
        self.spy_vte_nsp = Var() # Numer of spies on the team? 0..?
        # Statistics about voting behaviour (Resistance)
        self.rst_vte_alw = Var() # Always.
        self.rst_vte_mem = Var() # Am I team member? y/n
        self.rst_vte_ldr = Var() # Am I team leader? y/n
        self.rst_vte_sze = Var() # Team size? ?..?
        self.rst_vte_obv = Var() # Voting for obvious spies

    def __repr__(self):
        return "GS"+repr(vars(self))

class SuspectTracker:
    "Light version of aigd.LogicalBot's algorithm"
    def __init__(self, _, spies=None):
        self._ = _
        self.spies = spies or set()

    def asdf(self, team, sabotaged, simulate=False):
        suspects = set(team) - self.spies - {self._}
        spies = set(team) & self.spies
        if sabotaged < len(suspects) + len(spies):
            suspects = tuple()
        if not simulate:
            self.spies.update(suspects)
        return suspects

class Prediction:
    track = {}
    cos = set()
    def __init__(self, game, players, _, spies=tuple()):

        self.globalstats = self.track.setdefault(_.name, GlobalStats())
        self.game = game
        self._ = _
        self.spy = _ in spies
        self.tracker = not self.spy and SuspectTracker(_)

        #from player import registry
        #bottype = registry[_.name]
        #self.sim = getattr(bottype, "simulation_model", bottype)(game, _.index, self.spy)

        #self.sim = aigd.LogicalBot(game, _.index, self.spy)
        #self.sim.onGameRevealed(players, set(spies))

        self.sense = 1.0
        self.total = 1.0

    def likeliness_to_accept_team(self, team):
        #return 0.25+0.5*self.sim.vote(team)
        game = copy(self.game)
        game.team = team
        l = probsum2(
            (self.spy and self.spy_vte or self.rst_vte)(
                game, self.cos & set(team)
            )
        )
        return l[1]*0.5+l[2]

    def likeliness_to_sabotage(self, team):
        game = copy(self.game)
        game.team = team

        if not self.spy: return 0       # can't sabotage if not a spy
        if self._ not in team: return 0 # can't sabotage if not in team
        l = probsum2(self.spy_sab(
            self.cos, self.cos&team, game
        ))
        return l[1]*0.5+l[2]

    def consistency(self):
        return self.sense and self.sense/self.total

    # TODO: pass number of suspects, etc. calculate fraction: the possibliy that it was THIS spy who sabotaged
    #       then enter data in self.spy_sab_data with weight=fraction.

    def mission_complete(self, game, sabotaged):
        #self.sim.onMissionComplete(sabotaged)
        if not self.spy:
            self.tracker.asdf(game.team, sabotaged)

    def vote_complete(self, votes, p2v):
        #self.sim.onVoteComplete(votes)
        lat = self.likeliness_to_accept_team(self.game.team)
        if p2v[self._]:
            self.sense += lat
        else:
            self.sense += 1-lat
        self.total += 1
        rprint("the fact that", self._, "voted", p2v[self._] and "YES" or "NO", "for", self.game.team, "changed the consistency to", self.consistency())

    def try5(self, approve):
        if not approve and not self.spy:
            rprint("AHAHAHAH") # sadly it's not a 100% proof
            self.sense /= 4
            

    def spy_sab(self, spies, chosen_spies, game):
        g = self.globalstats
        if self._ not in chosen_spies: return tuple()
        sortspy = sorted(chosen_spies, key=lambda p: p.index)
        assert len(sortspy) >= 1
        return (
            #(g.spy_sab_alw, None),
            (g.spy_sab_inf, sortspy[ 0] == self._),
            (g.spy_sab_sup, sortspy[-1] == self._),
            (g.spy_sab_trn, game.turn),
            (g.spy_sab_ldr, game.leader == self._),
            (g.spy_sab_lda, game.leader in spies),
            (g.spy_sab_sze, len(game.team)),
            (g.spy_sab_nsp, len(spies))
        )

    def spy_vte(self, game, chosen_spies):
        g = self.globalstats
        return (
            #(g.spy_vte_alw, None),
            (g.spy_vte_mem, self._ in game.team),
            (g.spy_vte_ldr, self._ == game.leader),
            (g.spy_vte_sze, len(game.team)),
            (g.spy_vte_nsp, len(chosen_spies))
        )

    def rst_vte(self, game, _=None):
        g = self.globalstats
        return (
            #(g.rst_vte_alw, None),
            (g.rst_vte_mem, self._ in game.team),
            (g.rst_vte_ldr, self._ == game.leader),
            (g.rst_vte_sze, len(game.team)),
            (g.rst_vte_obv, bool(set(game.team) & self.tracker.spies))
        )

    def upload(self, gamelog, spies):
        for game, mode, arg in gamelog:
            chosen_spies = spies & game.team
            if mode == Log.Vote:
                p2v = arg
                flag = p2v[self._]
                prob = 1
                if self.spy:
                    pairs = self.spy_vte(game, chosen_spies)
                else:
                    pairs = self.rst_vte(game)

            elif mode == Log.Sab:
                if not self.spy: continue
                sabotaged = arg
                flag = round_success = sabotaged < 1 # Game.sabotageRequired(game)
                # TODO: reduce s and spies by one if KreuterBot contributed
                prob = round_success and 1 or sabotaged/len(chosen_spies)
                pairs = self.spy_sab(spies, chosen_spies, game)

            for k, v in pairs:
                k.put(v, flag, prob)

    def clone(self, f, *a):
        self = shallow_copy(self)
        self.tracker = self.tracker and SuspectTracker(self._, set(self.tracker.spies))
        getattr(self, f)(*a)
        return self

    def __repr__(self): return (self.spy and "SPY" or "RST")+"["+repr(self._)+"]"

class SelfPrediction(Prediction):
    tracker = None

    def __init__(self, game, players, _, spies=tuple()):
        self._ = _
        self.spy = _ in spies

    # Caller is responsible for ignoring this return value
    def likeliness_to_accept_team(self, team): return 0
    def likeliness_to_sabotage(self, team): return 0

    def mission_complete(self, game, sabotaged): pass
    def vote_complete(self, votes, p2v): pass
    def try5(self, approve): pass
    def consistency(self): return 1.0
    def upload(self, gamelog, spies): pass
    def clone(self, *a): return self
    def __repr__(self): return "SELF["+repr(self._)+"]"

class KreuterBot(Bot):


    #### #### #### #### #### #### API #### #### #### #### #### ####

    def select(self, players, count):
        self.mkplan(self.gen_select, players, count)
        return list(self.plan[0])

    def vote(self, team):
        if not self == self.game.leader:
            self.mkplan(self.gen_vote, frozenset(team))

        otherplan = (self.plan[0], 1-self.plan[1], self.plan[2])
        rprint(self, "voting", self.plan[1] and "YES" or "NO", "for score",
            self.stats[self.plan], "as opposed to", self.stats.get(otherplan, "N/A"))
        return bool(self.plan[1])

    def sabotage(self):
        return bool(self.plan[2])


    #### #### #### #### #### #### SOCIAL ANALYSIS #### #### #### #### #### ####

    def opt(self, tracker, team, sabotaged):
        if not tracker: return 0
        if self in tracker.asdf(team, sabotaged, simulate=True):
            return -1
        return 0

    #### #### #### #### #### #### GAME PHASES #### #### #### #### #### ####

    # hyp, select, vote, accept, sabotage, success

    def dff_hyp(self, func, *args):
        assert self.hyps

        if len(self.hyps) == 1:
            func(1.0, self.hyps[0], *args)
        else:
            for prob, hyp in weighted(consistency, self.hyps):
                func(prob, hyp, *args)

    def gen_select(self, prob, hyp, players, count):
        for team in map(frozenset, combinations(players, count)):
            self.gen_vote(prob, [pred for pred in hyp], team)

    def gen_vote(self, prob, hyp, team):
        dtr = m_out_of_n(pred.likeliness_to_accept_team(team) for pred in hyp)
        m = majority(len(self.game.players))
        rprint("team", team)
        rprint("vote-dtr", dtr)
        for vote in o(1, self.spy or self.game.tries<5):
            acceptance = 1-sum(dtr[:m-vote])
            # Vote successful
            rprint(" gvote", vote, "acceptance", acceptance)
            self.gen_sabotage(prob*acceptance, hyp, team, vote)
            # Vote failed
            pass

    def gen_sabotage(self, prob, hyp, team, vote):
        dtr = m_out_of_n(pred.likeliness_to_sabotage(team) for pred in hyp)
        m = 1 # Game.sabotageRequired(self.game)
        rprint(" sabotage-dtr", dtr)
        if self.spy:
            nhyp = [sum(self.opt(pred.tracker, team, i) for pred in hyp) for i in range(len(dtr))]
            rprint(" nhyp        ", nhyp)
        
        for sabotage in o(0, self.spy and self in team):
            ms = m-sabotage
            success = sum(dtr[:ms])
            if self.spy:
                sosco_v = [s*p for s, p in zip(nhyp[sabotage:], dtr[:len(dtr)-sabotage])]
                sosco = sum(sosco_v[ms:])
                score = 1-2*success
            else:
                sosco = 0
                score = 2*success-1
            key = (team, vote, sabotage)
            fadd = score + sosco*0.5
            fadd *= prob
            self.stats[key] = self.stats.get(key, 0) + fadd
            if self.spy:
                rprint("  gsabotage", sabotage, "success", success, "score", score, "sosco", sosco, "+", fadd)
            else:
                rprint("  gsabotage", sabotage, "success", success, "score", score, "+", fadd)


    #### #### #### #### #### #### NO IDEA #### #### #### #### #### ####

    def mkplan(self, *dff_hyp_args):
        self.stats = {}
        self.dff_hyp(*dff_hyp_args)
        assert self.stats
        pprint(self.stats)
        if not self.spy: self.stats_detection_accuracy()
        if len(self.stats):
            self.plan = max(self.stats, key=self.stats.__getitem__)
        else:
            rprint("Using fallback plan DOWNVOTE, NO SABOTAGE")
            self.plan = [None, False, False]

    def hypmatch(self, spies):
        return {frozenset(p._ for p in hyp if p._ in spies): hyp for hyp in self.hyps}[frozenset(spies)]

    #### #### #### #### #### #### GAME EVENTS #### #### #### #### #### ####

    def onGameRevealed(self, players, spies):
        rprint("\n\n\n\n\n\n\nA===============================")
        self.spies = spies or set()
        self.tracker = SuspectTracker(self)
        self.gamelog = []

        count = [0]
        def P(*a):
            count[0] += 1
            return (a[0] == self and SelfPrediction or Prediction)(self.game, players, *a)

        if self.spy:
            for p in players:
                rprint(p==self and "Z" or p in spies and "S" or "R", p.name)
            self.all_pred = [
                P(p, spies if p in spies else tuple())
                for p in players
            ]
            spo = {zz for zz in self.all_pred if zz.spy}
            for zz in spo: zz.cos = spo
            self.hyps = [self.all_pred]
        else:
            for p in players:
                rprint(p==self and "Y" or "?", p.name)

            # Five players 17 instances of Prediction
            # Ten players 514 instances of Prediction

            d = map(P, players)
            f = [None] * len(players)

            self.all_pred = d[:]
            self.hyps = []

            def sub(p, r, s):
                if not r+s:
                    n = list(compress(players, f))
                    z = {P(p, n) for v, p in zip(f, players) if v}
                    for zz in z: zz.cos = z
                    self.all_pred.extend(z)
                    self.hyps.append(list(z|{t for v, t in zip(f, d) if not v}))
                    #rprint("-*-", n, z, self.hyps[-1])
                    return 

                w = int(self.spy) if players[p] == self else -1 # -.-
                if r and w!=1: f[p]=0; sub(p+1, r-1, s)
                if s and w!=0: f[p]=1; sub(p+1, r, s-1)

            sub(0, 3, 2) # self.game.num_resistance, self.game.num_spies)

            rprint(count[0], "INSTANCES")

    def onMissionAttempt(self, *a):
        rprint("________________________________")

    def onVoteComplete(self, votes):
        rprint(self.game.leader, "chose", self.game.team, "which was", sum(votes)>len(self.game.players)/2 and "ACCEPTED" or "REJECTED")
        p2v = dict(zip(self.game.players, votes))
        for p, v in p2v.items():
            rprint(p, "voted", v and "YES" or "NO")
        self.gamelog.append((copy(self.game), Log.Vote, p2v))
        for pred in self.all_pred:
            approve = p2v[pred._]
            pred.vote_complete(votes, p2v)
            if self.game.tries == 5:
                pred.try5(approve)

    def onMissionComplete(self, sabotaged):
        rprint("The mission", sabotaged and "FAILED" or "SUCCEEDED")
        self.gamelog.append((copy(self.game), Log.Sab, sabotaged))
        print("recorded", self.gamelog[-1])

        if not self.spy:

            suspects = self.tracker.asdf(self.game.team, sabotaged)

            def tnt(hyp):
                for pred in hyp:
                    if pred._ in suspects:
                        if pred.spy: pred.consistency = lambda: 1
                        else: return False
                return True

            if suspects:
                self.hyps = filter(tnt, self.hyps)
                print("detected new spies", suspects, "hyps left:", len(self.hyps))

            if len(self.spies) == 2: #self.game.num_spies:
                if len(self.hyps) > 1: self.hyps = [self.hypmatch(self.spies)]

        for pred in self.all_pred:
            pred.mission_complete(self.game, sabotaged)

    def onGameComplete(self, win, spies):
        rprint("V===============================")
        rprint(win == self.spy and "LOST "*5 or "WON "*5)
        if not self.spy: self.stats_detection_accuracy(spies)

        for pred in self.hypmatch(spies):
            pred.upload(self.gamelog, spies)

        pprint(self.stats)
        for name, globalpred in Prediction.track.items():
            rprint(name)
            pprint(vars(globalpred))

    @classmethod
    def onCompetitionFinished(self):
        return
    
        from pprint import pprint
        for name, globalpred in Prediction.track.items():
            fprint(name)
            pprint(vars(globalpred))

    #### #### #### #### #### #### STAT OUTPUT #### #### #### #### #### ####

    def stats_detection_accuracy(self, spies=tuple()):
        return

        print = rprint
        cc = map(consistency, self.hyps)
        z = sum(cc)
        ranking = sorted(zip(cc, self.hyps))
        top = ranking #[-3:]
        #print("RSTART", len(top), len(ranking))
        for ur in top:
            gw, guess = ur
            perfect = True
            print(gw/z)
            for i in sorted(guess, key=lambda i: self.game.players.index(i._)):
                l = {False: "R", True: "S"}
                if i.spy != (i._ in spies): perfect = False
                if i._ == self:
                    print("- -", str(i._).ljust(20), i.consistency())
                else:
                    print(l[i.spy], spies and l[i._ in spies] or "-", str(i._).ljust(20), i.consistency())
            print("PERFECT!" if perfect else "")
