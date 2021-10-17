import logging

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ConversationHandler

from ..types import CCT as CallbackContext


def cancel(update: Update, context: CallbackContext) -> int:
    username: str = update.message.from_user.first_name
    logging.info(f'User {username} canceled the conversation.')

    context.user_data['filters'] = {}  # type: ignore

    update.message.reply_text(
        "Conversation's over.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END
