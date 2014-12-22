from __future__ import print_function

import re
import sys
import time
import random
import logging
import itertools

import gevent
from gevent import Greenlet
from gevent import queue
from gevent import pool 
from gevent.event import Event, AsyncResult, Timeout
from geventirc import Client
from geventirc import message

from competition import CompetitionRunner, CompetitionRound
from player import Player, Bot
from game import Game


RE_MAPPING = re.compile("([\w\-]*?)\s*[:=]\s*([\d\.]*?)\s*[,;$]")
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


class OnlineRound(CompetitionRound):
    
    def send(self, message):
        OnlineRound.client.msg(self.channel, message)

    def onGameRevealed(self, players, spies):
        self.send(str(players))
        super(OnlineRound, self).onGameRevealed(players, spies)

    def onMissionAttempt(self, mission, tries, leader):
        self.send("MISSION %i, TRY %i. LEADER %s!" % (mission, tries, leader))
        super(OnlineRound, self).onMissionAttempt(mission, tries, leader)

    def onTeamSelected(self, leader, team):
        self.send("SELECTION %s." % (team))
        super(OnlineRound, self).onTeamSelected(leader, team)

    def onVoteComplete(self, votes):
        self.send("VOTED %s." % (', '.join([showYesOrNo(v) for v in votes])))
        super(OnlineRound, self).onVoteComplete(votes)

    def onMissionComplete(self, sabotaged):
        self.send("SABOTAGED %i." % (sabotaged))
        super(OnlineRound, self).onMissionComplete(sabotaged)

    def onAnnouncement(self, source, announcement):
        self.send("ANNOUNCEMENT from %s: %r" % (source, announcement))
        super(OnlineRound, self).onAnnouncement(source, announcement)

    def onGameComplete(self, win, spies):
        if win:
            self.send("RESISTANCE WIN.")
        else:
            self.send("SPIES WIN...")
        super(OnlineRound, self).onGameComplete(win, spies)


class ProxyBot(Bot):

    def __init__(self, name, client, game, bot):
        self.name = name
        self.client = client
        self.bot = bot
        if bot:
            self.TIMEOUT = 60.0
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

        self._join = Event()

        self.channel = '%s-player-%i' % (self.game, index)
        self.client.send_message(message.Join(self.channel))
        self.client.send_message(message.Join(self.game))

        # Use elegant /INVITE command for humans that have better clients.
        # FIXME: Invitation fails when there's already someone else in the channel.
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

    def makeAnnouncement(self, msg):
        return {self.makePlayer(m.group(1)): float(m.group(2).rstrip('.')) for m in RE_MAPPING.finditer(msg)}

    def send(self, msg):
        self.client.msg(self.channel, msg)

    def onGameRevealed(self, players, spies):
        roles = {True: "Spy", False: "Resistance"}
        s = ""
        if self.spy:
            s = "; SPIES " + self.bakeTeam(spies)

        w = self._join.wait() # timeout=self.Timeout
        assert w is not None, "Problem with bot %r joining." % self
        self._join = None
        self.send('REVEAL %s; ROLE %s; PLAYERS %s%s.' % (self.game, roles[self.spy], self.bakeTeam(players), s))

    def onMissionAttempt(self, mission, tries, leader):
        self.send('MISSION %i.%i; LEADER %s.' % (mission, tries, Player.__repr__(leader)))

    def select(self, players, count):
        self._select = AsyncResult()
        self.state.count = count
        self.expecting = self.process_SELECTED

        self.send('SELECT %i!' % (count))
        if not self.bot:
            self.send('/me '  + self.expecting.__doc__)
        selection = self._select.get(timeout=self.TIMEOUT)
        self._select = None
        return selection

    def process_SELECTED(self, msg):
        """Type a list of players to select for the team, e.g. `select 1, 2.`"""

        if 'select' in msg[1].lower():
            msg = ' '.join(msg[2:])
        else:
            msg = ' '.join(msg[1:])
        team = self.makeTeam(msg)

        if len(team) != self.state.count:
            self.send('SELECT %i?' % (self.state.count))
        else:
            assert self._select is not None
            self._select.set(team)

    def onTeamSelected(self, leader, team):
        self._vote = AsyncResult()
        self.expecting = self.process_VOTED

        self.state.team = team[:]
        self.send("VOTE %s?" % (self.bakeTeam(team)))
        if not self.bot:
            self.send('/me '  + self.expecting.__doc__)

    def vote(self, team):
        v = self._vote.get(timeout=self.TIMEOUT)
        self._vote = None
        return v   

    def process_VOTED(self, msg):
        """Enter your vote, for example as `YES` or `NO`."""

        result = parseYesOrNo(' '.join(msg[1:]))
        if result is not None:
            assert self._vote is not None
            self._vote.set(result)

    def onVoteComplete(self, votes):
        self.send("VOTES %s." % (', '.join([showYesOrNo(v) for v in votes])))
        
        v = [b for b in votes if b]
        if self in self.state.team and len(v) > 2:
            self._sabotage = AsyncResult()
            self.expecting = self.process_SABOTAGED
            self.send("SABOTAGE?")
            if not self.bot:
                self.send('/me '  + self.expecting.__doc__)
        else:
            self._sabotage = None

    def sabotage(self):
        assert self._sabotage is not None
        s = self._sabotage.get(timeout=self.TIMEOUT)
        self._sabotage = None
        return s 

    def process_SABOTAGED(self, msg):
        """Decide whether to sabotage, for typing in `YES` or `NO`."""

        result = parseYesOrNo(' '.join(msg[1:]))
        if result is not None:
            assert self._sabotage is not None
            if result and not self.spy:
                self.send("Can't sabotage mission: you are resistance!")
                result = False
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

    def announce(self):
        self._announce = AsyncResult()
        self.expecting = self.process_ANNOUNCED

        self.send('ANNOUNCE!')
        if not self.bot:
            self.send('/me '  + self.expecting.__doc__)

        ann = self._announce.get(timeout=self.TIMEOUT)
        self._announce = None
        return ann

    def process_ANNOUNCED(self, msg):
        """Input a list of players and their spy probabilities, e.g. 3: 0.0, 4: 1.0."""

        if 'announce' in msg[1].lower():
            msg = ' '.join(msg[2:])
        else:
            msg = ' '.join(msg[1:])

        ann = self.makeAnnouncement(msg)
        self._announce.set(ann)

    def onAnnouncement(self, source, announcement):
        self.send("ANNOUNCES %s: %r" % (source, announcement))

    def onGameComplete(self, win, spies):
        if not self.spy:
            self.send("RESULT %s; SPIES %s." % ("Win" if win else "Loss", self.bakeTeam(spies)))
        else:
            self.send("RESULT %s." % ("Loss" if win else "Win",))

        self.client.send_message(message.Command(self.game, 'PART'))

        # Bots wait for the host to leave the channel for synchronization
        # purposes, but for humans we can display the results anyway.
        self._part = Event()
        if self.bot:
            self._part.wait(timeout=self.TIMEOUT)

        self.client.send_message(message.Command(self.channel, 'PART'))


