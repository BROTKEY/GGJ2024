import arcade
import argparse

from ggj2024.gamewindow import GameWindow
from ggj2024.config import *


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--no-leapmotion', '-L', action='store_true', help='Do not use leap motion')
    args = parser.parse_args()

    if args.no_leapmotion:
        leap_motion = False
    else:
        try:
            import leap
            leap_motion = True
        except ImportError:
            print('LeapMotion does not seem to be installed, starting without it')
            leap_motion = False

    """ Main function """
    window = GameWindow(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, leap_motion=leap_motion, debug=args.debug)
    window.setup()
    # HACK: close hands server in better way
    try:
        arcade.run()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    if window.hands:
        window.hands.stop()