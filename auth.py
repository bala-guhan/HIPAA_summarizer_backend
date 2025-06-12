import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
import bcrypt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
import jwt

# Create data directory if it doesn't exist
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Constants
USERS_DB_FILE = DATA_DIR / "users.json"
SESSIONS_DB_FILE = DATA_DIR / "sessions.json"
TOKEN_EXPIRY_HOURS = 24

# Initialize security
security = HTTPBearer()

class AuthHandler:
    def __init__(self):
        self.secret = "YOUR_SECRET_KEY"  # In production, use a secure secret key
        self.algorithm = "HS256"
        self.users = self._load_users()
        self.sessions_db = self._load_sessions()
        
    def _load_users(self):
        try:
            with open(USERS_DB_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _load_sessions(self) -> Dict:
        """Load sessions from JSON file or create if not exists"""
        if SESSIONS_DB_FILE.exists():
            with open(SESSIONS_DB_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_users(self):
        """Save users to JSON file"""
        with open(USERS_DB_FILE, 'w') as f:
            json.dump(self.users, f, indent=4)
    
    def _save_sessions(self):
        """Save sessions to JSON file"""
        with open(SESSIONS_DB_FILE, 'w') as f:
            json.dump(self.sessions_db, f, indent=4)
    
    def get_user_data(self, username: str) -> dict:
        """
        Retrieve user data from the users database.
        
        Args:
            username (str): The username to look up
            
        Returns:
            dict: User data including name, email, phone, dob, and ssn
        """
        if username not in self.users:
            return None
            
        user = self.users[username]
        return {
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
            "dob": user.get("dob", ""),
            "ssn": user.get("ssn", "")
        }
    
    def verify_password(self, plain_password, hashed_password):
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    
    def get_password_hash(self, password):
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    def encode_token(self, user_id):
        payload = {
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow(),
            'sub': user_id
        }
        return jwt.encode(
            payload,
            self.secret,
            algorithm=self.algorithm
        )
    
    def decode_token(self, token):
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm]
            )
            return payload['sub']
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail='Signature has expired'
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=401,
                detail='Invalid token'
            )
    
    def register_user(self, username: str, password: str, user_data: dict):
        if username in self.users:
            raise HTTPException(
                status_code=400,
                detail='Username already exists'
            )
        
        hashed_password = self.get_password_hash(password)
        self.users[username] = {
            "password": hashed_password,
            "name": user_data.get("name", ""),
            "email": user_data.get("email", ""),
            "phone": user_data.get("phone", ""),
            "dob": user_data.get("dob", ""),
            "ssn": user_data.get("ssn", "")
        }
        self._save_users()
        return {"message": "User registered successfully"}
    
    def authenticate_user(self, username: str, password: str):
        if username not in self.users:
            return False
        if not self.verify_password(password, self.users[username]["password"]):
            return False
        return True
    
    def verify_token(self, token: str) -> Dict:
        """Verify session token and return user info"""
        if token not in self.sessions_db:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        session = self.sessions_db[token]
        if datetime.fromisoformat(session["expires_at"]) < datetime.now():
            del self.sessions_db[token]
            self._save_sessions()
            raise HTTPException(status_code=401, detail="Token expired")
        
        return session
    
    def logout(self, token: str):
        """Invalidate session token"""
        if token in self.sessions_db:
            del self.sessions_db[token]
            self._save_sessions()

# Create global auth handler instance
auth_handler = AuthHandler()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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