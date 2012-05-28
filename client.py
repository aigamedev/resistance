from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

from player import Player
from game import State


class ResistanceClient(object):

    def __init__(self, protocol, constructor):
        self.protocol = protocol
        self.constructor = constructor
        self.bots = {}

    def uuid(self, bot, game):
        return "%s %s" % (Player.__repr__(bot), game)

    def getBot(self, game, index):
        return self.bots[game+'.'+index]

    def reply(self, message):
        self.protocol.msg(self.recipient, message)

    def process_JOIN(self, msg):
        game = msg.rstrip('.').split(' ')[1]
        self.protocol.join(game)
        self.recipient = game

    def process_REVEAL(self, mission, identifier, role, players, spies = None):
        game = mission.split(' ')[1]

        # ID 2-Random;
        index, name = identifier.split(' ')[1].split('-')
        bot = self.constructor(State(), int(index), False)
        self.bots["%s.%s-%s" % (game, index, name)] = bot

        # ROLE Spy.
        role = role.split(' ')[1]
        bot.spy = bool(role == 'Spy')

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
        # MISSION #game-0002 1.2;
        index, game, details = mission.split(' ')[1:]
        state = self.getBot(game, index).game
        state.turn, state.tries = [int(i) for i in details.split('.')]

        # LEADER 1-Random.
        state.leader = self.makePlayer(leader.split(' ')[1])

        bot = self.getBot(game, index)
        bot.onMissionAttempt(state.turn, state.tries, state.leader)

    def process_SELECT(self, select):
        index, game, count = select.split(' ')[1:]
        bot = self.getBot(game, index)
        players = bot.game.players
        selection = sorted(bot.select(players, int(count)), key = lambda p: p.index)
        self.reply('SELECTED %s %s.' % (self.uuid(bot, game), ', '.join([str(Player(s.name, s.index)) for s in selection])))

    def process_VOTE(self, vote, team):
        # VOTE #game-0002;
        index, game = vote.split(' ')[1:]
        bot = self.getBot(game, index)

        # TEAM 1-Random, 2-Hippie, 3-Paranoid.
        result = bot.vote(self.makeTeam(team))
        reply = {True: "Yes", False: "No"}
        self.reply('VOTED %s %s.' % (self.uuid(bot, game), reply[result]))

    def process_VOTED(self, voted, team, votes):
        index, game = voted.split(' ')[1:]
        bot = self.getBot(game, index)

        t = self.makeTeam(team)
        v = [bool(b.strip(',.') == 'Yes') for b in votes.split(' ')]
        bot.onVoteComplete(t, v)

    def process_SABOTAGE(self, mission, team):
        # SABOTAGE #game-0002;
        index, game = mission.split(' ')[1:]
        bot = self.getBot(game, index)

        # TEAM 1-Random, 2-Hippie, 3-Paranoid.
        result = bot.sabotage(self.makeTeam(team))
        reply = {True: "Yes", False: "No"}
        self.reply('SABOTAGED %s %s.' % (self.uuid(bot, game), reply[result]))

    def process_RESULT(self, result, team, sabotages):
        index, game = result.split(' ')[1:]
        bot = self.getBot(game, index)

        t = self.makeTeam(team)
        sabotaged = int(sabotages.split(' ')[1])
        
        bot.onMissionComplete(t, sabotaged)

    def process_COMPLETE(self, complete, win, spies):
        index, game = complete.split(' ')[1:]
        bot = self.getBot(game, index)

        w = bool(win.split(' ')[1] == 'Yes')
        s = self.makeTeam(spies)

        bot.onGameComplete(w, s)

    def makeTeam(self, team):
        return [self.makePlayer(t.strip('., ')) for t in team.split(' ')[1:]]

    def makePlayer(self, identifier):
        index, name = identifier.split('-')
        return Player(name, int(index))

    def message(self, sender, msg):
        cmd = msg.split(' ')[0]
        if not hasattr(self, 'process_'+cmd):
            return

        process = getattr(self, 'process_'+cmd)
        args = [i.strip(' ') for i in msg.rstrip('.').split(';')]
        process(*args)


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
