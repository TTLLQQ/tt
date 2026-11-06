import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fastapi.testclient import TestClient

from app.main import app


class MockModelHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(size))
        if any(message.get("role") == "tool" for message in request["messages"]):
            message = {"role": "assistant", "content": "计算结果是 5。"}
        else:
            message = {"role": "assistant", "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "calculator", "arguments": "{\"expression\":\"2 + 3\"}"}}]}
        body = json.dumps({"choices": [{"index": 0, "message": message, "finish_reason": "stop"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def test_authenticated_primary_flows_and_safe_tools():
    with TestClient(app) as client:
        assert client.get("/healthz").json()["status"] == "ok"
        login = client.post("/api/users/login", data={"username": "test-admin", "password": "test-password-long"})
        assert login.json()["expires_in"] == 1800
        admin_token = login.json()["access_token"]
        admin = {"Authorization": f"Bearer {admin_token}"}

        assert client.get("/api/admin/dashboard", headers=admin).status_code == 200
        assert client.get("/api/admin/dashboard").status_code == 401

        registration = client.post("/api/users/register", json={"username": "alice", "password": "correct-horse-battery", "display_name": "Alice"})
        assert registration.status_code == 201
        alice_token = client.post("/api/users/login", data={"username": "alice", "password": "correct-horse-battery"}).json()["access_token"]
        alice = {"Authorization": f"Bearer {alice_token}"}
        bob = client.post("/api/users/register", json={"username": "bob", "password": "correct-horse-battery"}).json()
        assert client.post(f"/api/users/friends/{bob['id']}", headers=alice).status_code == 201

        employee = client.post("/api/ai-agents/employees", headers=admin, json={"name": "帮助助手", "description": "演示员工", "system_prompt": "保持简洁", "model_id": None, "tool_ids": []})
        assert employee.status_code == 201, employee.text
        room = client.post("/api/chatrooms", headers=alice, json={"name": "项目讨论", "friend_ids": [bob["id"]], "employee_ids": [employee.json()["id"]]})
        assert room.status_code == 201, room.text
        room_id = room.json()["id"]
        assert client.get(f"/api/chatrooms/{room_id}/employees", headers=alice).json()[0]["name"] == "帮助助手"
        assert client.post(f"/api/chatrooms/{room_id}/messages", headers=alice, json={"content": "你好", "message_type": "text"}).status_code == 201
        assert len(client.get(f"/api/chatrooms/{room_id}/messages", headers=alice).json()) == 1
        assert client.post(f"/api/chatrooms/{room_id}/messages", headers=alice, json={"content": "javascript:alert(1)", "message_type": "image"}).status_code == 422

        with client.websocket_connect(f"/ws/chat/{room_id}/{registration.json()['id']}?token={alice_token}") as socket:
            socket.send_json({"content": "👋", "type": "emoji"})
            live = socket.receive_json()
            assert live["sender_id"] == registration.json()["id"] and live["type"] == "emoji"

        shared = client.post(f"/api/chatrooms/{room_id}/share", headers=alice).json()["share_link"]
        bob_token = client.post("/api/users/login", data={"username": "bob", "password": "correct-horse-battery"}).json()["access_token"]
        bob_headers = {"Authorization": f"Bearer {bob_token}"}
        joined = client.post(f"/api/chatrooms/join/{shared}", headers=bob_headers)
        assert joined.status_code == 200 and joined.json()["room_id"] == room_id

        tools = client.get("/api/ai-agents/tools", headers=admin).json()
        calculator = next(item for item in tools if item["builtin_key"] == "calculator")
        tested = client.post(f"/api/ai-agents/tools/{calculator['id']}/test", headers=admin, json={"arguments": {"expression": "(12 + 8) * 2"}})
        assert tested.status_code == 200 and tested.json()["result"] == "40"
        blocked = client.post(f"/api/ai-agents/tools/{calculator['id']}/test", headers=admin, json={"arguments": {"expression": "__import__('os').system('echo nope')"}})
        assert blocked.status_code == 422
        assert client.get("/api/ai-agents/tools/logs", headers=admin).json()

        model_server = ThreadingHTTPServer(("127.0.0.1", 0), MockModelHandler)
        model_thread = threading.Thread(target=model_server.serve_forever, daemon=True)
        model_thread.start()
        try:
            model = client.post("/api/ai-agents/models", headers=admin, json={"name": "mock-model", "provider": "compatible", "base_url": f"http://127.0.0.1:{model_server.server_port}/v1", "model_name": "mock", "api_key": "test-key"})
            assert model.status_code == 201, model.text
            agent = client.post("/api/ai-agents/employees", headers=admin, json={"name": "计算助手", "description": "执行白名单计算", "system_prompt": "保持简洁", "model_id": model.json()["id"], "tool_ids": [calculator["id"]]})
            assert agent.status_code == 201, agent.text
            assert client.post(f"/api/chatrooms/{room_id}/employees/{agent.json()['id']}", headers=alice).status_code == 201
            reply = client.post(f"/api/chatrooms/{room_id}/employee_reply", headers=alice, json={"employee_id": agent.json()["id"], "content": "帮我算 2+3"})
            assert reply.status_code == 200, reply.text
            assert reply.json()["sender_id"] == -agent.json()["id"]
            assert reply.json()["content"] == "计算结果是 5。"
            call_log = client.get("/api/ai-agents/tools/logs", headers=admin).json()
            assert any(row["tool_id"] == calculator["id"] and row["arguments"]["expression"] == "2 + 3" for row in call_log)
        finally:
            model_server.shutdown()
            model_server.server_close()
            model_thread.join(timeout=2)

        response = client.post("/api/chat-assistant/query", headers=admin, json={"question": "统计消息趋势"})
        assert response.status_code == 200 and response.headers["content-type"].startswith("text/event-stream")
        body = response.text
        for event in ("tool_call", "tool_result", "chart_call", "chart_result", "content", "done"):
            assert f"event: {event}" in body
        risk_stream = client.post("/api/admin/analyze-sensitive", headers=admin)
        assert risk_stream.status_code == 200
        assert "event: progress" in risk_stream.text and "event: done" in risk_stream.text

        assert client.patch("/api/users/profile", headers=alice, json={"display_name": "Alice Changed"}).json()["display_name"] == "Alice Changed"
        assert client.get("/api/admin/analytics", headers=admin).status_code == 200


def test_model_credentials_are_encrypted_and_never_returned():
    with TestClient(app) as client:
        token = client.post("/api/users/login", data={"username": "test-admin", "password": "test-password-long"}).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/ai-agents/models", headers=headers, json={"name": "test-model", "provider": "compatible", "base_url": "https://example.invalid/v1", "model_name": "demo", "api_key": "do-not-return-this"})
        assert response.status_code == 201, response.text
        models = client.get("/api/ai-agents/models", headers=headers).json()
        assert all("do-not-return-this" not in json.dumps(model) for model in models)
