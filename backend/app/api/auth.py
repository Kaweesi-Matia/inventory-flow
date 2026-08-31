from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.database.connection import get_db
from app.models.user import User
from app.schemas.auth import ChangePassword, TokenResponse, UserLogin, UserOut, UserRegister, to_user_out
from app.services.auth_service import (
    authenticate_user,
    get_current_user,
    issue_token_for_user,
    register_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    user = register_user(db, payload)
    return to_user_out(user)


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm uses "username" as the field name; we treat
    # it as the email, which keeps this compatible with the Swagger UI's
    # built-in "Authorize" button.
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    token = issue_token_for_user(user)
    return TokenResponse(access_token=token, user=to_user_out(user))


@router.post("/login-json", response_model=TokenResponse)
def login_json(payload: UserLogin, db: Session = Depends(get_db)):
    """JSON-body login for the React frontend (the form-encoded /login above exists for Swagger)."""
    user = authenticate_user(db, email=payload.email, password=payload.password)
    token = issue_token_for_user(user)
    return TokenResponse(access_token=token, user=to_user_out(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return to_user_out(current_user)


@router.put("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
