import unittest
from mock import MagicMock as Mock

from player import Player
from server import ProxyBot


class MockClient(object):
    def __init__(self):
        self.msg = Mock()

class TestServerProxyBot(unittest.TestCase):

    def assertCalled(self, mock, *params):
        mock.assert_called_once_with(*params)

    def test_OnRevealResistance(self):
        b = ProxyBot(None, 1, False, MockClient())
        b.onGameRevealed([Player('Test', i) for i in range(1,6)], [])
        self.assertCalled(b.client.msg, 'AJC', 'REVEAL #game-0001; ID 1-AJC; ROLE Resistance; PLAYERS 1-Test, 2-Test, 3-Test, 4-Test, 5-Test.')
        
    def test_OnRevealSpy(self):
        b = ProxyBot(None, 2, True, MockClient())
        b.onGameRevealed([Player('Test', i) for i in range(1,6)], [Player('Spy', 4), Player('Spy', 5)])
        self.assertCalled(b.client.msg, 'AJC', 'REVEAL #game-0001; ID 2-AJC; ROLE Spy; PLAYERS 1-Test, 2-Test, 3-Test, 4-Test, 5-Test; SPIES 4-Spy, 5-Spy.')


if __name__ == '__main__':
    unittest.main()
