import sqlite3
from collections.abc import Iterable

from telegram import Update, ReplyKeyboardMarkup, ForceReply
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)

from . import cancel
from ..db import DB_URI
from ..types import CCT, DataRecord


CHOOSING, FILTERING, PROMPTING_OUTPUT = range(3)


with sqlite3.connect(DB_URI) as conn:
    columns: dict[str, str] = {
        row[0]: row[1]
        for row in conn.cursor().execute('SELECT * FROM meta')
    }


def handle_query_command(update: Update, context: CCT) -> int:
    if 'filters' not in context.user_data:
        context.user_data['filters'] = {}

    params: list[str] = [
        key for key in columns.keys()
        if key not in context.user_data['filters']
    ]

    descriptions: str = '\n'.join(
        f'{name} << {columns[name]}' for name in params
    )

    update.message.reply_text(
        'We are in query mode. Choose parameter to filter deals by:\n\n'
        f'{descriptions}',
        reply_markup=ReplyKeyboardMarkup(
            [[name] for name in params],
            one_time_keyboard=True
        )
    )

    return CHOOSING


def handle_choosing(update: Update, context: CCT) -> int:
    param: str = update.message.text
    context.user_data['param'] = param
    update.message.reply_text(
        f'Now enter the target value for parameter: {param}.',
        reply_markup=ForceReply()
    )

    return FILTERING


def handle_filtering(update: Update, context: CCT) -> int:
    value: str = update.message.text
    context.user_data['filters'] |= {context.user_data['param']: value}

    WHERE_SQL = 'WHERE ' + ' AND '.join(
        f'{key} = {value}'
        for key, value in context.user_data['filters'].items()
    )

    with sqlite3.connect(DB_URI) as conn:
        count, avg_price = conn.cursor().execute(f'''
            SELECT
                count(price_doc)
            ,   avg(price_doc)
            FROM data
            {WHERE_SQL}
        ''').fetchone()

    if count == 0:
        update.message.reply_text(
            'No records met the current filtering conditions. '
            'Exiting query mode.'
        )
        context.user_data['filters'] = {}

        return ConversationHandler.END
    elif count == 1:
        with sqlite3.connect(DB_URI) as conn:
            result: DataRecord = conn.cursor().execute(f'''
                SELECT *
                FROM data
                {WHERE_SQL}
            ''').fetchone()

        single_record: str = '\n'.join((
            f'{key} = {value}'
            for key, value in zip(columns.keys(), result)
        ))

        update.message.reply_text(
            'Found a single matching record.\n\n'
            f'{single_record}\n\n'
            'Exiting query mode.'
        )
        context.user_data['filters'] = {}

        return ConversationHandler.END
    elif count <= 10:
        update.message.reply_text(
            f'Average price = {avg_price:.2f}\n'
            f'{count} records met the current filtering conditions.\n\n'
            'Would you like to output these records or to continue filtering?',
            reply_markup=ReplyKeyboardMarkup(
                [['output'], ['continue']],
                one_time_keyboard=True
            )
        )

        return PROMPTING_OUTPUT

    params: list[str] = [
        key for key in columns.keys()
        if key not in context.user_data['filters']
    ]

    descriptions: str = '\n'.join(
        f'{name} << {columns[name]}' for name in params
    )

    update.message.reply_text(
        f'Average price = {avg_price:.2f}\n'
        f'{count} records met the current filtering conditions.\n\n'
        'Choose another parameter to narrow down the current selection '
        'or type /cancel to quit query mode.\n\n'
        f'{descriptions}',
        reply_markup=ReplyKeyboardMarkup(
            [[name] for name in params],
            one_time_keyboard=True
        )
    )

    return CHOOSING


def handle_output_prompt(update: Update, context: CCT) -> int:
    value: str = update.message.text

    # match value:
    #     case 'output':
    if value == 'output':
        WHERE_SQL = 'WHERE ' + ' AND '.join(
            f'{key} = {value}' for key, value
            in context.user_data['filters'].items()
        )

        with sqlite3.connect(DB_URI) as conn:
            result: Iterable[DataRecord] = conn.cursor().execute(f'''
                SELECT *
                FROM data
                {WHERE_SQL}
            ''')

        multiple_records: str = '\n'.join((
            f'{i}: {value}'
            for i, value in enumerate(result, 1)
        ))

        update.message.reply_text(
            f'{multiple_records}\n\n'
            'Exiting query mode.'
        )
        context.user_data['filters'] = {}

        return ConversationHandler.END
        # case 'continue':
    elif value == 'continue':
        params: list[str] = [
            key for key in columns.keys()
            if key not in context.user_data['filters']
        ]

        descriptions: str = '\n'.join(
            f'{name} << {columns[name]}' for name in params
        )

        update.message.reply_text(
            'Choose another parameter to narrow down the current '
            'selection or type /cancel to quit query mode.\n\n'
            f'{descriptions}',
            reply_markup=ReplyKeyboardMarkup(
                [[name] for name in params],
                one_time_keyboard=True
            )
        )

        return CHOOSING

    return ConversationHandler.END


query_handler = ConversationHandler(
    entry_points=[CommandHandler('query', handle_query_command)],
    states={
        CHOOSING: [MessageHandler(
            Filters.regex(f'^({"|".join(columns.keys())})$'),
            handle_choosing
        )],
        FILTERING: [MessageHandler(
            Filters.text & ~Filters.command,
            handle_filtering
        )],
        PROMPTING_OUTPUT: [MessageHandler(
            Filters.regex('^(output|continue)$'),
            handle_output_prompt
        )]
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)
