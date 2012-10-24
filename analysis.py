import itertools
from multiprocessing import Pool

from competition import CompetitionRunner

from cheaters import RandomCheater
from sceptic import ScepticBot

def main(arg):
    res, spy = arg
    RandomCheater.cheat_SetRate(float(res) / 10.0, float(spy) / 10.0)
    competitors = [ScepticBot, RandomCheater, RandomCheater, RandomCheater, RandomCheater]
    runner = CompetitionRunner(competitors, 25, quiet = True)
    runner.main()
    return (res, spy), runner.score('ScepticBot')[1] # - runner.score('RandomCheater')[1]

if __name__ == '__main__':
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.pyplot as plt
    from matplotlib import cm
    import numpy as np

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    pool = Pool(processes=4)
    results = {}
    for i, t in pool.map(main, itertools.product(range(11), range(11))):
        results[i] = float(t)

    X, Y = np.meshgrid(range(11), range(11))
    zs = np.array([results[(x,y)] for x,y in zip(np.ravel(X), np.ravel(Y))])
    Z = zs.reshape(X.shape)

    ax.plot_surface(X, Y, Z, rstride=1, cstride=1, cmap=cm.jet, linewidth=1, antialiased=True)    

    ax.set_xlabel('Resistance Skill')
    ax.set_xticklabels(['r=%1.1f' % (float(i)/10.0) for i in range(10)])
    ax.set_ylabel('Spy Skill')
    ax.set_yticklabels(['s=%1.1f' % (float(i)/10.0) for i in range(10)])
    ax.set_zlabel('Improvement')

    plt.show()

    # for r in range(11):
    #     data = []
    #    for s in range(11):
    #        data.append(results[(r,s)])
    #
    #    indices = np.arange(11)
    #
    #    col = str(float(10-r)/10.0)
    #    ax.bar(indices, data, zs=r, zdir='y', color = col, alpha=0.8, width=0.4)
