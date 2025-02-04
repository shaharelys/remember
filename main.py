import os
import openai
from flask import Flask
from llm_interface import OpenAIInterface
from db_interface import DatabaseInterface
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from threading import Thread

from dotenv import load_dotenv



######## just for test ########
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from datetime import datetime
###############################

# Load environment variables from .env file
load_dotenv()

# Load sensitive keys from environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


app = Flask(__name__)

openai.api_key = OPENAI_KEY

db_config = {
    'database': 'whatsapp.db'  # SQLite database file
}

db = DatabaseInterface(db_config['database'])

illm = OpenAIInterface(api_key=OPENAI_KEY)

OPTIONS = (
    "1. Save to your personal knowledge.\n"
    "2. Question your personal knowledge.\n"
    "3. Abort"
)

user_states = {}

class MainFoos:
    @classmethod
    def get_related_pages(cls, embeddings: list, sender_pages: list[dict]) -> list[dict]:
        related_pages = []
        for page in sender_pages:
            if illm.is_similar(embeddings, page['embeddings']):
                related_pages.append(page)
        return related_pages

    @classmethod
    def generate_response(cls, query_message: str, related_pages: list[dict]) -> str:
        return illm.generate_response(
            query=query_message,
            context=str([
                f"message #{i}, from {page['date']}: {page['message']}"
                for i, page in enumerate(related_pages)
            ])
        )

    @classmethod
    def ask(cls, from_number: str, question: str) -> str:
        """Handle a question about saved data."""
        embeddings = illm.generate_embedding(question)
        filtered_messages = db.get_messages_by_sender(from_number)
        related_pages = cls.get_related_pages(embeddings, filtered_messages)
        return cls.generate_response(question, related_pages)



user_context = {}

@app.route("/all_messages", methods=["GET"])
def get_all_message():
    all_messages = db.get_all_messages()
    return all_messages

############################################################################################################
# async def start_command2(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     print(f"Received /start command from {update.effective_user.id}")
#     await update.message.reply_text('Hi! I am your memory assistant bot.')

# Replace your existing start_command with:
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Received /start command from {update.effective_user.id}")
    reply_markup = create_keyboard()
    await update.message.reply_text(
        'Hi! I am your memory assistant bot. Choose an option:',
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    await query.answer()
    
    if query.data == 'save':
        user_states[user_id] = {
            'mode': 'save',
            'chat_id': update.effective_chat.id,
            'start_time': datetime.now()
        }
        
        asyncio.create_task(end_save_mode(user_id, context))
        
        await query.message.reply_text(
            "Save mode activated! For the next 15 minutes, every message you send will be saved to the database.\n"
            "Click 'Exit Save Mode' to end the session early.",
            reply_markup=create_keyboard(True)
        )
    
    elif query.data == 'exit_save':
        if user_id in user_states:
            del user_states[user_id]
            await query.message.reply_text(
                "Save mode ended. Regular mode restored.",
                reply_markup=create_keyboard(False)
            )
    
    elif query.data == 'ask':
        await query.message.reply_text(
            f"Ask button pressed at {current_time}",
            reply_markup=create_keyboard(False)
        )


# async def handle_message2(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_id = str(update.effective_user.id)
#     message = update.message.text
    
#     if user_id in user_context:
#         context_data = user_context[user_id]
        
#         if context_data['state'] == 'awaiting_choice':
#             if message == "1":
#                 embeddings = illm.generate_embedding(context_data['message'])
#                 db.save_message(user_id, context_data['message'], embeddings)
#                 await update.message.reply_text("Your message has been saved to your personal knowledge. You can now ask questions about it in future chats!")
#                 del user_context[user_id]
#             elif message == "2":
#                 response = MainFoos.ask(user_id, context_data['message'])
#                 await update.message.reply_text(response)
#                 del user_context[user_id]
#             elif message == "3":
#                 await update.message.reply_text("Aborted.")
#                 del user_context[user_id]
#             else:
#                 await update.message.reply_text(f"Invalid choice. Please select a number representing a valid option:\n{OPTIONS}")
#             return

#     # If we get here, it's a new message
#     user_context[user_id] = {'message': message, 'state': 'awaiting_choice'}
#     await update.message.reply_text(f"What would you like to do with this message?\n{OPTIONS}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    
    if user_id in user_states and user_states[user_id]['mode'] == 'save':
        embeddings = illm.generate_embedding(message_text)
        db.save_message(user_id, message_text, embeddings)
        await update.message.reply_text(
            "✅ Message saved to database!",
            reply_markup=create_keyboard(True)
        )
    else:
        reply_markup = create_keyboard()
        await update.message.reply_text(
            'Choose an option:',
            reply_markup=reply_markup
        )



# def init_telegram_bot2():
#     application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
#     application.add_handler(CommandHandler("start", start_command))
#     application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
#     return application

def init_telegram_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_callback))  # Add this line
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return application
############################################################################################################


def run_telegram():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    finally:
        loop.close()


def create_keyboard(in_save_mode=False):
    if in_save_mode:
        keyboard = [[InlineKeyboardButton("Exit Save Mode", callback_data='exit_save')]]
    else:
        keyboard = [
            [
                InlineKeyboardButton("Save Text", callback_data='save'),
                InlineKeyboardButton("Ask Question", callback_data='ask')
            ]
        ]
    return InlineKeyboardMarkup(keyboard)


async def end_save_mode(user_id: str, context: ContextTypes.DEFAULT_TYPE):
    if user_id in user_states:
        chat_id = user_states[user_id]['chat_id']
        del user_states[user_id]
        await context.bot.send_message(
            chat_id=chat_id,
            text="Save mode has ended. Your 15-minute session is over.",
            reply_markup=create_keyboard(False)
        )



if __name__ == "__main__":
    telegram_app = init_telegram_bot()
    telegram_app.run_polling(allowed_updates=Update.ALL_TYPES)
    
    telegram_thread = Thread(target=run_telegram)
    telegram_thread.daemon = True  # This will help the thread shut down with the main program
    telegram_thread.start()
    
    app.run(host='0.0.0.0', port=5000, debug=False)