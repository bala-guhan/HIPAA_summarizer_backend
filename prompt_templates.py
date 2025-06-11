def structure_prompt_template(RAW_DATA: str) -> str:
    return """
    You are a medical data extractor.
    Given the raw text of a Complete Blood Count (CBC) test report, extract all relevant test parameters into a structured JSON format.
    For each parameter, provide:
    - test_name
    - value
    - unit
    - reference_range (low - high)
    - status ("low", "normal", "high")

    Ignore any non-essential text like headers, page numbers, or doctor's name.
    If reference range is missing, mark it as "unknown".

    Input:
    {raw_data}  

    Output Format (JSON):
    [
        {{
            "test_name": "Hemoglobin",
            "value": 15,
            "unit": "g/dl",
            "reference_range": "13 - 17",
            "status": "normal"
        }},
        ...
    ]
    """

def summary_prompt_template(STRUCTURED_DATA: str) -> str:
    return """
    You are a medical assistant.
    Given the structured data from a CBC report, provide a clear and easy-to-understand summary for a patient.
    Use layman terms and explain what each test means and whether it's in a healthy range or not.
    Mention any mildly or significantly abnormal values and what they may indicate.
    Avoid medical jargon unless necessary.

    Input (JSON):
    {structured_data}
    
    Output:
    A friendly, understandable paragraph explaining the CBC report to the patient.
    """