class TimeoutError(Exception):
    pass


class ResistanceCompetitionHandler(CompetitionRunner):
    """Host that moderates games of THE RESISTANCE given an IRC server."""

    commands = ['PRIVMSG', 'PING', 'JOIN', 'PART',
                '001', # CONNECT
                '353', # NAMES
    ]

    def __init__(self):
        CompetitionRunner.__init__(self, [], 0)
        self.games = []
        self.identities = []        
        self.expecting = None

    def echo(self, *args):
        self.client.msg('#resistance', ' '.join([str(a) for a in args]))

    def getNameRole(self, bot):
        if ':' in bot:
            name, role = bot.split(':')
            return (name.lstrip('@'), role[0].lower() == 's')
        return (bot.lstrip('@'), None)

    def run(self, game):
        t = time.time()
        GAMES = 1

        for s in '\t,.!;?': game = game.replace(s, ' ')
        candidates = [c for c in game.split(' ') if c]
        if candidates[0].isdigit():
            GAMES = int(candidates[0])
            candidates = candidates[1:]
        
        missing = [c for c in candidates if self.getNameRole(c)[0] not in self.competitors]
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

    def play(self, GameType, players, roles, channel):
        g = GameType(players, roles)
        g.channel = channel
        self.games.append(g)
        g.run()
        self.games.remove(g)

        for b in g.bots:
            s = g.statistics.get(b.name)
            if b.spy:
                s.spyWins.sample(int(not g.won))
            else:
                s.resWins.sample(int(g.won))
        return g

    def _play(self, count, candidates, result):
        try:
            channel = "#game-%05i" % (count+1)
            names, roles = zip(*[self.getNameRole(bot) for bot in candidates])
            players = [ProxyBot(name, self.client, channel, name in self.identities) for name in names]

            # Is the game bot-only and therefore fully automatic?
            auto = all([(name in self.identities) for name in names])
            if not auto:
                self.client.msg('#resistance', 'STARTING in %s' % (channel,))

            if roles.count(None) > 0:
                roles = [True, True, False, False, False]
                random.shuffle(roles)

            try:
                g = self.play(OnlineRound, players, roles = roles, channel = channel)
                result.put(g.won)
            except Timeout as t:
                result.put(None)

            self.channels.put(count)
        except TimeoutError:
            # self.upcoming.put((candidates, result))
            result.put(None)
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _loop(self):
        # Allocate a pool of hundreds of channels for playing games.
        self.channels = queue.Queue()
        for i in range(0, CHANNELS):
            self.channels.put(i)

        self.upcoming = queue.Queue()
        while True:
            candidates, result = self.upcoming.get()
            if not candidates or not result:
                break 

            index = self.channels.get()
            t = gevent.spawn(self._play, index, candidates, result)
            # gevent.spawn(self.monitor, t)

    def monitor(self, thread):
        thread.join(timeout=30.0)
        if not thread.ready():
            thread.kill(exception=TimeoutError)

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
                        if b.channel == msg.params[2]:
                            if b._join:
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
                        if b.channel == channel:
                            if b._join:
                                b._join.set()
                            return
                print("Not waiting for a player to join this channel.", file=sys.stderr)
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
            # Any human may ask this server to run games with available players.
            channel = msg.params[0].lstrip(':')
            if channel == '#resistance':
                if msg.params[1] == 'PLAY':
                    self.run(' '.join(msg.params[2:]))
                return

            # Connecting bots always self-identify as bot for future reference.
            if msg.params[1] == 'BOT':
                self.identities.append(msg.prefix.split('!')[0])

            for g in self.games:    
                # First check if this is a report message about sabotages in
                # games played between humans alone or with bots.
                if g.channel == channel and msg.params[1].upper() == 'SABOTAGES':
                    try:
                        remaining = int(msg.params[2].strip('.,!;')) 
                    except ValueError:
                        return

                    for bot in g.bots:
                        if bot._sabotage is not None:
                            r = bool(remaining > 0)
                            bot.send("SABOTAGED %s" % showYesOrNo(r))
                            if bot.spy:
                                bot._sabotage.set(r)
                                remaining -= 1
                            else:
                                bot._sabotage.set(False)
                            bot._sabotage = None

                if g.channel == channel and msg.params[1].upper() == 'VOTES':
                    votes = [parseYesOrNo(v) for v in msg.params[2:]]
                    for bot in g.bots:
                        if bot._vote is not None and bot.name not in self.identities:
                            v = votes.pop(0)
                            bot.send("VOTED %s." % showYesOrNo(v))
                            bot._vote.set(v)

                if g.channel == channel and msg.params[1].upper() == 'SELECTS':
                    for bot in g.bots:
                        if bot._select is not None:
                            bot.send("SELECTED %s" % ' '.join(msg.params[2:]))
                            bot.process_SELECTED(msg.params)

                # Now check if a bot is expecting a message, and pass it along.
                for bot in g.bots:
                    if bot.channel != channel:
                        continue
                    name = 'process_'+msg.params[1].upper()
                    if hasattr(self, name):
                        process = getattr(self, name)
                        process(msg.params)
                    elif hasattr(bot, name):
                        process = getattr(bot, name)
                        process(msg.params)
                    elif bot.expecting:
                        try:
                            bot.expecting(msg.params)
                        except:
                            # Comments can overflow in multiple lines.
                            pass
 
    def process_COMMENT(self, *args):
        pass

    def process_HELP(self, *args):
        if self.expecting:
            self.client.send('/me ' + self.expecting.__doc__)
        else:
            self.client.send("No input required at this stage.")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--server', type=str, required=False, default='irc.aigamedev.com',
                help = "IRC server name to connect to hosting running games.") 
    parser.add_argument('--port', type=int, required=False, default=6667,
                help = "Port of the IRC server to connect to.")
    parser.add_argument('--name', type=str, required=False, default='aigamedev',
                help = "Name of the IRC client that connects to the server.")
    args = parser.parse_args()

    irc = Client(args.server, args.name,  port=args.port, local_hostname='localhost')
    OnlineRound.client = irc
    h = ResistanceCompetitionHandler()
    irc.add_handler(h)
    try:
        irc.start()
        irc.join()
    except KeyboardInterrupt:
        h.upcoming.put(([], None))


