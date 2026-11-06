from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Friend, User
from app.schemas import RegisterRequest
from app.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/users", tags=["users"])


def public_user(user: User) -> dict:
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "is_admin": user.is_admin}


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(409, "Username already exists")
    user = User(username=payload.username, password_hash=hash_password(payload.password), display_name=payload.display_name or payload.username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return public_user(user)


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    from app.config import ACCESS_TOKEN_EXPIRE_MINUTES

    return {"access_token": create_access_token(user.id), "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return public_user(user)


@router.patch("/profile")
def update_profile(payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    display_name = payload.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip() or len(display_name) > 80:
        raise HTTPException(422, "display_name must contain 1 to 80 characters")
    user.display_name = display_name.strip()
    db.commit()
    return public_user(user)


@router.get("/search")
def search_users(q: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if len(q.strip()) < 2:
        raise HTTPException(400, "Search query must be at least 2 characters")
    return [public_user(item) for item in db.query(User).filter(User.username.ilike(f"%{q[:50]}%"), User.id != user.id).limit(20)]


@router.get("/friends")
def list_friends(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Friend, User).join(User, Friend.friend_id == User.id).filter(Friend.owner_id == user.id).all()
    return [{"id": friend.id, "remark": friend.remark, "user": public_user(target)} for friend, target in rows]


@router.post("/friends/{friend_id}", status_code=201)
def add_friend(friend_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if friend_id == user.id or not db.get(User, friend_id):
        raise HTTPException(404, "User not found")
    existing = db.query(Friend).filter_by(owner_id=user.id, friend_id=friend_id).first()
    if existing:
        return {"id": existing.id, "friend_id": friend_id}
    item = Friend(owner_id=user.id, friend_id=friend_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "friend_id": friend_id}


@router.patch("/friends/{friend_id}")
def update_friend_remark(friend_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(Friend).filter_by(owner_id=user.id, friend_id=friend_id).first()
    if not item:
        raise HTTPException(404, "Friend not found")
    remark = payload.get("remark")
    if not isinstance(remark, str) or len(remark) > 80:
        raise HTTPException(422, "remark must be a string of at most 80 characters")
    item.remark = remark
    db.commit()
    return {"ok": True}


@router.delete("/friends/{friend_id}", status_code=204)
def remove_friend(friend_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(Friend).filter_by(owner_id=user.id, friend_id=friend_id).first()
    if not item:
        raise HTTPException(404, "Friend not found")
    db.delete(item)
    db.commit()
