import logging
import io
import sqlite3

import pandas as pd
from sklearn.linear_model import LinearRegression
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ForceReply,
    ReplyKeyboardRemove,
    Document
)
from telegram.ext import CommandHandler, MessageHandler, Filters

from app.db import DB_URI
from . import BaseHandler
from ..types import CCT


class PredictHandler(BaseHandler):
    __slots__ = 'params', 'model'
    FILE_UPLOAD, PROMPTING_ANOTHER = range(2)

    def set_up_prediction_model(self) -> None:
        self.params: list[str] = [
            key for key in self.columns.keys()
            if key not in ('product_type', 'sub_area')
        ]

        with sqlite3.connect(DB_URI) as conn:
            df: pd.DataFrame = pd.read_sql_query(
                sql=f'''
                    SELECT {', '.join(self.params)}, price_doc
                    FROM data
                ''',
                con=conn
            )

        X = df[[*self.params]]
        y = df['price_doc'] / (10 ** 6)

        self.model = LinearRegression()
        self.model.fit(X=X, y=y)

    def __init__(self) -> None:
        self.set_up_prediction_model()

        super().__init__(
            entry_points=[CommandHandler(
                'predict',
                self.handle_predict_command
            )],
            states={
                self.FILE_UPLOAD: [MessageHandler(
                    Filters.document,
                    self.handle_file_upload
                )],
                self.PROMPTING_ANOTHER: [MessageHandler(
                    Filters.regex('^(YES|NO)$'),
                    self.handle_prompting_another
                )]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )

    def initial_reply(self, update: Update) -> None:
        update.message.reply_text(
            'We are in prediction mode.\n\n'
            'Upload your CSV or Excel file with the data '
            'you would like to predict prices for.\n\n'
            'Columns list:\n\n'
            f'{self.get_descriptions_string([*self.columns.keys()])}',
            reply_markup=ForceReply()
        )

    def handle_predict_command(self, update: Update, context: CCT) -> int:
        self.initial_reply(update)

        return self.FILE_UPLOAD

    def handle_file_upload(self, update: Update, context: CCT) -> int:
        document: Document = update.message.document
        logging.info(
            'File received from user '
            f'{update.message.from_user.first_name} '
            f'{update.message.from_user.last_name}: '
            f'{document.file_name}'
        )
        ext: str = document.file_name.split('.')[-1].lower()

        if ext not in ('csv', 'xls', 'xlsx'):
            update.message.reply_text(
                'Could not recognize file extension. Make sure it is either '
                '"csv", "xls" or "xlsx".\n\n',
                reply_markup=ForceReply()
            )

            return self.FILE_UPLOAD

        file = io.BytesIO(document.get_file().download_as_bytearray())

        try:
            if ext == 'csv':
                df: pd.DataFrame = pd.read_csv(file)
            elif ext in ('xls', 'xlsx'):
                df = pd.read_excel(file)
        except Exception as ex:
            logging.error(f'DataFrame import error: {ex}')
            update.message.reply_text(
                'Could not read from file. Try another one or '
                'type /cancel to exit.',
                reply_markup=ForceReply()
            )

            return self.FILE_UPLOAD

        try:
            X = df[[*self.params]]
            df_predicted = pd.DataFrame(
                self.model.predict(X),
                columns=['price_mil']
            )
        except Exception as ex:
            logging.error(f'Prediction attempt error: {ex}')
            update.message.reply_text(
                'Could not calculate prediction based on the received data. '
                'Try another file or type /cancel to exit.',
                reply_markup=ForceReply()
            )

            return self.FILE_UPLOAD

        df = pd.concat([df, df_predicted], axis=1)
        output = io.BytesIO()

        if ext == 'csv':
            df.to_csv(output)
        elif ext in ('xls', 'xlsx'):
            df.to_excel(output)

        output.seek(0)

        update.message.reply_document(
            document=output,
            filename=f'output.{ext}',
            caption='Prediction calculated! '
            'Would you like to create another one?',
            reply_markup=ReplyKeyboardMarkup(
                [['YES', 'NO']],
                one_time_keyboard=True
            )
        )
        logging.info(
            'Sent calculated prediction to '
            f'{update.message.from_user.first_name} '
            f'{update.message.from_user.last_name}'
        )

        return self.PROMPTING_ANOTHER

    def handle_prompting_another(self, update: Update, context: CCT) -> int:
        answer: str = update.message.text

        if answer == 'YES':
            self.initial_reply(update)

            return self.FILE_UPLOAD
        elif answer == 'NO':
            update.message.reply_text(
                'Exiting prediction mode.',
                reply_markup=ReplyKeyboardRemove()
            )

            return self.END

        return self.END
