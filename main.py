from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
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
import threading

# Load environment variables
load_dotenv()

# Create data directory if it doesn't exist
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI(title="PDF upload API")

ALLOWED_ORIGINS = ["http://localhost:3000", "https://hipaa-summarizer.vercel.app/"]
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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

# Audit log file path
AUDIT_LOG_FILE = DATA_DIR / "audit_log.json"
AUDIT_LOG_LOCK = threading.Lock()

def append_audit_log(entry):
    with AUDIT_LOG_LOCK:
        try:
            if AUDIT_LOG_FILE.exists():
                with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
        except Exception:
            logs = []
        logs.append(entry)
        with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

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
            append_audit_log({
                "event": "login",
                "username": user_data.username,
                "timestamp": datetime.utcnow().isoformat()
            })
            return JSONResponse(
                content={
                    "access_token": token,
                    "token_type": "bearer"
                },
                status_code=200
            )
        append_audit_log({
            "event": "login_failed",
            "username": user_data.username,
            "timestamp": datetime.utcnow().isoformat()
        })
        return JSONResponse(
            content={"detail": "Invalid credentials"},
            status_code=401
        )
    except Exception as e:
        append_audit_log({
            "event": "login_error",
            "username": user_data.username,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        })
        return JSONResponse(
            content={"detail": str(e)},
            status_code=401
        )

@app.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    try:
        auth_handler.logout(current_user["token"])
        append_audit_log({
            "event": "logout",
            "username": current_user["username"],
            "timestamp": datetime.utcnow().isoformat()
        })
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
    async def event_stream():
        try:
            yield json.dumps({"progress": "Received file data"}) + "\n"
            # Decode base64 file data
            try:
                file_content = base64.b64decode(file.file_data)
                yield json.dumps({"progress": "File decoded successfully"}) + "\n"
            except Exception as decode_error:
                yield json.dumps({"progress": f"File decoding failed: {str(decode_error)}", "error": True}) + "\n"
                return
            
            try:
                # PDF data extraction
                result, processing_duration = extract_pdf_content(file_content)
                result["processing_duration"] = processing_duration
                yield json.dumps({"progress": "PDF extraction completed"}) + "\n"
            except Exception as extract_error:
                yield json.dumps({"progress": f"PDF extraction failed: {str(extract_error)}", "error": True}) + "\n"
                return
            
            try:
                # Use data directory for file storage
                PDF_ANALYSIS_RESULT = DATA_DIR / "pdf_analysis_result.json"
                DEIDENTIFIED_PDF_ANALYSIS = DATA_DIR / "deidentified_pdf_analysis.json"

                with open(PDF_ANALYSIS_RESULT, 'w', encoding='utf-8') as json_file:
                    json.dump(result, json_file, indent=4, ensure_ascii=False)
                yield json.dumps({"progress": "Analysis result saved"}) + "\n"
                
                # De identification of the extracted content
                success, phi_info = process_json_file(str(PDF_ANALYSIS_RESULT), str(DEIDENTIFIED_PDF_ANALYSIS))

                if not success:
                    yield json.dumps({"progress": "Failed to process the file", "error": True}) + "\n"
                    return
                yield json.dumps({"progress": "De-identification completed"}) + "\n"

                # Get user data from the database or session
                user_data = auth_handler.get_user_data(current_user["username"])
                if not user_data:
                    yield json.dumps({"progress": "User data not found", "error": True}) + "\n"
                    return

                # Verify PHI information
                verification_results = {
                    "name_match": any(name.lower() in user_data["name"].lower() for name in phi_info["names"]),
                    "email_match": any(email.lower() == user_data["email"].lower() for email in phi_info["emails"]),
                    "phone_match": any(phone == user_data["phone"] for phone in phi_info["phones"]),
                    "dob_match": any(dob == user_data["dob"] for dob in phi_info["dates"]),
                    "ssn_match": any(ssn == user_data["ssn"] for ssn in phi_info["ssns"])
                }
                # Check if any PHI matches
                is_own_record = any(verification_results.values())
                append_audit_log({
                    "event": "upload",
                    "username": current_user["username"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "is_own_record": is_own_record,
                    "phi_verification": verification_results
                })
                if not is_own_record:
                    yield json.dumps({"progress": "No matching PHI information found. This document may not belong to you.", "error": True}) + "\n"
                    return

                yield json.dumps({"progress": "PHI verified"}) + "\n"

                # Generate summary only after verification
                summary = get_summary(str(DEIDENTIFIED_PDF_ANALYSIS))
                yield json.dumps({"progress": "Summary generated", "summary": summary, "phi_verification": verification_results, "done": True}) + "\n"

            except Exception as process_error:
                yield json.dumps({"progress": f"Processing failed: {str(process_error)}", "error": True}) + "\n"
                return
        except Exception as e:
            yield json.dumps({"progress": f"Upload Failed: {str(e)}", "error": True}) + "\n"
            return
    return StreamingResponse(event_stream(), media_type="text/event-stream")

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


