from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
import time
from openai import RateLimitError

# Load environment variables from .env
load_dotenv()

# Access the API_KEY
#base_url="https://api.perplexity.ai",api_key="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"
client = OpenAI()

GOOGLE_API_KEY= os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)


def read_json_file(file_path):
   with open(file_path, 'r', encoding='utf-8') as file:
       data = json.load(file)
   return data

def clean_json_string(json_string):
    start_index = json_string.find('{')  # Find the first occurrence of {
    end_index = json_string.rfind('}')  # Find the last occurrence of }
    cleaned_json_string = json_string[start_index:end_index+1]  # Extract the substring between these indices
    return cleaned_json_string
    

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
   return """You are an AI task to extract meaningful tags from text related to the world of One Piece from SBS. When given a passage of text, your mission is to identify relevant tags within 4 categories:

   Remeber "O:" means Eiichiro Oda, the author. and "D:" means reader
   Characters - Recognize any characters mentioned, like Luffy, Nami, etc.
   Places - Identify any locations referenced, like a village or island.
   Topics - Pinpoint central themes being discussed, like Devil Fruits, Fan theory,Food, Places, Ship, relantionship, family, Oda's personal life etc.
   Emotions - Discern any emotional tones conveyed through the text, whether it is sad, happy, neutro etc. Always return emotions, this field should never be empty.
   Importance - if it is funny (joke), perverted, silly, relevant, irrelevant, also if the author avoids to answer the question, or pretend to dont know etc.
   Is Character Insertion -  A character insertion is when a character shows up to answer a question or be part of the conversetion, for example, "I don't know, let me ask Nami. Nami: Yes, I love money." This demonstrates a true character insertion. Use a boolean to fill this field..
   Your goal is to comprehend the significance of these tags within the narrative of One Piece. Importance (very_hight,hight,normal,low) should be never empty, a example of hight is when in the conversetion the author explain something to the reader or a confirmation of something.
   The output need to be in format json, {tags: {characters:["moneky_d_luffy"], places:["dressrosa","wano"], emotions:["happy","funny"], topics:["kaido_backstory","devil_fruit"],importance:["hight"], isCharacterInsertion: false (boolean) }}
   Never include more then the json object in your response.
   Only output accept in json object are accept.
   """

def create_qa_summary_about():
    return """
        Summarize the Q&A of One Piece (SBS) by breaking the questions and answers into one easy to understand sentence; 
        do not add information not present in the Q&A. Remeber "O:" means Eiichiro Oda, the author. and "D:" means reader; 
        return a JSON object containing the text summary in 30 words or less. {text: ""}.
        Never include more then the json object in your response.
        Only output accept is for example {"text": "Oda starts his Q&A session, mentioning he's entering a 'slump' stage." }.
    """    

def create_question():
   return """
   D: "Huh? Huuuh?? The Baratie has gotten bigger in chapter 902!!! Is their business expanding? Hooray! I want too tell Sanji-kun!"
   O: "Yep. That's right! In the cover story of chapter 625 the Baratie was in the middle of being renovated and this is its final form! Furthermore, the Meat Master Carne and the Patissier Patty run separate chain restaurants, so there are now 3 "Sea Faring Restaurant Baraties".{{-}}"
   """


def extract_tags(file_path,volume):
    print(f"Extracting tags from Volume ... {volume}")
    if os.path.exists(f"./sbs_tags/sbs_{volume}.json"):
        with open(f'./sbs_tags/sbs_{volume}.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
    else:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    
    current_limit_retries = TOTAL_RATE_LIMIT_RETRIES = 65
    for item in data:
        for qa_item in item["qa"]:
            error_message = ""
            if "tags" in qa_item and "summary" in qa_item:
                continue
            qa_text = format_qa(qa_item)
            if(error_message):
                qa_text += error_message
            print(f"Text: \n {qa_text}")
            retries = 3
            for i in range(retries):
                try:
                    response = call_api(qa_text)
                    qa_item["tags"] = response["tags"]
                    qa_item["summary"] = response["summary"]
                    print(f'Summary: {qa_item["summary"]}')
                    break  # If the API call is successful, break the loop
                except RateLimitError:
                    print(f"Rate limit exceeded. Waiting for 1 minute before retrying ({i+1}/{current_limit_retries})...")
                    retries = retries - 1
                    time.sleep(30)  # Wait for 1 minute before retrying
                    if i >= current_limit_retries - 1:
                        raise  # If still rate limited after maximum retries, raise the exception
                except Exception as e:
                    print(f"Error on API call: {e}. Retrying ({i+1}/{retries})...")
                    qa_text += f"\n [REMEBER TO RETURN VALID JSON error {e}. Be sure JSON is properly formatted and all special characters and quotation marks are handled correctly]"
                    print(qa_text)
                    time.sleep(60)  # Wait for 2 seconds before retrying
            # Save the current data to a JSON file after each iteration
            with open(f'./sbs_tags/sbs_{volume}.json', 'w') as file:
                json.dump(data, file, indent=4)
                print(f"Saving current Volume data {volume}")
            current_limit_retries = TOTAL_RATE_LIMIT_RETRIES
            error_message = ""
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
   response = {}
   auto_tag_prompt = create_auto_tag_prompt()
   
   qa_summary_prompt = create_qa_summary_about()
   summary_content = send_request(qa_summary_prompt,question,model="openai")  
   summary_content = clean_json_string(summary_content)
   print(summary_content)
   response["summary"] = json.loads(summary_content)["text"]
   tag_content =  send_request(auto_tag_prompt,question,model="openai")
   tag_content = clean_json_string(tag_content)
   response["tags"] = json.loads(tag_content)["tags"]

   return response

def openai(prompts=[],model="gpt-3.5-turbo-1106"):
    system_prompt = prompts[0]
    user_prompt = prompts[1]
    
    response = client.chat.completions.create(
     model=model,
     messages=[
         {"role": "system", "content": f"{system_prompt}"},
         {"role": "user", "content": f"{user_prompt}"}
     ],
    response_format={ "type": "json_object" },
   )
    return response.choices[0].message.content

def google(prompts=[],model="gemini-pro"):
    genaiPro = genai.GenerativeModel(model)
    merged_prompt = f"{prompts[0]}\n{prompts[1]}" 
    response = genaiPro.generate_content(merged_prompt)
    return response.text

def send_request(system_prompt,user_prompt,model):
    if("openai" == model):
        return openai([system_prompt,user_prompt])
    return google([system_prompt,user_prompt])
def main():
    for file in os.listdir('sbs_json'):
        if file.startswith('qa_volume_') and file.endswith('.json'):
            volume = file.split('_')[2].split('.')[0]
            print(f"SBS Volume {volume}")
            data = extract_tags(os.path.join('sbs_json', file), volume)
            with open('output.json', 'w') as file:
                json.dump(data, file, indent=4)
# Call the main function to start the program
if __name__ == "__main__":
   main()
