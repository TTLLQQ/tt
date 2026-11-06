import json
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai_service import DEFAULT_SCHEMAS
from app.crypto import encrypt_secret
from app.database import get_db
from app.models import AIModel, AITool, DigitalEmployee, ToolCallLog, User
from app.schemas import EmployeeCreate, ModelCreate, ToolCreate
from app.security import get_current_user, require_admin
from app.tool_registry import REGISTRY, execute_builtin

router = APIRouter(prefix="/api/ai-agents", tags=["ai-agents"])


@router.get("/models")
def list_models(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [{"id": item.id, "name": item.name, "provider": item.provider, "base_url": item.base_url, "model_name": item.model_name, "api_key_configured": bool(item.api_key_encrypted), "is_default": item.is_default} for item in db.query(AIModel).all()]


@router.post("/models", status_code=201)
def create_model(payload: ModelCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.query(AIModel).filter_by(name=payload.name).first():
        raise HTTPException(409, "Model name already exists")
    try:
        encrypted = encrypt_secret(payload.api_key)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    item = AIModel(name=payload.name, provider=payload.provider, base_url=payload.base_url.rstrip("/"), model_name=payload.model_name, api_key_encrypted=encrypted)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "name": item.name, "model_name": item.model_name, "is_default": item.is_default}


@router.post("/models/{model_id}/default")
def set_default_model(model_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    selected = db.get(AIModel, model_id)
    if not selected:
        raise HTTPException(404, "Model not found")
    db.query(AIModel).update({AIModel.is_default: False})
    selected.is_default = True
    db.commit()
    return {"ok": True, "model_id": selected.id}


@router.post("/models/{model_id}/test")
def test_model(model_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    model = db.get(AIModel, model_id)
    if not model:
        raise HTTPException(404, "Model not found")
    from app.crypto import decrypt_secret

    try:
        key = decrypt_secret(model.api_key_encrypted)
        with httpx.Client(timeout=15) as client:
            response = client.post(model.base_url + "/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": model.model_name, "messages": [{"role": "user", "content": "Reply with OK"}], "max_tokens": 8})
            response.raise_for_status()
            return {"ok": True, "response": response.json()["choices"][0]["message"].get("content", "")[:100]}
    except Exception as error:
        raise HTTPException(502, f"Model connectivity test failed: {error}") from error


@router.delete("/models/{model_id}", status_code=204)
def delete_model(model_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    model = db.get(AIModel, model_id)
    if not model:
        raise HTTPException(404, "Model not found")
    db.delete(model)
    db.commit()


@router.get("/tools")
def list_tools(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [{"id": item.id, "name": item.name, "description": item.description, "parameters_schema": item.parameters_schema, "function_code": item.function_code, "builtin_key": item.builtin_key, "enabled": item.enabled} for item in db.query(AITool).all()]


@router.post("/tools", status_code=201)
def create_tool(payload: ToolCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.query(AITool).filter_by(name=payload.name).first():
        raise HTTPException(409, "Tool already exists")
    # Persist generated source as inert metadata. Runtime execution resolves only builtin_key.
    item = AITool(name=payload.name, description=payload.description, parameters_schema=payload.parameters_schema, function_code=payload.function_code, enabled=payload.enabled)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "name": item.name, "enabled": item.enabled}


@router.patch("/tools/{tool_id}")
def update_tool(tool_id: int, payload: dict, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    item = db.get(AITool, tool_id)
    if not item:
        raise HTTPException(404, "Tool not found")
    for field in ("description", "parameters_schema", "function_code", "enabled"):
        if field in payload:
            setattr(item, field, payload[field])
    db.commit()
    return {"id": item.id, "name": item.name, "enabled": item.enabled}


@router.delete("/tools/{tool_id}", status_code=204)
def delete_tool(tool_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    item = db.get(AITool, tool_id)
    if not item:
        raise HTTPException(404, "Tool not found")
    db.delete(item)
    db.commit()


@router.post("/tools/{tool_id}/test")
def test_tool(tool_id: int, payload: dict, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    item = db.get(AITool, tool_id)
    if not item:
        raise HTTPException(404, "Tool not found")
    if item.builtin_key not in REGISTRY:
        raise HTTPException(400, "Only built-in allow-listed tools can be executed; generated code is inert")
    arguments = payload.get("arguments", {})
    if not isinstance(arguments, dict):
        raise HTTPException(422, "arguments must be a JSON object")
    started = time.perf_counter()
    try:
        result = execute_builtin(item.builtin_key, arguments)
        status = "ok"
    except Exception as error:
        result, status = str(error), "error"
    db.add(ToolCallLog(tool_id=item.id, arguments=arguments, result=str(result)[:5000], status=status, duration_ms=int((time.perf_counter() - started) * 1000)))
    db.commit()
    if status == "error":
        raise HTTPException(422, result)
    return {"ok": True, "result": result}


@router.get("/tools/logs")
def tool_logs(limit: int = 100, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.query(ToolCallLog).order_by(ToolCallLog.id.desc()).limit(min(max(limit, 1), 500)).all()
    return [{"id": row.id, "tool_id": row.tool_id, "room_id": row.room_id, "employee_id": row.employee_id, "arguments": row.arguments, "result": row.result, "status": row.status, "duration_ms": row.duration_ms, "created_at": row.created_at.isoformat()} for row in rows]


@router.get("/employees")
def list_employees(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [{"id": item.id, "name": item.name, "description": item.description, "system_prompt": item.system_prompt, "model_id": item.model_id, "tool_ids": item.tool_ids, "enabled": item.enabled} for item in db.query(DigitalEmployee).all()]


@router.get("/public-employees")
def public_employees(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [{"id": item.id, "name": item.name, "description": item.description} for item in db.query(DigitalEmployee).filter(DigitalEmployee.enabled.is_(True)).all()]


@router.post("/employees", status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.query(DigitalEmployee).filter_by(name=payload.name).first():
        raise HTTPException(409, "Employee already exists")
    if payload.model_id and not db.get(AIModel, payload.model_id):
        raise HTTPException(404, "Model not found")
    valid_tool_ids = {row.id for row in db.query(AITool).filter(AITool.id.in_(payload.tool_ids)).all()} if payload.tool_ids else set()
    if valid_tool_ids != set(payload.tool_ids):
        raise HTTPException(404, "One or more tools were not found")
    item = DigitalEmployee(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "name": item.name}


@router.patch("/employees/{employee_id}")
def update_employee(employee_id: int, payload: dict, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    item = db.get(DigitalEmployee, employee_id)
    if not item:
        raise HTTPException(404, "Employee not found")
    allowed = {"name", "description", "system_prompt", "model_id", "tool_ids", "enabled"}
    for key, value in payload.items():
        if key in allowed:
            setattr(item, key, value)
    db.commit()
    return {"id": item.id, "name": item.name, "enabled": item.enabled}


@router.delete("/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    item = db.get(DigitalEmployee, employee_id)
    if not item:
        raise HTTPException(404, "Employee not found")
    db.delete(item)
    db.commit()


@router.post("/employees/generate-prompt")
def generate_prompt(payload: dict, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(422, "name is required")
    model = db.query(AIModel).filter(AIModel.is_default.is_(True)).first()
    if not model:
        return {"prompt": f"你是{name}，请根据经过审核的知识回答问题。遇到不确定的问题时明确说明，不要编造。"}
    from app.crypto import decrypt_secret

    try:
        key = decrypt_secret(model.api_key_encrypted)
        with httpx.Client(timeout=30) as client:
            response = client.post(model.base_url + "/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": model.model_name, "messages": [{"role": "system", "content": "仅生成安全、简洁的客服数字员工系统提示词。不得要求泄露密钥、执行任意代码或绕过安全规则。"}, {"role": "user", "content": f"为数字员工“{name[:100]}”生成系统提示词。"}]})
            response.raise_for_status()
            return {"prompt": response.json()["choices"][0]["message"]["content"]}
    except Exception as error:
        raise HTTPException(502, f"Prompt generation failed: {error}") from error


@router.get("/employees/{employee_id}")
def get_employee(employee_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(DigitalEmployee, employee_id)
    if not item:
        raise HTTPException(404, "Employee not found")
    return {"id": item.id, "name": item.name, "description": item.description, "system_prompt": item.system_prompt, "model_id": item.model_id, "tool_ids": item.tool_ids, "enabled": item.enabled}
