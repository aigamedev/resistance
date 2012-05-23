import unittest
from mock import MagicMock as Mock

from client import ResistanceClient

class MockProtocol(object):
    join = Mock()


class TestClient(ResistanceClient):
    def __init__(self):
        ResistanceClient.__init__(self, MockProtocol())


class TestResistanceClient(unittest.TestCase):

    def assertCalled(self, mock, *params):
        mock.assert_called_once_with(*params)

    def test_JoinGame(self):
        client = TestClient()
        client.message('JOIN #game-0001')
        self.assertTrue('#game-0001' in client.games)
        self.assertCalled(client.protocol.join, '#game-0001')

    def test_RevealGame(self):
        client = TestClient()
        client.message('REVEAL #game-0001; PLAYERS 1-Random, 2-Hippie, 3-Deceiver, 4-Paranoid, 5-Simple; ROLE Resistance;')
        self.assertEquals(5, len(client.players['#game-0001']))


if __name__ == '__main__':
    unittest.main()
