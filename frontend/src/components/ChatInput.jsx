import { useState } from 'react';
import { SendIcon } from './Icons';

export default function ChatInput({ onSend }) {
  const [value, setValue] = useState('');

  const submit = (e) => {
    e.preventDefault();
    if (!value.trim()) return;
    onSend(value);
    setValue('');
  };

  return (
    <form className="composer" onSubmit={submit}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Type your question"
        aria-label="Type your question"
        maxLength={1000}
        autoComplete="off"
      />
      <button type="submit" className="send" aria-label="Send message" disabled={!value.trim()}>
        <SendIcon width={20} height={20} />
      </button>
    </form>
  );
}
