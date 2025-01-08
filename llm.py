import ollama
from pymongo import MongoClient
import uuid
import cred
import certifi


session_id = str(uuid.uuid4())


MONGO_URI = f"mongodb+srv://{cred.db_username}:{cred.db_password}@cosmos.f2pie.mongodb.net/?retryWrites=true&w=majority&appName=Cosmos"  # Replace with your MongoDB connection URI
client = MongoClient(MONGO_URI)
db = client.cosmosBot
conversation_collection = db.conversation_hist
print(db, conversation_collection)
convoHistory = []

def load_conversation(session_id):
    document = conversation_collection.find_one({"session_id": session_id})
    if document:
        return document["conversation"]
    return []

def save_conversation(session_id, conversation):
    document = {
        "session_id": session_id,
        "conversation": conversation
    }
    conversation_collection.update_one(
        {"session_id": session_id},
        {"$set": document},
        upsert=True
    )

print("Cosmos: Hi I am your bot. How can I assist you today?", end='\n')
while True:
    bot = ''
    quest = input("You: ")
    convoHistory.append({'role': 'user', 'content': quest})
    response = ollama.chat(
        model='llama3.2',
        messages=convoHistory,
        stream=True
    )
    print("Cosmos: ", end='')
    for chunk in response:
        print(chunk['message']['content'], end='', flush=True)
        bot += chunk['message']['content']
    convoHistory.append({'role': 'assistant', 'content': bot})
    save_conversation(session_id, convoHistory)

    print('\n')

    if quest.lower() == 'exit' or quest.lower() == 'bye':
        break
