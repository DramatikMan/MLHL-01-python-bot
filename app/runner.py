import logging
import sys

from bot import Bot


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='[%(levelname)s]:[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def main() -> None:
    bot = Bot()
    bot.run()


if __name__ == '__main__':
    main()
