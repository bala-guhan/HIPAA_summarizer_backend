import json

with open('data/deidentified_pdf_analysis.json', 'r') as file:
    data = json.load(file)

try:
    print(data['text'])
except Exception as e:
    print(e)