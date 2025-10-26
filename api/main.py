import os
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from typing import List
import json
import csv 
from mangum import Mangum
from fastapi import HTTPException
from fastapi import FastAPI
import datetime

GENERATED_ATTRACTIONS_FILE = "generated_attractions.csv"
INFO_FILE = os.path.join("/tmp", "info.csv")
app = FastAPI()


load_dotenv()

client = genai.Client()

class Attraction(BaseModel):
    Title: str
    Location: str
    Description: str
    Tags: str 
    Hazards: str 
    Considerations: str
    Alternatives: str

class AttractionList(BaseModel):
    """The root object containing the list of all attractions."""
    attractions: List[Attraction]

def parse_csv(filename: str = INFO_FILE) -> List[dict[str, any]]:
    with open(filename, mode='r', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)
        print("Header:", header)
        for row in csv_reader:
            print(row)

def store_data_to_csv(project: str, prompt: str, filename: str = INFO_FILE) -> None:
    if not project or not prompt:
        return
    file_exists = os.path.exists(filename)
    
    data_row = {
        'project': project,
        'prompt': prompt,
        'timestamp': datetime.datetime.now().isoformat()
    }

    FIELD_NAMES = ['project', 'prompt', 'timestamp']

    try:
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELD_NAMES)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data_row)
    except Exception as e:
        print(f"Error writing to CSV file {filename}: {e}")

def generate_content(keyline: str, main_prompt: str) -> None:
    with open(INFO_FILE, 'rb') as f:
        sample_doc = client.files.upload(
            file=f,
            config=dict(
                mime_type='text/csv'
            )
        )
    prompt = (
        "Based on the context file and your general knowledge, "
        f"generate a list of the 5 best places to visit in {keyline}."
        "The output MUST strictly follow the provided JSON schema."
        f"Assume a customer is asking you information regarding the place with prompt '{main_prompt}'"
        "and give the best results you can regarding that prompt. If you cannot find any information"
        f"on the prompt given, use the best places to visit in {keyline} given the CSV file attached based on recent search history."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[sample_doc, prompt],
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AttractionList,
        )
    )

    client.files.delete(name=sample_doc.name)
    data = json.loads(response.text)
    attractions_list = data.get('attractions', [])
    return attractions_list


@app.get('/')
def testidea():
    return {'message': 'Hello from FastAPI!'}

@app.get('/testapi/')
def get_attraction_results(key_project: str, prompt: str):
    try:
        store_data_to_csv(key_project, prompt, INFO_FILE)
        data = generate_content(key_project, prompt)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

handler = Mangum(app)