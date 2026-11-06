from datetime import datetime, timedelta, timezone
import hashlib

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_SECRET_KEY
from app.database import get_db
from app.models import User

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")


def hash_password(password: str) -> str:
    normalized = hashlib.sha256(password.encode()).hexdigest().encode()
    return bcrypt.hashpw(normalized, bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        normalized = hashlib.sha256(password.encode()).hexdigest().encode()
        return bcrypt.checkpw(normalized, hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, JWT_SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    try:
        subject = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
        user = db.get(User, int(subject))
        if user is None:
            raise unauthorized
        return user
    except (JWTError, TypeError, ValueError):
        raise unauthorized


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Administrator role required")
    return user
