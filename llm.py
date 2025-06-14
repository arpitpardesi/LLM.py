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

MONGO_URI = f"mongodb+srv://{cred.db_username}:{cred.db_password}@cosmos.f2pie.mongodb.net/?retryWrites=true&w=majority&appName={cred.db_username}"  # Replace with your MongoDB connection URI
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.cosmosBot
conversation_collection = db.conversation_hist
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

def cosmosResponse(convo, dialogID):
    bot = """"""
    response = ollama.chat(
        model='llama3.2',
        # model="artifish/llama3.2-uncensored",
        messages=convo,
        stream=True
    )
    print(f"Cosmos: ", end='')
    for chunk in response:
        print(chunk['message']['content'], end='', flush=True)
        bot += chunk['message']['content']
    print("\n")
    convoHistory.append({'role': 'assistant', 'content': bot})
    save_message_to_mongo(role='assistant', content=bot, dialogID=dialogID)
    # return bot

print(len(convoHistory))

if len(convoHistory) == 0:
    pass

elif convoHistory[-1].get('role') == "assistant":
    print(f"Cosmos: {convoHistory[-1].get('content')}\n")

elif convoHistory[-1].get('role') == "user":
    cosmosResponse(convo=convoHistory, dialogID=dialogID)

    # res = cosmosResponse(convo=convoHistory)
    # print(f"Cosmos: {res}", end='')
    # print('\n')

while True:
    quest = input("You: ")
    convoHistory.append({'role': 'user', 'content': quest, 'dialogID': dialogID})
    save_message_to_mongo(role='user', content=quest, dialogID=dialogID)

    cosmosResponse(convo=convoHistory, dialogID=dialogID)

    # res = cosmosResponse(convo=convoHistory)
    # print(f"Cosmos: {res}", end='')
    # print('\n')

    if quest.lower() == 'exit' or quest.lower() == 'bye' or quest.lower() == 'bye cosmos' or quest.lower() == 'see you soon':
        break


