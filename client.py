from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

from player import Player
from game import State


class ResistanceClient(object):

    def __init__(self, protocol, constructor):
        self.protocol = protocol
        self.constructor = constructor
        self.games = {}

    def uuid(self, bot, game):
        return "%s %s" % (Player.__repr__(bot), game)

    def getBot(self, game, index):
        for b in self.games[game]['bots']:
            if index == Player.__repr__(b):
                return b
        assert False, "Bot '%s' not found for %s!" % (index, game)

    def reply(self, message):
        self.protocol.msg(self.recipient, message)

    def process_JOIN(self, msg):
        game = msg.rstrip('.').split(' ')[1]
        self.protocol.join(game)
        self.reply('JOINED %s.' % (game))

    def process_REVEAL(self, mission, identifier, role, players, spies = None):
        game = mission.split(' ')[1]
        self.makeGame(game)

        # ID 2-Random;
        index, name = identifier.split(' ')[1].split('-')
        bot = self.constructor(self.games[game]['state'], int(index), False)
        self.games[game]['bots'].append(bot)

        # ROLE Spy.
        role = role.split(' ')[1]
        bot.spy = bool(role == 'Spy')

        # PLAYERS 1-Deceiver, 2-Random, 3-Hippie;
        participants = []
        for p in players.split(' ')[1:]:
            participants.append(self.makePlayer(p.rstrip(',')))
        self.games[game]['state'].players = participants

        # SPIES 1-Deceiver.
        saboteurs = []
        if spies:
            for s in spies.split(' ')[1:]:
                saboteurs.append(self.makePlayer(s.rstrip(',')))
            self.games[game]['state'].spies = saboteurs

        bot.onGameRevealed(participants, saboteurs)

    def process_MISSION(self, mission, leader):
        # MISSION #game-0002 1.2;
        index, game, details = mission.split(' ')[1:]
        state = self.games[game]['state']
        state.turn, state.tries = [int(i) for i in details.split('.')]

        # LEADER 1-Random.
        state.leader = self.makePlayer(leader.split(' ')[1])

        bot = self.getBot(game, index)
        bot.onMissionAttempt(state.turn, state.tries, state.leader)

    def process_SELECT(self, select):
        index, game, count = select.split(' ')[1:]
        bot = self.getBot(game, index)
        players = self.games[game]['state'].players
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

    def makeGame(self, game):
        if game not in self.games:
            self.games[game] = {'state': State(), 'bots': []}

    def message(self, sender, msg):
        cmd = msg.split(' ')[0]
        # print msg
        process = getattr(self, 'process_'+cmd)
        args = [i.strip(' ') for i in msg.rstrip('.').split(';')]
        self.recipient = sender.split('!')[0]
        process(*args)
        self.recipient = None


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

    from bots import RandomBot, Deceiver, Hippie, Paranoid, RuleFollower

    reactor.connectTCP("localhost", 6667, ResistanceFactory(RandomBot))
    reactor.connectTCP("localhost", 6667, ResistanceFactory(Deceiver))
    reactor.connectTCP("localhost", 6667, ResistanceFactory(Hippie))
    reactor.connectTCP("localhost", 6667, ResistanceFactory(Paranoid))
    reactor.connectTCP("localhost", 6667, ResistanceFactory(RuleFollower))
    reactor.run()

