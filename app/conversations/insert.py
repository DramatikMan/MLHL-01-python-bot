import logging
import sqlite3

from telegram import Update, ReplyKeyboardMarkup, ForceReply
from telegram.ext import CommandHandler, MessageHandler, Filters

from . import BaseHandler
from .utils import get_columns_meta
from ..db import DB_URI
from ..types import CCT


class InsertHandler(BaseHandler):
    ENTERING_PRICE, ENTERING_OTHERS, PROMPTING_RETRY = range(3)

    def __init__(self) -> None:
        self.columns: dict[str, str] = get_columns_meta()

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

    def handle_insert_command(self, update: Update, context: CCT) -> int:
        context.user_data['insert'] = {}

        update.message.reply_text(
            'We are in insert mode. '
            'Enter the price value for the new record:',
            reply_markup=ForceReply()
        )

        return self.ENTERING_PRICE

    def handle_entering_price(self, update: Update, context: CCT) -> int:
        context.user_data['insert']['price_doc'] = update.message.text

        variable_list: str = '\n'.join([*self.columns.keys()][:-1])

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

        match answer:
            case 'YES':
                context.user_data['insert'] = {}

                update.message.reply_text(
                    'Enter the price value for the new record:',
                    reply_markup=ForceReply()
                )

                return self.ENTERING_PRICE
            case 'NO':
                update.message.reply_text('Exiting insert mode.')

                return self.END

        return self.END
