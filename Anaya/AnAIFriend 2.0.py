import datetime
import ollama
from pymongo import MongoClient
import uuid
import cred
import certifi

# Initialize MongoDB connection
MONGO_URI = f"mongodb+srv://{cred.db_username}:{cred.db_password}@cosmos.f2pie.mongodb.net/?retryWrites=true&w=majority&appName={cred.db_app_name}"  # Replace with your MongoDB connection URI in cred file
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.cosmosBot
conversation_collection = db.anayav2

# Generate unique session ID
session_id = str(uuid.uuid4())


def load_conversation_history():
    try:
        history = list(conversation_collection.find().sort("timestamp", 1))
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
            model="llama3.2",
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

if convoHistory[-1].get('role') == "assistant":
    print(f"Anaya - {convoHistory[-1].get('timestamp')}\n{convoHistory[-1].get('content')}\n")

elif convoHistory[-1].get('role') == "user":
    anayaResponse(convo=convoHistory)


def main():

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
