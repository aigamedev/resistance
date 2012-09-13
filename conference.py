import sys
import itertools
from competition import CompetitionRunner, getCompetitors


class ConferenceRunner(CompetitionRunner):

    def listRoundsOfCompetitors(self):
        # Second round.  Always the same bots in the games.
        if len(self.competitors) == 5:
            for i in range(self.rounds):
                yield self.competitors
            return

        # First round.  Evaluate the test bot against known combinations
        # of others bots, so the results are predictable.
        for i in range(self.rounds):
            for competitors in itertools.combinations(self.competitors[1:], 4):
                yield [self.competitors[0]] + list(competitors)
        return


if __name__ == '__main__':
    if len(sys.argv) <= 2:
        print('USAGE: competition.py 10000 file.BotName [...]')
        sys.exit(-1)

    competitors = getCompetitors(sys.argv[2:])
    opponents = getCompetitors(['bots.RuleFollower', 'bots.Paranoid', 'bots.Jammer', 'bots.Hippie', 'bots.Deceiver', 'aigd.Statistician', 'aigd.LogicalBot'])

    scores = {}
    for i in range(10):
      for c in sorted(competitors, key = lambda x: x.__name__):
        print >>sys.stderr, '.',
        runner = ConferenceRunner([c] + opponents, rounds = 10, quiet = True)
        runner.main()
        # score = runner.score(c.__name__)
        # scores[c] = score[2].total
        scores.setdefault(c, 0)
        scores[c] += runner.rank(c.__name__)
      print >>sys.stderr, 'o'

    print "\n\nCOMPETITION ROUND #1"
    results = sorted(scores.items(), key = lambda x: x[1])
    for c in results:
        print ' ', '{0:<16s}'.format(c[0].__name__), c[1]+1

    print "\n"
    runner = CompetitionRunner([b for b, r in results[:5]], rounds = int(sys.argv[1]), quiet = False)
    runner.main()
    print "\n\nCOMPETITION ROUND #2",
    runner.show(summary=True)

