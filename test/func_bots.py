import unittest
import random
from inspect import isclass

from game import Game
from player import Bot
from bots import beginners, intermediates, validators


def run_game(cls):
    players = [cls] * 3 + [beginners.RandomBot, validators.StateChecker]
    random.shuffle(players)

    roles = [True, True, False, False, False]
    random.shuffle(roles)

    game = Game(players, roles)
    game.run()


def test_beginners():
    for name, cls in beginners.__dict__.items():
        if isclass(cls) and issubclass(cls, Bot) and cls is not Bot:
            yield run_game, cls


def test_intermediates():
    for name, cls in intermediates.__dict__.items():
        if isclass(cls) and issubclass(cls, Bot) and cls is not Bot:
            yield run_game, cls


if __name__ == "__main__":
    unittest.main()
