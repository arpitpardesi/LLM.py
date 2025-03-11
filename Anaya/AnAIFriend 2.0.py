import datetime
import ollama
from pymongo import MongoClient
import uuid
import cred
import certifi

# Initialize MongoDB connection
MONGO_URI = f"mongodb+srv://{cred.db_username}:{cred.db_password}@cosmos.f2pie.mongodb.net/?retryWrites=true&w=majority&appName=Cosmos"
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.cosmosBot
conversation_collection = db.anayav2

# Generate unique session ID
session_id = str(uuid.uuid4())


def load_conversation_history():
    try:
        history = list(conversation_collection.find({"session_id": session_id}).sort("timestamp", 1))
        return [{"role": h["role"], "content": h["content"]} for h in history]
    except Exception as e:
        print("Error loading conversation history:", e)
        return []


convoHistory = load_conversation_history()
dialogID = len(convoHistory)


def save_message_to_mongo(role, content):
    global dialogID
    dialogID += 1
    try:
        conversation_collection.insert_one({
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now(datetime.UTC),
            "session_id": session_id,
            "dialogID": dialogID
        })
    except Exception as e:
        print("Error saving message to MongoDB:", e)


def anayaResponse(convo):
    response_text = ""
    try:
        response = ollama.chat(
            model="artifish/llama3.2-uncensored",
            messages=convo,
            stream=True
        )
        print("Anaya: ", end='')
        for chunk in response:
            content = chunk['message']['content']
            print(content, end='', flush=True)
            response_text += content
        print("\n")

        # Save bot response
        convoHistory.append({'role': 'assistant', 'content': response_text})
        save_message_to_mongo('assistant', response_text)
    except Exception as e:
        print("Error generating Anaya response:", e)


def main():
    if convoHistory:
        print(f"Anaya: {convoHistory[-1]['content']}\n")

    while True:
        user_input = input("Arpit: ")
        if user_input.lower() in ['exit', 'bye', 'bye anaya', 'see you soon']:
            break

        # Save user message
        convoHistory.append({'role': 'user', 'content': user_input})
        save_message_to_mongo('user', user_input)

        # Get Anaya's response
        anayaResponse(convoHistory)


if __name__ == "__main__":
    main()
