import random
import itertools

from game import State
from player import Bot


class StateChecker(Bot):

    def onGameRevealed(self, players, spies):
        self.leadership = itertools.cycle(players)

        s = State()
        s.players = players
        s.leader = next(self.leadership)
        self.state = s

    def onMissionAttempt(self, mission, tries, leader):
        self.state.phase = 1
        self.state.team = None
        self.state.votes = None
        self.state.sabotages = None
        if not (self.state == self.game):
            print("EXPECTED %r ACTUAL %r" % (self.state, self.game))
        assert self.state == self.game

    def select(self, players, count):
        assert not self.game.team
        return random.sample(players, count)

    def onTeamSelected(self, leader, team):
        assert self.state.leader == leader
        for p in team:
            assert p in self.state.players
        self.state.team = team
        if not (self.state == self.game):
            print("EXPECTED %r ACTUAL %r" % (self.state, self.game))
        assert self.state == self.game
        self.state.phase = 2

    def vote(self, team):
        assert self.state.team == team
        return random.choice([True, False])

    def onVoteComplete(self, votes):
        self.state.votes = votes
        if not (self.state == self.game):
            print("EXPECTED %r ACTUAL %r" % (self.state, self.game))
        assert self.state == self.game
        if len([v for v in votes if v]) > len([v for v in votes if not v]):
            self.state.phase = 3

    def sabotage(self):
        assert self.spy
        if not (self.state == self.game):
            print("EXPECTED %r ACTUAL %r" % (self.state, self.game))
        assert self.state == self.game
        return True

    def onMissionComplete(self, sabotaged):
        assert len([v for v in self.game.votes if v]) > len([v for v in self.game.votes if not v])

        self.state.sabotages = sabotaged
        if sabotaged:
            self.state.losses += 1
        else:
            self.state.wins += 1

        if not (self.state == self.game):
            print("EXPECTED %r ACTUAL %r" % (self.state, self.game))
        assert self.state == self.game

        self.state.turn += 1
        self.state.tries = 1
        self.state.leader = next(self.leadership)
        self.state.phase = 1

    def onMissionFailed(self, leader, team):
        assert len([v for v in self.game.votes if v]) < len([v for v in self.game.votes if not v])
        assert leader == self.state.leader
        assert team == self.state.team

        if not (self.state == self.game):
            print("EXPECTED %r ACTUAL %r" % (self.state, self.game))
        assert self.state == self.game
        self.state.tries += 1
        self.state.leader = next(self.leadership)
        self.state.phase = 1
