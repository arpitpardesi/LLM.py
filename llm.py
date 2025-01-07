import ollama

convoHistory = []

print("Cosmos: Hi I am your bot. How can I assist you today?", end='\n')
while True:
    bot = ''
    quest = input("You: ")
    convoHistory.append({'role': 'user', 'content': quest})
    response = ollama.chat(
        model='llama3.2',
        messages=convoHistory,
        stream=True
    )
    print("Cosmos: ", end='')
    for chunk in response:
        print(chunk['message']['content'], end='', flush=True)
        bot += chunk['message']['content']
    convoHistory.append({'role': 'assistant', 'content': bot})
    print('\n')

    if quest.lower() == 'exit' or quest.lower() == 'bye':
        break
