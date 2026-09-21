# WaveLink: 24/7 AI Customer Support Chatbot

A customer support chat widget built with React, connected to a Python server over WebSockets. Every message goes through a LangGraph workflow that categorizes the question, checks the customer's sentiment, and either answers or hands the chat to a human agent. Escalated chats become tickets that support agents manage in a small dashboard.

The demo site is for a fictional internet provider called **WaveLink**.

**Live demo:** _add your Netlify link here_

## Features

**Chat**
- Chat widget with launcher, typing indicator, timestamps and unread badge
- Real-time messages over a **WebSocket**, with automatic reconnect (1s, 2s, 4s ... up to 15s)
- **REST API fallback** (`POST /api/chat`) when the socket is not available
- Conversation saved in the browser (survives a page reload) and a "New chat" button
- Follow-up questions work: the browser sends the last turns with each message, so the server stays stateless
- Thumbs up / down on every answer, saved on the server
- Understands English and simple Hinglish ("mera internet nahi chal raha"). With an LLM key it replies in the customer's language

**Support workflow (LangGraph)**
- categorize (Technical, Billing, General) then analyze sentiment then route
- Upset customers are **escalated to a human agent** and get a ticket number
- "Talk to a human" button (and phrases like "I want a human agent") escalates any time

**Agent dashboard** (open `/#agent`, sign in with the admin key)
- Statistics: messages handled, escalations, open tickets, share of answers rated helpful, messages per category
- Escalated tickets stored in SQLite, with Open / Resolved / All tabs and a "Mark resolved" button

**Reliability and safety**
- Works with no API key (rule-based replies). Add an OpenAI or Groq key for real AI replies
- If the LLM call fails, the server falls back to the rule-based reply instead of crashing
- Rate limit per visitor (default 20 messages a minute) so nobody can run up the LLM bill
- History sent by the browser is validated on the server, and the agent API needs an admin key
- Clear error messages when the server cannot be reached

## How it works

```
Browser (React)  <--- WebSocket /ws/chat --->  FastAPI  --->  LangGraph  --->  SQLite
                 <--- REST POST /api/chat --->

categorize -> analyze_sentiment -> route -> handle_technical
                                         -> handle_billing
                                         -> handle_general
                                         -> escalate (negative sentiment, or the customer asked for a person)
```

The workflow is in `backend/agent.py`. It follows the LangGraph customer support tutorial, with a few changes: the model output is matched safely (the tutorial compares exact strings), the prompts avoid placeholders such as "[Your Name]", and there is a rule-based fallback.

## Tech

- **Frontend:** React 18, Vite, custom hook (`useChat`), plain CSS
- **Backend:** Python, FastAPI, WebSockets, LangGraph, LangChain (OpenAI-compatible models), SQLite
- **Tests:** pytest (workflow, REST, WebSocket, tickets, feedback, rate limiter)

## Run it on your computer

You need two terminals: one for the backend and one for the frontend.

### 1. Backend (Python 3.10 or newer)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac / Linux
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```

Check that it works by opening http://localhost:8000/api/health. You should see `{"status":"ok","mode":"rules"}`.

### 2. Frontend (Node.js 20.19 or newer)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and click the chat button.

### 3. Agent dashboard

Open http://localhost:5173/#agent. The default admin key is `demo-admin`. Send a message such as "This is terrible, my internet is broken" in the chat, then refresh the dashboard to see the ticket.

### Optional: real AI replies

Copy `backend/.env.example` to `backend/.env`, remove the `#` in front of the lines for your provider, and paste your key. Restart the backend. `/api/health` will now show `"mode":"llm"`.

Never commit `.env` (it is already in `.gitignore`).

### Run the tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

## Deploy

The frontend and the backend are deployed separately.

**Backend on Render (free plan):**
1. Push the project to GitHub.
2. On render.com create a **Web Service** from the repo. Set **Root Directory** to `backend`.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add these environment variables: `ADMIN_KEY` (**choose your own password**), `ALLOWED_ORIGINS` (your Netlify address, added after the step below), and your LLM key if you use one.

**Frontend on Netlify:**
1. Create a new site from the same repo.
2. Base directory: `frontend`. Build command: `npm run build`. Publish directory: `frontend/dist`.
3. Add the environment variable `VITE_API_URL` with your Render address (no trailing slash), then redeploy.

Notes:
- The free Render plan sleeps when nobody uses it, so the first reply after a break can take up to a minute. The chat shows "Reconnecting" until the server wakes up.
- The free Render plan also resets its disk when it restarts, so the SQLite tickets and statistics can disappear. For real use, move the tables to a hosted database such as PostgreSQL.
- Tickets store the customer's message. Do not type personal data into the public demo.

## Folder structure

```
backend/
  agent.py          LangGraph workflow (nodes, routing, rule-based fallback)
  main.py           FastAPI app: chat (WebSocket + REST), feedback, agent API, rate limiter
  db.py             SQLite: tickets, message log, feedback
  test_app.py       tests
frontend/
  src/hooks/useChat.js              WebSocket connection, reconnect, REST fallback, saved history
  src/components/                   ChatWidget, MessageBubble, ChatInput, AgentDashboard ...
  src/App.jsx                       Demo website and routing to the dashboard
```

## Ideas to extend it

- Stream the reply word by word
- Move the database to PostgreSQL
- Real agent login instead of a shared admin key
- Let agents reply to a ticket from the dashboard
