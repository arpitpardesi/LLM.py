import datetime
import ollama
from pymongo import MongoClient
import uuid
import cred
import certifi

session_id = str(uuid.uuid4())

MONGO_URI = f"mongodb+srv://{cred.db_username}:{cred.db_password}@cosmos.f2pie.mongodb.net/?retryWrites=true&w=majority&appName=Cosmos"  # Replace with your MongoDB connection URI
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.cosmosBot
conversation_collection = db.conversation_hist


def load_conversation_history():
    try:
        history = list(conversation_collection.find().sort("timestamp", -1))
        return [{"role": h["role"], "content": h["content"]} for h in history]
    except Exception as e:
        print("Error loading conversation history:", e)
        return []

convo = load_conversation_history()

print(convo[0].get('role'))
