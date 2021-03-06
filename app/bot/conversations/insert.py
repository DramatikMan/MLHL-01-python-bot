import logging
import sqlite3

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ForceReply,
    ReplyKeyboardRemove
)
from telegram.ext import CommandHandler, MessageHandler, Filters

from app.db import DB_URI
from . import BaseHandler
from ..types import CCT


class InsertHandler(BaseHandler):
    ENTERING_PRICE, ENTERING_OTHERS, PROMPTING_RETRY = range(3)

    def __init__(self) -> None:
        super().__init__(
            entry_points=[CommandHandler(
                'insert',
                self.handle_insert_command
            )],
            states={
                self.ENTERING_PRICE: [MessageHandler(
                    Filters.text & ~Filters.command,
                    self.handle_entering_price
                )],
                self.ENTERING_OTHERS: [MessageHandler(
                    Filters.text & ~Filters.command,
                    self.handle_entering_others
                )],
                self.PROMPTING_RETRY: [MessageHandler(
                    Filters.regex('^(YES|NO)$'),
                    self.handle_prompting_retry
                )]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )

    def initial_reply(self, update: Update) -> None:
        update.message.reply_text(
            'We are in insert mode. '
            'Enter the price value for the new record:',
            reply_markup=ForceReply()
        )

    def handle_insert_command(self, update: Update, context: CCT) -> int:
        context.user_data['insert'] = {}
        self.initial_reply(update)

        return self.ENTERING_PRICE

    def handle_entering_price(self, update: Update, context: CCT) -> int:
        context.user_data['insert']['price_doc'] = update.message.text

        variable_list: str = self.get_descriptions_string(
            [*self.columns.keys()]
        )

        update.message.reply_text(
            'Now enter the rest of the values, separated by comma. '
            'The order goes like this:\n\n'
            f'{variable_list}',
            reply_markup=ForceReply()
        )

        return self.ENTERING_OTHERS

    def handle_entering_others(self, update: Update, context: CCT) -> int:
        values: list[str] = update.message.text.split(',')

        try:
            if len(values) != len(self.columns.keys()):
                raise ValueError('Wrong number of values.')

            context.user_data['insert'] |= {
                key: value for key, value
                in zip(self.columns.keys(), values)
            }

            SQL = f'''
                INSERT INTO data ({
                    ', '.join(context.user_data['insert'].keys())
                })
                VALUES ('{
                    "', '".join(context.user_data['insert'].values())
                }')
            '''
            logging.info(SQL.lstrip())

            with sqlite3.connect(DB_URI) as conn:
                conn.cursor().execute(SQL)
        except Exception:
            text = 'Insert failed. Would you like to try again?'
        else:
            text = 'Provided record inserted successfully. ' \
                'Would you like to insert another one?'
        finally:
            update.message.reply_text(
                text,
                reply_markup=ReplyKeyboardMarkup(
                    [['YES', 'NO']],
                    one_time_keyboard=True
                )
            )

            return self.PROMPTING_RETRY

    def handle_prompting_retry(self, update: Update, context: CCT) -> int:
        answer: str = update.message.text
        context.user_data['insert'] = {}

        if answer == 'YES':
            self.initial_reply(update)

            return self.ENTERING_PRICE
        elif answer == 'NO':
            update.message.reply_text(
                'Exiting insert mode.',
                reply_markup=ReplyKeyboardRemove()
            )

            return self.END

        return self.END
