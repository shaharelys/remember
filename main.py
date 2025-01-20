from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from requests.auth import HTTPBasicAuth
from llm_interface import OpenAIInterface
from db_interface import DatabaseInterface
from twilio.rest import Client
import json
from keys import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, openai_key

import openai

app = Flask(__name__)

openai.api_key = openai_key

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

db_config = {
    'host': 'localhost',
    'user': 'root',  # Replace with your MySQL username
    'password': '',  # Replace with your MySQL password
    'database': 'messages'
}

db = DatabaseInterface(db_config["host"], db_config["user"], db_config["password"], db_config["database"])
illm = OpenAIInterface()


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


@app.route("/webhook", methods=["POST"])
def webhook():
    # Get the incoming message from WhatsApp
    message = request.form.get("Body")
    from_number = request.form.get("From")
    response = MessagingResponse()

    # Check for command prefixes
    if message.lower().startswith("d "):
        # Save data to DB
        embeddings = illm.generate_embedding(message)
        text_to_save = message[2:].strip()
        db.save_message(from_number, text_to_save, embeddings)
        response.message("Added this message to my DB")
    
    elif message.lower().startswith("a "):
        # Ask question about saved data
        question = message[2:].strip()
        response.message(MainFoos.ask(from_number, question))
    
    elif message.lower().startswith("s "):
        # Summarize text without saving data
        text_to_summarize = message[2:].strip()
        response.message(MainFoos.summarize(text_to_summarize))
    
    elif message.lower().startswith("r "):
        # 4. Check grammar and rephrase
        text_to_rephrase = message[2:].strip()
        response.message(illm.rephrase_text(text_to_rephrase))
    
    else:
        response_message = (
            "Please start the conversation with one of the following commands:\n"
            "- `d: <your message>` to save data to the DB\n"
            "- `a: <your question>` to ask a question about saved data\n"
            "- `s: <your text>` to summarize text without saving it\n"
            "- `r: <your text>` to rephrase the text for clarity or grammar correction"
        )
        response.message(response_message)        
    
    return str(response)


if __name__ == "__main__":
    app.run(debug=True)
