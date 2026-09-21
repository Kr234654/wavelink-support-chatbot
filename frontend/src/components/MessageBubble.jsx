import { ThumbDownIcon, ThumbUpIcon, UserIcon } from './Icons';

const formatTime = (iso) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

export default function MessageBubble({ message, onRate }) {
  const isUser = message.role === 'user';
  const canRate = !isUser && message.category; // only real answers, not the welcome message or errors

  return (
    <div className={`row ${isUser ? 'row-user' : 'row-bot'}`}>
      <div className="stack">
        <div
          className={[
            'bubble',
            isUser ? 'bubble-user' : 'bubble-bot',
            message.escalated ? 'bubble-escalated' : '',
            message.isError ? 'bubble-error' : '',
          ].join(' ')}
        >
          {message.escalated && (
            <p className="escalation-tag">
              <UserIcon width={14} height={14} /> Passed to a human agent · Ticket {message.ticket}
            </p>
          )}
          <p className="bubble-text">{message.text}</p>
        </div>

        <div className="meta-row">
          <p className="meta">
            {formatTime(message.time)}
            {message.category && <span> · {message.category} · {message.sentiment}</span>}
          </p>
          {canRate && (
            message.rating ? (
              <span className="thanks">Thanks for the feedback</span>
            ) : (
              <span className="rate">
                <button type="button" onClick={() => onRate(message.id, 'up')} aria-label="This answer helped">
                  <ThumbUpIcon width={15} height={15} />
                </button>
                <button type="button" onClick={() => onRate(message.id, 'down')} aria-label="This answer did not help">
                  <ThumbDownIcon width={15} height={15} />
                </button>
              </span>
            )
          )}
        </div>
      </div>
    </div>
  );
}
