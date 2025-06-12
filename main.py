from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import base64
from pathlib import Path
from extract import extract_pdf_content
from deidentify import process_json_file
from llm_chain import get_summary
from auth import auth_handler, get_current_user
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional, Dict
from datetime import datetime

# Load environment variables
load_dotenv()

# Create data directory if it doesn't exist
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Configure allowed origins
ALLOWED_ORIGINS = [
    
]

app = FastAPI(title="PDF upload API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://hipaa-summarizer.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request validation
class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    email: str
    phone: str
    dob: str
    ssn: str
    role: str = "user"

class LoginCredentials(BaseModel):
    username: str
    password: str

class FileUpload(BaseModel):
    file_data: str

@app.get("/hello")
async def root():
    return {"message": "Server up and running! You got this!"}

@app.post("/register")
async def register(user_data: UserCreate):
    try:
        auth_handler.register_user(
            user_data.username,
            user_data.password,
            {
                "name": user_data.name,
                "email": user_data.email,
                "phone": user_data.phone,
                "dob": user_data.dob,
                "ssn": user_data.ssn
            }
        )
        return JSONResponse(
            content={"message": "User registered successfully"},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"detail": str(e)},
            status_code=400
        )

@app.post("/login")
async def login(user_data: LoginCredentials):
    try:
        # Authenticate with plain credentials
        if auth_handler.authenticate_user(user_data.username, user_data.password):
            token = auth_handler.encode_token(user_data.username)
            return JSONResponse(
                content={
                    "access_token": token,
                    "token_type": "bearer"
                },
                status_code=200
            )
        return JSONResponse(
            content={"detail": "Invalid credentials"},
            status_code=401
        )
    except Exception as e:
        return JSONResponse(
            content={"detail": str(e)},
            status_code=401
        )

@app.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    try:
        auth_handler.logout(current_user["token"])
        return JSONResponse(
            content={"message": "Logged out successfully"},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"detail": str(e)},
            status_code=400
        )

@app.post("/upload")
async def upload(
    file: FileUpload,
    current_user: dict = Depends(get_current_user)
):
    try:
        print("Received file data")
        # Decode base64 file data
        try:
            file_content = base64.b64decode(file.file_data)
            print("File decoded successfully")
        except Exception as decode_error:
            print(f"Decoding error: {str(decode_error)}")
            return JSONResponse(
                content={"detail": f"File decoding failed: {str(decode_error)}"},
                status_code=400
            )
        
        try:
            # PDF data extraction
            result, processing_duration = extract_pdf_content(file_content)
            result["processing_duration"] = processing_duration
            print("PDF extraction completed")
        except Exception as extract_error:
            print(f"PDF extraction error: {str(extract_error)}")
            return JSONResponse(
                content={"detail": f"PDF extraction failed: {str(extract_error)}"},
                status_code=400
            )
        
        try:
            # Use data directory for file storage
            PDF_ANALYSIS_RESULT = DATA_DIR / "pdf_analysis_result.json"
            DEIDENTIFIED_PDF_ANALYSIS = DATA_DIR / "deidentified_pdf_analysis.json"

            with open(PDF_ANALYSIS_RESULT, 'w', encoding='utf-8') as json_file:
                json.dump(result, json_file, indent=4, ensure_ascii=False)
            print("Analysis result saved")
            
            # De identification of the extracted content
            success, phi_info = process_json_file(str(PDF_ANALYSIS_RESULT), str(DEIDENTIFIED_PDF_ANALYSIS))
            print(f"PHI Info : {phi_info}")
            if not success:
                return JSONResponse(
                    content={"detail": "Failed to process the file"},
                    status_code=400
                )
            print("De-identification completed")

            # Get user data from the database or session
            user_data = auth_handler.get_user_data(current_user["username"])
            if not user_data:
                return JSONResponse(
                    content={"detail": "User data not found"},
                    status_code=400
                )

            # Verify PHI information
            verification_results = {
                "name_match": any(name.lower() in user_data["name"].lower() for name in phi_info["names"]),
                "email_match": any(email.lower() == user_data["email"].lower() for email in phi_info["emails"]),
                "phone_match": any(phone == user_data["phone"] for phone in phi_info["phones"]),
                "dob_match": any(dob == user_data["dob"] for dob in phi_info["dates"]),
                "ssn_match": any(ssn == user_data["ssn"] for ssn in phi_info["ssns"])
            }

            # Check if any PHI matches
            if not any(verification_results.values()):
                return JSONResponse(
                    content={"detail": "No matching PHI information found. This document may not belong to you."},
                    status_code=403
                )

            summary = get_summary(str(DEIDENTIFIED_PDF_ANALYSIS))
            print("Summary generated")

            return JSONResponse(
                content={
                    "summary": summary,
                    "phi_verification": verification_results
                },
                status_code=200
            )

        except Exception as process_error:
            print(f"Processing error: {str(process_error)}")
            return JSONResponse(
                content={"detail": f"Processing failed: {str(process_error)}"},
                status_code=400
            )
    
    except Exception as e:
        print(f"Unexpected error in upload: {str(e)}")
        return JSONResponse(
            content={"detail": f"Upload Failed: {str(e)}"},
            status_code=500
        )

# Dependency for protected routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Dependency to get current authenticated user"""
    try:
        username = auth_handler.decode_token(credentials.credentials)
        return {"username": username}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )


