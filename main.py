from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from extract import extract_pdf_content
from spacy1 import process_json_file
from prompt_engineer import get_summary
from auth import auth_handler, get_current_user
from pydantic import BaseModel

app = FastAPI(title="PDF upload API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request validation
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"

class UserLogin(BaseModel):
    username: str
    password: str

@app.get("/")
async def root():
    return {"message": "Server up and running! Good luck yo!"}

@app.post("/register")
async def register(user_data: UserCreate):
    try:
        auth_handler.register_user(user_data.username, user_data.password, user_data.role)
        return {"message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login")
async def login(user_data: UserLogin):
    try:
        token = auth_handler.authenticate_user(user_data.username, user_data.password)
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    try:
        auth_handler.logout(current_user["token"])
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Read the uploaded file
        content = await file.read()
        
        # PDF data extraction
        result, processing_duration = extract_pdf_content(content)
        result["processing_duration"] = processing_duration
        
        # Write the complete result to a JSON file
        PDF_ANALYSIS_RESULT = "pdf_analysis_result.json"
        DEIDENTIFIED_PDF_ANALYSIS = "deidentified_pdf_analysis.json"

        with open(PDF_ANALYSIS_RESULT, 'w', encoding='utf-8') as json_file:
            json.dump(result, json_file, indent=4, ensure_ascii=False)
        
        # De identification of the extracted content
        process_json_file(PDF_ANALYSIS_RESULT, DEIDENTIFIED_PDF_ANALYSIS)

        summary = get_summary(DEIDENTIFIED_PDF_ANALYSIS)

        return JSONResponse(content=summary)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload Failed: {str(e)}")


