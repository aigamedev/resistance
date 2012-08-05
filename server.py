# COMPETITION
# - Check current games for players disconnecting and invalidate them.
# - Mark bots that timed out and punish them for it -- or notify channel.
# - (DONE) Check for bots timing out and cancel the game...
# - (DONE) Output the statistics of the competition that was just run.
# - (DONE) Performance checks for running games to try to improve simulations.
# - (DONE) Allow specifying a number of games to run, and their permutations.
# - (DONE) Run multiple games in parallel in multiple greenlets for speed.
# - (DONE) Let the server detect if the bot is already in the private channel.
# - (DONE) Have clients detect if the server disconnects or leaves a channel.
# - For speed, use a constant set of bot channels rather than game channels.
# - For speed, run multiple games with the same bots, different configurations. 

# HUMAN PLAY
# - Have bots respond to questions about suspicion levels of players.
# - Use custom name channels for IRC clients acting as proxy for real players.
# - Provide a HELP command that provides some contextual explanation.
# - (DONE) Let bots output debug explanations for select & vote via self.log.
# - (DONE) In mixed human/bot games, allow moderator to type result of mission.
# - (DONE) Check for valid players when requesting specific games.
# - (DONE) Simplify most responses to avoid the need for commands altogether.
# - (DONE) Parse human input better for SELECT list and the yes/no responses.
# - (DONE) Index players and channels from [1..5] rather than starting at zero.
# - (DONE) Require a sabotage response from humans, always to make it fair.
# - Handle renaming of clients so the player list is up-to-date.

import sys
import time
import random
import logging
import itertools

from gevent import Greenlet
from gevent import queue
from gevent import pool 
from gevent.event import Event, AsyncResult, Timeout
from geventirc import Client
from geventirc import message

from competition import CompetitionRunner, CompetitionRound
from player import Player, Bot
from game import Game


CHANNELS = 100


def showYesOrNo(b):
    result = {True: 'Yes', False: 'No'}
    return result[b]

def parseYesOrNo(text):
    text = text.lower()
    result = None
    for t in ['yes', 'true']:
        if t in text: result = True
    for t in ['no', 'false']:
        if t in text: result = False
    return result 


