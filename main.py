import os
import openai
from flask import Flask, request
from llm_interface import OpenAIInterface
from db_interface import DatabaseInterface
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from threading import Thread

from dotenv import load_dotenv

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
    "3. Summarize this message\n"
    "4. Rephrase this message\n"
    "5. Abort"
)

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

    @staticmethod
    def summarize(text: str) -> str:
        """Summarize text without saving to the database."""
        return illm.generate_summary(text)


user_context = {}

@app.route("/all_messages", methods=["GET"])
def get_all_message():
    all_messages = db.get_all_messages()
    return all_messages



# @app.route("/webhook", methods=["POST"])
# def webhook():
#     OPTIONS = (
#         "1. Save to your personal knowledge.\n"
#         "2. Quesiton your personal knowledge.\n"
#         "3. Summarize this message\n"
#         "4. Rephrase this message\n"
#         "5. Abort"
#     )

#     message = request.form.get("Body")
#     from_number = request.form.get("From")
#     response = MessagingResponse()
#     if from_number in user_context:
#         context = user_context[from_number]

#         if context['state'] == 'awaiting_choice':
#             if message == "1":
#                 embeddings = illm.generate_embedding(context['message'])
#                 db.save_message(from_number, context['message'], embeddings)
#                 response.message("Your message has been saved to your personal knowledge. You can now ask questions about it in future chats!")
#                 del user_context[from_number]
#             elif message == "2":
#                 response.message(MainFoos.ask(from_number, context['message']))
#                 del user_context[from_number]
#             elif message == "3":
#                 response.message(MainFoos.summarize(context['message']))
#                 del user_context[from_number]
#             elif message == "4":
#                 response.message(illm.rephrase_text(context['message']))
#                 del user_context[from_number]
#             elif message == "5":
#                 response.message("Aborted.")
#                 del user_context[from_number]
#             else:
#                 response.message(f"Invalid choice. Please select a number representing a valid option:\n{OPTIONS}")
#         return str(response)

#     user_context[from_number] = {'message': message, 'state': 'awaiting_choice'}
#     response.message(f"What would you like to do with this message?\n{OPTIONS}")
#     return str(response)


############################################################################################################
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Received /start command from {update.effective_user.id}")
    await update.message.reply_text('Hi! I am your memory assistant bot.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    message = update.message.text
    
    if user_id in user_context:
        context_data = user_context[user_id]
        
        if context_data['state'] == 'awaiting_choice':
            if message == "1":
                embeddings = illm.generate_embedding(context_data['message'])
                db.save_message(user_id, context_data['message'], embeddings)
                await update.message.reply_text("Your message has been saved to your personal knowledge. You can now ask questions about it in future chats!")
                del user_context[user_id]
            elif message == "2":
                response = MainFoos.ask(user_id, context_data['message'])
                await update.message.reply_text(response)
                del user_context[user_id]
            elif message == "3":
                response = MainFoos.summarize(context_data['message'])
                await update.message.reply_text(response)
                del user_context[user_id]
            elif message == "4":
                response = illm.rephrase_text(context_data['message'])
                await update.message.reply_text(response)
                del user_context[user_id]
            elif message == "5":
                await update.message.reply_text("Aborted.")
                del user_context[user_id]
            else:
                await update.message.reply_text(f"Invalid choice. Please select a number representing a valid option:\n{OPTIONS}")
            return

    # If we get here, it's a new message
    user_context[user_id] = {'message': message, 'state': 'awaiting_choice'}
    await update.message.reply_text(f"What would you like to do with this message?\n{OPTIONS}")

def init_telegram_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
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

if __name__ == "__main__":
    telegram_app = init_telegram_bot()
    telegram_app.run_polling(allowed_updates=Update.ALL_TYPES)
    
    telegram_thread = Thread(target=run_telegram)
    telegram_thread.daemon = True  # This will help the thread shut down with the main program
    telegram_thread.start()
    
    app.run(host='0.0.0.0', port=5000, debug=False)