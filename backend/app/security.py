import os
from datetime import datetime, timedelta, timezone
import bcrypt, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models import User

SECRET = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGO = "HS256"
bearer = HTTPBearer(auto_error=False)

def _pw(p: str) -> bytes: return p.encode()[:72]  # bcrypt only uses (and bcrypt>=5 only accepts) 72 bytes
def hash_pw(p: str) -> str: return bcrypt.hashpw(_pw(p), bcrypt.gensalt()).decode()
def verify_pw(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(_pw(p), h.encode())
    except ValueError:  # malformed stored hash
        return False

def make_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=12)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, SECRET, ALGO)

def current_user(cred=Depends(bearer), db: Session = Depends(get_db)) -> User:
    if cred is None:  # FastAPI's default here is 403; a missing login is a 401 so the app returns to login
        raise HTTPException(401, "Please log in")
    try:
        uid = int(jwt.decode(cred.credentials, SECRET, algorithms=[ALGO])["sub"])
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(401, "User no longer exists")
    return user

def admin_only(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user
