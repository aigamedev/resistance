import unittest
from mock import MagicMock as Mock

from client import ResistanceClient

class MockProtocol(object):
    join = Mock()
    send = Mock()


class TestClient(ResistanceClient):
    def __init__(self):
        MockProtocol.join.reset_mock()
        MockProtocol.send.reset_mock()

        ResistanceClient.__init__(self, MockProtocol())



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
        client.message('REVEAL #game-0001; PLAYERS 1-Random, 2-Hippie, 3-Paranoid; ROLE Resistance.')
        self.assertEquals(3, len(client.players['#game-0001']))
        self.assertEquals('[1-Random, 2-Hippie, 3-Paranoid]', str(client.players['#game-0001']))
    
    def test_StartMission(self):
        client = TestClient()
        client.message('MISSION #game-0001 1.2; LEADER 1-Random.')
        self.assertEquals(1, client.games['#game-0001'].turn)
        self.assertEquals(2, client.games['#game-0001'].tries)

    def test_SelectTeam(self):
        client = TestClient()
        client.message('SELECT 3.')
        self.assertEquals(3, client.count)
        self.assertCalled(client.protocol.send, 'SELECTED 1-Random, 2-Hippie, 3-Deceiver.')

    def test_VoteSelection(self):
        client = TestClient()
        client.message('VOTE 1-Random, 2-Hippie, 3-Deceiver.')
        self.assertCalled(client.protocol.send, 'VOTED Yes.')
        

if __name__ == '__main__':
    unittest.main()
