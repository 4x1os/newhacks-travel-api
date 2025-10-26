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

from fastapi import FastAPI
app = FastAPI()

load_dotenv()
client = genai.Client()

INFO_FILE = './info.csv'

class Attraction(BaseModel):
    Title: str
    Location: str
    Description: str
    Tags: str # Keeping this as a string, but could be a list if needed

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

    # Check if file exists to determine if we need to write the header
    file_exists = os.path.exists(filename)
    
    # Extract keys from the first item to use as column headers

    try:
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile)
            writer.writerow(prompt)
    except Exception as e:
        print(f"Error writing to CSV file {filename}: {e}")

@app.get('/testapi/')
def get_attraction_results(key_project: str, prompt: str):
    data = generate_content(key_project, prompt)
    store_data_to_csv(key_project, prompt, INFO_FILE)
    return data

@app.get('/')
def testidea():
    return {"Hello": "World"}

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
        "generate a list of the 5 best places to visit in ${keyline}. "
        "The output MUST strictly follow the provided JSON schema."
        "Assume a customer is asking you information regarding the place with ${main_prompt}"
        "If the prompt is irrelevant or incoherent, ignore the prompt and base your findings off"
        "of the location given, and the prior info in info.csv."
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