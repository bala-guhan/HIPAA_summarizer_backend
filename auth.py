import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
import bcrypt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path

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
        self.users_db = self._load_users()
        self.sessions_db = self._load_sessions()
        
    def _load_users(self) -> Dict:
        """Load users from JSON file or create if not exists"""
        if USERS_DB_FILE.exists():
            with open(USERS_DB_FILE, 'r') as f:
                return json.load(f)
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
            json.dump(self.users_db, f, indent=4)
    
    def _save_sessions(self):
        """Save sessions to JSON file"""
        with open(SESSIONS_DB_FILE, 'w') as f:
            json.dump(self.sessions_db, f, indent=4)
    
    def register_user(self, username: str, password: str, role: str = "user") -> bool:
        """Register a new user with hashed password"""
        if username in self.users_db:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        
        # Store user
        self.users_db[username] = {
            "password": hashed.decode(),
            "role": role,
            "created_at": datetime.now().isoformat()
        }
        self._save_users()
        return True
    
    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return session token"""
        if username not in self.users_db:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = self.users_db[username]
        if not bcrypt.checkpw(password.encode(), user["password"].encode()):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Generate session token
        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
        
        # Store session
        self.sessions_db[token] = {
            "username": username,
            "role": user["role"],
            "expires_at": expiry.isoformat()
        }
        self._save_sessions()
        
        return token
    
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

# Dependency for protected routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    return auth_handler.verify_token(credentials.credentials) 