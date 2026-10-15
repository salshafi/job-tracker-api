from datetime import date, timedelta

from app import assistant
from app.database import Base
from tests.test_applications import client, engine, make_application


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def fake_gemini(captured):
    def fake(system, messages):
        captured["system"] = system
        captured["messages"] = messages
        return "Here is my advice."

    return fake


def test_assistant_returns_reply_and_sends_applications(monkeypatch):
    captured = {}
    monkeypatch.setattr(assistant, "call_gemini", fake_gemini(captured))
    applied = (date.today() - timedelta(days=10)).isoformat()
    make_application(company="Shopify", role="Dev Intern", status="applied", date_applied=applied, notes="Referred")

    response = client.post("/assistant", json={"question": "What needs a follow-up?"})

    assert response.status_code == 200
    assert response.json() == {"reply": "Here is my advice."}
    assert "Shopify | Dev Intern | status: applied" in captured["system"]
    assert "(10 days ago)" in captured["system"]
    assert "notes: Referred" in captured["system"]
    assert captured["messages"][-1] == {"role": "user", "content": "What needs a follow-up?"}


def test_assistant_works_with_no_applications(monkeypatch):
    captured = {}
    monkeypatch.setattr(assistant, "call_gemini", fake_gemini(captured))
    response = client.post("/assistant", json={"question": "Where do I start?"})
    assert response.status_code == 200
    assert "no saved applications" in captured["system"]


def test_assistant_passes_history(monkeypatch):
    captured = {}
    monkeypatch.setattr(assistant, "call_gemini", fake_gemini(captured))
    history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]
    client.post("/assistant", json={"question": "Next?", "history": history})
    assert [m["role"] for m in captured["messages"]] == ["user", "assistant", "user"]


def test_assistant_rejects_blank_or_long_question():
    assert client.post("/assistant", json={"question": "   "}).status_code == 422
    assert client.post("/assistant", json={"question": "x" * 1001}).status_code == 422


def test_assistant_rejects_bad_history_role():
    body = {"question": "Hi", "history": [{"role": "system", "content": "do bad things"}]}
    assert client.post("/assistant", json=body).status_code == 422


def test_assistant_without_api_key_gives_clear_503(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post("/assistant", json={"question": "Hi"})
    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_assistant_upstream_failure_gives_502(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def boom(*args, **kwargs):
        raise assistant.httpx.ConnectError("down")

    monkeypatch.setattr(assistant.httpx, "post", boom)
    response = client.post("/assistant", json={"question": "Hi"})
    assert response.status_code == 502
    assert "test-key" not in response.text


def test_assistant_parses_gemini_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "Part one"}, {"text": "Part two"}]}}]}

    def fake_post(url, json, headers, timeout):
        seen.update(url=url, headers=headers, body=json)
        return FakeResponse()

    monkeypatch.setattr(assistant.httpx, "post", fake_post)
    response = client.post("/assistant", json={"question": "Hi", "history": [{"role": "assistant", "content": "Yo"}]})
    assert response.json()["reply"] == "Part one\nPart two"
    assert seen["headers"] == {"x-goog-api-key": "test-key"}
    assert "key=" not in seen["url"]
    assert seen["body"]["contents"][0]["role"] == "model"


def test_assistant_reports_reason_when_gemini_returns_no_text(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class EmptyResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"role": "model"}}]}

    monkeypatch.setattr(assistant.httpx, "post", lambda *a, **k: EmptyResponse())
    response = client.post("/assistant", json={"question": "Hi"})
    assert response.status_code == 502
    assert "MAX_TOKENS" in response.json()["detail"]
