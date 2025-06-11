import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
import traceback
from prompt_templates import structure_prompt_template, summary_prompt_template

load_dotenv()
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

llama = ChatGroq(
    api_key=GROQ_API_KEY,
    model='llama-3.3-70b-versatile',
    temperature=0.7
)

gemini = ChatGoogleGenerativeAI(
    google_api_key=GEMINI_API_KEY,
    model='gemini-2.0-flash',
    temperature=0.7
)

def get_summary(filepath):
    try:
        if filepath.endswith('.json'):
            pass
        else:
            raise TypeError
        
        with open(filepath, 'r') as file:
            data = json.load(file)
            RAW_DATA = data['text']
            
            # Create the prompt template
            raw2str_prompt = ChatPromptTemplate.from_template(structure_prompt_template(RAW_DATA))
            # Create the chain
            raw2str_chain = raw2str_prompt | gemini
            # Invoke the chain with the input variable
            STRUCTURED_DATA = raw2str_chain.invoke({"raw_data": RAW_DATA})

            # Create the summary prompt template
            str2sum_prompt = ChatPromptTemplate.from_template(summary_prompt_template(STRUCTURED_DATA.content))
            # Create the chain
            str2sum_chain = str2sum_prompt | gemini
            # Invoke the chain with the input variable
            summary = str2sum_chain.invoke({"structured_data": STRUCTURED_DATA}).content
            
            return summary

    except Exception as e:
        print(str(e))
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print(get_summary('deidentified_pdf_analysis.json'))