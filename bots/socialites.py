import intermediates
import experts


class Clippy(intermediates.Bounder):

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
            return p.name in message or str(p.index) in message
        return [p for p in self.game.players if matches(p)]

    def onMessage(self, source, message):
        if 'about' not in message:
            return

        players = self._extractPlayers(message)
        configs = self.likeliest()
        if len(players) == 1:
            p = players[0]
            for c in configs:
                role = "a spy" if p in self.getSpies(c) else "resistance"
                self.say("It's possible %r is %s." % (p, role))
