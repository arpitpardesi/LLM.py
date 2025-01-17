from pymongo import MongoClient
from datetime import datetime, timedelta
import ollama
from pymongo import MongoClient
import uuid
import cred
import certifi

# from uploadData import save_message_to_mongo

session_id = str(uuid.uuid4())


MONGO_URI = f"mongodb+srv://{cred.db_username}:{cred.db_password}@cosmos.f2pie.mongodb.net/?retryWrites=true&w=majority&appName=Cosmos"  # Replace with your MongoDB connection URI
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.cosmosBot
# conversation = db.conversation_hist
conversation = db.myBotV2
# conversation = db.myUbot

history = list(conversation.find().sort("timestamp", -1))

# print(len(history))

date = history[0].get('timestamp')

# print(history[0].get('content'), date)
# Define the specific date (e.g., "2025-01-01")
# specific_date = datetime(date)

# Create the start and end of the date range
# start_timestamp = specific_date
# end_timestamp = specific_date + timedelta(days=1)

# # Delete documents with a timestamp in the specified range
def usingDatetime(start_timestamp, conversation):
    end_timestamp = start_timestamp + timedelta(days=1)
    result = conversation.delete_many({
        "timestamp": {
            "$gte": start_timestamp,
            "$lt": end_timestamp
       }
    })
    return result.deleted_count

# Delete documents with a timestamp in the specified range

def deletedAll(conversation):
    result = conversation.remove()

    return result

def usingExcatDate(date, conversation):
    result = conversation.delete_many({
        "timestamp": date
    })
    return result.deleted_count

def usingDialogID(ID, conversation):
    result = conversation.delete_many({
        "dialogID": {
            "$gte": ID
        }
    })
    return result.deleted_count

# result = conversation.delete_many({
#         "dialogID": {
#             "$gte": 971
#         }
#     })
# Print the number of deleted documents
print(f"Deleted {usingDialogID(1,   conversation=conversation)} documents.")