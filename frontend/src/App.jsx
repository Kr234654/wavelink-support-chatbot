import { useEffect, useState } from 'react';
import AgentDashboard from './components/AgentDashboard';
import ChatWidget, { SUGGESTIONS } from './components/ChatWidget';
import { ChatIcon, WaveMark } from './components/Icons';
import useChat from './hooks/useChat';

const TOPICS = [
  { title: 'Technical help', text: 'Connection drops, slow speeds, router problems and app errors.', ask: SUGGESTIONS[0] },
  { title: 'Billing', text: 'Receipts, invoices, payments and plan changes.', ask: SUGGESTIONS[1] },
  { title: 'General questions', text: 'Opening hours, how WaveLink works and where to find things.', ask: SUGGESTIONS[2] },
];

const STEPS = [
  { name: 'Categorize', text: 'Technical, Billing or General' },
  { name: 'Analyze sentiment', text: 'Positive, Neutral or Negative' },
  { name: 'Route', text: 'Send to the right handler' },
  { name: 'Reply or escalate', text: 'Upset customers, or anyone who asks, get a human agent' },
];

function Website() {
  const chat = useChat();
  const [open, setOpen] = useState(false);
  const [seen, setSeen] = useState(0);

  // Count bot replies that arrived while the chat was closed.
  useEffect(() => {
    if (open) setSeen(chat.messages.length);
  }, [open, chat.messages.length]);
  const unread = open ? 0 : chat.messages.slice(seen).filter((m) => m.role === 'bot' && !m.welcome).length;

  const ask = (question) => {
    setOpen(true);
    chat.send(question);
  };

  return (
    <>
      <header className="site-header">
        <div className="wrap site-header-inner">
          <a href="#top" className="brand"><WaveMark /> wavelink</a>
          <nav aria-label="Main">
            <a href="#help">Support</a>
            <a href="#how">How it works</a>
          </nav>
          <button type="button" className="btn btn-accent" onClick={() => setOpen(true)}>Chat with us</button>
        </div>
      </header>

      <main id="top">
        <section className="hero">
          <div className="wrap">
            <div className="hero-inner">
              <p className="pill"><span className="dot" /> Support online, 24/7</p>
              <h1>Internet that just works. Help that always does.</h1>
              <p className="hero-sub">
                Ask our AI assistant about your connection, your bill or anything else, at any hour. If it sounds like
                you need a person, it hands you over to a human agent.
              </p>
              <div className="hero-actions">
                <button type="button" className="btn btn-accent" onClick={() => setOpen(true)}>Start a chat</button>
                <a className="btn btn-outline" href="#how">See how it works</a>
              </div>
            </div>
          </div>
        </section>

        <section className="wrap section" id="help">
          <h2 className="section-title">What can we help with?</h2>
          <div className="topics">
            {TOPICS.map((t) => (
              <article key={t.title} className="topic">
                <h3>{t.title}</h3>
                <p>{t.text}</p>
                <button type="button" className="link-btn" onClick={() => ask(t.ask)}>
                  Ask: “{t.ask}”
                </button>
              </article>
            ))}
          </div>
        </section>

        <section className="wrap section" id="how">
          <h2 className="section-title">How the assistant works</h2>
          <p className="section-sub">
            Every message goes through a small workflow built with LangGraph. The chat talks to the server over a
            WebSocket, and falls back to a REST call if the socket is not available.
          </p>
          <ol className="steps">
            {STEPS.map((s, i) => (
              <li key={s.name}>
                <span className="step-num">{i + 1}</span>
                <h3>{s.name}</h3>
                <p>{s.text}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer className="site-footer">
        <div className="wrap footer-inner">
          <p>WaveLink is a fictional company created for this demo project.</p>
          <a href="#agent">Agent dashboard</a>
        </div>
      </footer>

      <ChatWidget open={open} onClose={() => setOpen(false)} chat={chat} />

      <button
        type="button"
        className={`launcher ${open ? 'is-hidden' : ''}`}
        onClick={() => setOpen(true)}
        aria-label={unread ? `Open chat, ${unread} new message` : 'Open chat'}
        aria-expanded={open}
        aria-controls="chat-panel"
      >
        <ChatIcon width={26} height={26} />
        {unread > 0 && <span className="badge">{unread}</span>}
      </button>
    </>
  );
}

export default function App() {
  const [hash, setHash] = useState(window.location.hash);

  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);

  // The dashboard is a separate page (/#agent). The chat connection only starts on the public website.
  return hash === '#agent' ? <AgentDashboard /> : <Website />;
}
