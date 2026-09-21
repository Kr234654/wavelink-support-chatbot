import { useEffect, useRef } from 'react';
import ChatInput from './ChatInput';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';
import { CloseIcon, HeadsetIcon, RefreshIcon } from './Icons';

export const SUGGESTIONS = [
  'My internet connection keeps dropping. Can you help?',
  'Where can I find my receipt?',
  'What are your business hours?',
];

const STATUS_TEXT = {
  online: 'Online · replies in seconds',
  connecting: 'Connecting…',
  offline: 'Reconnecting…',
};

export default function ChatWidget({ open, onClose, chat }) {
  const { messages, status, typing, mode, send, askForHuman, newChat, rate } = chat;
  const listRef = useRef(null);

  // Keep the newest message in view.
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [messages.length, typing, open]);

  const onlyWelcome = messages.length <= 1;

  const onNewChat = () => {
    if (messages.length <= 2 || window.confirm('Start a new chat? The current conversation will be cleared.')) newChat();
  };

  return (
    <section
      id="chat-panel"
      className={`panel ${open ? 'is-open' : ''}`}
      aria-label="WaveLink support chat"
      aria-hidden={!open}
      inert={open ? undefined : ''}
    >
      <header className="panel-head">
        <div>
          <h2>WaveLink Assistant</h2>
          <p className={`status status-${status}`}>
            <span className="dot" /> {STATUS_TEXT[status]}
          </p>
        </div>
        <div className="head-actions">
          <button type="button" className="icon-btn" onClick={onNewChat} aria-label="Start a new chat" title="New chat">
            <RefreshIcon width={20} height={20} />
          </button>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close chat">
            <CloseIcon />
          </button>
        </div>
      </header>

      <div className="messages" ref={listRef} role="log" aria-live="polite" aria-label="Conversation">
        {messages.map((m) => <MessageBubble key={m.id} message={m} onRate={rate} />)}
        {typing && <TypingIndicator />}

        {onlyWelcome && (
          <div className="suggestions">
            <p>Try one of these:</p>
            {SUGGESTIONS.map((s) => (
              <button key={s} type="button" className="suggestion" onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}
      </div>

      {mode === 'rules' && (
        <p className="mode-note">Demo mode: replies are rule-based. Add an LLM key on the server for AI replies.</p>
      )}
      <div className="toolbar">
        <button type="button" className="human-btn" onClick={askForHuman}>
          <HeadsetIcon width={16} height={16} /> Talk to a human
        </button>
      </div>
      <ChatInput onSend={send} />
    </section>
  );
}
