import spacy
import re
import json
import time
from typing import Dict, List, Tuple

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

def extract_phi_info(text: str) -> Dict[str, List[str]]:
    """Extract PHI information from text and return as a dictionary."""
    if not isinstance(text, str):
        return {}
        
    doc = nlp(text)
    phi_info = {
        "names": [],
        "phones": [],
        "emails": [],
        "ssns": [],
        "mrns": [],
        "dates": [],
        "addresses": []
    }

    # Extract named entities
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            clean_name = ent.text.split('\n')[0]
            # Remove any additional text that might be attached
            clean_name = clean_name.split(' Sample')[0]
            clean_name = clean_name.split(' Age')[0]
            # Only add if it's not empty and not already in the list
            if clean_name and clean_name not in phi_info["names"]:
                phi_info["names"].append(clean_name)
        elif ent.label_ == "GPE":
            phi_info["addresses"].append(ent.text)
        elif ent.label_ == "DATE":
            phi_info["dates"].append(ent.text)

    # Extract using regex patterns
    for label, pattern in CUSTOM_PATTERNS.items():
        for match in re.finditer(pattern, text):
            value = match.group()
            if label == "PHONE":
                phi_info["phones"].append(value)
            elif label == "EMAIL":
                phi_info["emails"].append(value)
            elif label == "SSN":
                phi_info["ssns"].append(value)
            elif label == "MRN":
                phi_info["mrns"].append(value)
            elif label in ["DOB", "DATE"]:
                phi_info["dates"].append(value)
    
    return phi_info

def deidentify_text(text: str) -> Tuple[str, Dict[str, List[str]]]:
    """Deidentify text and return both deidentified text and extracted PHI."""
    if not isinstance(text, str):
        return text, {}
        
    doc = nlp(text)
    spans_to_replace = []
    people = []

    phi_info = extract_phi_info(text)

    # Detect named entities (built-in NER)
    for ent in doc.ents:
        if ent.label_ in ["PERSON", "GPE", "DATE"]:
            spans_to_replace.append((ent.start_char, ent.end_char, f"{{{{{ent.label_}}}}}"))
            if ent.label_ in ["PERSON"]:
                people.append(ent)
            
    # Apply regex-based PHI detection
    for label, pattern in CUSTOM_PATTERNS.items():
        for match in re.finditer(pattern, text):
            spans_to_replace.append((match.start(), match.end(), f"{{{{{label}}}}}"))

    # Sort spans in reverse order to avoid messing up indices while replacing
    spans_to_replace.sort(reverse=True, key=lambda x: x[0])

    # Replace spans
    for start, end, replacement in spans_to_replace:
        text = text[:start] + replacement + text[end:]

    return text, phi_info

def process_table_data(table_data: List) -> Tuple[List, Dict[str, List[str]]]:
    """Process table data and return both processed data and extracted PHI."""
    if not isinstance(table_data, list):
        return table_data, {}
        
    processed_data = []
    all_phi_info = {
        "names": [], "phones": [], "emails": [], "ssns": [],
        "mrns": [], "dates": [], "addresses": []
    }

    for row in table_data:
        if isinstance(row, list):
            processed_row = []
            for cell in row:
                if isinstance(cell, str):
                    processed_cell, phi_info = deidentify_text(cell)
                    processed_row.append(processed_cell)
                    # Merge PHI information
                    for key in all_phi_info:
                        all_phi_info[key].extend(phi_info.get(key, []))
                else:
                    processed_row.append(cell)
            processed_data.append(processed_row)
        else:
            processed_data.append(row)

    return processed_data, all_phi_info

def process_json_file(input_file: str, output_file: str) -> Tuple[bool, Dict[str, List[str]]]:
    """Process JSON file and return success status and extracted PHI information."""
    try:
        # Read the JSON file
        start = time.time()
        with open(input_file, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Create a copy of the data to modify
        deidentified_data = data.copy()
        all_phi_info = {
            "names": [], "phones": [], "emails": [], "ssns": [],
            "mrns": [], "dates": [], "addresses": []
        }

        # Process text fields
        if 'text' in deidentified_data:
            deidentified_data['text'], phi_info = deidentify_text(deidentified_data['text'])
            # Merge PHI information
            for key in all_phi_info:
                all_phi_info[key].extend(phi_info.get(key, []))

        # Process pages
        if 'pages' in deidentified_data:
            for page in deidentified_data['pages']:
                if 'text' in page:
                    page['text'], phi_info = deidentify_text(page['text'])
                    # Merge PHI information
                    for key in all_phi_info:
                        all_phi_info[key].extend(phi_info.get(key, []))
                if 'tables' in page:
                    for table in page['tables']:
                        if 'data' in table:
                            table['data'], table_phi = process_table_data(table['data'])
                            # Merge PHI information
                            for key in all_phi_info:
                                all_phi_info[key].extend(table_phi.get(key, []))
    
        # Process tables at root level
        if 'tables' in deidentified_data:
            for table in deidentified_data['tables']:
                if 'data' in table:
                    table['data'], table_phi = process_table_data(table['data'])
                    # Merge PHI information
                    for key in all_phi_info:
                        all_phi_info[key].extend(table_phi.get(key, []))

        # Write the de-identified data to a new JSON file
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(deidentified_data, file, indent=4, ensure_ascii=False)

        print("Successfully completed de-identification of JSON file!")
        conversion_time = time.time() - start
        print(f"Time taken for conversion : {conversion_time}")
        
        # Remove duplicates from PHI information
        for key in all_phi_info:
            all_phi_info[key] = list(set(all_phi_info[key]))
            
        return True, all_phi_info

    except Exception as e:
        print(f"Error during JSON processing: {str(e)}")
        return False, {}

if __name__ == "__main__":
    input_file = "pdf_analysis_result.json"
    output_file = "deidentified_pdf_analysis.json"
    success, phi_info = process_json_file(input_file, output_file)
    if success:
        print("\nExtracted PHI Information:")
        for key, values in phi_info.items():
            if values:
                print(f"\n{key.upper()}:")
                for value in values:
                    print(f"  - {value}")