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

    def reply(self, message):
        self.protocol.msg(self.recipient, message)

    def process_JOIN(self, msg):
        game = msg.rstrip('.').split(' ')[1]
        self.protocol.join(game)
        self.reply('JOINED %s.' % (game))

    def process_REVEAL(self, mission, identifier, players, role):
        game = mission.split(' ')[1]
        self.makeGame(game)

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
        self.reply('SELECTED %s.' % ', '.join([str(Player(s.name, s.index)) for s in selection]))

    def process_VOTE(self, vote, team):
        # VOTE #game-0002;
        game = vote.split(' ')[1]
        bot = self.games[game]['bots'][0]

        # TEAM 1-Random, 2-Hippie, 3-Paranoid.
        result = bot.vote(self.games[game]['state'].leader, self.makeTeam(team))
        reply = {True: "Yes", False: "No"}
        self.reply('VOTED %s.' % (reply[result]))

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
        self.reply('OK.')

    def process_SABOTAGE(self, mission, team):
        # SABOTAGE #game-0002;
        game = mission.split(' ')[1]
        bot = self.games[game]['bots'][0]

        # TEAM 1-Random, 2-Hippie, 3-Paranoid.
        result = bot.sabotage(self.makeTeam(team))
        reply = {True: "Yes", False: "No"}
        self.reply('SABOTAGED %s.' % (reply[result]))

    def makeTeam(self, team):
        return [self.makePlayer(t) for t in team.split(' ')[1:]]

    def makePlayer(self, identifier):
        index, name = identifier.split('-')
        return Player(name, int(index))

    def makeGame(self, game):
        self.games[game] = {'state': State(), 'bots': []}

    def message(self, sender, msg):
        cmd = msg.split(' ')[0]
        process = getattr(self, 'process_'+cmd)
        args = [i.strip(' ') for i in msg.rstrip('.').split(';')]
        self.recipient = sender
        process(*args)
        self.recipient = None


class ResistanceProtocol(irc.IRCClient):
           
    def __init__(self):
        self.client = None

    def getNickname(self):
        return self.factory.nickname

    nickname = property(getNickname)

    def signedOn(self):
        print 'Signed on!'
        self.client = ResistanceClient(self, self.factory.constructor)
        self.join('#resistance')

    def joined(self, channel):
        pass

    def privmsg(self, user, channel, msg):
        u = user.split('!')[0]
        self.client.message(user, msg)
    

class ResistanceFactory(protocol.ClientFactory):

    protocol = ResistanceProtocol

    def __init__(self, bot):
        self.constructor = bot
        self.nickname = bot.__name__

    def clientConnectionLost(self, connector, reason):        
        print 'Connection lost.', reason
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed.', reason
        reactor.stop()


if __name__ == '__main__':

    from bots import RandomBot
    f = ResistanceFactory(RandomBot)
    reactor.connectTCP("irc.aigamedev.com", 6667, f)
    reactor.run()

