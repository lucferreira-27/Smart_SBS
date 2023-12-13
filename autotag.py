from openai import OpenAI
from dotenv import load_dotenv
import os
import json

# Load environment variables from .env
load_dotenv()

# Access the API_KEY
client = OpenAI()


def read_json_file(file_path):
   with open(file_path, 'r', encoding='utf-8') as file:
       data = json.load(file)
   return data


# Define your custom function
def define_custom_function():
   return {
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

def create_auto_tag_prompt():
   return """You are an advanced AI assistant created by Anthropic to extract meaningful tags from text related to the world of One Piece. When given a passage of text, your mission is to identify relevant tags within 4 categories:

   Characters - Recognize any characters mentioned, like Luffy, Nami, etc.
   Places - Identify any locations referenced, like a village or island.
   Topics - Pinpoint central themes being discussed, like Devil Fruits, Fan theory,Food, Places, Ship, relantionship, family, Oda's personal life etc.
   Emotions - Discern any emotional tones conveyed through the text, whether it is sad, happy, neutro etc. Always return emotions, this field should never be empty.
   Importance - if it is funny (joke), perverted, silly, relevant, irrelevant, also if the author avoids to answer the question, or pretend to dont know etc.
   Is Character Insertion -  A character insertion is when a character shows up to answer a question or be part of the conversetion, for example, "I don't know, let me ask Nami. Nami: Yes, I love money." This demonstrates a true character insertion. Use a boolean to fill this field..
   Your goal is to comprehend the significance of these tags within the narrative of One Piece. Importance should be never empty.
   The output need to be in format json, {tags: {characters:[], places:[], emotions:[], topics:[],importance:[], isCharacterInsertion: (boolean) }}"""

def create_qa_summary_about():
    return """
        Summarize the Q&A by breaking the questions and answers into one easy to understand sentence; 
        do not add information not present in the Q&A; 
        return a JSON object containing the text summary in 30 words or less. {text: ""}.
    """    

def create_question():
   return """
   D: "Huh? Huuuh?? The Baratie has gotten bigger in chapter 902!!! Is their business expanding? Hooray! I want too tell Sanji-kun!"
   O: "Yep. That's right! In the cover story of chapter 625 the Baratie was in the middle of being renovated and this is its final form! Furthermore, the Meat Master Carne and the Patissier Patty run separate chain restaurants, so there are now 3 "Sea Faring Restaurant Baraties".{{-}}"
   """

def extract_tags(file_path):
   data = read_json_file(file_path)
   for item in data:
       for qa_item in item["qa"]:
        qa_text = format_qa(qa_item)
        response = call_api(qa_text)
        qa_item["tags"] = response["tags"]
        #qa_item["summary"] = response["summary"]
   return data
def format_qa(qa_item):
    dialog = ""
    for dialog_item in qa_item['dialog']:
        if dialog_item['type'] == 'question':
            if dialog_item["text"] == "N/A":
                continue
            dialog += f'D: "{dialog_item["text"]}"\n'
        elif dialog_item['type'] == 'answer':
            dialog += f'O: "{dialog_item["text"]}"\n'
    return dialog


def call_api(question):
   # custom_function = define_custom_function()
   response = {}
   auto_tag_prompt = create_auto_tag_prompt()
   #qa_summary_prompt = create_qa_summary_about()
   
   tag_content =  send_request(system_prompt=auto_tag_prompt,user_prompt=question)  
   #summary_content = send_request(system_prompt=qa_summary_prompt,user_prompt=question)  
   
   response["tags"] = json.loads(tag_content)["tags"]
   #response["summary"] = json.loads(summary_content)["text"]
   #print(response["summary"])
   return response

def send_request(system_prompt,user_prompt):
    response = client.chat.completions.create(
     model="gpt-3.5-turbo-1106",
     response_format={ "type": "json_object" },
     messages=[
         {"role": "system", "content": f"{system_prompt}"},
         {"role": "user", "content": f"{user_prompt}"}
     ],
   )
    return response.choices[0].message.content

def main():
   data = extract_tags('./qa_volume_107.json')
   with open('output.json', 'w') as file:
    json.dump(data, file, indent=4)
# Call the main function to start the program
if __name__ == "__main__":
   main()
