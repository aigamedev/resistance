import gevent
from gevent.event import Event, AsyncResult
from geventirc import Client
from geventirc import message
from geventirc import handlers

from player import Player, Bot
from game import Game


class ProxyBot(Bot):

    def __init__(self, game, name, index, spy, client):
        Player.__init__(self, name, index)
        self.game = game
        self.spy = spy

        self.client = client

        self._vote = None
        self._select = None
        self._sabotage = None
        self.game = '#game-0001'

    def bakeTeam(self, team):
        return ', '.join([str(p) for p in team])

    def makePlayer(self, identifier):
        index, name = identifier.split('-')
        return Player(name, int(index))

    @property
    def uuid(self):
        return "%s %s" % (Player.__repr__(self), self.game)

    def onGameRevealed(self, players, spies):
        roles = {True: "Spy", False: "Resistance"}
        s = ""
        if self.spy:
            s = "; SPIES " + self.bakeTeam(spies)
        self.client.msg(self.name, 'REVEAL %s; ID %s; ROLE %s; PLAYERS %s%s.' % (self.game, Player.__repr__(self), roles[self.spy], self.bakeTeam(players), s))

    def onMissionAttempt(self, mission, tries, leader):
        self.client.msg(self.name, 'MISSION %s %i.%i; LEADER %s.' % (self.uuid, mission, tries, Player.__repr__(leader)))

    def select(self, players, count):
        self.client.msg(self.name, 'SELECT %s %i.' % (self.uuid, count))
        self._select = AsyncResult()
        return self._select.get()

    def process_SELECTED(self, msg):
        print 'select()'
        team = [self.makePlayer(p.strip(',.')) for p in msg[4:]]
        self._select.set(team)

    def vote(self, team):
        self.client.msg(self.name, 'VOTE %s; TEAM %s.' % (self.uuid, self.bakeTeam(team)))
        self._vote = AsyncResult()
        return self._vote.get()

    def process_VOTED(self, msg):
        print 'vote()'
        self._vote.set(msg[4] == 'Yes.')

    def sabotage(self, team):
        self.client.msg(self.name, 'SABOTAGE %s; TEAM %s.' % (self.uuid, self.bakeTeam(team)))
        self._sabotage = AsyncResult()
        return self._sabotage.get()

    def process_SABOTAGED(self, msg):
        print 'sabotage()'
        self._sabotage.set(msg[4] == 'Yes.')

    def onGameComplete(self, *args):
        print 'DONE.'


class ResistanceServerHandler(object):
    """Host that moderates games of THE RESISTANCE given an IRC server."""

    commands = ['PRIVMSG', '001', 'PING']

    def __init__(self):
        pass

    def start(self, client):
        client.send_message(message.Join('#resistance'))

        self.game = Game([lambda g, i, s: ProxyBot(g, 'RandomBot', i, s, client)] * 5)
        self.game.run()


    def __call__(self, client, msg):
        if msg.command == '001':
            self.start(client)
        elif msg.command == 'PING':
            print 'PONG'
            client.cmd(message.Pong())
        else:
            for bot in self.game.bots:
                if bot != bot.makePlayer(msg.params[2]):
                    continue
                name = 'process_'+msg.params[1]
                if hasattr(bot, name):
                    print ' '.join(msg.params)
                    process = getattr(bot, name)
                    process(msg.params)
            
if __name__ == '__main__':
    irc = Client('irc.aigamedev.com', 'aigamedev',  port=6667)
    irc.add_handler(ResistanceServerHandler())
    irc.start()
    irc.join()

