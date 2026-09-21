export default function TypingIndicator() {
  return (
    <div className="row row-bot" role="status" aria-label="The assistant is typing">
      <div className="bubble bubble-bot typing">
        <span /><span /><span />
      </div>
    </div>
  );
}
