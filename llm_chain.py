import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
import traceback
from prompt_templates import structure_prompt_template, summary_prompt_template
from validation import validation_check

# Load environment variables
load_dotenv()

# Get API keys with better error handling
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Validate API keys
if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY environment variable is not set. "
        "Please create a .env file in the backend directory with your API key: "
        "GEMINI_API_KEY=your_api_key_here"
    )

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY environment variable is not set. "
        "Please create a .env file in the backend directory with your API key: "
        "GROQ_API_KEY=your_api_key_here"
    )

# Initialize language models
try:
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
except Exception as e:
    raise ValueError(f"Failed to initialize language models: {str(e)}")

def get_summary(filepath):
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
            print("Here is the data from the file")
            print(data.keys())
            
        RAW_DATA = data['text']
        RAW_DATA.replace("\n", " ")

        critique_feedback = None  # Initialize critique_feedback for the first iteration

        for i in range(3): # Loop up to 3 times
            print(f"Attempt {i+1} to generate summary...")
            # Create the prompt template, passing critique_feedback if available
            # Assuming structure_prompt_template accepts CRITIQUE_FEEDBACK as a keyword argument
            raw2str_prompt = ChatPromptTemplate.from_template(structure_prompt_template(RAW_DATA, CRITIQUE_FEEDBACK=critique_feedback))
            # Create the chain
            raw2str_chain = raw2str_prompt | gemini
            # Invoke the chain with the input variable
            STRUCTURED_DATA = raw2str_chain.invoke({"raw_data": RAW_DATA, "CRITIQUE_FEEDBACK" : critique_feedback})

            # Create the summary prompt template
            str2sum_prompt = ChatPromptTemplate.from_template(summary_prompt_template(STRUCTURED_DATA.content))
            # Create the chain
            str2sum_chain = str2sum_prompt | gemini
            # Invoke the chain with the input variable
            summary = str2sum_chain.invoke({"structured_data": STRUCTURED_DATA}).content
            
            # Validate the generated summary
            validation_result = validation_check(RAW_DATA, summary)
            print(f"Validation result for attempt {i+1}: {validation_result}")

            if "yes" in validation_result.lower():
                # If validation passes, return the summary
                print("Summary validated successfully!")
                return summary
            else:
                # If validation fails, update critique_feedback for the next iteration
                print("Summary validation failed. Retrying with critique feedback.")
                critique_feedback = validation_result
                # Continue to the next iteration of the loop

        # If the loop finishes without returning a valid summary after 3 attempts
        print("Failed to generate a valid summary after multiple attempts.")
        return "Failed to generate a valid summary after multiple attempts."
        
    except Exception as e:
        error_details = traceback.format_exc()
        return f"Error: {str(e)}\nDetailed traceback:\n{error_details}"
    

if __name__ == "__main__":
    print(get_summary('data/deidentified_pdf_analysis.json'))