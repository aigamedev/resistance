from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

from game import State


class ResistanceClient(object):

    def __init__(self, protocol):
        self.protocol = protocol
        self.games = {}
        self.players = {}

    def message(self, msg):
        if msg.startswith('JOIN'):
            game = msg.split(' ')[1]
            self.games[game] = State()
            self.protocol.join(game)
        elif msg.startswith('REVEAL'):
            info = msg.split(';')
            game = info[0].split(' ')[1]
            self.players[game] = range(5)


class ResistanceProtocol(irc.IRCClient):
           
    def __init__(self):
        self.games = {}

    def getNickname(self):
        return self.factory.nickname

    nickname = property(getNickname)

    def signedOn(self):
        print 'Signed on!'
        self.join('#resistance')

    def joined(self, channel):
        # if channel.startswith('#game'):
        #   self.bot[channel] = DeceiverBot()
        pass

    def privmsg(self, user, channel, msg):
        u = user.split('!')[0]

    def action(self, user, channel, msg):
        print 'ACTION', user.split('!')[0], channel, msg
    

class ResistanceFactory(protocol.ClientFactory):

    protocol = ResistanceProtocol

    def __init__(self, bot):
        self.constructor = bot
        self.nickname = bot.__class__.__name__

    def clientConnectionLost(self, connector, reason):        
        print 'Connection lost.', reason
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed.', reason
        reactor.stop()


if __name__ == '__main__':

    from bots import RandomBot
    import sys
    f = ResistanceFactory(RandomBot)
    reactor.connectTCP("irc.aigamedev.com", 6667, f)
    reactor.run()

