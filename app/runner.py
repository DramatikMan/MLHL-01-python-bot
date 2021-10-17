import logging
import os
import sqlite3
import sys

from telegram import Update
from telegram.ext import Updater, CommandHandler

from app.conversations.insert import InsertHandler
from app.conversations.query import query_handler
from app.db import DB_URI
from app.types import CCT, DP


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='[%(levelname)s]:[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


commands = dict(
    help='Gives you information about the available commands',
    query='Enter query mode (average price lookup with filtering)',
    insert='Enter insert mode (adding records to the database)',
    reset='Reset the database to its original state',
    cancel='Quit current conversation mode'
)


def print_help(update: Update, context: CCT) -> None:
    help_text = 'The following commands are available: \n'

    for key in commands:
        help_text += '/' + key + ': '
        help_text += commands[key] + '\n'

    update.message.reply_text(help_text)


def reset_database(update: Update, context: CCT) -> None:
    with sqlite3.connect(DB_URI) as conn:
        conn.cursor().execute('DROP TABLE data')
        conn.cursor().execute('CREATE TABLE data AS SELECT * FROM original')

    update.message.reply_text('The database was reset to its original state.')


def main() -> None:
    updater = Updater(token=os.environ['BOT_TOKEN'], use_context=True)
    dispatcher: DP = getattr(updater, 'dispatcher')

    help_handler = CommandHandler('help', print_help)
    reset_DB_handler = CommandHandler('reset', reset_database)

    # generic commands
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(reset_DB_handler)

    # conversations
    dispatcher.add_handler(InsertHandler())
    dispatcher.add_handler(query_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
