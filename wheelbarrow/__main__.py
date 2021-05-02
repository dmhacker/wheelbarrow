import game
import sys


import argparse

parser = argparse.ArgumentParser(description='Run a bot that plays JKLM Bomb Party continuously.')
parser.add_argument('room', type=str, help='4-letter JKLM room code')
parser.add_argument('--human', dest='human', action='store_true',
                    help='pretend to be a human (delayed typing)')
parser.add_argument('--no-human', dest='human', action='store_false',
                    help='do not pretend to be a human (instant typing)')
parser.set_defaults(human=False)

args = parser.parse_args()
game.Game(args.room, args.human).start()
