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
convoHistory = []


# def load_conversation(session_id):
#     document = conversation_collection.find_one({"session_id": session_id})
#     if document:
#         return document["conversation"]
#     return []
#


def save_message_to_mongo(role, content):
    try:
        conversation_collection.insert_one({
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now(datetime.UTC),
            "session_id": session_id
        })
    except Exception as e:
        print("Error saving message to MongoDB:", e)


def load_conversation_history():
    try:
        history = list(conversation_collection.find().sort("timestamp", 1))
        return [{"role": h["role"], "content": h["content"]} for h in history]
    except Exception as e:
        print("Error loading conversation history:", e)
        return []


def cosmosResponse(convo):
    bot = ''
    response = ollama.chat(
        model='llama3.2',
        messages=convo,
        stream=True
    )

    for chunk in response:
        # print(chunk['message']['content'], end='', flush=True)
        bot += chunk['message']['content']
    convoHistory.append({'role': 'assistant', 'content': bot})
    # save_message_to_mongo(role='assistant', content=bot)
    return bot


# print("Cosmos: Hi I am your bot. How can I assist you today?", end='\n')
# save_message_to_mongo(role='assistant', content="Hi I am your bot. How can I assist you today?")

convoHistory = load_conversation_history()

res = cosmosResponse(convo=convoHistory)
print(f"Cosmos: {res}", end='')
print('\n')
while True:
    quest = input("You: ")
    convoHistory.append({'role': 'user', 'content': quest})
    save_message_to_mongo(role='user', content=quest)
    #
    res = cosmosResponse(convo=convoHistory)
    print(f"Cosmos: {res}", end='')

    # for chunk in response:
    #     print(chunk['message']['content'], end='', flush=True)
    #     bot += chunk['message']['content']
    # convoHistory.append({'role': 'assistant', 'content': bot})

    # save_message_to_mongo(role='assistant', content=bot)

    print('\n')

    if quest.lower() == 'exit' or quest.lower() == 'bye':
        break
