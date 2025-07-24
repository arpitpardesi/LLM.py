# - [ ] Create an AI personality maker for AI bots that uses user inputs and suggestions from the AI. Users can also add new personality traits. The personality traits can be saved in a file that the bot can access and use.

import ollama
personality_traits = {}


def add_personality_trait():
    trait = input("Enter the personality trait: ")
    description = input("Enter a brief description of the trait: ")

    # confirm if trait looks good
    confirm = input(
        f"Does the trait '{trait}' with description '{description}' look good? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Trait not added. Trying again.")
        askOllama(f"Suggest a personality trait for {trait} with description: {description}")
    else:
        print("Trait confirmed. Proceeding to add or update the trait.")
        personality_traits[trait] = description
        # Check if the trait already exists
        print("Adding or updating personality trait...")

    if trait in personality_traits:
        print(f"Trait '{trait}' already exists. Updating description.")
        print(f"Current description: {personality_traits[trait]}")
        # Confirm if the user wants to update the existing trait
        update_confirm = input(f"Do you want to update the description for '{trait}'? (yes/no): ").strip().lower()
        if update_confirm == 'yes':
            personality_traits[trait] = description
            print(f"Trait '{trait}' updated successfully.")
    else:
        print(f"Adding new trait '{trait}'.")
    # Add or update the trait in the dictionary
    if not description.strip():
        print("Description cannot be empty. Please try again.")
        continue

    personality_traits[trait] = description
    print(f"Trait '{trait}' added successfully.")


def delete_personality_trait(trait):
    print("here you can delete a personality trait")
    if not personality_traits:
        print("No personality traits to delete.")
        return;
    print("Available Personality Traits:")
    for trait in personality_traits.keys():
        print(f"- {trait}")

    delete_trait = input("Enter the trait you want to delete: ")
    if delete_trait in personality_traits:
        del personality_traits[delete_trait]
        print(f"Trait '{delete_trait}' deleted successfully.")
    else:
        print(f"Trait '{delete_trait}' not found.")

    if personality_traits:
        print("Updated Personality Traits:")
        for trait in personality_traits.keys():
            print(f"- {trait}")
        print("Want to delete another trait? (yes/no)")
        choice = input().strip().lower()
        if choice == 'yes':
            delete_personality_trait(personality_traits)
        elif choice == 'no':
            print("Exiting deletion process.")
    else:
        print("No personality traits left.")


def load_personality_trait(personality_traits):
    # displays the personality traits from the ditionary
    if not personality_traits:
        print("No personality traits loaded.")
        return
    else:
        print("Loading personality traits...")
        for trait, description in personality_traits.items():
            print(f"{trait}: {description}")


def save_personality_to_file(traits):
    with open("personality.txt", "w") as file:
        for trait, description in traits.items():
            file.write(f"{trait}: {description}\n")
    print("Personality traits saved to personality.txt")


def askOllama(prompt):
    response = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )
    response_text = ""
    for chunk in response:
        content = chunk['message']['content']
        print(content, end='', flush=True)
        response_text += content
    print("\n")
    return response_text


# initialize ollama with context
ollama.init(model="llama3.2",
            context="You are an AI personality maker that helps users create and manage personality traits for AI bots. You can suggest traits based on user input and save them for future use.")

# Dict to hold personality  traits  where keys are traits and values are descriptions

print("Menu")
print("1. Add Personality Trait")
print("2. Delete Personality Trait")
print("3. Load Personality Trait")
print("4. Save Personality to File")
print("5. Ask Ollama for Personality Suggestions")
print("6. Exit")

while True:
    choice = input("Enter your choice (1-6): ")

    if choice == '1':
        add_personality_trait()

    elif choice == '2':
        delete_personality_trait(personality_traits)

    elif choice == '3':
        load_personality_trait(personality_traits)

    elif choice == '4':
        save_personality_to_file(personality_traits)

    elif choice == '5':
        prompt = input("Enter a prompt for Ollama to suggest personality traits: ")
        askOllama(prompt)

    elif choice == '6':
        print("Exiting the program.")
        break

    else:
        print("Invalid choice. Please try again.")
