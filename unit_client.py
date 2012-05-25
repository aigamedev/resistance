import unittest
from mock import MagicMock as Mock

from player import Player
from bots import Hippie
from client import ResistanceClient

class MockProtocol(object):
    join = Mock()
    send = Mock()


class TestClient(ResistanceClient):
    def __init__(self):
        MockProtocol.join.reset_mock()
        MockProtocol.send.reset_mock()

        ResistanceClient.__init__(self, MockProtocol(), Hippie)
        self.createGame('#game-0002')


class TestResistanceClient(unittest.TestCase):

    def assertCalled(self, mock, *params):
        mock.assert_called_once_with(*params)

    def test_JoinGame(self):
        client = TestClient()
        client.message('JOIN #game-0001.')
        self.assertTrue('#game-0001' in client.games)
        self.assertCalled(client.protocol.join, '#game-0001')

    def test_RevealGame(self):
        client = TestClient()
        client.message('REVEAL #game-0001; ID 2-Hippie; PLAYERS 1-Random, 2-Hippie, 3-Paranoid; ROLE Spy.')
        players = client.players['#game-0001']
        self.assertEquals(3, len(players))
        self.assertEquals('[1-Random, 2-Hippie, 3-Paranoid]', str(players))
        for p in players:
            self.assertTrue(isinstance(p, Player))

        bots = client.games['#game-0001']['bots']
        self.assertEquals(1, len(bots))
        self.assertTrue(isinstance(bots[0], Hippie))
        self.assertEquals('<Hippie #2 SPY>', str(bots[0]))
    
    def test_StartMission(self):
        client = TestClient()
        client.message('MISSION #game-0002 1.2; LEADER 1-Random.')
        self.assertEquals(1, client.games['#game-0002']['state'].turn)
        self.assertEquals(2, client.games['#game-0002']['state'].tries)

        leader = client.games['#game-0002']['state'].leader
        self.assertTrue(isinstance(leader, Player))
        self.assertEquals('1-Random', str(leader))

    def test_SelectTeam(self):
        client = TestClient()
        client.message('REVEAL #game-0001; ID 2-Hippie; PLAYERS 1-Random, 2-Hippie, 3-Paranoid; ROLE Spy.')
        client.message('SELECT #game-0001 3.')
        self.assertCalled(client.protocol.send, 'SELECTED 1-Random, 2-Hippie, 3-Paranoid.')

    def test_VoteSelection(self):
        client = TestClient()
        client.message('VOTE 1-Random, 2-Hippie, 3-Paranoid.')
        self.assertCalled(client.protocol.send, 'VOTED Yes.')
        

if __name__ == '__main__':
    unittest.main()
