import openai
import numpy as np


SIMILARITY_THRESHOLD = 0.8

class OpenAIInterface:
    def __init__(self, api_key: str):
        """Initialize the OpenAI interface with API key."""
        openai.api_key = api_key
        self.embedding_model = "text-embedding-3-small" #"text-embedding-ada-002"
        self.chat_model = "gpt-4o-mini"
        
    def generate_embedding(self, text: str) -> list[float]:
        """Generate embeddings for a given text using OpenAI's API."""
        try:
            # Generate the embedding for the given text using the OpenAI API
            response = openai.Embedding.create(
                model="text-embedding-ada-002",  # You can use a different model if you prefer
                input=text
            )
            # Extract the embedding from the response
            embedding = response['data'][0]['embedding']
            return embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None

    def generate_response(self, query: str, context: str,) -> str:
        """Generate a response using relevant conversation pages as context."""

        prompt = f"""
        \n
        context: {context}
        \n
        query: {query}
        """
        response = openai.ChatCompletion.create(
            model=self.chat_model,
            messages=[
                {"role": "developer", "content": "You are a helpful assistant with access to previous conversation history. Use the provided context to give natural, conversational responses that relay on past discussions. In your answer, include the times of the responses history you rely on. Content has context: <context>, and query: <query>. Answer the query based only on the provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content

    def is_similar(self, vec1: list[float], vec2: list[float], threshold: float=SIMILARITY_THRESHOLD) -> bool:
        if vec1 is None or vec2 is None:
            return False
        array1, array2 = np.array(vec1), np.array(vec2)
        similarity = np.dot(array1, array2)
        return similarity > threshold
    
    def generate_summary(self, text):
        """Generate summary for the given text using gpt-3.5-turbo."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Use gpt-3.5-turbo for summarization
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Please summarize the following text in 2 lines: {text}"}
                ],
                max_tokens=150,  # Adjust the summary length as needed
                temperature=0.5
            )
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"Error summarizing text: {e}")
            return None
        
    def rephrase_text(self, text):
        """Rephrase the given text using gpt-3.5-turbo."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Use gpt-3.5-turbo for rephrasing
                messages=[
                    {"role": "system", "content": "You are a rephrasing assistant."},
                    {"role": "user", "content": f"Please rephrase the following sentence for better clarity or grammar in his language: {text}"}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"Error rephrasing text: {e}")
            return None


def main():
    # Retrieve your OpenAI API key from environment variables
    from keys import openai_key as api_key

    # Initialize the OpenAIInterface with your API key
    openai_interface = OpenAIInterface(api_key)

    # Test the generate_embedding method
    text = "Sample text for embedding"
    embedding = openai_interface.generate_embedding(text)
    if embedding:
        print("Embedding generated successfully.")
    else:
        print("Failed to generate embedding.")

    # Test the generate_response method
    query = "What is the capital of France?"
    context = "This is a geography-related question."
    response = openai_interface.generate_response(query, context)
    if response:
        print("Response generated successfully:")
        print(response)
    else:
        print("Failed to generate response.")

if __name__ == "__main__":
    main()