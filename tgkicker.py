import random, threading, os
from queue import Queue
from telegram import Bot, ChatMemberUpdated, Update
from telegram.ext import MessageHandler, Filters, ChatMemberHandler, CallbackContext, Dispatcher, Updater
from dotenv import load_dotenv

#import var values
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_GROUP_ADMIN_ID = os.getenv('TELEGRAM_GROUP_ADMIN_ID')

# This dict will hold the arithmetic tasks for each user
tasks = {}

def arithmetic_task():
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    question = f"{a} + {b}"
    answer = a + b
    return question, answer

def new_member(update: Update, context: CallbackContext) -> None:
    for member in update.message.new_chat_members:
        if member.id != context.bot.id:
            question, answer = arithmetic_task()
            tasks[member.id] = answer
            greeting_message = context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Hello {member.username}, what's {question}? You have 30 seconds to answer.",
                                     timeout=15)
            # Save the message_id of the greeting message
            greeting_message_id = greeting_message.message_id
            # Set a 30-second timer to check if the user has answered
            threading.Timer(61, check_answer, args=[update, context, member.id, greeting_message_id]).start()

def check_answer(update: Update, context: CallbackContext, user_id: int, greeting_message_id: int) -> None:
    if user_id in tasks:
        # The user did not answer in time, remove them from the group
        # context.bot.send_message(chat_id=update.effective_chat.id, text="Time's up! You will be removed.", timeout=15)
        context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user_id, timeout=15)
        context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=user_id, timeout=15)
        # Delete the greeting message
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=greeting_message_id)


def message(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id in tasks and int(update.message.text) == tasks[update.effective_user.id]:
        del tasks[update.effective_user.id]
        # context.bot.send_message(chat_id=update.effective_chat.id, text="Correct!") # sending "correct" upon correct answer
    else:
        # context.bot.send_message(chat_id=update.effective_chat.id, text="Wrong answer. You will be removed.")
        context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=update.effective_user.id, timeout=15)
        context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=update.effective_user.id, timeout=15)

def main() -> None:
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, new_member))
    dispatcher.add_handler(MessageHandler(Filters.status_update.left_chat_member, delete_system_message))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message))

    updater.start_polling()
    updater.idle()

def delete_system_message(update: Update, context: CallbackContext) -> None:
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id, timeout=15)


if __name__ == '__main__':
    main()
