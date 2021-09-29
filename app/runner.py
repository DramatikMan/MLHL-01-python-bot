import logging
import os
import sys

from requests import Response, get
from telegram import Update
from telegram.ext import Updater, CommandHandler

from app.types import Quote, CCT as CallbackContext, DP as Dispatcher


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='[%(levelname)s]:[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def random(update: Update, context: CallbackContext) -> None:
    try:
        resp: Response = get('https://zenquotes.io/api/random')
        data: list[Quote] = resp.json()

        quote: str = data[0]['q']
        author: str = data[0]['a']

        context.bot.send_message(
            chat_id=getattr(update, 'effective_chat').id,
            text=''.join((quote, '\n', '\n', author))
        )
    except Exception as ex:
        raise ex
    else:
        logging.info(f'Sent quote by {author}: {quote}')


def main() -> None:
    updater = Updater(token=os.environ['BOT_TOKEN'], use_context=True)
    dispatcher: Dispatcher = getattr(updater, 'dispatcher')

    quotes_handler = CommandHandler('random', random)
    dispatcher.add_handler(quotes_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
