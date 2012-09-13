import sys
from time import time
import itertools
from competition import CompetitionRunner, getCompetitors


class ConferenceRunner(CompetitionRunner):

    def listRoundsOfCompetitors(self):
        # Evaluate the test bot against known combinations
        # of others bots, so the results are predictable.
        for i in range(self.rounds):
            for competitors in itertools.combinations(self.competitors[1:], 4):
                print >>sys.stderr, '.',
                for games in itertools.permutations([self.competitors[0]] + list(competitors)):
                    yield games
        return


if __name__ == '__main__':
    if len(sys.argv) <= 2:
        print('USAGE: competition.py 10000 file.BotName [...]')
        sys.exit(-1)

    competitors = getCompetitors(sys.argv[2:])
    opponents = getCompetitors(['bots.RuleFollower', 'bots.Deceiver', 'bots.Jammer', \
                                'bots.Hippie', 'bots.Deceiver',                      \
                                # 'aigd.Statistician', 'aigd.LogicalBot',              \
                                #'bots.Neighbor'
                                ])

    scores = {}
    for i in range(1):
      for c in sorted(competitors, key = lambda x: x.__name__):
        t = time()
        print >>sys.stderr, '{0:<12s}'.format(c.__name__),
        runner = ConferenceRunner([c] + opponents, rounds = 1, quiet = True)
        runner.main()
        score = runner.score(c.__name__)
        scores[c] = score[2]
        # scores.setdefault(c, 0)
        # scores[c] += runner.rank(c.__name__)
        print >>sys.stderr, 'o', "t=%3.1fs" % (time() - t)

    print "\n\nCOMPETITION ROUND #1"
    results = sorted(scores.items(), key = lambda x: x[1].estimate(), reverse = True)
    for c in results:
        print ' ', '{0:<16s}'.format(c[0].__name__), c[1].detail()

    print "\n"
    runner = CompetitionRunner([b for b, r in results[:5]], rounds = int(sys.argv[1]), quiet = False)
    runner.main()
    print "\n\nCOMPETITION ROUND #2",
    runner.show(summary=True)

