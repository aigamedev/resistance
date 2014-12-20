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
        self.calls = {}

    def step(self, count=1):
        for _ in range(count):
            super(FakeGame, self).step()

    def __getattribute__(self, name):
        """Intercept all observer notifications for functions named on*() and
        store the arguments."""
        if name.startswith('on'):
            def onCallback(*args):
                self.calls[name] = args
                return BaseGame.__getattribute__(self, name)(*args)
            return onCallback
        return BaseGame.__getattribute__(self, name)

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
        self.assertNotIn('onGameRevealed', self.game.calls)

    def test_AfterPreparation(self):        
        self.game.step()
        self.assertEquals(self.game.state.phase, State.PHASE_SELECTION)
        self.assertIn('onGameRevealed', self.game.calls)


class TestGameSelection(unittest.TestCase):

    def setUp(self):
        self.game = FakeGame()
        self.game.step()

    def test_BeforeSelection(self):
        self.assertEquals(self.game.state.phase, State.PHASE_SELECTION)
        self.assertNotIn('onTeamSelected', self.game.calls)

    def test_AfterSelection(self):
        self.game.replay = [
            ('selection', self.game.state.players[0:2])
        ]
        self.game.step()
        self.assertEquals(self.game.state.phase, State.PHASE_VOTING)
        self.assertIn('onTeamSelected', self.game.calls)


class TestGameVoting(unittest.TestCase):

    def setUp(self):
        self.game = FakeGame()
        self.game.replay = [
            ('selection', self.game.state.players[0:2])
        ]
        self.game.step(2)

    def test_BeforeVoting(self):
        self.assertEquals(self.game.state.phase, State.PHASE_VOTING)
        self.assertNotIn('onVoteComplete', self.game.calls)

    def test_AfterMajoritySupportThenProceed(self):
        # When a majority votes the mission up, the game goes to mission phase.
        self.game.replay = [('votes', (True, True, True, False, False))]
        self.game.step()
        self.assertEquals(self.game.state.phase, State.PHASE_MISSION)
        self.assertEquals(self.game.state.turn, 1)
        self.assertEquals(self.game.state.tries, 1)
        self.assertIn('onVoteComplete', self.game.calls)
        self.assertNotIn('onMissionFailed', self.game.calls)

    def test_AfterMajorityAgainstThenRetry(self):
        # When a majority votes the mission down, the game proceeds to next try.
        self.game.replay = [('votes', (True, True, False, False, False))]
        self.game.step()        
        self.assertEquals(self.game.state.phase, State.PHASE_ANNOUNCING)
        self.assertEquals(self.game.state.turn, 1)
        self.assertEquals(self.game.state.tries, 2)
        self.assertIn('onVoteComplete', self.game.calls)
        self.assertIn('onMissionFailed', self.game.calls)


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
        self.assertNotIn('onMissionComplete', self.game.calls)

    def test_AfterMissionFails(self):
        self.game.replay.append(('sabotages', 1))
        self.game.step()
        self.assertEquals(self.game.state.phase, State.PHASE_ANNOUNCING)
        self.assertEquals(self.game.state.losses, 1)
        self.assertIn('onMissionComplete', self.game.calls)

    def test_AfterMissionSucceeds(self):
        self.game.replay.append(('sabotages', 0))
        self.game.step()
        self.assertEquals(self.game.state.phase, State.PHASE_ANNOUNCING)
        self.assertEquals(self.game.state.wins, 1)
        self.assertIn('onMissionComplete', self.game.calls)


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
        self.assertNotIn('onAnnouncement', self.game.calls)

    def test_AfterAnnouncement(self):
        p = self.game.state.players
        self.game.replay.append(('announcements', [(p[0], {p[1]: 1.0})]))
        self.game.step()
        self.assertIn('onAnnouncement', self.game.calls)

        self.assertEquals(self.game.state.phase, State.PHASE_SELECTION)
        self.assertEquals(self.game.state.leader, self.game.state.players[1])


if __name__ == "__main__":
    unittest.main()
