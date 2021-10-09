import logging
import os
import sys
from typing import Any

import pandas as pd
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)

from app.types import CCT as CallbackContext, DP as Dispatcher


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='[%(levelname)s]:[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


df: pd.DataFrame = pd.read_csv(f'{os.environ["PWD"]}/app/data/db.csv')
params: list[str] = [*df.columns]


def query(update: Update, context: CallbackContext) -> int:
    reply_keyboard: list[list[str]] = [params]
    update.message.reply_text(
        'We are in query mode. Enter parameter name to filter deals by:\n',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True
        )
    )

    return 0


def request_value(update: Update, context: CallbackContext) -> int:
    param_name: str = update.message.text
    context.update({'param_name': param_name})
    update.message.reply_text(
        f'Now enter the target value for {param_name}.',
        reply_markup=ReplyKeyboardRemove()
    )

    return 1


def return_average(update: Update, context: CallbackContext) -> int:
    value: Any = update.message.text
    update.message.reply_text(f'{value}')

    return 2


# def add_record(update: Update, context: CallbackContext) -> int:
#     ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    username: str = update.message.from_user.first_name
    logging.info(f'User {username} canceled the conversation.')
    update.message.reply_text(
        "Conversation's over.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

0
def main() -> None:
    updater = Updater(token=os.environ['BOT_TOKEN'], use_context=True)
    dispatcher: Dispatcher = getattr(updater, 'dispatcher')

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('query', query),
            # CommandHandler('add', add_record)
        ],
        states={
            0: [MessageHandler(
                Filters.regex(f'^({"|".join(params)})$'),
                request_value
            )],
            1: [MessageHandler(
                Filters.text & ~Filters.command,
                return_average
            )],
            2: [MessageHandler(
                Filters.regex(f'^({"|".join(params)})$'),
                request_value
            )],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
