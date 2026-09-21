import { useCallback, useEffect, useState } from 'react';
import { API_URL } from '../config';

const KEY_STORAGE = 'wavelink-admin-key';
const formatDate = (iso) => new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });

// Page for support agents: statistics and the list of escalated tickets. Open it with /#agent.
export default function AgentDashboard() {
  const [key, setKey] = useState(() => sessionStorage.getItem(KEY_STORAGE) || '');
  const [input, setInput] = useState('');
  const [tab, setTab] = useState('open');
  const [data, setData] = useState({ tickets: [], stats: null });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const signOut = useCallback((message = '') => {
    sessionStorage.removeItem(KEY_STORAGE);
    setKey('');
    setData({ tickets: [], stats: null });
    setError(message);
  }, []);

  const request = useCallback(async (path, options = {}) => {
    const res = await fetch(`${API_URL}${path}`, { ...options, headers: { 'X-Admin-Key': key } });
    if (res.status === 401) throw new Error('unauthorized');
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    return res.json();
  }, [key]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [stats, tickets] = await Promise.all([request('/api/stats'), request(`/api/tickets?status=${tab}`)]);
      setData({ stats, tickets });
    } catch (err) {
      if (err.message === 'unauthorized') signOut('That admin key is not correct.');
      else setError('Could not reach the server. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, [request, tab, signOut]);

  useEffect(() => {
    if (key) load();
  }, [key, tab, load]);

  const resolve = async (ticket) => {
    try {
      await request(`/api/tickets/${ticket}/resolve`, { method: 'POST' });
      load();
    } catch {
      setError('Could not resolve that ticket. Try again.');
    }
  };

  const login = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    sessionStorage.setItem(KEY_STORAGE, input.trim());
    setKey(input.trim());
    setInput('');
  };

  if (!key) {
    return (
      <main className="agent-login">
        <form className="login-card" onSubmit={login}>
          <h1>Agent dashboard</h1>
          <p>Enter the admin key to see escalated tickets and statistics.</p>
          <label htmlFor="admin-key">Admin key</label>
          <input id="admin-key" type="password" value={input} onChange={(e) => setInput(e.target.value)} autoFocus />
          {error && <p className="form-error" role="alert">{error}</p>}
          <button type="submit" className="btn btn-accent">Sign in</button>
          <a href="#" className="back">Back to the website</a>
        </form>
      </main>
    );
  }

  const { stats, tickets } = data;
  const rated = stats ? stats.feedback.up + stats.feedback.down : 0;
  const helpful = rated ? `${Math.round((stats.feedback.up / rated) * 100)}%` : 'No ratings yet';
  const maxCategory = stats ? Math.max(1, ...Object.values(stats.by_category)) : 1;

  return (
    <main className="agent">
      <div className="wrap">
        <div className="agent-head">
          <div>
            <h1>Agent dashboard</h1>
            <p className="section-sub">Escalated conversations and how the assistant is doing.</p>
          </div>
          <div className="agent-actions">
            <button type="button" className="btn btn-small" onClick={load} disabled={loading}>{loading ? 'Loading…' : 'Refresh'}</button>
            <button type="button" className="btn btn-small" onClick={() => signOut()}>Sign out</button>
            <a href="#" className="btn btn-small">Back to website</a>
          </div>
        </div>

        {error && <p className="form-error" role="alert">{error}</p>}

        {stats && (
          <>
            <div className="stat-grid">
              <div className="stat"><span>Messages handled</span><strong>{stats.messages}</strong></div>
              <div className="stat"><span>Escalated to humans</span><strong>{stats.escalated}</strong></div>
              <div className="stat"><span>Open tickets</span><strong>{stats.open_tickets}</strong></div>
              <div className="stat"><span>Answers rated helpful</span><strong>{helpful}</strong></div>
            </div>

            <div className="bars" aria-label="Messages by category">
              {Object.entries(stats.by_category).map(([name, count]) => (
                <div key={name} className="bar-row">
                  <span>{name}</span>
                  <div className="bar"><div style={{ width: `${(count / maxCategory) * 100}%` }} /></div>
                  <b>{count}</b>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="tabs" role="tablist" aria-label="Ticket status">
          {['open', 'resolved', 'all'].map((t) => (
            <button key={t} type="button" role="tab" aria-selected={tab === t} className={tab === t ? 'is-active' : ''} onClick={() => setTab(t)}>
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Ticket</th><th>Time</th><th>Category</th><th>Customer message</th><th>Status</th></tr>
            </thead>
            <tbody>
              {tickets.length === 0 && (
                <tr><td colSpan="5" className="empty">{loading ? 'Loading…' : 'No tickets here yet.'}</td></tr>
              )}
              {tickets.map((t) => (
                <tr key={t.ticket}>
                  <td><b>{t.ticket}</b></td>
                  <td>{formatDate(t.created_at)}</td>
                  <td>{t.category}</td>
                  <td className="msg">{t.query}</td>
                  <td>
                    {t.status === 'open'
                      ? <button type="button" className="btn btn-small btn-dark" onClick={() => resolve(t.ticket)}>Mark resolved</button>
                      : <span className="resolved">Resolved</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
