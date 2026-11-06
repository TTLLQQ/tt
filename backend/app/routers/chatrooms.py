import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai_service import run_employee_turn
from app.database import get_db
from app.models import ChatRoom, DigitalEmployee, Friend, Message, RoomEmployee, RoomMember, User
from app.schemas import MessageCreate, RoomCreate
from app.security import get_current_user

router = APIRouter(prefix="/api/chatrooms", tags=["chatrooms"])


@router.get("/employees/catalog")
def employee_catalog(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [{"id": item.id, "name": item.name, "description": item.description} for item in db.query(DigitalEmployee).filter(DigitalEmployee.enabled.is_(True)).all()]


def member_required(db: Session, room_id: int, user_id: int) -> ChatRoom:
    room = db.get(ChatRoom, room_id)
    if not room or not db.query(RoomMember).filter_by(room_id=room_id, user_id=user_id).first():
        raise HTTPException(404, "Room not found")
    return room


@router.post("", status_code=201)
def create_room(payload: RoomCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = ChatRoom(name=payload.name, owner_id=user.id, share_link=secrets.token_urlsafe(24), is_group=True)
    db.add(room)
    db.flush()
    db.add(RoomMember(room_id=room.id, user_id=user.id))
    for friend_id in set(payload.friend_ids):
        friend = db.query(Friend).filter_by(owner_id=user.id, friend_id=friend_id).first()
        if not friend:
            raise HTTPException(403, f"User {friend_id} is not your friend")
        db.add(RoomMember(room_id=room.id, user_id=friend_id))
    for employee_id in set(payload.employee_ids):
        employee = db.get(DigitalEmployee, employee_id)
        if not employee or not employee.enabled:
            raise HTTPException(404, f"Digital employee {employee_id} not found")
        db.add(RoomEmployee(room_id=room.id, employee_id=employee_id))
    db.commit()
    return {"id": room.id, "name": room.name, "share_link": room.share_link}


@router.get("")
def list_rooms(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rooms = db.query(ChatRoom).join(RoomMember, RoomMember.room_id == ChatRoom.id).filter(RoomMember.user_id == user.id).all()
    return [{"id": room.id, "name": room.name, "owner_id": room.owner_id, "is_group": room.is_group, "share_link": room.share_link} for room in rooms]


@router.post("/private/{friend_id}", status_code=201)
def create_private_room(friend_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not db.query(Friend).filter_by(owner_id=user.id, friend_id=friend_id).first():
        raise HTTPException(403, "User is not your friend")
    existing = db.query(ChatRoom).join(RoomMember, RoomMember.room_id == ChatRoom.id).filter(ChatRoom.is_group.is_(False), RoomMember.user_id == user.id).all()
    for room in existing:
        if db.query(RoomMember).filter_by(room_id=room.id, user_id=friend_id).first():
            return {"id": room.id, "name": room.name, "owner_id": room.owner_id, "is_group": room.is_group}
    room = ChatRoom(name=f"私聊-{friend_id}", owner_id=user.id, share_link=secrets.token_urlsafe(24), is_group=False)
    db.add(room)
    db.flush()
    db.add_all([RoomMember(room_id=room.id, user_id=user.id), RoomMember(room_id=room.id, user_id=friend_id)])
    db.commit()
    return {"id": room.id, "name": room.name, "owner_id": room.owner_id, "is_group": room.is_group}


@router.post("/join/{share_link}")
def join_by_share_link(share_link: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = db.query(ChatRoom).filter_by(share_link=share_link).first()
    if not room:
        raise HTTPException(404, "Share link is invalid or expired")
    if not db.query(RoomMember).filter_by(room_id=room.id, user_id=user.id).first():
        db.add(RoomMember(room_id=room.id, user_id=user.id))
        db.commit()
    return {"room_id": room.id, "name": room.name}


@router.post("/{room_id}/share")
def share_room(room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = member_required(db, room_id, user.id)
    return {"share_link": room.share_link}


@router.get("/{room_id}/messages")
def history(room_id: int, limit: int = 100, before_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member_required(db, room_id, user.id)
    query = db.query(Message).filter(Message.room_id == room_id)
    if before_id:
        query = query.filter(Message.id < before_id)
    messages = query.order_by(Message.id.desc()).limit(min(max(limit, 1), 200)).all()
    messages.reverse()
    return [{"id": item.id, "sender_id": item.sender_id, "content": item.content, "type": item.message_type, "created_at": item.created_at.isoformat(), "is_sensitive": item.is_sensitive} for item in messages]


@router.post("/{room_id}/messages", status_code=201)
async def send_message(room_id: int, payload: MessageCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member_required(db, room_id, user.id)
    message = Message(room_id=room_id, sender_id=user.id, content=payload.content, message_type=payload.message_type)
    db.add(message)
    db.commit()
    db.refresh(message)
    result = {"id": message.id, "room_id": room_id, "sender_id": message.sender_id, "content": message.content, "type": message.message_type, "created_at": message.created_at.isoformat()}
    from app.main import manager

    await manager.broadcast(room_id, result)
    return result


@router.post("/{room_id}/members/{member_id}", status_code=201)
def add_member(room_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = member_required(db, room_id, user.id)
    if room.owner_id != user.id:
        raise HTTPException(403, "Only the room owner can add members")
    if not db.get(User, member_id):
        raise HTTPException(404, "User not found")
    if not db.query(RoomMember).filter_by(room_id=room_id, user_id=member_id).first():
        db.add(RoomMember(room_id=room_id, user_id=member_id))
        db.commit()
    return {"ok": True}


@router.delete("/{room_id}/members/{member_id}", status_code=204)
def remove_member(room_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = member_required(db, room_id, user.id)
    if room.owner_id != user.id:
        raise HTTPException(403, "Only the room owner can remove members")
    if member_id == room.owner_id:
        raise HTTPException(400, "The room owner cannot remove themselves")
    member = db.query(RoomMember).filter_by(room_id=room_id, user_id=member_id).first()
    if not member:
        raise HTTPException(404, "Member not found")
    db.delete(member)
    db.commit()


@router.get("/{room_id}/employees")
def room_employees(room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member_required(db, room_id, user.id)
    rows = db.query(DigitalEmployee).join(RoomEmployee, RoomEmployee.employee_id == DigitalEmployee.id).filter(RoomEmployee.room_id == room_id).all()
    return [{"id": row.id, "name": row.name, "description": row.description} for row in rows]


@router.get("/{room_id}/members")
def room_members(room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member_required(db, room_id, user.id)
    rows = db.query(User).join(RoomMember, RoomMember.user_id == User.id).filter(RoomMember.room_id == room_id).all()
    return [{"id": item.id, "username": item.username, "display_name": item.display_name} for item in rows]


@router.delete("/{room_id}/leave", status_code=204)
def leave_room(room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = member_required(db, room_id, user.id)
    if room.owner_id == user.id:
        raise HTTPException(400, "Room owner cannot leave; transfer ownership or delete the room")
    item = db.query(RoomMember).filter_by(room_id=room_id, user_id=user.id).first()
    db.delete(item)
    db.commit()


@router.post("/{room_id}/employees/{employee_id}", status_code=201)
def add_room_employee(room_id: int, employee_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = member_required(db, room_id, user.id)
    if room.owner_id != user.id:
        raise HTTPException(403, "Only room owner can manage digital employees")
    employee = db.get(DigitalEmployee, employee_id)
    if not employee or not employee.enabled:
        raise HTTPException(404, "Digital employee not found")
    if not db.query(RoomEmployee).filter_by(room_id=room_id, employee_id=employee_id).first():
        db.add(RoomEmployee(room_id=room_id, employee_id=employee_id))
        db.commit()
    return {"ok": True}


@router.delete("/{room_id}/employees/{employee_id}", status_code=204)
def remove_room_employee(room_id: int, employee_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = member_required(db, room_id, user.id)
    if room.owner_id != user.id:
        raise HTTPException(403, "Only room owner can manage digital employees")
    item = db.query(RoomEmployee).filter_by(room_id=room_id, employee_id=employee_id).first()
    if not item:
        raise HTTPException(404, "Employee not in room")
    db.delete(item)
    db.commit()


@router.post("/{room_id}/employee_reply")
async def employee_reply(room_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member_required(db, room_id, user.id)
    employee_id, prompt = payload.get("employee_id"), payload.get("content")
    employee = db.get(DigitalEmployee, employee_id) if isinstance(employee_id, int) else None
    if not employee or not employee.enabled or not db.query(RoomEmployee).filter_by(room_id=room_id, employee_id=employee.id).first():
        raise HTTPException(404, "Digital employee is not in this room")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 10000:
        raise HTTPException(422, "content must contain 1 to 10000 characters")
    answer = run_employee_turn(db, employee, prompt, room_id)
    message = Message(room_id=room_id, sender_id=-employee.id, content=answer, message_type="text")
    db.add(message)
    db.commit()
    db.refresh(message)
    result = {"id": message.id, "sender_id": message.sender_id, "employee": employee.name, "content": answer, "type": "text", "created_at": message.created_at.isoformat()}
    from app.main import manager

    await manager.broadcast(room_id, result)
    return result