class ProxyBot(Bot):

    def __init__(self, name, client, game, bot):
        self.name = name
        self.client = client
        self.bot = bot
        if bot:
            self.TIMEOUT = 1.0
        else:
            self.TIMEOUT = None

        self.expecting = None
        self._vote = None
        self._select = None
        self._sabotage = None
        self._join = None
        self._part = None
        self.game = game 

    def __call__(self, game, index, spy):
        """This function pretends to be a Builder, but in fact just
        configures this object in place as it's easier to setup and maintain."""
        Player.__init__(self, self.name, index)
        self.state = game
        self.spy = spy

        self.channel = '%s-player-%i' % (self.game, index)
        self.client.send_message(message.Join(self.channel))
        self.client.send_message(message.Join(self.game))

        self._join = Event() 
        # Use elegant /INVITE command for humans that have better clients.
        self.client.send_message(message.Command([self.name, self.channel], 'INVITE'))
        return self

    def bakeTeam(self, team):
        return ', '.join([str(p) for p in team])

    def makeTeam(self, msg):
        for s in '\t,.!;?': msg = msg.replace(s, ' ')
        names = [n for n in msg.split(' ') if n]
        players = []
        for n in names:
            players.append(self.makePlayer(n))
        return players

    def makePlayer(self, name):
        for p in self.state.players:
            if str(p.index) in name:
                return p
            if name in p.name:
                return p
        assert False, "Can't find player for input name '%s'." % (name)

    def send(self, msg):
        self.client.msg(self.channel, msg)

    def onGameRevealed(self, players, spies):
        roles = {True: "Spy", False: "Resistance"}
        s = ""
        if self.spy:
            s = "; SPIES " + self.bakeTeam(spies)

        self._join.wait()
        self._join = None
        self.send('REVEAL %s; ROLE %s; PLAYERS %s%s.' % (self.game, roles[self.spy], self.bakeTeam(players), s))

    def onMissionAttempt(self, mission, tries, leader):
        self.send('MISSION %i.%i; LEADER %s.' % (mission, tries, Player.__repr__(leader)))

    def select(self, players, count):
        self.send('SELECT %i!' % (count))
        self._select = AsyncResult()
        self.state.count = count
        self.expecting = self.process_SELECTED
        return self._select.get(timeout=self.TIMEOUT)

    def process_SELECTED(self, msg):
        if 'select' in msg[1].lower():
            msg = ' '.join(msg[2:])
        else:
            msg = ' '.join(msg[1:])
        team = self.makeTeam(msg)
        if len(team) != self.state.count:
            self.send('SELECT %i?' % (self.state.count))
        else:
            self._select.set(team)

    def onTeamSelected(self, leader, team):
        self.state.team = team[:]
        self.send("VOTE %s?" % (self.bakeTeam(team)))
        self._vote = AsyncResult()
        self.expecting = self.process_VOTED

    def vote(self, team):
        return self._vote.get(timeout=self.TIMEOUT)

    def process_VOTED(self, msg):
        result = parseYesOrNo(' '.join(msg[1:]))
        if result is not None:
            self._vote.set(result)

    def onVoteComplete(self, votes):
        self.send("VOTES %s." % (', '.join([showYesOrNo(v) for v in votes])))
        
        v = [b for b in votes if b]
        if self in self.state.team and len(v) > 2:
            self.send("SABOTAGE?")
            self._sabotage = AsyncResult()
            self.expecting = self.process_SABOTAGED
        else:
            self._sabotage = None

    def sabotage(self):
        assert self._sabotage is not None
        return self._sabotage.get(timeout=self.TIMEOUT)

    def process_SABOTAGED(self, msg):
        result = parseYesOrNo(' '.join(msg[1:]))
        if result is not None:
            self._sabotage.set(result)

    def onMissionComplete(self, sabotaged):
        # Force synchronization in case sabotage() is not called due to the bot
        # being resistance.  This helps hide human identity by having the same
        # input delay in Spy or Resistance cases.
        if self._sabotage and not self._sabotage.ready():
            s = self._sabotage.get(timeout=self.TIMEOUT)
            assert not s, "Expecting sabotage() to be False if it was handled automatically."

        self.send("SABOTAGES %i." % (sabotaged))
        self.expecting = None

    def onGameComplete(self, win, spies):
        self.send("RESULT %s; SPIES %s." % (showYesOrNo(win), self.bakeTeam(spies)))

        self.client.send_message(message.Command(self.game, 'PART'))
        self._part = Event() 
        self._part.wait()
        self.client.send_message(message.Command(self.channel, 'PART'))


