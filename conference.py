import sys
from competition import CompetitionRunner, getCompetitors


if __name__ == '__main__':
    if len(sys.argv) <= 2:
        print('USAGE: competition.py 10000 file.BotName [...]')
        sys.exit(-1)

    competitors = getCompetitors(sys.argv[2:])
    opponents = getCompetitors(['bots', 'intermediate', 'aigd'])

    scores = {}
    for c in sorted(competitors, key = lambda x: x.__name__):
        print >>sys.stderr, '.',
        runner = CompetitionRunner([c] + opponents, rounds = int(sys.argv[1]), quiet = True)
        runner.main()
        score = runner.score(c.__name__)
        scores[c] = score[2]

    print "\n\nCOMPETITION ROUND #1"
    results = sorted(scores.items(), key = lambda x: -x[1].total)
    for c in results:
        print ' ', '{0:<16s}'.format(c[0].__name__), c[1]

    print "\n"
    runner = CompetitionRunner([b for b, r in results[:5]], rounds = int(sys.argv[1]), quiet = False)
    runner.main()
    print "\n\nCOMPETITION ROUND #2",
    runner.show(summary=True)

