import json
import time

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crypto import decrypt_secret
from app.models import AIModel, AITool, DigitalEmployee, ToolCallLog
from app.tool_registry import execute_builtin

DEFAULT_SCHEMAS = {
    "calculator": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
    "date_format": {"type": "object", "properties": {"date_text": {"type": "string"}}},
    "text_process": {"type": "object", "properties": {"text": {"type": "string"}, "operation": {"type": "string", "enum": ["trim", "upper", "lower", "word_count"]}}, "required": ["text"]},
    "random_number": {"type": "object", "properties": {"minimum": {"type": "integer"}, "maximum": {"type": "integer"}}},
    "weather_lookup": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
}


def available_model(db: Session, employee: DigitalEmployee) -> AIModel | None:
    if employee.model_id:
        return db.get(AIModel, employee.model_id)
    return db.query(AIModel).filter(AIModel.is_default.is_(True)).first()


def run_employee_turn(db: Session, employee: DigitalEmployee, question: str, room_id: int | None = None) -> str:
    model = available_model(db, employee)
    if not model:
        return "该数字员工尚未绑定可用模型。请管理员配置模型后重试。"
    try:
        api_key = decrypt_secret(model.api_key_encrypted)
    except Exception as error:
        raise HTTPException(status_code=503, detail="模型凭据无法解密，请检查 DATA_ENCRYPTION_KEY") from error
    tool_rows = db.query(AITool).filter(AITool.id.in_(employee.tool_ids or []), AITool.enabled.is_(True)).all() if employee.tool_ids else []
    tool_by_name = {row.name: row for row in tool_rows if row.builtin_key in DEFAULT_SCHEMAS}
    tools = [{"type": "function", "function": {"name": row.name, "description": row.description, "parameters": row.parameters_schema or DEFAULT_SCHEMAS[row.builtin_key]}} for row in tool_by_name.values()]
    messages = [{"role": "system", "content": employee.system_prompt or f"你是{employee.name}。回答简洁、准确。"}, {"role": "user", "content": question}]
    endpoint = model.base_url.rstrip("/") + "/chat/completions"
    try:
        with httpx.Client(timeout=45) as client:
            response = client.post(endpoint, headers={"Authorization": f"Bearer {api_key}"}, json={"model": model.model_name, "messages": messages, **({"tools": tools, "tool_choice": "auto"} if tools else {})})
            response.raise_for_status()
            payload = response.json()
            choice = payload["choices"][0]["message"]
            calls = choice.get("tool_calls") or []
            if not calls:
                return choice.get("content") or "模型未返回文本答复。"
            messages.append(choice)
            for call in calls[:5]:
                name = call["function"]["name"]
                row = tool_by_name.get(name)
                arguments = json.loads(call["function"].get("arguments") or "{}")
                started = time.perf_counter()
                try:
                    if row is None:
                        raise ValueError("Tool is not allow-listed for this employee")
                    result = execute_builtin(row.builtin_key, arguments)
                    status = "ok"
                except Exception as error:
                    result, status = str(error), "error"
                db.add(ToolCallLog(tool_id=row.id if row else None, room_id=room_id, employee_id=employee.id, arguments=arguments, result=str(result)[:5000], status=status, duration_ms=int((time.perf_counter() - started) * 1000)))
                db.flush()
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": str(result)})
            response = client.post(endpoint, headers={"Authorization": f"Bearer {api_key}"}, json={"model": model.model_name, "messages": messages})
            response.raise_for_status()
            db.commit()
            return response.json()["choices"][0]["message"].get("content") or "模型未返回文本答复。"
    except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as error:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"模型请求失败: {error}") from error
