import requests
from bs4 import BeautifulSoup
import re
import json
import os
import os
import shutil
from urllib.parse import urlparse


def extract_content(text):
    pattern = r'\[\[(.*?)\]\]'
    matches = [(m.start(), m.end(), m.group(1)) for m in re.finditer(pattern, text)]
    return matches

def clean_header(header):
    if "file:" not in header.lower(): 
        return None
    text_header = extract_content(header)[0][2]  # File:SBS106 Header 3.png|thumb|center|400px
    filename_header = text_header.split(':')[1].split('|')[0].strip()
    return filename_header

def categorize_content(block):
    matches = block['dialog']
    files = []
    character_names = []
    normal_links = []
    
    for dialog in matches:
        for start, end, match in dialog['matches']:
            if match.lower().startswith('file:') or match.lower().startswith('image:'):
                file_parts = match.split('|')
                file_name = file_parts[0][5:]  # Remove 'File:' prefix
                size = next((part for part in file_parts if 'px' in part), None)
                if size:
                    size = size.replace('px', '')  # Remove 'px' suffix
                files.append({'file': file_name, 'size': size, 'start': start, 'end': end})
            elif '|' in match:
                text, link_title = match.split('|')
                is_wikipedia = 'wikipedia:' in text
                if is_wikipedia:
                    text = text.replace('wikipedia:', '')
                character_names.append({'text': link_title, 'link_title': '/wiki/' + text, 'is_wikipedia': is_wikipedia, 'start': start, 'end': end})
            else:
                is_wikipedia = 'wikipedia:' in match
                if is_wikipedia:
                    match = match.replace('wikipedia:', '')
                normal_links.append({'text': match, 'link_title': '/wiki/' + match, 'is_wikipedia': is_wikipedia, 'start': start, 'end': end})
    
    return files, character_names, normal_links

def create_qa_block(number, question, answer):
    block = {'number': number, 'dialog': []}
    question_content = {'type': 'question', 'text': question, 'matches': extract_content(question)}
    answer_content = {'type': 'answer', 'text': answer, 'matches': extract_content(answer)}
    block['dialog'].append(question_content)
    block['dialog'].append(answer_content)
    files, character_names, normal_links = categorize_content(block)
    block['files'] = files
    block['character_names'] = character_names
    block['normal_links'] = normal_links
    return block

def add_to_block(block, dialog_type, dialog):
    dialog_content = {'type': dialog_type, 'text': dialog, 'matches': extract_content(dialog)}
    if dialog_content not in block["dialog"]:
        block["dialog"].append(dialog_content)
def get_qa_block(number,blocks):
    for block in blocks:
        if block['number'] == number:
            return block
    return None
def create_qa_blocks(sbs_questions):
    pages_qa_blocks = []
    for i, page in enumerate(sbs_questions['pages'], start=1):
        qa_blocks = []
        page['questions'].sort(key=lambda x: x[0])
        page['answers'].sort(key=lambda x: x[0])
        page_header = None
        if "page_header" in page and page["page_header"] is not None:
            page_header = clean_header(page["page_header"])
        for j, (a_dialogue_number, answer) in enumerate(page['answers']):
            if j < len(page['questions']):
                __, question = page['questions'][j]  
            if question == None:
                question = "N/A"
            block = get_qa_block(a_dialogue_number,qa_blocks)
            if block == None:
               block = create_qa_block(a_dialogue_number, question, answer)
               qa_blocks.append(block)
            else:
                if question != "N/A":
                    add_to_block(block, 'question', question)
                elif answer:
                    add_to_block(block, 'answer', answer)
        pages_qa_blocks.append({"qa":qa_blocks,"page": page["page"],'chapter_number':page["chapter"],'page_header': page_header})    
    return pages_qa_blocks

