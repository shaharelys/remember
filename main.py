import os
import openai
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from llm_interface import OpenAIInterface
from db_interface import DatabaseInterface
from twilio.rest import Client

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load sensitive keys from environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")


app = Flask(__name__)

openai.api_key = OPENAI_KEY

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

db_config = {
    'database': 'whatsapp.db'  # SQLite database file
}

db = DatabaseInterface(db_config['database'])

illm = OpenAIInterface(api_key=OPENAI_KEY)

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



@app.route("/webhook", methods=["POST"])
def webhook():
    message = request.form.get("Body")
    from_number = request.form.get("From")
    response = MessagingResponse()
    if from_number in user_context:
        context = user_context[from_number]

        if context['state'] == 'awaiting_choice':
            if message == "1":
                embeddings = illm.generate_embedding(context['message'])
                db.save_message(from_number, context['message'], embeddings)
                response.message("Your message has been saved to the database.")
            elif message == "2":
                response.message(MainFoos.ask(from_number, context['message']))
            elif message == "3":
                response.message(MainFoos.summarize(context['message']))
            elif message == "4":
                response.message(illm.rephrase_text(context['message']))
            else:
                response.message("Invalid choice. Please select a valid option.")

            del user_context[from_number]
        return str(response)

    user_context[from_number] = {'message': message, 'state': 'awaiting_choice'}
    response.message(
        "What would you like to do with this message?\n"
        "1. Save to DB\n"
        "2. Ask a question\n"
        "3. Summarize\n"
        "4. Rephrase"
    )
    return str(response)


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5000, debug=False)