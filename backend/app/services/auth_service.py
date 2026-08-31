from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password, decode_access_token
from app.database.connection import get_db
from app.models.user import User, UserRole, WarehouseUser
from app.models.warehouse import Warehouse, WarehouseStatus
from app.schemas.auth import UserRegister

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def register_user(db: Session, payload: UserRegister) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists"
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    if payload.role in (UserRole.WAREHOUSE_MANAGER, UserRole.SALES_USER):
        warehouses = db.query(Warehouse).filter(Warehouse.status == WarehouseStatus.ACTIVE).all()
        for warehouse in warehouses:
            db.add(WarehouseUser(user_id=user.id, warehouse_id=warehouse.id))
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This account has been deactivated"
        )
    return user


def issue_token_for_user(user: User) -> str:
    return create_access_token(subject=str(user.id), extra_claims={"role": user.role.value})


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user
