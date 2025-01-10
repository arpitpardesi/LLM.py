import openai
import cred
# Set your OpenAI API key
openai.api_key = cred.openaiapi_key

while True:
    quest= input("You: ")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Use GPT-3.5 instead
        messages=[
            {"role": "system", "content": "You are a helpful intelligent assistant."},
            {"role": "user", "content": quest}
        ]
    )
    print(response['choices'][0]['message']['content'].strip())

    if quest == 'exit':
        break

