import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import FRONTEND_ORIGINS, JWT_SECRET_KEY, validate_config
from app.database import SessionLocal, engine
from app.models import AITool, RoomMember, User
from app.routers import admin, ai_agents, chat_assistant, chatrooms, users, weather
from app.security import ALGORITHM, hash_password

BUILTINS = [
    ("天气查询", "查询配置好的城市天气", "weather_lookup", {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}),
    ("计算器", "执行受限数字四则运算", "calculator", {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}),
    ("日期格式化", "格式化 ISO 日期", "date_format", {"type": "object", "properties": {"date_text": {"type": "string"}}}),
    ("文本处理", "安全地处理文本", "text_process", {"type": "object", "properties": {"text": {"type": "string"}, "operation": {"type": "string", "enum": ["trim", "upper", "lower", "word_count"]}}, "required": ["text"]}),
    ("随机数生成", "在指定范围生成随机整数", "random_number", {"type": "object", "properties": {"minimum": {"type": "integer"}, "maximum": {"type": "integer"}}}),
]


def seed_data() -> None:
    with SessionLocal() as db:
        for name, description, key, schema in BUILTINS:
            if not db.query(AITool).filter_by(name=key).first():
                db.add(AITool(name=key, description=description, builtin_key=key, parameters_schema=schema, enabled=True))
        admin_name = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "")
        admin_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
        if admin_name and admin_password and not db.query(User).filter_by(username=admin_name).first():
            db.add(User(username=admin_name, display_name=admin_name, password_hash=hash_password(admin_password), is_admin=True))
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_config()
    from alembic import command
    from alembic.config import Config

    migration_config = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    command.upgrade(migration_config, "head")
    seed_data()
    yield


app = FastAPI(title="TT AI 客服系统 API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
for route_module in (users, chatrooms, admin, ai_agents, chat_assistant, weather):
    app.include_router(route_module.router)


@app.get("/healthz")
def health():
    from sqlalchemy import text

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[int, set[WebSocket]] = {}

    async def connect(self, room_id: int, websocket: WebSocket):
        await websocket.accept()
        self.rooms.setdefault(room_id, set()).add(websocket)

    def disconnect(self, room_id: int, websocket: WebSocket):
        self.rooms.get(room_id, set()).discard(websocket)
        if not self.rooms.get(room_id):
            self.rooms.pop(room_id, None)

    async def broadcast(self, room_id: int, payload: dict):
        stale = []
        for socket in self.rooms.get(room_id, set()):
            try:
                await socket.send_json(payload)
            except Exception:
                stale.append(socket)
        for socket in stale:
            self.disconnect(room_id, socket)


manager = ConnectionManager()


@app.websocket("/ws/chat/{room_id}/{user_id}")
async def room_socket(websocket: WebSocket, room_id: int, user_id: int, token: str):
    try:
        claims = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        authenticated_id = int(claims["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        await websocket.close(code=1008, reason="Invalid access token")
        return
    with SessionLocal() as db:
        member = db.query(RoomMember).filter_by(room_id=room_id, user_id=authenticated_id).first()
        user = db.get(User, authenticated_id)
    if authenticated_id != user_id or not member or not user:
        await websocket.close(code=1008, reason="Room membership required")
        return
    await manager.connect(room_id, websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            content, message_type = payload.get("content"), payload.get("type", "text")
            if not isinstance(content, str) or not content.strip() or len(content) > 10000 or message_type not in {"text", "emoji", "image"}:
                await websocket.send_json({"error": "Invalid message"})
                continue
            from app.models import Message

            with SessionLocal() as db:
                message = Message(room_id=room_id, sender_id=user_id, content=content, message_type=message_type)
                db.add(message)
                db.commit()
                db.refresh(message)
                result = {"id": message.id, "room_id": room_id, "sender_id": user_id, "content": content, "type": message_type, "created_at": message.created_at.isoformat()}
            await manager.broadcast(room_id, result)
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
