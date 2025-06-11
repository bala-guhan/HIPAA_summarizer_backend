import spacy
import re
import json
import time

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

# Define custom PHI-like patterns (optional extension to spaCy)
CUSTOM_PATTERNS = {
    "PHONE": r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
    "EMAIL": r"[\w\.-]+@[\w\.-]+",
    "SSN": r"\d{3}-\d{2}-\d{4}",
    "MRN": r"\b(?:MRN|Medical Record Number)[:\s]*[\w\d-]+\b",
    "DOB": r"(?:DOB|Date of Birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
    "AGE": r"\d+\s*(?:YRS|years|yrs)",
    "REG_NO": r"Reg\.\s*no\.\s*:\s*\d+",
    "DATE": r"\d{1,2}/\d{1,2}/\d{4}",
    "NAME_PREFIX": r"(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Za-z\s]+"
}

def deidentify_text(text):
    if not isinstance(text, str):
        return text
        
    doc = nlp(text)
    spans_to_replace = []

    # Detect named entities (built-in NER)
    for ent in doc.ents:
        # Exclude ORG from being masked
        if ent.label_ in ["PERSON", "GPE", "DATE"]:  # Removed "ORG" from this list
            spans_to_replace.append((ent.start_char, ent.end_char, f"{{{{{ent.label_}}}}}"))

    # Apply regex-based PHI detection
    for label, pattern in CUSTOM_PATTERNS.items():
        for match in re.finditer(pattern, text):
            spans_to_replace.append((match.start(), match.end(), f"{{{{{label}}}}}"))

    # Sort spans in reverse order to avoid messing up indices while replacing
    spans_to_replace.sort(reverse=True, key=lambda x: x[0])

    # Replace spans
    for start, end, replacement in spans_to_replace:
        text = text[:start] + replacement + text[end:]

    return text

def process_table_data(table_data):
    if not isinstance(table_data, list):
        return table_data
        
    processed_data = []
    for row in table_data:
        if isinstance(row, list):
            processed_row = []
            for cell in row:
                if isinstance(cell, str):
                    # Process each cell's content
                    processed_cell = deidentify_text(cell)
                    processed_row.append(processed_cell)
                else:
                    processed_row.append(cell)
            processed_data.append(processed_row)
        else:
            processed_data.append(row)
    return processed_data

def process_json_file(input_file, output_file):
    try:
        # Read the JSON file
        start = time.time()
        with open(input_file, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Create a copy of the data to modify
        deidentified_data = data.copy()

        # Process text fields
        if 'text' in deidentified_data:
            deidentified_data['text'] = deidentify_text(deidentified_data['text'])

        # Process pages
        if 'pages' in deidentified_data:
            for page in deidentified_data['pages']:
                if 'text' in page:
                    page['text'] = deidentify_text(page['text'])
                if 'tables' in page:
                    for table in page['tables']:
                        if 'data' in table:
                            table['data'] = process_table_data(table['data'])
    
        # Process tables at root level
        if 'tables' in deidentified_data:
            for table in deidentified_data['tables']:
                if 'data' in table:
                    table['data'] = process_table_data(table['data'])

        # Write the de-identified data to a new JSON file
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(deidentified_data, file, indent=4, ensure_ascii=False)

        print("Successfully completed de-identification of JSON file!")
        conversion_time = time.time() - start
        print(f"Time taken for conversion : {conversion_time}")
        return True

    except Exception as e:
        print(f"Error during JSON processing: {str(e)}")
        return False

if __name__ == "__main__":
    input_file = "pdf_analysis_result.json"
    output_file = "deidentified_pdf_analysis.json"
    process_json_file(input_file, output_file)