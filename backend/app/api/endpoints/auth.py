import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.db.database import get_db
from app.db.models.user import User

router = APIRouter()


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: uuid.UUID
    username: str
    display_name: str | None = None
    avatar_url: str | None = None


class UserProfile(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str | None = None
    avatar_url: str | None = None

    class Config:
        from_attributes = True


@router.post("/signup", response_model=Token)
@limiter.limit("5/minute")
def signup(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.username == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    new_user = User(
        username=user_data.email, password_hash=get_password_hash(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate token
    access_token = create_access_token(data={"sub": new_user.username})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=new_user.id,
        username=new_user.username,
        display_name=new_user.display_name,
        avatar_url=new_user.avatar_url,
    )


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # Find user
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    access_token = create_access_token(data={"sub": user.username})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
    )


@router.get("/me", response_model=UserProfile)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


class ProfileUpdate(BaseModel):
    display_name: str
    avatar_url: str


@router.put("/profile", response_model=UserProfile)
def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.display_name = profile_data.display_name
    current_user.avatar_url = profile_data.avatar_url
    db.commit()
    db.refresh(current_user)
    return current_user


class GoogleLoginRequest(BaseModel):
    credential: str


@router.post("/google", response_model=Token)
@limiter.limit("10/minute")
def google_login(
    request: Request, login_request: GoogleLoginRequest, db: Session = Depends(get_db)
):
    import logging

    try:
        client_id = (
            settings.GOOGLE_CLIENT_ID.strip() if settings.GOOGLE_CLIENT_ID else ""
        )
        idinfo = id_token.verify_oauth2_token(
            login_request.credential,
            google_requests.Request(),
            client_id,
            clock_skew_in_seconds=10,
        )

        email = idinfo.get("email")
        if not email:
            raise ValueError("No email in token")

        user = db.query(User).filter(User.username == email).first()

        if not user:
            user = User(
                username=email, password_hash=get_password_hash(str(uuid.uuid4()))
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        access_token = create_access_token(data={"sub": user.username})
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
        )

    except ValueError as e:
        logging.error(f"Google OAuth Validation Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google credential: {e}",
        )
    except Exception as e:
        logging.error(f"Unexpected error in Google Auth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error during authentication: {e}",
        )
