import datetime

import ollama
from pymongo import MongoClient
import uuid
import cred
import certifi

def load_conversation_history():
    try:
        history = list(conversation_collection.find().sort("timestamp", 1))
        return [{"role": h["role"], "content": h["content"]} for h in history]
    except Exception as e:
        print("Error loading conversation history:", e)
        return []


session_id = str(uuid.uuid4())

MONGO_URI = f"mongodb+srv://{cred.db_username}:{cred.db_password}@cosmos.f2pie.mongodb.net/?retryWrites=true&w=majority&appName=Cosmos"  # Replace with your MongoDB connection URI
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.cosmosBot
conversation_collection = db.anayaAI
convoHistory = load_conversation_history()
dialogID = len(convoHistory)


def save_message_to_mongo(role, content, dialogID):
    dialogID += 1
    try:
        conversation_collection.insert_one({
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now(datetime.UTC),
            "session_id": session_id,
            "dialogID": dialogID
        })
        dialogID += 1
    except Exception as e:
        print("Error saving message to MongoDB:", e)

def anayaResponse(convo, dialogID):
    bot = """"""
    response = ollama.chat(
        # model='llama3.2',
        model="artifish/llama3.2-uncensored",
        messages=convo,
        stream=True
    )
    print(f"Anaya: ", end='')
    for chunk in response:
        print(chunk['message']['content'], end='', flush=True)
        bot += chunk['message']['content']
    print("\n")
    convoHistory.append({'role': 'assistant', 'content': bot})
    save_message_to_mongo(role='assistant', content=bot, dialogID=dialogID)
    # return bot

if convoHistory[-1].get('role') == "assistant":
    print(f"Anaya: {convoHistory[-1].get('content')}\n")

elif convoHistory[-1].get('role') == "user":
    anayaResponse(convo=convoHistory, dialogID=dialogID)

    # res = anayaResponse(convo=convoHistory)
    # print(f"Anaya: {res}", end='')
    # print('\n')

while True:
    quest = input("You: ")
    convoHistory.append({'role': 'user', 'content': quest, 'dialogID': dialogID})
    save_message_to_mongo(role='user', content=quest, dialogID=dialogID)

    anayaResponse(convo=convoHistory, dialogID=dialogID)

    # res = anayaResponse(convo=convoHistory)
    # print(f"Anaya: {res}", end='')
    # print('\n')

    if quest.lower() == 'exit' or quest.lower() == 'bye' or quest.lower() == 'bye anaya' or quest.lower() == 'see you soon':
        break


