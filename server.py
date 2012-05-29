# COMPETITION
# - Run multiple games in parallel in multiple greenlets for speed.
# - Check current games for players disconnecting and invalidate them.

# HUMAN PLAY
# - Simplify most responses to avoid the need for commands altogether.
# - Parse human input better for SELECT list and the yes/no responses.
# - Require a sabotage response from humans, always to make it fair.
# - Provide a HELP command that provides some contextual explanation.


import sys
import random

import gevent
from gevent.event import Event, AsyncResult
from geventirc import Client
from geventirc import message

from competition import CompetitionRunner
from player import Player, Bot
from game import Game


def YesOrNo(b):
    result = {True: 'Yes', False: 'No'}
    return result[b]


def makePlayer(identifier):
    index, name = identifier.split('-')
    return Player(name, int(index))


class ProxyBot(Bot):

    def __init__(self, name, client, game):
        self.name = name
        self.client = client

        self._vote = None
        self._select = None
        self._sabotage = None
        self._join = None
        self.game = game 

    def __call__(self, game, index, spy):
        """This function pretends to be a Builder, but in fact just
        configures this object in place as it's easier."""
        Player.__init__(self, self.name, index)
        self.state = game
        self.spy = spy

        self.channel = '%s-player-%i' % (self.game, index)
        self.client.send_message(message.Join(self.channel))
        self.client.send_message(message.Join(self.game))

        self._join = Event() 
        self.client.msg(self.name, "JOIN %s." % (self.channel))
        return self

    def bakeTeam(self, team):
        return ', '.join([str(p) for p in team])

    def send(self, msg):
        self.client.msg(self.channel, msg)

    def onGameRevealed(self, players, spies):
        roles = {True: "Spy", False: "Resistance"}
        s = ""
        if self.spy:
            s = "; SPIES " + self.bakeTeam(spies)

        self._join.wait()
        self.send('REVEAL %s; ROLE %s; PLAYERS %s%s.' % (self.game, roles[self.spy], self.bakeTeam(players), s))

    def onMissionAttempt(self, mission, tries, leader):
        self.send('MISSION %i.%i; LEADER %s.' % (mission, tries, Player.__repr__(leader)))

    def select(self, players, count):
        self.send('SELECT %i!' % (count))
        self._select = AsyncResult()
        return self._select.get()

    def process_SELECTED(self, msg):
        team = [makePlayer(p.strip(' ,.')) for p in msg[2:]]
        self._select.set(team)

    def onTeamSelected(self, leader, team):
        self.send("VOTE %s?" % (self.bakeTeam(team)))
        self._vote = AsyncResult()

    def vote(self, team):
        return self._vote.get()

    def process_VOTED(self, msg):
        self._vote.set(msg[2] == 'Yes.')

    def onVoteComplete(self, votes):
        self.send("VOTES %s." % (', '.join([YesOrNo(v) for v in votes])))

    def sabotage(self):
        self.send("SABOTAGE?")
        self._sabotage = AsyncResult()
        return self._sabotage.get()

    def process_SABOTAGED(self, sabotaged):
        self._sabotage.set(sabotaged[2] == 'Yes.')

    def onMissionComplete(self, sabotaged):
        self.send("SABOTAGES %i." % (sabotaged))

    def onGameComplete(self, win, spies):
        self.send("RESULT %s; SPIES %s." % (YesOrNo(win), self.bakeTeam(spies)))

        self.client.send_message(message.Command(self.game, 'PART'))
        self.client.send_message(message.Command(self.channel, 'PART'))


class ResistanceCompetitionHandler(CompetitionRunner):
    """Host that moderates games of THE RESISTANCE given an IRC server."""

    commands = ['PRIVMSG', 'PING', 'JOIN', 'PART',
                '001', # CONNECT
                '353', # NAMES
    ]

    def pickPlayersForRound(self):
        assert len(self.competitors) > 0
        if len(self.competitors) < 5:
            participants = [random.choice(self.competitors) for x in range(0,5)]
        else:
            participants = random.sample(self.competitors, 5)
        return [ProxyBot(bot, self.client, "#game-0002") for bot in participants]

    def start(self):
        self.main()
        self.show()

        # self.client.send_message(message.Command('#resistance', 'NAMES'))
   
        self.client.stop()

    def run(self, game):
        for s in '\t,.!;?': game = game.replace(s, ' ')
        candidates = [c for c in game.split(' ') if c]

        # Put an '@' in front of humans when specifying the players.
        bots = [c for c in candidates if '@' not in c]

        while len(candidates) < 5:
            missing = min(5 - len(candidates), len(bots))
            candidates.extend(random.sample(bots, missing))
        
        if len(candidates) > 5:
            candidates = random.sample(candidates, 5)

        self.client.msg('#resistance', 'PLAYING %s!' % (' '.join(candidates)))
        players = [ProxyBot(bot.lstrip('@'), self.client, "#game-0001") for bot in candidates]
        g = self.play(Game, players)
        result = {True: "Resistance WON!", False: "Spies WON..."}
        self.client.msg('#resistance', 'PLAYED %s. %s' % (' '.join(candidates), result[g.won]))

    def __call__(self, client, msg):
        if msg.command == '001':
            self.client = client
            client.send_message(message.Join('#resistance'))
        elif msg.command == 'PING':
            client.send_message(message.Command(msg.params, 'PONG'))
        elif msg.command == '353':
            if msg.params[2] != '#resistance':
                return
            self.competitors = [u.strip('+@') for u in msg.params[3:]]
            self.competitors.remove(client.nick)
            # Once we've connected and joined the channel, we'll get a list
            # of people there.  We can start games with those!
            # self.start()
        elif msg.command == 'JOIN':
            user = msg.prefix.split('!')[0].strip('+@')
            if user == client.nick:
                return
            channel = msg.params[0].lstrip(':')
            if channel != '#resistance':
                for b in self.game.bots:
                    if b.channel == channel:
                        b._join.set()
                        return
                assert False, "Not waiting for a player to join this channel."
            else:
                self.competitors.append(user)
        elif msg.command == 'PART':
            user = msg.prefix.split('!')[0].strip('+@')
            if user == client.nick:
                return
            channel = msg.params[0].lstrip(':')
            if channel == '#resistance':
                self.competitors.remove(user)
        elif msg.command == 'PRIVMSG':
            channel = msg.params[0].lstrip(':')
            if channel == '#resistance':
                if msg.params[1] == 'PLAY':
                    self.run(' '.join(msg.params[2:]))
                return
            for bot in self.game.bots:
                if bot.channel != channel:
                    continue
                name = 'process_'+msg.params[1]
                if hasattr(bot, name):
                    process = getattr(bot, name)
                    process(msg.params)
 

if __name__ == '__main__':
    
    if len(sys.argv) == 1:
        print 'USAGE: server.py 25'
        sys.exit(-1)

    irc = Client('localhost', 'aigamedev',  port=6667)
    h = ResistanceCompetitionHandler([], int(sys.argv[1]))
    irc.add_handler(h)
    irc.start()
    irc.join()

