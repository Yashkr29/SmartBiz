from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..security import hash_pw, verify_pw, make_token, current_user
from .. import models as m, schemas as s

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=s.TokenOut, status_code=201)
def register(body: s.RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(m.User).filter_by(email=email).first():
        raise HTTPException(409, "An account with this email already exists")
    role = "admin" if db.query(m.User).count() == 0 else "staff"  # first account owns the business
    user = m.User(name=body.name, email=email, password_hash=hash_pw(body.password), role=role)
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token": make_token(user), "user": user}

@router.post("/login", response_model=s.TokenOut)
def login(body: s.LoginIn, db: Session = Depends(get_db)):
    user = db.query(m.User).filter_by(email=body.email.lower()).first()
    if not user or not verify_pw(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": make_token(user), "user": user}

@router.get("/me", response_model=s.UserOut)
def me(user: m.User = Depends(current_user)):
    return user
