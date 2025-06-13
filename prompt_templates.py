def structure_prompt_template(RAW_DATA: str, CRITIQUE_FEEDBACK: str = None) -> str:
    base_prompt = """
    You are a medical data extractor with strict guidelines for data handling.
    
    IMPORTANT RULES:
    1. NEVER interpret or make assumptions about the data
    2. If a value is masked (appears as {{PERSON}}, {{DATE}}, etc.), DO NOT include it in the summary
    3. Only include values that are explicitly present in the source data
    4. Always include reference ranges when they are provided
    5. Do not add any interpretive statements or conclusions
    6. If a value is missing its reference range, mark it as "Reference range not provided"
    7. Format all values exactly as they appear in the source data
    
    For each parameter, provide:
    - test_name
    - value (only if explicitly present and not masked)
    - unit (only if explicitly present)
    - reference_range (only if explicitly provided)
    - status (only if explicitly stated in the source)

    Input Data:
    {raw_data}
    """

    if CRITIQUE_FEEDBACK:
        critique_section = f"""
        Previous Critique Feedback:
        {CRITIQUE_FEEDBACK}
        
        Please ensure to:
        1. Do not include masked values
        2. Do not make assumptions about normal ranges
        3. Do not add interpretive statements
        4. Only include data that is explicitly present in the source
        """
        base_prompt += critique_section

    
    return base_prompt

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

def validation_prompt_template(source_data: str, generated_summary: str) -> str:
    return """
You are a helpful and precise medical assistant.

Your task is to validate whether the **LLM-generated summary** accurately reflects the information in the **source data**. 
Personal identifiers in the source data have been masked to prevent data leakage.

### Instructions:
- Carefully compare the generated summary against the source data.
- Determine whether the summary contains any **hallucinated or fabricated content** not present in the source.
- **Do not flag omissions or missing details unless the summary adds incorrect or unsupported information.**
- If the source data contains errors, **ignore them**; your job is only to verify that the summary stays true to the source content.
- A summary that is factually consistent with the source—even if not exhaustive—is considered valid.

### Your Response Should Include:
- A simple **YES** or **NO** based on the comparison.
- A **one-line explanation** justifying your decision.

---

### Source Data:
{source_data}

---

### Generated Summary:
{generated_summary}

---

### Output Format:
If the summary is valid:
<Yes, the generated summary matches the content of the source data and does not include any hallucinated or redundant information.>

If the summary includes false or unsupported data:
<No, the generated summary includes hallucinated or unsupported information. Here are the issues: ...>
"""
