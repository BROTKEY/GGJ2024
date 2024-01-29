import arcade
import argparse

from ggj2024.gamewindow import GameWindow
from ggj2024.config import SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    """ Main function """
    window = GameWindow(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, leap_motion=not args.debug)
    window.setup()
    # HACK: close hands server in better way
    try:
        arcade.run()
        window.hands.stop()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        window.hands.stop()