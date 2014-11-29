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
        self.state.team = None
        assert self.state == self.game

    def select(self, players, count):
        assert not self.game.team
        return random.sample(players, count)

    def onTeamSelected(self, leader, team):
        assert self.state.leader is leader
        for p in team:
            assert p in self.state.players
        self.state.team = team
        assert self.state == self.game

    def vote(self, team):
        assert self.state.team == team
        return random.choice([True, False])

    def onVoteComplete(self, votes):
        assert self.state == self.game

    def sabotage(self):
        assert self.state == self.game
        return True

    def onMissionComplete(self, sabotaged):
        if sabotaged:
            self.state.losses += 1
        else:
            self.state.wins += 1
        assert self.state == self.game

        self.state.turn += 1
        self.state.tries = 1
        self.state.leader = next(self.leadership)

    def onMissionFailed(self, leader, team):
        assert leader == self.state.leader
        assert team == self.state.team
        assert self.state == self.game
        self.state.tries += 1
        self.state.leader = next(self.leadership)
