from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from requests.auth import HTTPBasicAuth
from llm_interface import OpenAIInterface
from twilio.rest import Client
import mysql.connector
from mysql.connector import Error
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


# Function to get database connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None

def get_messages_by_sender(sender: str):
    """Retrieve all messages for a specific sender from the database."""
    conn = get_db_connection()
    if conn is None:
        print("Failed to connect to the database.")
        return []

    cursor = conn.cursor()

    # SQL query to fetch messages for the specified sender
    cursor.execute('''
    SELECT message, embeddings, date
    FROM messages
    WHERE sender_number = %s
    ORDER BY date DESC
    ''', (sender,))

    # Fetch all rows from the result
    rows = cursor.fetchall()

    # Convert rows to a list of dictionaries for easier processing
    messages = []
    for row in rows:
        message, embeddings_json, date = row
        embeddings = json.loads(embeddings_json)  # Convert JSON string back to list of floats
        messages.append({
            'message': message,
            'embeddings': embeddings,  # List of floats
            'date': date
        })

    conn.close()
    return messages

def save_message(sender, message, embeddings):
    """Save a message and its embeddings to the database."""
    # Open a database connection
    conn = get_db_connection()
    if conn is None:
        print("Failed to connect to the database.")
        return

    cursor = conn.cursor()

    # Convert embeddings list to JSON string
    embeddings_json = json.dumps(embeddings)  # Convert list of floats to JSON string

    # Insert message into the database, including embeddings
    cursor.execute('''
    INSERT INTO messages (sender_number, message, embeddings) 
    VALUES (%s, %s, %s)
    ''', (sender, message, embeddings_json))

    conn.commit()
    conn.close()


# find close embeddings - shahar input: query {message: message, embedding: embeddings, date: date}, rows by sender [{message: message, embedding: embeddings, date: date}], output: embedding related [{message: message, embedding: embeddings, date: date}]
def get_related_pages(embeddings: list, sender_pages:list[dict]) -> list[dict]:
    illm = OpenAIInterface()
    related_pages = []
    for page in sender_pages:
        if illm.is_similar(embeddings, page['embeddings']):
            related_pages.append(page)
    return related_pages

# send to openai - input  embedding related [{message: message, embedding: embeddings, date: date}], output: string
def generate_response(query_message: str, related_pages: list[dict]) -> str:
    illm = OpenAIInterface()
    return illm.generate_response(
        query=query_message,
        context=str([
                f"message #{i}, from {page['date']}: {page['message']}" 
                for i, page in enumerate(related_pages)
                ])
            )

def ask_question_about_saved_data(from_number, question):
    """Handle a question about saved data."""
    illm = OpenAIInterface()
    embeddings = illm.generate_embedding(question)
    filtered_messages = get_messages_by_sender(from_number)
    related_page = get_related_pages(embeddings, filtered_messages)
    return generate_response(question, related_page)

def summarize_text_without_saving(text):
    """Summarize text without saving to the database."""
    illm = OpenAIInterface()
    return illm.generate_summary(text)


# # Route to handle incoming messages
@app.route("/webhook", methods=["POST"])
def webhook():
    # Get the incoming message from WhatsApp
    message = request.form.get("Body")
    from_number = request.form.get("From")

    # Check for command prefixes
    if message.lower().startswith("d "):
        # Save data to DB
        illm = OpenAIInterface()
        embeddings = illm.generate_embedding(message)
        text_to_save = message[2:].strip()
        save_message(from_number, text_to_save, embeddings)
        return str("Added this message to my DB")
    elif message.lower().startswith("a "):
        # Ask question about saved data
        question = message[2:].strip()
        response_message = ask_question_about_saved_data(from_number, question)
        response = MessagingResponse()
        response.message(response_message)
        return str(response)
    elif message.lower().startswith("s "):
        # Summarize text without saving data
        text_to_summarize = message[10:].strip()  # Remove "summarize:" prefix
        response_message = summarize_text_without_saving(text_to_summarize)
        response = MessagingResponse()
        response.message(response_message)
        return str(response)
    elif message.lower().startswith("r "):
        # 4. Check grammar and rephrase
        text_to_rephrase = message[2:].strip()  # Remove "rephrase:" prefix
        illm = OpenAIInterface()
        response_message = illm.rephrase_text(text_to_rephrase)
        response = MessagingResponse()
        response.message(response_message)
        return str(response)
    else:
        response_message = (
            "Please start the conversation with one of the following commands:\n"
            "- `d: <your message>` to save data to the DB\n"
            "- `a: <your question>` to ask a question about saved data\n"
            "- `s: <your text>` to summarize text without saving it\n"
            "- `r: <your text>` to rephrase the text for clarity or grammar correction"
        )

        # Prepare response for WhatsApp
        response = MessagingResponse()
        response.message(response_message)
        
        return str(response)


if __name__ == "__main__":
    app.run(debug=True)
