from transformers import AutoModelForCausalLM, AutoTokenizer, GPTNeoXForCausalLM, GPTNeoXTokenizerFast

import json

# Load LLM (GPT-J)
model_name = "EleutherAI/gpt-neox-20b"
tokenizer = GPTNeoXTokenizerFast.from_pretrained(model_name)
model = GPTNeoXForCausalLM.from_pretrained(model_name)

# Load personality configuration
with open("ananya_config.json", "r") as file:
    config = json.load(file)

def generate_response(user_input):
    # Extract personality traits
    name = config["name"]
    mood = config["traits"]["mood"]
    tone = config["traits"]["tone"]
    behavior = config["traits"]["behavior"]

    # Prepare the input prompt
    prompt = f"Anaya ({mood}, {tone}): {user_input}\nResponse:"
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(inputs.input_ids, max_length=200, temperature=0.8)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# Example Usage
user_message = input("Arpit: ")
response = generate_response(user_message)
print(f"Anaya: {response}")