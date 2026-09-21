import os
import tempfile

# Use a separate temporary database for the tests. This must be set before the app is imported.
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["ADMIN_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

import db  # noqa: E402
from agent import run_support  # noqa: E402
from main import RateLimiter, app, clean_history  # noqa: E402

client = TestClient(app)
ADMIN = {"X-Admin-Key": "test-key"}


# ---- workflow
def test_technical_query_that_sounds_upset_is_escalated():
    result = run_support("My internet connection keeps dropping. Can you help?")
    assert result["category"] == "Technical"
    assert result["sentiment"] == "Negative"
    assert result["escalated"] is True
    assert result["ticket"].startswith("WL-")


def test_neutral_technical_query_gets_a_technical_answer():
    result = run_support("How do I reset my router?")
    assert result["category"] == "Technical"
    assert result["escalated"] is False
    assert "router" in result["text"].lower()


def test_billing_query():
    result = run_support("where can i find my receipt?")
    assert result["category"] == "Billing"
    assert result["escalated"] is False


def test_general_query_about_hours():
    result = run_support("What are your business hours?")
    assert result["category"] == "General"
    assert "24/7" in result["text"]


def test_asking_for_a_human_escalates_even_when_calm():
    result = run_support("I would like to talk to a human agent.")
    assert result["sentiment"] != "Negative"
    assert result["escalated"] is True
    assert "human agent" in result["text"]


def test_hinglish_query_is_understood():
    result = run_support("mera internet nahi chal raha")
    assert result["category"] == "Technical"


# ---- REST API
def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_rest_chat_endpoint():
    res = client.post("/api/chat", json={"message": "where can i find my receipt?"})
    assert res.status_code == 200
    assert res.json()["category"] == "Billing"


def test_rest_chat_rejects_empty_message():
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/chat", json={"message": "   "}).status_code == 422


# ---- WebSocket
def test_websocket_chat_flow():
    with client.websocket_connect("/ws/chat") as ws:
        assert ws.receive_json()["type"] == "welcome"
        ws.send_json({"type": "message", "text": "What are your business hours?", "history": []})
        assert ws.receive_json()["type"] == "typing"
        reply = ws.receive_json()
        assert reply["type"] == "message"
        assert reply["category"] == "General"


# ---- tickets, stats, feedback
def test_escalation_creates_a_ticket_that_an_agent_can_resolve():
    reply = client.post("/api/chat", json={"message": "This is terrible, my internet is broken"}).json()
    assert reply["escalated"] is True

    open_tickets = client.get("/api/tickets", headers=ADMIN).json()
    assert reply["ticket"] in [t["ticket"] for t in open_tickets]

    assert client.post(f"/api/tickets/{reply['ticket']}/resolve", headers=ADMIN).status_code == 200
    open_after = client.get("/api/tickets", headers=ADMIN).json()
    assert reply["ticket"] not in [t["ticket"] for t in open_after]
    resolved = client.get("/api/tickets?status=resolved", headers=ADMIN).json()
    assert reply["ticket"] in [t["ticket"] for t in resolved]


def test_agent_endpoints_need_the_admin_key():
    assert client.get("/api/tickets").status_code == 401
    assert client.get("/api/stats", headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert client.post("/api/tickets/WL-00000/resolve").status_code == 401


def test_resolving_an_unknown_ticket_returns_404():
    assert client.post("/api/tickets/WL-00000/resolve", headers=ADMIN).status_code == 404


def test_feedback_is_counted_in_stats():
    before = db.stats()["feedback"]["up"]
    assert client.post("/api/feedback", json={"rating": "up", "category": "Billing"}).status_code == 200
    assert client.post("/api/feedback", json={"rating": "maybe"}).status_code == 422
    stats = client.get("/api/stats", headers=ADMIN).json()
    assert stats["feedback"]["up"] == before + 1
    assert stats["messages"] > 0


# ---- safety helpers
def test_history_from_the_browser_is_cleaned():
    raw = [{"role": "user", "text": "hi"}, {"role": "hacker", "text": "x"}, "junk", {"role": "bot", "text": 5}]
    assert clean_history(raw) == [{"role": "user", "text": "hi"}]
    assert clean_history("not a list") == []


def test_rate_limiter_blocks_after_the_limit():
    limiter = RateLimiter(limit=3, window=60)
    assert [limiter.allow("a") for _ in range(4)] == [True, True, True, False]
    assert limiter.allow("b") is True  # another visitor is not affected
