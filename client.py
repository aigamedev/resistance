from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

from player import Player
from game import State


class ResistanceClient(object):

    def __init__(self, protocol, constructor):
        self.protocol = protocol
        self.constructor = constructor
        self.games = {}
        self.players = {}

    def process_JOIN(self, msg):
        game = msg.rstrip('.').split(' ')[1]
        self.protocol.join(game)
        self.createGame(game)

    def createGame(self, game):
        self.games[game] = {'state': State(), 'bots': []}

    def process_REVEAL(self, mission, identifier, players, role):
        game = mission.split(' ')[1]
        self.createGame(game)

        # ID 2-Random;
        index, name = identifier.split(' ')[1].split('-')
        bot = self.constructor(name, int(index), False)
        self.games[game]['bots'].append(bot)

        # PLAYERS 1-Deceiver, 2-Random, 3-Hippie;
        participants = []
        for p in players.split(' ')[1:]:
            ident = p.rstrip(',').split('-')
            participants.append(Player(ident[1], int(ident[0])))
        self.players[game] = participants

        # ROLE Spy.
        role = role.split(' ')[1]
        bot.spy = bool(role == 'Spy')

    def process_SELECT(self, select):
        game, count = select.split(' ')[1:]
        bot = self.games[game]['bots'][0]
        selection = sorted(bot.select(self.players[game], int(count)), key = lambda p: p.index)
        self.protocol.send('SELECTED %s.' % ', '.join([str(Player(s.name, s.index)) for s in selection]))

    def process_VOTE(self, game, team):
        game = select.split(' ')[1:]
        bot = self.games[game]['bots'][0]
        selection = [self.makePlayer(t) for t in team.split(' ')]
        result = bot.vote(self.games[game]['state'].leader, selection)
        self.protocol.send('VOTED Yes.')

    def process_MISSION(self, mission, leader):
        # MISSION #game-0002 1.2;
        game = mission.split(' ')[1]
        details = mission.split(' ')[2].split('.')
        state = self.games[game]['state']
        state.turn = int(details[0])
        state.tries = int(details[1])

        # LEADER 1-Random.
        index, name = leader.split(' ')[1].split('-')
        state.leader = Player(name, int(index))

    def makePlayer(self, identifier):
        index, name = identifier.split('-')
        return Player(name, int(index))

    def message(self, msg):
        cmd = msg.split(' ')[0]
        process = getattr(self, 'process_'+cmd)
        args = [i.strip(' ') for i in msg.rstrip('.').split(';')]
        process(*args)


class ResistanceProtocol(irc.IRCClient):
           
    def __init__(self):
        self.client = ResistanceClient(self, self.factory.constructor)

    def getNickname(self):
        return self.factory.nickname

    nickname = property(getNickname)

    def signedOn(self):
        print 'Signed on!'
        self.join('#resistance')

    def joined(self, channel):
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

