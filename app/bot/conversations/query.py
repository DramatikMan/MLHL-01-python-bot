import sqlite3
from collections.abc import Iterable
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ForceReply,
    ReplyKeyboardRemove,
    InputMediaPhoto
)
from telegram.ext import CommandHandler, MessageHandler, Filters

from app.db import DB_URI
from . import BaseHandler
from ..types import CCT, DataRecord


class QueryHandler(BaseHandler):
    CHOOSING, FILTERING, PROMPTING_OUTPUT, PROMPTING_PREDICTION = range(4)

    def __init__(self) -> None:
        super().__init__(
            entry_points=[CommandHandler('query', self.handle_query_command)],
            states={
                self.CHOOSING: [
                    MessageHandler(
                        Filters.regex(f'^({"|".join(self.columns.keys())})$'),
                        self.handle_choosing
                    ),
                    CommandHandler('charts', self.handle_charts_command)
                ],
                self.FILTERING: [MessageHandler(
                    Filters.text & ~Filters.command,
                    self.handle_filtering
                )],
                self.PROMPTING_OUTPUT: [MessageHandler(
                    Filters.regex('^(output|continue)$'),
                    self.handle_output_prompt
                )],
                self.PROMPTING_PREDICTION: [MessageHandler(
                    Filters.regex('^(YES|NO)$'),
                    self.handle_prediction_prompt
                )]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )

    def get_not_yet_filtered_params(self, context: CCT) -> list[str]:
        return [
            key for key in self.columns.keys()
            if key not in context.user_data['filters']
        ]

    def handle_query_command(self, update: Update, context: CCT) -> int:
        if 'filters' not in context.user_data:
            context.user_data['filters'] = {}

        params: list[str] = self.get_not_yet_filtered_params(context)
        descriptions: str = self.get_descriptions_string(params)

        update.message.reply_text(
            'We are in query mode. Choose parameter to filter deals by:\n\n'
            f'{descriptions}',
            reply_markup=ReplyKeyboardMarkup(
                [params[i:i + 3] for i in range(0, len(params), 3)],
                one_time_keyboard=True
            )
        )

        return self.CHOOSING

    def handle_choosing(self, update: Update, context: CCT) -> int:
        param: str = update.message.text
        context.user_data['param'] = param
        update.message.reply_text(
            f'Now enter the target value for parameter: {param}.',
            reply_markup=ForceReply()
        )

        return self.FILTERING

    def handle_filtering(self, update: Update, context: CCT) -> int:
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
                'No records met the current filtering conditions.\n\n'
                'Would you like to get a modeled prediction of the price '
                'for the current filter (excluding NaN variables)?',
                reply_markup=ReplyKeyboardMarkup(
                    [['YES', 'NO']],
                    one_time_keyboard=True
                )
            )

            return self.PROMPTING_PREDICTION
        elif count == 1:
            with sqlite3.connect(DB_URI) as conn:
                result: DataRecord = conn.cursor().execute(f'''
                    SELECT *
                    FROM data
                    {WHERE_SQL}
                ''').fetchone()

            single_record: str = '\n'.join((
                f'{key} = {value}'
                for key, value in zip(self.columns.keys(), result)
            ))

            update.message.reply_text(
                'Found a single matching record.\n\n'
                f'{single_record}\n\n'
                'Exiting query mode.',
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data['filters'] = {}

            return self.END
        elif count <= 10:
            update.message.reply_text(
                f'Average price = {avg_price:.2f}.\n\n'
                f'{count} records met the current filtering conditions.\n\n'
                'Would you like to output these records '
                'or to continue filtering?',
                reply_markup=ReplyKeyboardMarkup(
                    [['output', 'continue']],
                    one_time_keyboard=True
                )
            )

            return self.PROMPTING_OUTPUT

        params: list[str] = self.get_not_yet_filtered_params(context)
        descriptions: str = self.get_descriptions_string(params)

        update.message.reply_text(
            f'Average price = {avg_price:.2f}.\n\n'
            f'{count} records met the current filtering conditions.\n\n'
            'Choose another parameter to narrow down the current selection '
            'or type /cancel to quit query mode.\n\n'
            + (
                'You can also type /charts to get visualization of how the '
                'price depends on each of the not yet filtered parameters '
                '(excluding NaNs).\n\n'
                if count <= 1000 else ''
            )
            + f'{descriptions}',
            reply_markup=ReplyKeyboardMarkup(
                [params[i:i + 3] for i in range(0, len(params), 3)],
                one_time_keyboard=True
            )
        )

        return self.CHOOSING

    def handle_output_prompt(self, update: Update, context: CCT) -> int:
        value: str = update.message.text

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
                'Exiting query mode.',
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data['filters'] = {}

            return self.END
        elif value == 'continue':
            params: list[str] = self.get_not_yet_filtered_params(context)
            descriptions: str = self.get_descriptions_string(params)

            update.message.reply_text(
                'Choose another parameter to narrow down the current '
                'selection or type /cancel to quit query mode.\n\n'
                f'{descriptions}',
                reply_markup=ReplyKeyboardMarkup(
                    [params[i:i + 3] for i in range(0, len(params), 3)],
                    one_time_keyboard=True
                )
            )

            return self.CHOOSING

        return self.END

    def get_chart_images(self, context: CCT) -> list[InputMediaPhoto]:
        params: list[str] = self.get_not_yet_filtered_params(context)
        VARS_SQL = ', '.join(params)
        WHERE_SQL = 'WHERE ' + ' AND '.join(
            f'{key} = {value}'
            for key, value in context.user_data['filters'].items()
        )

        with sqlite3.connect(DB_URI) as conn:
            df: pd.DataFrame = pd.read_sql_query(
                sql=f'SELECT {VARS_SQL}, price_doc FROM data {WHERE_SQL}',
                con=conn
            )

        label_size = 25
        plt.rcParams.update({
            'axes.labelsize': label_size,
            'xtick.labelsize': label_size,
            'ytick.labelsize': label_size,
            'figure.figsize': (15, 15)
        })

        images: list[InputMediaPhoto] = []

        for param in (
            param for param in params
            if param not in ('product_type', 'sub_area')
        ):
            plt.clf()
            plt.xlabel(self.columns[param])
            plt.ylabel('sale price')
            plt.hexbin(
                x=df[param],
                y=df['price_doc'].apply(lambda x: x / (10 ** 6)),
                gridsize=50,
                cmap='coolwarm'
            )

            image_io = BytesIO()
            plt.savefig(image_io)
            images.append(InputMediaPhoto(image_io.getvalue()))

        return images

    def handle_charts_command(self, update: Update, context: CCT) -> int:
        update.message.reply_text(
            'Building charts...',
            reply_markup=ReplyKeyboardRemove()
        )

        images: list[InputMediaPhoto] = self.get_chart_images(context)
        update.message.reply_media_group(media=images)  # type: ignore
        context.user_data['filters'] = {}

        return self.END

    def get_prediction(self, context: CCT) -> tuple[float, float]:
        params = {
            key: value for key, value in context.user_data['filters'].items()
            if key not in ('product_type', 'sub_area')
        }

        with sqlite3.connect(DB_URI) as conn:
            df: pd.DataFrame = pd.read_sql_query(
                sql=f'''
                    SELECT {', '.join(params)}, price_doc
                    FROM data
                ''',
                con=conn
            )

        X = df[[*params]]
        y = df['price_doc'] / (10 ** 6)

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.33,
            random_state=42
        )

        model = LinearRegression()
        model.fit(X=X_train, y=y_train)

        return (
            float(model.score(X=X_test, y=y_test)),
            float(
                model.coef_ @ [*map(float, params.values())] + model.intercept_
            )
        )

    def handle_prediction_prompt(self, update: Update, context: CCT) -> int:
        value: str = update.message.text

        if value == 'NO':
            update.message.reply_text(
                'Exiting query mode.',
                reply_markup=ReplyKeyboardRemove()
            )

            return self.END
        elif value == 'YES':
            R_squared, prediction = self.get_prediction(context)

            update.message.reply_text(
                f'Predicted price = {prediction:.6f} M.'
                '\n'
                f'R-squared for test subset = {R_squared:.2f}.'
                '\n\nExiting query mode.'
            )

        context.user_data['filters'] = {}

        return self.END
