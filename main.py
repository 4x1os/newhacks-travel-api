import os
from google import genai
import csv
file_path = "travel_data.csv"
parsed_data = []
with open(file_path, mode='r', encoding='utf-8') as file:
    csv_reader = csv.reader(file)
    header = next(csv_reader)
    print("Header:", header)
    for row in csv_reader:
        parsed_data.append(row)
