"""FastAPI server: WebSocket chat, REST fallback, feedback, and a small agent API (tickets and stats)."""
import asyncio
import logging
import os
import random
import secrets
import time
from collections import defaultdict, deque
from typing import List, Literal, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db
from agent import COMPANY, MODE, run_support

load_dotenv()
log = logging.getLogger("uvicorn.error")

MAX_LENGTH = 1000
MAX_HISTORY = 12
WELCOME = f"Hi, I am the {COMPANY} assistant. I am here 24/7. Ask me about your connection, billing or anything else."

ADMIN_KEY = os.getenv("ADMIN_KEY", "demo-admin")
if ADMIN_KEY == "demo-admin":
    log.warning("ADMIN_KEY is not set, so the agent dashboard uses the default key 'demo-admin'. Set ADMIN_KEY before deploying.")

app = FastAPI(title=f"{COMPANY} Support Chatbot API")

origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------- helpers
class RateLimiter:
    """Allows `limit` messages per `window` seconds for each client. Stops one visitor from running up the LLM bill."""

    def __init__(self, limit: int, window: int = 60):
        self.limit = limit
        self.window = window
        self.hits = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


limiter = RateLimiter(int(os.getenv("RATE_LIMIT_PER_MIN", "20")))


def client_ip(headers, client) -> str:
    forwarded = headers.get("x-forwarded-for")  # set by hosting platforms such as Render
    if forwarded:
        return forwarded.split(",")[0].strip()
    return client.host if client else "unknown"


def clean_history(raw) -> List[dict]:
    """The browser sends the last turns with each message. Never trust it: keep only well-formed, short entries."""
    if not isinstance(raw, list):
        return []
    history = []
    for item in raw[-MAX_HISTORY:]:
        if isinstance(item, dict) and item.get("role") in ("user", "bot") and isinstance(item.get("text"), str):
            history.append({"role": item["role"], "text": item["text"][:MAX_LENGTH]})
    return history


def process(text: str, history: List[dict]) -> dict:
    """Run the LangGraph workflow, then save the result (statistics and tickets)."""
    reply = run_support(text, history)
    try:
        db.log_message(reply)
        if reply["escalated"]:
            db.create_ticket(reply["ticket"], text, reply["category"], reply["sentiment"])
    except Exception:  # a database problem must not break the chat
        log.exception("Could not save to the database")
    return reply


def require_admin(x_admin_key: str = Header(default="")):
    if not secrets.compare_digest(x_admin_key.encode(), ADMIN_KEY.encode()):
        raise HTTPException(status_code=401, detail="Wrong admin key.")


# ---------------------------------------------------------------- chat
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_LENGTH)
    history: List[dict] = Field(default_factory=list)


@app.get("/api/health")
def health():
    """Used by the frontend and by hosting platforms to check that the server is up."""
    return {"status": "ok", "mode": MODE}


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request):
    """Plain REST version of the chat. The frontend uses it when the WebSocket is not available."""
    if not limiter.allow(client_ip(request.headers, request.client)):
        raise HTTPException(status_code=429, detail="You are sending messages too fast. Please wait a moment.")
    text = body.message.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message is empty.")
    return await asyncio.to_thread(process, text, clean_history(body.history))


@app.websocket("/ws/chat")
async def chat_socket(ws: WebSocket):
    await ws.accept()
    await ws.send_json({"type": "welcome", "text": WELCOME, "mode": MODE})
    ip = client_ip(ws.headers, ws.client)

    try:
        while True:
            data = await ws.receive_json()
            text = str(data.get("text", "")).strip()

            if not text:
                continue
            if len(text) > MAX_LENGTH:
                await ws.send_json({"type": "error", "text": f"Please keep messages under {MAX_LENGTH} characters."})
                continue
            if not limiter.allow(ip):
                await ws.send_json({"type": "error", "text": "You are sending messages too fast. Please wait a moment."})
                continue

            await ws.send_json({"type": "typing"})
            if MODE == "rules":
                await asyncio.sleep(random.uniform(0.6, 1.2))  # a short pause so the typing indicator is visible

            try:
                reply = await asyncio.to_thread(process, text, clean_history(data.get("history")))
            except Exception:
                await ws.send_json({"type": "error", "text": "Something went wrong on our side. Please try again."})
                continue

            await ws.send_json({"type": "message", **reply})
    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------- feedback
class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]
    category: Optional[str] = Field(default=None, max_length=20)


@app.post("/api/feedback")
def feedback(body: FeedbackRequest):
    db.add_feedback(body.rating, body.category)
    return {"ok": True}


# ---------------------------------------------------------------- agent API (needs the admin key)
@app.get("/api/tickets", dependencies=[Depends(require_admin)])
def tickets(status: Literal["open", "resolved", "all"] = "open"):
    return db.list_tickets(status)


@app.post("/api/tickets/{ticket}/resolve", dependencies=[Depends(require_admin)])
def resolve(ticket: str):
    if not db.resolve_ticket(ticket):
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return {"ok": True}


@app.get("/api/stats", dependencies=[Depends(require_admin)])
def stats():
    return db.stats()
