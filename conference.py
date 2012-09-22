import sys
from time import time
import itertools
from competition import CompetitionRunner, getCompetitors


if __name__ == '__main__':
    if len(sys.argv) <= 2:
        print('USAGE: competition.py 10000 file.BotName [...]')
        sys.exit(-1)

    competitors = getCompetitors(sys.argv[2:])
    opponents = getCompetitors([# 'bots.RandomBot', 'bots.RuleFollower', 'bots.Deceiver', 'bots.Jammer', 'bots.Hippie', 'bots.Neighbor',
                                'aigd.Statistician', 'aigd.LogicalBot'])
    
    pool = competitors + opponents
    rnd = 1
    while len(pool) >= 5:
        r = int(sys.argv[1])
        if len(pool) == 5:
            runner = CompetitionRunner(pool, rounds = int(r * 2.5), quiet = False)
        else:
            runner = CompetitionRunner(pool, rounds = r, quiet = True)
        runner.main()
    
        if len(pool) == 5:
            runner.show(summary=True)
            break
        else:
            last, other = runner.last()
            print "ROUND #%i: Eliminated %s." % (rnd, last[0].__name__),
            if last[1].estimate() + last[1].error() < other[1].estimate()     \
            and other[1].estimate() + other[1].error() > last[1].estimate():
                print "(approved)"
            else:
                print "(suspect %s)" % (other[0].__name__)
            print " %s vs %s" % (last[1].detail(), other[1].detail())
            pool.remove(last[0])
        rnd += 1

