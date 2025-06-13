from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os, json
from langchain.prompts import ChatPromptTemplate
from prompt_templates import validation_prompt_template
load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.7,
    verbose=True
)

def validation_check(source_data: str, generated_summary: str) :
    try:
        if source_data is None:
            raise ValueError
        
        validation_prompt = ChatPromptTemplate.from_template(validation_prompt_template(source_data, generated_summary))
        validation_chain = validation_prompt | gemini

        validation_result = validation_chain.invoke({"source_data" : source_data, "generated_summary" : generated_summary})

        if validation_result.content:
            return validation_result.content
        else:
            return validation_result
    except Exception as e:
        print(e)


if __name__ == "__main__":
    with open("data/generated_summary.txt", 'r') as file:
        generated_summary = file.read()
    validation_check(source_file_path='data/deidentified_pdf_analysis.json', generated_summary=generated_summary)