import random, threading, os, logging, telegram
from queue import Queue
from telegram import Bot, ChatMemberUpdated, Update
from telegram.ext import MessageHandler, Filters, ChatMemberHandler, CallbackContext, Dispatcher, Updater
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

#import var values
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_GROUP_ADMIN_ID = os.getenv('TELEGRAM_GROUP_ADMIN_ID')

# This dict will hold the arithmetic tasks and message ids for each user
tasks = {}

# This list will hold all timer threads
timer_threads = []

def cleanup():
    for thread in timer_threads:
        if thread.is_alive():
            print(f"Stopping thread {thread.name}")
            thread.cancel()

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
            # Use a tuple of (chat_id, user_id) as the key
            greeting_message = context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Hello {member.username}, what's {question}? You have 60 seconds to answer.",
                                     timeout=15)
            logger.info(f"Asked question to new member {member.username} in chat {update.effective_chat.id}")
            # Save the message_id of the greeting message
            greeting_message_id = greeting_message.message_id
            tasks[(update.effective_chat.id, member.id)] = (answer, greeting_message_id)
            # Set a 61-second timer to check if the user has answered
            timer_thread = threading.Timer(61, check_answer, args=[update, context, member.id, greeting_message_id])
            timer_thread.start()
            timer_threads.append(timer_thread)

def check_answer(update: Update, context: CallbackContext, user_id: int, greeting_message_id: int) -> None:
    # Use a tuple of (chat_id, user_id) as the key
    if (update.effective_chat.id, user_id) in tasks:
        # The user did not answer in time, remove them from the group
        context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user_id, timeout=15)
        context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=user_id, timeout=15)
        logger.info(f"Removed user {user_id} from chat {update.effective_chat.id} due to timeout")
        # Delete the greeting message
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=greeting_message_id, timeout=15)

def message(update: Update, context: CallbackContext) -> None:
    if (update.effective_chat.id, update.effective_user.id) in tasks and int(update.message.text) == tasks[(update.effective_chat.id, update.effective_user.id)][0]:
        # Get the greeting message id before deleting the task
        greeting_message_id = tasks[(update.effective_chat.id, update.effective_user.id)][1]
        del tasks[(update.effective_chat.id, update.effective_user.id)]
        logger.info(f"User {update.effective_user.id} answered correctly in chat {update.effective_chat.id}")
        # Delete the arithmetic question message
        for _ in range(3):  # Retry up to 3 times
            try:
                context.bot.delete_message(chat_id=update.effective_chat.id, message_id=greeting_message_id, timeout=15)
                break  # If successful, break the loop
            except telegram.error.TimedOut:
                continue  # If a timeout occurs, retry
        # Delete the user's answer message
        for _ in range(3):  # Retry up to 3 times
            try:
                context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id, timeout=15)
                break  # If successful, break the loop
            except telegram.error.TimedOut:
                continue  # If a timeout occurs, retry
    else:
        context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=update.effective_user.id, timeout=15)
        context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=update.effective_user.id, timeout=15)
        logger.info(f"Removed user {update.effective_user.id} from chat {update.effective_chat.id} due to incorrect answer")



def main() -> None:
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, new_member))
    dispatcher.add_handler(MessageHandler(Filters.status_update.left_chat_member, delete_system_message))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message))

    try:
        updater.start_polling()
        updater.idle()
    except KeyboardInterrupt:
        print("Received interrupt, cleaning up...")
        cleanup()

def delete_system_message(update: Update, context: CallbackContext) -> None:
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id, timeout=15)
    logger.info(f"Deleted system message in chat {update.effective_chat.id}")

if __name__ == '__main__':
    main()
