from pymongo import MongoClient
import json
import wikipedia
from textblob import TextBlob
from googletrans import Translator
import speech_recognition as sr
import pyttsx3
from rasa_nlu.model import Interpreter
import openai
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import datetime

# MongoDB Setup
MONGO_URI = "mongodb://localhost:27017/"  # Replace with your MongoDB connection URI
client = MongoClient(MONGO_URI)
db = client.chatbot
conversation_collection = db.conversation_history

# Google Calendar API Setup
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Set your OpenAI API key here
openai.api_key = 'your-openai-api-key'

# Load conversation history from MongoDB
def load_conversation_history():
    try:
        history = list(conversation_collection.find().sort("timestamp", 1))
        return [{"role": h["role"], "content": h["content"]} for h in history]
    except Exception as e:
        print("Error loading conversation history:", e)
        return []

# Save a single message to MongoDB
def save_message_to_mongo(role, content):
    try:
        conversation_collection.insert_one({
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.utcnow()
        })
    except Exception as e:
        print("Error saving message to MongoDB:", e)

# Sentiment Analysis
def analyze_sentiment(text):
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity
    if sentiment > 0:
        return "positive"
    elif sentiment < 0:
        return "negative"
    else:
        return "neutral"

# Translation (Multilingual Support)
def translate_input(text):
    translator = Translator()
    translated = translator.translate(text, src='auto', dest='en')
    return translated.text

# Speech-to-Text (Voice Input)
def listen_to_user():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
        user_input = recognizer.recognize_google(audio)
        return user_input

# Text-to-Speech (Voice Output)
def speak_response(response):
    engine = pyttsx3.init()
    engine.say(response)
    engine.runAndWait()

# Intent Recognition (Rasa NLU)
def handle_intent(user_input, interpreter):
    intent = interpreter.parse(user_input)['intent']['name']
    if intent == 'set_reminder':
        return "Sure, I can set a reminder for you!"
    elif intent == 'ask_weather':
        return "Let me check the weather for you."
    elif intent == 'greet':
        return "Hello! How can I assist you today?"
    return None

# Wikipedia Knowledge Base
def get_wikipedia_summary(query):
    try:
        summary = wikipedia.summary(query, sentences=1)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Sorry, there are multiple results for {query}. Please clarify."
    except wikipedia.exceptions.HTTPTimeoutError:
        return "I'm unable to fetch information right now. Please try again later."

# DALL·E Image Generation
def generate_image_dalle(description):
    response = openai.Image.create(
        prompt=description,
        n=1,
        size="1024x1024"
    )
    image_url = response['data'][0]['url']
    print(f"Generated Image URL: {image_url}")
    return image_url

# Google Calendar Integration
def authenticate_google():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('calendar', 'v3', credentials=creds)
    return service

def create_calendar_event(service, summary, start_time, end_time):
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time,
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'UTC',
        },
    }
    event_result = service.events().insert(calendarId='primary', body=event).execute()
    print(f"Event created: {event_result['summary']}")

# Main Conversation Loop
def advanced_conversation():
    # Load previous conversation history from MongoDB
    conversation_history = load_conversation_history()

    # Initialize the intent recognizer
    interpreter = Interpreter.load("path_to_your_rasa_model")

    print("Welcome to the Advanced Interactive Assistant!")
    print("Type 'exit' to end the conversation.")

    google_service = None  # For Google Calendar integration

    while True:
        # Capture input (either voice or text)
        try:
            user_input = input("\nYou (text): ")  # Or use `listen_to_user()` for voice
        except Exception as e:
            print("Error capturing input:", e)
            continue

        # Exit condition
        if user_input.lower() == 'exit':
            print("Goodbye! Have a great day.")
            break

        # Translate input
        translated_input = translate_input(user_input)

        # Analyze sentiment
        sentiment = analyze_sentiment(translated_input)
        print(f"Sentiment: {sentiment.capitalize()}")

        # Intent recognition
        action_response = handle_intent(translated_input, interpreter)
        if action_response:
            print(f"Assistant (action): {action_response}")
            save_message_to_mongo("assistant", action_response)
            continue

        # Wikipedia query
        if "wikipedia" in translated_input.lower():
            topic = translated_input.replace("wikipedia", "").strip()
            summary = get_wikipedia_summary(topic)
            print(f"Assistant: {summary}")
            save_message_to_mongo("assistant", summary)
            continue

        # Image generation
        if "generate image" in translated_input.lower():
            description = translated_input.replace("generate image", "").strip()
            print(f"Assistant: Generating image for: {description}")
            image_url = generate_image_dalle(description)
            save_message_to_mongo("assistant", image_url)
            continue

        # Add input to conversation history
        conversation_history.append({"role": "user", "content": translated_input})
        save_message_to_mongo("user", translated_input)

        # Get response from OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation_history
        )
        model_response = response["choices"][0]["message"]["content"]
        print(f"Assistant: {model_response}")

        # Add response to conversation history and save to MongoDB
        conversation_history.append({"role": "assistant", "content": model_response})
        save_message_to_mongo("assistant", model_response)

# Run the assistant
advanced_conversation()