# COMPETITION
# - Check current games for players disconnecting and invalidate them.
# - Mark bots that timed out and punish them for it -- or notify channel.
# - For speed, use a constant set of bot channels rather than game channels.
# - For speed, run multiple games with the same bots, different configurations. 
# - (DONE) Check for bots timing out and cancel the game...
# - (DONE) Output the statistics of the competition that was just run.
# - (DONE) Performance checks for running games to try to improve simulations.
# - (DONE) Allow specifying a number of games to run, and their permutations.
# - (DONE) Run multiple games in parallel in multiple greenlets for speed.
# - (DONE) Let the server detect if the bot is already in the private channel.
# - (DONE) Have clients detect if the server disconnects or leaves a channel.

# HUMAN PLAY
# - Have bots respond to questions about suspicion levels of players.
# - Handle renaming of clients so the player list is up-to-date.
# - Keep going if there's already a human observer in the bot channel!
# - Remind humans when they need to type input with a repeat message.
# - If there's a timeout, inform everyone and stop the game cleanly.
# - If a bot throws an exception, inform everyone and bail out.
# - Request for announcements after sabotage results are provided.
# - (DONE) Provide a HELP command that provides some contextual explanation.
# - (DONE) When game is over show the results without requiring player to leave channel.
# - (DONE) Show the game channel in #resistance when the players include a human.
# - (DONE) Show personalized statistics about game that tell you WIN/LOSS.
# - (DONE) Let bots output debug explanations for select & vote via self.log.
# - (DONE) In mixed human/bot games, allow moderator to type result of mission.
# - (DONE) Check for valid players when requesting specific games.
# - (DONE) Simplify most responses to avoid the need for commands altogether.
# - (DONE) Parse human input better for SELECT list and the yes/no responses.
# - (DONE) Index players and channels from [1..5] rather than starting at zero.
# - (DONE) Require a sabotage response from humans, always to make it fair.
