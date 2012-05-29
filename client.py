from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

from player import Player
from game import State


class ResistanceClient(object):

    def __init__(self, protocol, constructor):
        self.protocol = protocol
        self.constructor = constructor
        self.bots = {}
        self.channel = None

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
        self.bots[self.channel] = bot

        # PLAYERS 1-Deceiver, 2-Random, 3-Hippie;
        participants = []
        for p in players.split(' ')[1:]:
            participants.append(self.makePlayer(p.rstrip(',')))
        bot.game.players = participants

        # SPIES 1-Deceiver.
        saboteurs = []
        if spies:
            for s in spies.split(' ')[1:]:
                saboteurs.append(self.makePlayer(s.rstrip(',')))
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
        result = bot.vote(bot.game.team)
        reply = {True: "Yes", False: "No"}
        self.reply('VOTED %s.' % (reply[result]))

    def process_VOTES(self, votes):
        bot = self.getBot()
        v = [bool(b.strip(',.') == 'Yes') for b in votes.split(' ')[1:]]
        bot.onVoteComplete(v)

    def process_SABOTAGE(self, sabotage):
        bot = self.getBot()
        result = bot.sabotage()
        reply = {True: "Yes", False: "No"}
        self.reply('SABOTAGED %s.' % (reply[result]))

    def process_SABOTAGES(self, sabotages):
        bot = self.getBot()
        sabotaged = int(sabotages.split(' ')[1])
        bot.onMissionComplete(sabotaged)

    def process_RESULT(self, result, spies):
        bot = self.getBot()

        w = bool(result.split(' ')[1] == 'Yes')
        s = self.makeTeam(spies)

        bot.onGameComplete(w, s)
        self.protocol.part(self.channel)

    def makeTeam(self, team):
        return [self.makePlayer(t.strip('., ')) for t in team.split(' ')[1:]]

    def makePlayer(self, identifier):
        index, name = identifier.split('-')
        return Player(name, int(index))

    def message(self, channel, msg):
        cmd = msg.split(' ')[0].rstrip('?!.')
        if not hasattr(self, 'process_'+cmd):
            return

        process = getattr(self, 'process_'+cmd)
        args = [i.strip(' ') for i in msg.rstrip('.?!').split(';')]
        self.channel = channel
        process(*args)
        self.channel = None


class ResistanceProtocol(irc.IRCClient):
           
    def __init__(self):
        self.client = None

    @property
    def nickname(self):
        return self.factory.nickname

    def signedOn(self):
        print "CONNECTED %s" % (self.nickname)
        self.client = ResistanceClient(self, self.factory.constructor)
        self.join('#resistance')

    def joined(self, channel):
        pass

    def privmsg(self, user, channel, msg):
        u = user.split('!')[0]
        self.client.message(channel, msg)
    

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

    for path in sys.argv[1:]:
        filename, classname = path.split('.')
        module = importlib.import_module(filename)
        cls = getattr(module, classname)
        reactor.connectTCP("localhost", 6667, ResistanceFactory(cls))

    reactor.run()
