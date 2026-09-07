import datetime

import ollama
from pymongo import MongoClient
import uuid
import cred
import certifi
import fetchData

session_id = str(uuid.uuid4())

# print(fetchData.convo)

MONGO_URI = f"mongodb+srv://{cred.db_username}:{cred.db_password}@cosmos.f2pie.mongodb.net/?retryWrites=true&w=majority&appName=Cosmos"  # Replace with your MongoDB connection URI
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.cosmosBot
conversation_collection = db.conversation_hist
NewBot = db.myUbot


def save_message_to_mongo(collection, role, content, datetimestr, dialogID):
    try:
        collection.insert_one({
            "role": role,
            "content": content,
            "timestamp": datetimestr,
            "session_id": session_id,
            "dialogID": dialogID
        })
    except Exception as e:
        print("Error saving message to MongoDB:", e)


# conversation_collection.insert_one({
#             "role": role,
#             "content": content,
#             "timestamp": datetime.datetime.utcnow()
#         })

# print(fetchData.convo[0].get("timestamp"))

i = 0
for doc in fetchData.convo:
    print(i, doc.get("role"), doc.get("content"), doc.get("datetime"))
    save_message_to_mongo(collection=NewBot, role=doc.get("role"), content=doc.get("content"),
                          datetimestr=doc.get("timestamp"), dialogID=i)
    i += 1

# for i in range(0, len(list)):
#     if list[i].startswith("Cosmos: "):
#         save_message_to_mongo("assistant", list[i].replace("Cosmos: ",""))
#     if list[i].startswith("You: "):
#         save_message_to_mongo("user", list[i].replace("Cosmos: ",""))
#


# convoHistory.append({'role': 'user', 'content': quest})
# convoHistory.append({'role': 'assistant', 'content': bot})
# save_conversation(session_id, convoHistory)
