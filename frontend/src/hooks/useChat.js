import { useCallback, useEffect, useRef, useState } from 'react';
import { API_URL, WS_URL } from '../config';

const STORAGE_KEY = 'wavelink-chat-v1';
const MAX_SAVED = 60;
const DEFAULT_WELCOME = 'Hi, I am the WaveLink assistant. I am here 24/7. Ask me about your connection, billing or anything else.';

let counter = 0;
const nextId = () => `${Date.now()}-${++counter}`;
const now = () => new Date().toISOString();
const makeWelcome = (text) => ({ id: nextId(), role: 'bot', text, time: now(), welcome: true });

function loadMessages() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

// The last turns of the conversation. Sent with every message so the server can answer follow-up questions
// (the server does not have to remember anything, so reconnecting or reloading the page never loses context).
const toHistory = (messages) =>
  messages.filter((m) => !m.welcome && !m.isError).slice(-12).map((m) => ({ role: m.role, text: m.text }));

// Keeps the chat state and the WebSocket connection.
// - The conversation is saved in localStorage, so it survives a page reload.
// - Connects on mount and reconnects automatically (waits 1s, 2s, 4s ... up to 15s).
// - If the socket is not open when the user sends a message, the message goes through the REST API instead.
export default function useChat() {
  const [messages, setMessages] = useState(loadMessages);
  const [status, setStatus] = useState('connecting'); // connecting | online | offline
  const [typing, setTyping] = useState(false);
  const [mode, setMode] = useState(null); // 'rules' or 'llm', told by the server

  const wsRef = useRef(null);
  const retryRef = useRef(0);
  const timerRef = useRef(null);
  const welcomeRef = useRef(DEFAULT_WELCOME);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_SAVED)));
    } catch {
      // Storage can be full or blocked. The chat keeps working without saving.
    }
  }, [messages]);

  const addMessage = useCallback((message) => {
    setMessages((list) => [...list, { id: nextId(), time: now(), ...message }]);
  }, []);

  const addBotReply = useCallback((data) => {
    addMessage({
      role: 'bot', text: data.text, category: data.category, sentiment: data.sentiment,
      escalated: data.escalated, ticket: data.ticket,
    });
  }, [addMessage]);

  const connect = useCallback(() => {
    setStatus('connecting');
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      retryRef.current = 0;
      setStatus('online');
    };

    ws.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      if (data.type === 'welcome') {
        welcomeRef.current = data.text;
        setMode(data.mode);
        // Show the welcome message only when the chat is empty (not after a reload or reconnect).
        setMessages((list) => (list.length ? list : [makeWelcome(data.text)]));
      } else if (data.type === 'typing') {
        setTyping(true);
      } else if (data.type === 'message') {
        setTyping(false);
        addBotReply(data);
      } else if (data.type === 'error') {
        setTyping(false);
        addMessage({ role: 'bot', text: data.text, isError: true });
      }
    };

    ws.onclose = () => {
      if (wsRef.current !== ws) return; // an old socket closing after a newer one was opened
      setTyping(false);
      setStatus('offline');
      const delay = Math.min(15000, 1000 * 2 ** retryRef.current);
      retryRef.current += 1;
      timerRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
  }, [addMessage, addBotReply]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(timerRef.current);
      const ws = wsRef.current;
      wsRef.current = null; // tells onclose that we closed it on purpose
      ws?.close();
    };
  }, [connect]);

  const send = useCallback(async (text) => {
    const clean = text.trim();
    if (!clean) return;

    const history = toHistory(messagesRef.current); // taken before the new message is added
    addMessage({ role: 'user', text: clean });

    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'message', text: clean, history }));
      return;
    }

    // REST fallback
    setTyping(true);
    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: clean, history }),
      });
      if (res.status === 429) throw new Error('rate');
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      addBotReply(await res.json());
    } catch (err) {
      addMessage({
        role: 'bot', isError: true,
        text: err.message === 'rate'
          ? 'You are sending messages too fast. Please wait a moment.'
          : 'I cannot reach the support server right now. Please check your connection and try again in a moment.',
      });
    } finally {
      setTyping(false);
    }
  }, [addMessage, addBotReply]);

  const askForHuman = useCallback(() => send('I would like to talk to a human agent.'), [send]);

  const newChat = useCallback(() => {
    setTyping(false);
    setMessages([makeWelcome(welcomeRef.current)]);
  }, []);

  // Thumbs up / down on a bot reply. The rating is also sent to the server (errors are ignored).
  const rate = useCallback((id, rating) => {
    const target = messagesRef.current.find((m) => m.id === id);
    if (!target || target.rating) return;
    setMessages((list) => list.map((m) => (m.id === id ? { ...m, rating } : m)));
    fetch(`${API_URL}/api/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating, category: target.category }),
    }).catch(() => {});
  }, []);

  return { messages, status, typing, mode, send, askForHuman, newChat, rate };
}
