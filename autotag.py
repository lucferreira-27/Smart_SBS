from openai import OpenAI
client = OpenAI(api_key="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")
import json

# Define your custom function
custom_function = {
    'name': 'extract_tags',
    'description': 'Extract tags from a Q&A of One Piece authors and readers',
    'parameters': {
        'type': 'object',
        'properties': {
            'text': {
                'type': 'string',
                'description': 'The text to extract tags from.'
            }
        }
    }
}

sample = """You are an advanced AI assistant created by Anthropic to extract meaningful tags from text related to the world of One Piece. When given a passage of text, your mission is to identify relevant tags within 4 categories:

Characters - Recognize any characters mentioned, like Luffy, Nami, etc.
Places - Identify any locations referenced, like a village or island.
Topics - Pinpoint central themes being discussed, like Devil Fruits, Food, Places, Ship ,relantionship etc.
Emotions - Discern any emotional tones conveyed through the text, whether it is sad, happy, neutro etc.
Importance - if it is funny, perverted, silly, relevant, irrelevant, also if the author avoids to answer the question, or pretend to dont know etc.

Your goal is to comprehend the significance of these tags within the narrative of One Piece. Importance should be never empty.
The output need to be in format json, {tags: {characters:[], places:[], emotions:[], topics:[],importance:[]}}"""


sampe_2 = """
    Break the questions and answer as one sentece to be easy understand. Return in json {text:""} Max size of 25 words. What is about? 
"""

question = """
D: "Huh? Huuuh?? The Baratie has gotten bigger in chapter 902!!! Is their business expanding? Hooray! I want too tell Sanji-kun! by Chopa"
O: "Yep. That's right! In the cover story of chapter 625 the Baratie was in the middle of being renovated and this is its final form! Furthermore, the Meat Master Carne and the Patissier Patty run separate chain restaurants, so there are now 3 "Sea Faring Restaurant Baraties".{{-}}"
"""

# Call the GPT-3.5 API with the function
response = client.chat.completions.create(
  model="gpt-3.5-turbo-1106",
  #response_format={ "type": "json_object" },
  messages=[
      {"role": "system", "content": f"{sample}"},
      {"role": "user", "content": f"{question}"}
  ],
)

print(response.choices[0].message.content)