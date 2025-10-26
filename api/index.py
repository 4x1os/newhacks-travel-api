import os
from dotenv import load_dotenv
from google import genai
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import io
import httpx
from pydantic import BaseModel
from typing import List
import json
import csv 
from mangum import Mangum
from fastapi import HTTPException
from fastapi import FastAPI
app = FastAPI()

load_dotenv()
client = genai.Client()

INFO_FILE = './info.csv'

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
    with open('./generated_attractions.csv', mode='r', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)
        print("Header:", header)
        for row in csv_reader:
            print(row)

def store_data_to_csv(project: str, prompt: str, filename: str = INFO_FILE) -> None:
    if not project or not prompt:
        return
    file_exists = os.path.exists(filename)
    
    import datetime
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
        f"generate a list of the 5 best places to visit in ${keyline}."
        "The output MUST strictly follow the provided JSON schema."
        f"Assume a customer is asking you information regarding the place with ${main_prompt}"
        "If the prompt is irrelevant, ignore the prompt and base your findings off"
        f"of the the top 5 best places to visit in ${keyline}"
        "Use the CSV file attached as prior search history and use it to base user interest."
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
    return {"Hello": "World"}

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


# --- CSV CONVERSION AND SAVING ---

    # data = json.loads(response.text)
    # attractions_list = data.get('attractions', [])

    # if not attractions_list:
    #     print("Model returned an empty list of attractions.")
    # else:
    #     # 8. Define the output file and use Python's built-in csv module
    #     OUTPUT_CSV_PATH = 'generated_attractions.csv'
        
    #     # Extract keys from the first item to use as column headers
    #     fieldnames = list(attractions_list[0].keys())

    #     with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as csvfile:
    #         writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
    #         writer.writeheader() # Write the headers
    #         writer.writerows(attractions_list) # Write the rows

handler = Mangum(app)