def save_as_json(qa_blocks, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(qa_blocks, f, ensure_ascii=False, indent=4)

def save_to_file(qa_blocks, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for block in qa_blocks:
            f.write(f"-------Question {block['number']}----------\n")
            for dialog in block['dialog']:
                type = dialog['type']
                text = dialog['text']
                type = "O" if type == "answer" else "D"
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if i == 0:
                        f.write(f"{type}: \"{line.strip()}\"\n")
                    else:
                        f.write(f"         {line.strip()}\n")
            f.write("------------------------\n")

def find_first_header(template):
    first_line = template.split('\n')[0]
    pattern = r'\[\[File:SBS(.*?)\]\]'
    match = re.search(pattern, first_line)
    if match:
        return match.group(0)
    else:
        return None
def find_first_chapter_header(template):
    lines = template.split('\n')
    for line in lines:
        if "==Chapter" in line:
            numbers = re.findall(r'[0-9]+', line)
            if numbers and len(numbers) >= 2:
                chapter = int(numbers[0])
                page = int(numbers[1])
                return chapter, page
    return None, None
    
def get_sbs_template(edit_url,volume):
    json_file_path = f"./sbs_json/qa_volume_{volume}.json"
    if os.path.exists(json_file_path):
        print(f"JSON file for SBS Volume {volume} already exists. Skipping...")
        return
    else:
        response = requests.get(edit_url)
        html_content = response.text

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the #wpTextbox1 element and get its text content
    textbox = soup.find(id="wpTextbox1")
    text = textbox.text.replace("'''","")


    # Ignore everything below "==Site Navigation=="
    text = text.split("==Site Navigation==")[0]
    
    # Create a pattern to match "O:" or "D:" followed by any text until the next "O:" or "D:"
    pattern = re.compile(r"(O:|D:|==.*?==)(.*?)(?=O:|D:|==.*?==|$)", re.DOTALL)

    # Find all matches in the text
    matches = pattern.findall(text)

    # Initialize a list to store the parts of the SBS
    sbs_parts = []

    # Initialize lists to store questions and answers
    questions = []
    answers = []
    announcements = []

    # Initialize a counter for the dialogues
    dialogue_counter = 0
    found_question = False
    page_header = find_first_header(text)
    chapter,page = find_first_chapter_header(text)
    first_header = page_header is not None
    # Iterate over the matches
    for i, match in enumerate(matches):
        
        if match[0] == "O:":
            answers.append((dialogue_counter, match[1].strip()))
            if not found_question:
                questions.append((dialogue_counter, None))
            found_question = False
        # If te match starts with "D:", it's a question
        elif match[0] == "D:":
            found_question = True
            dialogue_counter+= 1
            questions.append((dialogue_counter, match[1].strip()))
        # If the match starts with "==Chapter", it's a new part of the SBS
        elif match[0].startswith("==Chapter"):
            numbers = re.findall(r'[0-9]+', match[0])

            # If there are any questions or answers from the previous part, add them to the list
            if questions or answers:
                if page_header is None:
                    page_header = match[1]
                sbs_parts.append({'announcements': announcements,
                                  'questions': questions, 
                                  'answers': answers,
                                  'page_header':page_header, 
                                  'chapter': chapter, 
                                  'page': page})
                first_header = False
            # Start a new list of questions and answers for the new part
            questions = []
            answers = []
            if not first_header:
                page_header = match[1]
                chapter = numbers[0]
                page = numbers[1]

            

    # Add the questions and answers from the last part
    if questions or answers:
        sbs_parts.append({'announcements': announcements,
                          'questions': questions, 
                          'answers': answers,
                          'page_header': page_header, 
                          'chapter': chapter, 
                          'page': page})
    # Create the final dictionary
    sbs_questions = {'pages': sbs_parts}


    # Save the questions and answers to a file
    qa_blocks = create_qa_blocks(sbs_questions)
    print(f"Getting Images from SBS Volume {volume}...")
    url = edit_url.split('?')[0]
    get_sbs_images(url,qa_blocks,volume)
    #save_to_file(qa_blocks,'output.txt')
    save_as_json(qa_blocks,f"./sbs_json/qa_volume_{volume}.json")
    return qa_blocks

os.makedirs('sbs_json', exist_ok=True)



def get_sbs_images(url, sbs_content, volume):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    base_dir = f'./sbs_images/volume_{volume}'
    os.makedirs(base_dir, exist_ok=True)

    for content in sbs_content:
        page = content.get('page')
        page_dir = os.path.join(base_dir, f'page_{page}')

        header_file_name = content.get('page_header')
        if header_file_name:
            img_tag = soup.find('img', {'data-image-name': header_file_name})
            if img_tag:
                img_url  = img_tag.get('data-src',img_tag.get('src')).split("/revision/")[0]

                # Download the image
                response = requests.get(img_url, stream=True)
                if response.status_code == 200:
                    # Get the file name from the url
                    a = urlparse(img_url)
                    file_name = os.path.basename(a.path)
                    os.makedirs(page_dir, exist_ok=True)
                    # Save the image to the file
                    with open(os.path.join(page_dir, file_name), 'wb') as out_file:
                        shutil.copyfileobj(response.raw, out_file)

        for qa in content.get('qa', []):
            for file in qa.get('files', []):
                file_name = file.get('file')
                img_tag = soup.find('img', {'data-image-name': file_name})
                if img_tag:
                    img_url  = img_tag.get('data-src',img_tag.get('src')).split("/revision/")[0]
                    file['url'] = img_url 

                    # Download the image
                    response = requests.get(img_url, stream=True)
                    if response.status_code == 200:
                        # Get the file name from the url
                        a = urlparse(img_url)
                        file_name = os.path.basename(a.path)
                        os.makedirs(page_dir, exist_ok=True)
                        # Save the image to the file
                        with open(os.path.join(page_dir, file_name), 'wb') as out_file:
                            shutil.copyfileobj(response.raw, out_file)

for volume in range(4, 108):
    url = f"https://onepiece.fandom.com/wiki/SBS_Volume_{volume}?action=edit"
    print(f"Processing SBS Volume {volume}...")
    sbs_content = get_sbs_template(url,volume)

