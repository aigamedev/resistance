import intermediates
import experts

from mods import speech


class Clippy(intermediates.Bounder):
    """This is a Microsoft Clippy-style bot for The Resistance, announcing
    various facts as the game progresses.
    """

    def onGameRevealed(self, players, spies):
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


class Vocally(intermediates.Simpleton, speech.SpeechMixin):
    """Example bot that uses the speech module (as a mixin class) to support
    both text-to-speech and speech-to-text.  This requires a `say` command-line
    application and the Python `SpeechRecognition` library respectively.
    """

    def onGameRevealed(self, players, spies):
        self.voice = "Alex"

    def say(self, message):
        """Override for the regular say() function that outputs to IRC
        that also pronounces everything via text-to-speech.
        """
        super(Vocally, self).say(message)
        self.speak(message)

    def onMessage(self, source, message):
        # This is an utterance that was detected by voice.
        if source == None:
            if message == "":
                self.speak("What do you mean?")
                return

            # Check in logs/Vocally.log to see debug output.
            message = message.lower()

            for p in ["hello", "hi there", "howdy", "hey"]:
                if p in message:
                    self.speak("How are you today?")
                    return

            for p in ["goodbye", "see you", "cu"]:
                if p in message:
                    self.speak("Great talking to you!")
                    return

            for p in ["i am", "i'm", "this is", "that's"]:
                if p in message:                    
                    name = message[len(p)+1:]
                    self.speak("Hello %s!" % name)
                    break


class Justiffy(experts.Suspicious):
    """Plays the same as the Suspicious bot, but allows players to query the
    bot's guess of the each player's allegiance."""

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
            spy_score += int(p in self.getSpies(c))
            res_score += int(p in self.getResistance(c))

        # Express beliefs about the current estimates for the player.
        if spy_score == res_score:
            self.say("It's unclear at this stage what %r is playing." % (p))
        if spy_score > res_score:
            confidence = "arguably" if res_score > 0 else "likely"
            self.say("I think %r is %s a spy at this stage." % (p, confidence))
        if res_score > spy_score:
            confidence = "arguably" if spy_score > 0 else "likely"
            self.say("I think %r is %s resistance at this stage." % (p, confidence))
