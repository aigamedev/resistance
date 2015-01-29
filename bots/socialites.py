import intermediates
import experts


class Clippy(intermediates.Bounder):
    """This is a Microsoft Clippy-style bot for The Resistance, announcing
    various facts as the game progresses.
    """

    def onGameRevealed(self, *args):
        self.say("It looks like we're trying to play a game...")

    def onMissionAttempt(self, mission, tries, leader):
        person = ("you're" if self != leader else "I'm")
        self.say("It looks like %s trying to lead a mission..." % person)

    def onTeamSelected(self, leader, team):
        if self in team:
            self.say("It looks like I'm picked for a mission!")
        else:
            self.say("It looks like we're going to have to vote...")

    def onVoteComplete(self, votes):
        if all(votes):
            self.say("It looks like everyone is in agreement!")
        elif not any(votes):
            self.say("It looks like that was a bad idea.")
        else:
            self.say("It looks like we're trying to proceed to mission...")

    def onMissionComplete(self, sabotaged):
        if sabotaged > 0:
            self.say("It looks like someone's trying to cover up...")
        else:
            self.say("It looks like someone's trying to slow play...")

    def onMissionFailed(self, leader, team):
        pronoun = ("my" if self == leader else "that")
        self.say("It looks like nobody liked %s idea..." % pronoun)


class Justiffy(experts.Suspicious):

    def _extractPlayers(self, message):
        def matches(p):
            return p.name in message or ("#%i" % p.index) in message
        return set([p for p in self.game.players if matches(p)])

    def onMessage(self, source, message):
        # Only respond to queries directly addressed to this bot.
        if not message.startswith(self.name) or 'about' not in message:
            return

        players = self._extractPlayers(message) - set([self])
        configs = self.likeliest()
        if len(players) != 1:
            return

        # Determine how player fits into most likely configurations.
        p = players.pop()
        spy_score, res_score = 0, 0
        for c in configs:
            spy_score = int(p in self.getSpies(c))
            res_score = int(p in self.getResistance(c))

        # Express beliefs about the current estimates for the player.
        if spy_score == res_score:
            self.say("It's unclear at this stage what %r is playing." % (p))
        if spy_score > res_score:
            confidence = "arguably" if res_score > 0 else "likely"
            self.say("I think %r is %s a spy at this stage." % (p, confidence))
        if res_score > spy_score:
            confidence = "arguably" if spy_score > 0 else "likely"
            self.say("I think %r is %s resistance at this stage." % (p, confidence))
