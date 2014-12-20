import unittest

import random

from player import Player
from game import State, BaseGame


class FakeGame(BaseGame):

    def __init__(self, replay=[]):
        super(FakeGame, self).__init__()
        self.state.players = [Player("Mock", i) for i in range(5)]
        self.state.leader = self.next_leader()
        self.spies = set()

        self.replay = replay

    def step(self, count=1):
        for _ in range(count):
            super(FakeGame, self).step()

    def get_selection(self, count):
        phase, data = self.replay.pop(0)
        assert phase == 'selection'
        return data

    def get_votes(self):
        phase, data = self.replay.pop(0)
        assert phase == 'votes'
        return data

    def get_sabotages(self):
        phase, data = self.replay.pop(0)
        assert phase == 'sabotages'
        return data

    def get_announcements(self):
        phase, data = self.replay.pop(0)
        assert phase == 'announcements'
        return data


class TestGamePreparation(unittest.TestCase):

    def setUp(self):
        self.game = FakeGame()

    def test_BeforePreparation(self):
        self.assertEquals(self.game.state.phase, State.PHASE_PREPARING)

    def test_AfterPreparation(self):
        self.game.step()
        self.assertEquals(self.game.state.phase, State.PHASE_SELECTION)


class TestGameSelection(unittest.TestCase):

    def setUp(self):
        self.game = FakeGame()
        self.game.step()

    def test_BeforeSelection(self):
        self.assertEquals(self.game.state.phase, State.PHASE_SELECTION)

    def test_AfterSelection(self):
        self.game.replay = [
            ('selection', self.game.state.players[0:2])
        ]
        self.game.step()
        self.assertEquals(self.game.state.phase, State.PHASE_VOTING)


class TestGameVoting(unittest.TestCase):

    def setUp(self):
        self.game = FakeGame()
        self.game.replay = [
            ('selection', self.game.state.players[0:2])
        ]
        self.game.step(2)

    def test_BeforeVoting(self):
        self.assertEquals(self.game.state.phase, State.PHASE_VOTING)

    def test_AfterMajoritySupportThenProceed(self):
        # When a majority votes the mission up, the game goes to mission phase.
        self.game.replay = [('votes', (True, True, True, False, False))]
        self.game.step()
        self.assertEquals(self.game.state.phase, State.PHASE_MISSION)
        self.assertEquals(self.game.state.turn, 1)
        self.assertEquals(self.game.state.tries, 1)

    def test_AfterMajorityAgainstThenRetry(self):
        # When a majority votes the mission down, the game proceeds to next try.
        self.game.replay = [('votes', (True, True, False, False, False))]
        self.game.step()        
        self.assertEquals(self.game.state.phase, State.PHASE_ANNOUNCING)
        self.assertEquals(self.game.state.turn, 1)
        self.assertEquals(self.game.state.tries, 2)


class TestGameMission(unittest.TestCase):

    def setUp(self):
        self.game = FakeGame()
        self.game.replay = [
            ('selection', self.game.state.players[0:2]),
            ('votes', (True, True, True, True, True)),
        ]
        self.game.step(3)

    def test_BeforeMission(self):
        self.assertEquals(self.game.state.phase, State.PHASE_MISSION)

    def test_AfterMissionFails(self):
        self.game.replay.append(('sabotages', 1))
        self.game.step()
        self.assertEquals(self.game.state.phase, State.PHASE_ANNOUNCING)
        self.assertEquals(self.game.state.losses, 1)

    def test_AfterMissionSucceeds(self):
        self.game.replay.append(('sabotages', 0))
        self.game.step()
        self.assertEquals(self.game.state.phase, State.PHASE_ANNOUNCING)
        self.assertEquals(self.game.state.wins, 1)


class TestAnnouncements(unittest.TestCase):

    def setUp(self):
        self.game = FakeGame()
        self.game.replay = [
            ('selection', self.game.state.players[0:2]),
            ('votes', (True, True, True, True, True)),
            ('sabotages', 0)
        ]
        self.game.step(4)

    def test_BeforeAnnouncement(self):
        self.assertEquals(self.game.state.phase, State.PHASE_ANNOUNCING)
        self.assertEquals(self.game.state.leader, self.game.state.players[0])

    def test_AfterAnnouncement(self):
        self.game.replay.append(('announcements', {}))
        self.game.step()
        self.assertEquals(self.game.state.phase, State.PHASE_SELECTION)
        self.assertEquals(self.game.state.leader, self.game.state.players[1])


if __name__ == "__main__":
    unittest.main()