class ResistanceCompetitionHandler(CompetitionRunner):
    """Host that moderates games of THE RESISTANCE given an IRC server."""

    commands = ['PRIVMSG', 'PING', 'JOIN', 'PART',
                '001', # CONNECT
                '353', # NAMES
    ]

    def __init__(self):
        CompetitionRunner.__init__(self, [], 0)
        self.identities = [] 

    def echo(self, *args):
        self.client.msg('#resistance', ' '.join([str(a) for a in args]))

    def run(self, game):
        t = time.time()
        GAMES = 1

        for s in '\t,.!;?': game = game.replace(s, ' ')
        candidates = [c for c in game.split(' ') if c]
        if candidates[0].isdigit():
            GAMES = int(candidates[0])
            candidates = candidates[1:]
        
        missing = [c for c in candidates if c.strip('@') not in self.competitors]
        if len(missing) != 0:
            self.client.msg('#resistance', 'ERROR. %s was not found in %s.' % (' '.join(missing), self.competitors))
            assert len(missing) == 0, "Not all specified players were found."
    
        self.client.msg('#resistance', 'PLAYING %s!' % (' '.join(candidates)))

        # Put an '@' in front of humans when specifying the players.
        bots = [c for c in candidates if '@' not in c]

        if len(candidates) < 5:
            while len(candidates) < 5:
                missing = min(5 - len(candidates), len(bots))
                candidates.extend(random.sample(bots, missing))
            random.shuffle(candidates)
        
        if len(candidates) > 5:
            candidates = random.sample(candidates, 5)

        results = queue.Queue()
        for i in range(0, GAMES):
            self.upcoming.put((candidates, results))
        
        wins = 0
        timeouts = 0
        for i in range(0, GAMES):
            r = results.get()
            if r is not None:
                wins += int(r)
            else:
                timeouts += 1

        seconds = (time.time() - t)
        if GAMES > 1:
            self.client.msg('#resistance', 'PLAYED %i games in %0.2fs, at %0.2f GPS.%s' % (GAMES, seconds, float(GAMES)/seconds, (' WARNING: %i timed out!' % timeouts) if timeouts else ' '))
        else:
            if timeouts > 0:
                self.client.msg('#resistance', 'TIMEOUT for game, took %0.2fs.' % (seconds))
            else:
                self.client.msg('#resistance', 'PLAYED game in %0.2fs.' % (seconds))
        self.show()

    def _play(self, count, candidates, result):
        channel = "#game-%04i" % (count+1)
        players = [ProxyBot(bot.lstrip('@'), self.client, channel, bot.lstrip('@') in self.identities) for bot in candidates]
        try:
            g = self.play(CompetitionRound, players, channel)
            result.put(g.won)
        except Timeout, t:
            result.put(None)
        self.channels.put(count)
    
    def _loop(self):
        # Allocate a pool of 100 channels for playing games.
        self.channels = queue.Queue()
        for i in range(0, CHANNELS):
            self.channels.put(i)

        self.upcoming = queue.Queue()
        while True:
            candidates, result = self.upcoming.get()
            if not candidates or not result:
                break 
            index = self.channels.get()
            Greenlet.spawn(self._play, index, candidates, result)

    def __call__(self, client, msg):
        if msg.command == '001':
            self.client = client
            client.send_message(message.Join('#resistance'))
            Greenlet.spawn(self._loop)
        elif msg.command == 'PING':
            client.send_message(message.Command(msg.params, 'PONG'))
        elif msg.command == '353':
            if msg.params[2] != '#resistance':
                # When joining specific bot private channels, see if the bot is
                # already there waiting and don't require rejoin.
                waiting = [u.strip('+@') for u in msg.params[3:]]
                for g in self.games:
                    for b in [b for b in g.bots if b.name in waiting]:
                        if b.channel == msg.params[2] and b._join and not b._join.ready():
                            b._join.set()
                return

            self.competitors = [u.strip('+@') for u in msg.params[3:]]
            self.competitors.remove(client.nick)

        elif msg.command == 'JOIN':
            user = msg.prefix.split('!')[0].strip('+@')
            if user == client.nick:
                return
            channel = msg.params[0].lstrip(':')
            if channel != '#resistance':
                for g in self.games:
                    for b in g.bots:
                        if b.channel == channel and b._join:
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
                return
            else:
                for g in self.games:
                    for b in g.bots:
                        if b.channel == channel and b._part:
                            # Only leave the channel once the other has left, to avoid
                            # synchronization problems when batch processing games.
                            b._part.set()
                            return
        elif msg.command == 'PRIVMSG':
            channel = msg.params[0].lstrip(':')
            if channel == '#resistance':
                if msg.params[1] == 'PLAY':
                    self.run(' '.join(msg.params[2:]))
                return
            if msg.params[1] == 'BOT':
                self.identities.append(msg.prefix.split('!')[0])
            for g in self.games:    
                # First check if this is a report message about sabotages in
                # games played between humans alone or with bots.
                if g.channel == channel and msg.params[1].upper() == 'SABOTAGES':
                    remaining = int(msg.params[2].strip('.,!;')) 
                    for bot in g.bots:
                        if bot._sabotage is not None:
                            bot.send("SABOTAGES %i" % (remaining))
                            if bot.spy:
                                bot._sabotage.set(bool(remaining > 0))
                                remaining -= 1
                            else:
                                bot._sabotage.set(False)

                # Now check if a bot is expecting a message, and pass it along.
                for bot in g.bots:
                    if bot.channel != channel:
                        continue
                    name = 'process_'+msg.params[1].upper()
                    if name == 'process_COMMENT':
                        pass
                    elif hasattr(bot, name):
                        process = getattr(bot, name)
                        process(msg.params)
                    elif bot.expecting:
                        bot.expecting(msg.params)
 

if __name__ == '__main__':
    
    server = 'localhost'
    if len(sys.argv) > 1:
        server = sys.argv[1]

    irc = Client(server, 'aigamedev',  port=6667, local_hostname='localhost')
    h = ResistanceCompetitionHandler()
    irc.add_handler(h)
    try:
        irc.start()
        irc.join()
    except KeyboardInterrupt:
        h.upcoming.put(([], None))

