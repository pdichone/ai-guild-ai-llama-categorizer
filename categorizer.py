import os
import asyncio
import random
from ollama import AsyncClient
import json

model = "llama3.2"


# Load the grocery list from a text file
def load_grocery_list(file_path):
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        return []
    with open(file_path, "r") as file:
        items = [line.strip() for line in file if line.strip()]
        print(f"Loaded {len(items)} items from the grocery list.")
    return items


# Function to fetch price and nutrition data for an item
async def fetch_price_and_nutrition(item):
    # Simulate API call delay
    await asyncio.sleep(0.1)
    # Return mock data
    print(f"Fetching data for: {item}")
    return {
        "item": item,
        "price": f"${random.uniform(1, 10):.2f}",
        "calories": f"{random.randint(50, 500)} kcal",
        "fat": f"{random.randint(1, 20)} g",
        "protein": f"{random.randint(1, 30)} g",
    }

    # Updated fetch_recipe function to use the language model


async def fetch_recipe(category, client):

    # Construct the prompt for the model
    recipe_prompt = f"""
As a chef, create a recipe in the "{category}" category.

**Instructions:**

- Provide the recipe as a **valid JSON object**.
- **Do not include any text** before or after the JSON.
- Use **double quotes** for all strings.
- Ensure the JSON is properly formatted.

**JSON Format:**

{{
  "recipe_name": "Recipe Name",
  "ingredients": ["Ingredient 1", "Ingredient 2", "..."],
  "instructions": "Step 1: ... Step 2: ..."
}}

Begin now.
"""

    messages = [{"role": "user", "content": recipe_prompt}]

    # Make the API call to the model with adjusted parameters
    response = await client.chat(
        model=model,
        messages=messages,
        format="json",
    )

    # Parse the model's response
    assistant_message = response["message"]["content"]

    # Print the assistant's response for debugging
    print("\nAssistant's Response:")
    print(assistant_message)

    # Use regex to extract JSON object
    import re

    match = re.search(r"\{.*\}", assistant_message, re.DOTALL)
    if match:
        json_str = match.group(0)
        # Replace single quotes with double quotes
        json_str = json_str.replace("'", '"')
        # Remove any trailing commas before closing braces or brackets
        json_str = re.sub(r",\s*([\]}])", r"\1", json_str)
        try:
            recipe = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            recipe = None
    else:
        print("No valid JSON found in the assistant's response.")
        recipe = None

    # Add the category to the recipe data
    if recipe:
        recipe["category"] = category

    return recipe


async def main():

    # load the grocery list
    grocery_list = load_grocery_list("./data/grocery_list.txt")
    if not grocery_list:
        print("Grocery list is empty or file not found.")
        return

    # Initialize Ollama client
    client = AsyncClient()

    # Define the functions (tools) for the model
    tools = [
        {
            "type": "function",
            "function": {
                "name": "fetch_price_and_nutrition",
                "description": "Fetch price and nutrition data for a grocery item",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item": {
                            "type": "string",
                            "description": "The name of the grocery item",
                        },
                    },
                    "required": ["item"],
                },
            },
        },
    ]

    # Step 1: Categorize items using the model
    categorize_prompt = f"""
You are an assistant that categorizes grocery items.

**Instructions:**

- Return the result **only** as a valid JSON object.
- Do **not** include any explanations, greetings, or additional text.
- Use double quotes ("") for all strings.
- Ensure the JSON is properly formatted.
- The JSON should have categories as keys and lists of items as values.

**Example Format:**

{{
  "Produce": ["Apples", "Bananas"],
  "Dairy": ["Milk", "Cheese"]
}}

**Grocery Items:**

{', '.join(grocery_list)}
"""

    messages = [{"role": "user", "content": categorize_prompt}]

    # First model call: Categorize items
    response = await client.chat(
        model=model,
        messages=messages,
        format="json",
        tools=tools,
    )
    assistant_message = response["message"]["content"]

    # Attempt to parse the assistant's response as JSON
    try:
        # import json  # Moved import statement here

        categorized_items = json.loads(assistant_message)
    except json.JSONDecodeError:
        # If parsing fails, try to extract JSON from the response
        import re

        match = re.search(r"\{[\s\S]*\}", assistant_message)
        if match:
            json_str = match.group(0)
            json_str = json_str.replace(
                "'", '"'
            )  # Replace single quotes with double quotes
            try:
                categorized_items = json.loads(json_str)
            except json.JSONDecodeError:
                print("Failed to parse the JSON from the assistant's response.")
                return
        else:
            print("No valid JSON found in the assistant's response.")
            return

    print("\nCategorized Items:")
    print(json.dumps(categorized_items, indent=2))

    # Flatten the categorized items for processing
    all_items = []
    for items in categorized_items.values():
        all_items.extend(items)

    # Fetch price and nutrition data for each item asynchronously
    item_details = await asyncio.gather(
        *(fetch_price_and_nutrition(item) for item in all_items)
    )

    print("\nPrice and Nutrition Data:")
    for detail in item_details:
        print(json.dumps(detail, indent=2))

    # Choose a random category and fetch a recipe using the model
    random_category = random.choice(list(categorized_items.keys()))
    recipe = await fetch_recipe(random_category, client)

    if recipe:
        print(f"\nRecipe for Category '{random_category}':")
        print(json.dumps(recipe, indent=2))
    else:
        print("Failed to generate a recipe.")

    # Write Final Results to a .txt File in readable text format
    with open("./data/final_results.txt", "w") as f:
        # Write Categorized Items
        f.write("=== Categorized Items ===\n\n")
        for category, items in categorized_items.items():
            f.write(f"{category}:\n")
            for item in items:
                f.write(f" - {item}\n")
            f.write("\n")

        # Write Price and Nutrition Data
        f.write("=== Price and Nutrition Data ===\n\n")
        for detail in item_details:
            f.write(f"Item: {detail['item']}\n")
            f.write(f"Price: {detail['price']}\n")
            f.write(f"Calories: {detail['calories']}\n")
            f.write(f"Fat: {detail['fat']}\n")
            f.write(f"Protein: {detail['protein']}\n")
            f.write("\n")

        # Write Recipe
        if recipe:
            f.write(f"=== Recipe for Category '{random_category}' ===\n\n")
            f.write(f"Recipe Name: {recipe.get('recipe_name', 'N/A')}\n")
            f.write("\nIngredients:\n")
            for ingredient in recipe.get("ingredients", []):
                f.write(f" - {ingredient}\n")
            f.write("\nInstructions:\n")
            f.write(recipe.get("instructions", "N/A") + "\n")
        else:
            f.write("Failed to generate a recipe.\n")

    print("\nFinal results have been written to 'final_results.txt'.")


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
