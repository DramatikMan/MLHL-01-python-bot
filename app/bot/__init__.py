import os
import sqlite3

from telegram import Update
from telegram.ext import Updater, CommandHandler

from app.db import DB_URI
from .conversations.insert import InsertHandler
from .conversations.query import QueryHandler
from .types import CCT, DP


class Bot:
    commands = dict(
        help='Gives you information about the available commands',
        query='Enter query mode (average price lookup with filtering)',
        insert='Enter insert mode (adding records to the database)',
        reset='Reset the database to its original state',
        cancel='Quit current conversation mode'
    )

    def print_help(self, update: Update, context: CCT) -> None:
        help_text = 'The following commands are available: \n'

        for key in self.commands:
            help_text += '/' + key + ': '
            help_text += self.commands[key] + '\n'

        update.message.reply_text(help_text)

    def reset_database(self, update: Update, context: CCT) -> None:
        with sqlite3.connect(DB_URI) as conn:
            conn.cursor().execute('DROP TABLE data')
            conn.cursor().execute('''
                CREATE TABLE data AS
                SELECT * FROM original
            ''')

        update.message.reply_text(
            'The database was reset to its original state.'
        )

    def __init__(self) -> None:
        self.updater = Updater(token=os.environ['BOT_TOKEN'], use_context=True)
        self.dispatcher: DP = getattr(self.updater, 'dispatcher')

        help_handler = CommandHandler('help', self.print_help)
        reset_DB_handler = CommandHandler('reset', self.reset_database)

        # generic commands
        self.dispatcher.add_handler(help_handler)
        self.dispatcher.add_handler(reset_DB_handler)

        # conversations
        self.dispatcher.add_handler(InsertHandler())
        self.dispatcher.add_handler(QueryHandler())

    def run(self) -> None:
        self.updater.start_polling()
        self.updater.idle()
