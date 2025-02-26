import datetime
import ollama
from pymongo import MongoClient
import uuid
import cred
import certifi

class AnayaChatBot:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.mongo_client = MongoClient(
            f"mongodb+srv://{cred.db_username}:{cred.db_password}@cosmos.f2pie.mongodb.net/?retryWrites=true&w=majority&appName=Cosmos",
            tlsCAFile=certifi.where()
        )
        self.db = self.mongo_client.cosmosBot
        self.conversation_collection = self.db.anayaAI
        self.convo_history = self.load_conversation_history()
        self.dialogID = self.get_latest_dialog_id()  # Fetch latest dialogID

    def load_conversation_history(self):
        """Loads conversation history from MongoDB."""
        try:
            history = list(self.conversation_collection.find({}, {"_id": 0}).sort("timestamp", 1))
            return [{"role": h["role"], "content": h["content"]} for h in history]
        except Exception as e:
            print("Error loading conversation history:", e)
            return []

    def get_latest_dialog_id(self):
        """Retrieves the latest dialogID from MongoDB."""
        try:
            last_entry = self.conversation_collection.find_one({}, {"dialogID": 1}, sort=[("dialogID", -1)])
            return last_entry["dialogID"] + 1 if last_entry else 1
        except Exception as e:
            print("Error fetching latest dialogID:", e)
            return 1

    def save_message_to_mongo(self, role, content):
        """Saves a chat message to MongoDB."""
        self.dialogID += 1
        try:
            self.conversation_collection.insert_one({
                "role": role,
                "content": content,
                "timestamp": datetime.datetime.now(datetime.UTC),
                "session_id": self.session_id,
                "dialogID": self.dialogID
            })
        except Exception as e:
            print("Error saving message to MongoDB:", e)

    def stream_response(self, convo):
        """Streams response from the chatbot."""
        bot_response = ""
        try:
            response = ollama.chat(
                model="artifish/llama3.2-uncensored",
                messages=convo,
                stream=True
            )

            print("Anaya: ", end="", flush=True)
            for chunk in response:
                text = chunk['message']['content']
                print(text, end="", flush=True)
                bot_response += text

            print("\n")
            return bot_response
        except Exception as e:
            print("Error generating response:", e)
            return "Sorry, I encountered an issue."

    def chat(self):
        """Handles the chat loop."""
        if self.convo_history and self.convo_history[-1].get('role') == "assistant":
            print(f"Anaya: {self.convo_history[-1].get('content')}\n")
        elif self.convo_history and self.convo_history[-1].get('role') == "user":
            response = self.stream_response(self.convo_history)
            self.convo_history.append({'role': 'assistant', 'content': response})
            self.save_message_to_mongo('assistant', response)

        while True:
            user_input = input("Arpit: ").strip()
            if user_input.lower() in {'exit', 'bye', 'bye anaya', 'see you soon'}:
                print("Anaya: Bye, Arpit! Take care. 😊")
                break

            self.convo_history.append({'role': 'user', 'content': user_input})
            self.save_message_to_mongo('user', user_input)

            response = self.stream_response(self.convo_history)
            self.convo_history.append({'role': 'assistant', 'content': response})
            self.save_message_to_mongo('assistant', response)


if __name__ == "__main__":
    bot = AnayaChatBot()
    bot.chat()