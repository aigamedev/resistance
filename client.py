import logging
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

from competition import getCompetitors
from player import Player
from game import State


class ResistanceLogger(logging.Handler):

    def __init__(self, protocol):
        logging.Handler.__init__(self)
        self.protocol = protocol
        self.channel = None

    def flush(self):
        pass

    def emit(self, record):
        if self.channel is None:
            return

        try:
            msg = self.format(record)
            self.protocol.msg(self.channel, 'COMMENT %s' % (msg))
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class ResistanceClient(object):

    def __init__(self, protocol, constructor):
        self.protocol = protocol
        self.constructor = constructor
        self.bots = {}

        self.channel = None
        self.logger = None
        self.sender = None

    def getBot(self):
        return self.bots[self.channel]

    def reply(self, message):
        self.protocol.msg(self.channel, message)

    def process_JOIN(self, msg):
        channel = msg.rstrip('.').split(' ')[1]
        self.protocol.join(channel)

    def process_REVEAL(self, reveal, role, players, spies = None):
        # ROLE Resistance.
        index = self.channel.split('-')[-1]
        spy = bool(role.split(' ')[1] == 'Spy')
        bot = self.constructor(State(), int(index), spy)
        if self.logger is None:
            self.logger = ResistanceLogger(self.protocol)
            bot.log.addHandler(self.logger)
            bot.log.setLevel(logging.DEBUG)

        bot.recipient = self.sender
        self.bots[self.channel] = bot

        # PLAYERS 1-Deceiver, 2-Random, 3-Hippie;
        participants = []
        for p in players.split(' ')[1:]:
            participants.append(self.makePlayer(p.rstrip(',')))
        bot.game.players = participants

        # SPIES 1-Deceiver.
        saboteurs = set()
        if spies:
            for s in spies.split(' ')[1:]:
                saboteurs.add(self.makePlayer(s.rstrip(',')))
            bot.game.spies = saboteurs

        bot.onGameRevealed(participants, saboteurs)

    def process_MISSION(self, mission, leader):
        bot = self.getBot()

        # MISSION #game-0002 1.2;
        details = mission.split(' ')[1]
        state = bot.game
        state.turn, state.tries = [int(i) for i in details.split('.')]

        # LEADER 1-Random.
        state.leader = self.makePlayer(leader.split(' ')[1])

        bot.onMissionAttempt(state.turn, state.tries, state.leader)

    def process_SELECT(self, select):
        count = select.split(' ')[1]
        bot = self.getBot()
        players = bot.game.players
        selection = sorted(bot.select(players, int(count)), key = lambda p: p.index)
        self.reply('SELECTED %s.' % (', '.join([str(Player(s.name, s.index)) for s in selection])))

    def process_VOTE(self, team):
        # VOTE 1-Random, 2-Hippie, 3-Paranoid.
        bot = self.getBot()
        bot.game.team = self.makeTeam(team)
        bot.onTeamSelected(bot.game.leader, bot.game.team)
        result = bot.vote(bot.game.team)
        reply = {True: "Yes", False: "No"}
        self.reply('VOTED %s.' % (reply[result]))

    def process_VOTES(self, votes):
        bot = self.getBot()
        v = [bool(b.strip(',.') == 'Yes') for b in votes.split(' ')[1:]]
        bot.onVoteComplete(v)

    def process_SABOTAGE(self, sabotage):
        bot = self.getBot()
        result = bot.spy and bot.sabotage()
        reply = {True: "Yes", False: "No"}
        self.reply('SABOTAGED %s.' % (reply[result]))

    def process_SABOTAGES(self, sabotages):
        bot = self.getBot()
        sabotaged = int(sabotages.split(' ')[1])
        if sabotaged == 0:
            bot.game.wins += 1
        else:
            bot.game.losses += 1
        bot.onMissionComplete(sabotaged)

    def process_RESULT(self, result, spies):
        bot = self.getBot()

        w = bool(result.split(' ')[1] == 'Yes')
        s = self.makeTeam(spies)

        bot.onGameComplete(w, s)
        self.protocol.part(self.channel)
        del self.bots[self.channel]

    def process_QUERY(self, *args):
        bot = self.getBot()
        if 'SELECT' in args[0].upper():
            selection = bot.select(bot.game.players, 3)
            players = [Player(s.name, s.index) for s in selection]
            self.reply("QUERY %s" % (players))

    def makeTeam(self, team):
        return set([self.makePlayer(t.strip('., ')) for t in team.split(' ')[1:]])

    def makePlayer(self, identifier):
        index, name = identifier.split('-')
        return Player(name, int(index))

    def message(self, sender, channel, msg):
        cmd = msg.split(' ')[0].rstrip('?!.')
        if not hasattr(self, 'process_'+cmd):
            return

        process = getattr(self, 'process_'+cmd)
        args = [i.strip(' ') for i in msg.rstrip('.?!').split(';')]
        self.sender = sender
        self.channel = channel
        if self.logger is not None:
            self.logger.channel = channel

        process(*args)

        if self.logger is not None:
            self.logger.channel = None
        self.channel = None
        self.sender = None

    def disconnect(self, user, channel = None):
        for ch, bot in list(self.bots.items()):
            if user != bot.recipient:
                continue
            if not channel or ch == channel:
                self.protocol.part(ch)
                del self.bots[ch]


class ResistanceProtocol(irc.IRCClient):
           
    @property
    def nickname(self):
        return self.factory.nickname

    def signedOn(self):
        print "CONNECTED %s" % (self.nickname)
        self.client = ResistanceClient(self, self.factory.constructor)
        self.join('#resistance')
        self.msg('aigamedev', 'BOT')

    def joined(self, channel):
        pass

    def privmsg(self, user, channel, msg):
        u = user.split('!')[0]
        self.client.message(u, channel, msg)

    def userLeft(self, user, channel):
        self.client.disconnect(user, channel)
    
    def userQuit(self, user, reason):
        self.client.disconnect(user)

    def irc_INVITE(self, user, args):
        channel = args[1]
        if '#game-' in channel:
            self.join(channel) 


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
    import importlib
    import sys
    
    if len(sys.argv) == 1:
        print 'USAGE: client.py file.BotName [...]'
        sys.exit(-1)

    server = 'localhost'
    if 'irc.' in sys.argv[1]:
        server = sys.argv.pop(1)

    for cls in getCompetitors(sys.argv[1:]):
        reactor.connectTCP(server, 6667, ResistanceFactory(cls))

    reactor.run()
