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
# conversation = db.myBotV2
# conversation = db.myUbot
# conversation = db.anayaAI

bots = [db.conversation_hist, db.myBotV2, db.myUbot, db.anayaAI, db.anayav2]

# history = list(conversation.find().sort("timestamp", -1))

# date = history[0].get('timestamp')


# print(history[0].get('content'), date)
# Define the specific date (e.g., "2025-01-01")
# specific_date = datetime(date)

# Create the start and end of the date range
# start_timestamp = specific_date
# end_timestamp = specific_date + timedelta(days=1)

# # Delete documents with a timestamp in the specified range
def usingDatetime(start_timestamp, conversation):
    days = input("Days from the start date: ")
    end_timestamp = start_timestamp + timedelta(days=days)
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


def usingExactDate(date, conversation):
    result = conversation.delete_many({
        "timestamp": date
    })
    return result.deleted_count


def usingDialogID(conversation):
    ID = int(input('Enter Dialog ID: '))
    result = conversation.delete_many({
        "dialogID": {
            "$gte": ID
        }
    })
    return result.deleted_count

def usingSessionID(conversation):
    ID = int(input('Enter Session ID: '))
    result = conversation.delete_many({
        "session_id": {
            "$eq": ID
        }
    })
    return result.deleted_count

def load_conversation_history(bot):
    try:
        history = list(bot.find().sort("timestamp", 1))
        return [{"role": h["role"], "content": h["content"]} for h in history]
    except Exception as e:
        print("Error loading conversation history:", e)
        return []


print("Bot names: ")
for i in range(0, len(bots)):
    print(f'{i + 1}. {bots[i].name}')

bot = int(input("\nselect a bot first: "))
bot = bots[bot - 1]
print(f"Total documents in {bot.name}: {len(load_conversation_history(bot))}")
print(
    "\nMenu: \n1. Delete all Documents\n2. Delete using timestamp \n3. Delete using exact Date \n4. Delete using Dialog ID \n5. Delete using Session ID")
menu = int(input('Select operation to perform: '))



match menu:
    case 1:
        print(deletedAll(conversation=bot))
    case 2:
        start_timestamp = input("Start timestamp: ")
        print(usingDatetime(start_timestamp=start_timestamp, conversation=bot))
    case 3:
        date = input('Enter date: ')
        print(usingExactDate(date=date, conversation=bot))
    case 4:
        # ID = int(input('Enter Dialog ID: '))
        print(f'Documents deleted: {usingDialogID(conversation=bot)}')
    case 5:
        # ID = int(input('Enter Dialog ID: '))
        print(f'Documents deleted: {usingDSessionID(conversation=bot)}')
