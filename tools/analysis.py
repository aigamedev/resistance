#!/usr/bin/python2.7 -u
import itertools
import multiprocessing

from competition import CompetitionRunner

from bots.cheaters import RandomCheater
from sceptic import ScepticBot


def main(arg):
    print '.',
    res, spy = arg
    RandomCheater.cheat_SetRate(float(res) / 10.0, float(spy) / 10.0)

    # Score of this bot is calculated relative to the scores of all these other bots.
    competitors = [ScepticBot, RandomCheater, RandomCheater, RandomCheater, RandomCheater]
    runner = CompetitionRunner(competitors, 250, quiet = True)
    runner.main()

    # TODO: Split the evaluation depending on whether the bot is Spy or Resistance.
    return (res, spy), runner.score('ScepticBot')[1] - runner.score('RandomCheater')[1]


if __name__ == '__main__':
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.pyplot as plt
    from matplotlib import cm
    import numpy as np

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    print "Measuring performance of Resistance AI (SkepticBot) against bots of exact skill."
    print " - 10 total skill levels for spy and resistance."
    print " - 121 jobs run in total, for 250 games each."
    print " - Using %i threads to run the evaluations...\n" % multiprocessing.cpu_count()

    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    results = {}
    for i, t in pool.map(main, itertools.product(range(11), range(11))):
        results[i] = float(t)

    X, Y = np.meshgrid(range(11), range(11))
    zs = np.array([results[(x,y)] for x,y in zip(np.ravel(X), np.ravel(Y))])
    Z = zs.reshape(X.shape)

    ax.plot_surface(X, Y, Z, rstride=1, cstride=1, cmap=cm.jet, linewidth=1, antialiased=True)

    ax.set_xlabel('Resistance Skill')
    ax.set_xticklabels(['r=%1.1f' % (float(i*2)/10.0) for i in range(6)])
    ax.set_ylabel('Spy Skill')
    ax.set_yticklabels(['s=%1.1f' % (float(i*2)/10.0) for i in range(6)])
    ax.set_zlabel('Improvement')

    print "\n\nShowing performance graph of the evaluated bot relative to its opponents."
    plt.show()

