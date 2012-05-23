from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

from player import Player
from game import State


class ResistanceClient(object):

    def __init__(self, protocol):
        self.protocol = protocol
        self.games = {}
        self.players = {}

    def process_JOIN(self, msg):
        game = msg.rstrip('.').split(' ')[1]
        self.games[game] = State()
        self.protocol.join(game)

    def process_REVEAL(self, msg):
        info = msg.split(';')
        game = info[0].split(' ')[1]
        players = []
        for p in info[1].split(' ')[2:]:
            ident = p.rstrip(',').split('-')
            players.append(Player(ident[1], int(ident[0])))
        self.players[game] = players

    def process_SELECT(self, msg):
        count = int(msg.rstrip('.').split(' ')[1])
        self.count = count
        self.protocol.send('SELECTED 1-Random, 2-Hippie, 3-Deceiver.')

    def process_VOTE(self, msg):
        self.protocol.send('VOTED Yes.')

    def process_MISSION(self, msg):
        mission = msg.split(';')[0]
        game = mission.split(' ')[1]
        self.games[game] = State()
        details = mission.split(' ')[2].split('.')
        self.games[game].turn = int(details[0])
        self.games[game].tries = int(details[1])

    def message(self, msg):
        cmd = msg.split(' ')[0]
        process = getattr(self, 'process_'+cmd)
        process(msg)


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

