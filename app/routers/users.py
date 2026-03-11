from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas, models
from app.auth import verify_password, create_access_token, require_current_user
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
async def register(user_data: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    if await crud.get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    if await crud.get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return await crud.create_user(db, user_data)


@router.post("/login", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user = await crud.get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
async def get_me(current_user: models.User = Depends(require_current_user)):
    return current_user