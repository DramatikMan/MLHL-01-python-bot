import logging
from typing import cast

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ConversationHandler

from app.db.utils import get_columns_meta
from ..types import CCT


class BaseHandler(ConversationHandler[CCT]):
    columns: dict[str, str]

    def __new__(cls) -> 'BaseHandler':
        inst = ConversationHandler.__new__(cls)
        inst.__dict__['columns'] = get_columns_meta()

        return cast('BaseHandler', inst)

    def cancel(self, update: Update, context: CCT) -> int:
        username: str = update.message.from_user.first_name
        logging.info(f'User {username} canceled the conversation.')

        context.user_data['filters'] = {}

        update.message.reply_text(
            "Conversation's over.",
            reply_markup=ReplyKeyboardRemove()
        )

        return self.END
