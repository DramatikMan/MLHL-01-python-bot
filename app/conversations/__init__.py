import logging

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ConversationHandler

from ..types import CCT


class BaseHandler(ConversationHandler[CCT]):
    def cancel(self, update: Update, context: CCT) -> int:
        username: str = update.message.from_user.first_name
        logging.info(f'User {username} canceled the conversation.')

        context.user_data['filters'] = {}

        update.message.reply_text(
            "Conversation's over.",
            reply_markup=ReplyKeyboardRemove()
        )

        return self.END
