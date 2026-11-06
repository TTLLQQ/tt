import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Message, ToolCallLog, User
from app.security import require_admin

router = APIRouter(prefix="/api/chat-assistant", tags=["chat-assistant"])


def event(name: str, payload: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/query")
def query(payload: dict, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    question = payload.get("question", "")
    if not isinstance(question, str) or not question.strip() or len(question) > 1000:
        from fastapi import HTTPException
        raise HTTPException(422, "question must contain 1 to 1000 characters")

    def generate():
        normalized = question.lower()
        yield event("tool_call", {"name": "safe_analytics_select", "status": "started"})
        if any(term in normalized for term in ("工具", "tool")):
            rows = db.query(ToolCallLog.status, func.count(ToolCallLog.id)).group_by(ToolCallLog.status).all()
            labels, values, title, kind = [str(row[0]) for row in rows], [row[1] for row in rows], "工具调用状态分布", "pie"
        elif any(term in normalized for term in ("用户", "user")):
            rows = db.query(func.strftime("%Y-%m-%d", User.created_at).label("day"), func.count(User.id)).group_by("day").order_by("day").all()
            labels, values, title, kind = [str(row[0]) for row in rows], [row[1] for row in rows], "每日注册用户数", "line"
        else:
            rows = db.query(func.strftime("%Y-%m-%d", Message.created_at).label("day"), func.count(Message.id)).group_by("day").order_by("day").all()
            labels, values, title, kind = [str(row[0]) for row in rows], [row[1] for row in rows], "每日消息数", "bar"
        if "散点" in normalized or "scatter" in normalized:
            kind = "scatter"
        yield event("tool_result", {"rows": [{"label": label, "value": value} for label, value in zip(labels, values)]})
        yield event("chart_call", {"type": kind, "title": title})
        chart = {"type": kind, "title": title, "labels": labels, "values": values}
        yield event("chart_result", chart)
        yield event("content", {"text": f"{title}共 {sum(values)} 条。"})
        yield event("done", {"ok": True})

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
