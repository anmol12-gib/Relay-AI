import React, { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Activity, ArrowDown, ArrowRight, ArrowUp, Check, CheckCircle2, ChevronDown, CircleHelp, Clock3, Code2, Copy, Cpu, Database, ExternalLink, Fingerprint, Gauge, Layers3, Menu, MessageSquareText, MoreHorizontal, Plus, Radio, RotateCcw, Send, Settings2, ShieldCheck, Sparkles, Terminal, X, Zap } from 'lucide-react';

const API = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const newSession = () => `s-${crypto.randomUUID()}`;
const SUGGESTIONS = [
  { icon: Sparkles, label: 'Learn something new', prompt: 'Explain how large language models work in simple terms, with an analogy.' },
  { icon: Code2, label: 'Build something great', prompt: 'Suggest a clean architecture for a small scalable web application.' },
  { icon: Layers3, label: 'Think through a problem', prompt: 'Help me break down a complex problem into small, actionable steps.' },
  { icon: Zap, label: 'Get inspired', prompt: 'Share five unusual but practical ideas for improving my productivity.' },
];

function useConnectivity() {
  const [health, setHealth] = useState({ status: 'checking' });
  const check = useCallback(async () => {
    try {
      const res = await fetch(`${API}/health`, { signal: AbortSignal.timeout(8000) });
      const body = await res.json();
      setHealth(res.ok && body.status === 'ok' ? body : { status: 'offline' });
    } catch { setHealth({ status: 'offline' }); }
  }, []);
  useEffect(() => { check(); const timer = setInterval(check, 25000); return () => clearInterval(timer); }, [check]);
  return { health, check };
}

function SourceBadge({ source }) {
  return <span data-testid="meta-source" className={`source-badge ${source === 'LLM_CACHE' ? 'cached' : 'live'}`}><span className="source-dot" />{source}</span>;
}

function Message({ entry, index, onCopy }) {
  if (entry.role === 'user') return <div className="message user-msg"><div className="message-user-bubble">{entry.content}</div><div className="user-avatar">Y</div></div>;
  if (entry.role === 'error') return <div className="message assistant-msg"><div className="assistant-avatar"><ShieldCheck size={17}/></div><div className="assistant-body"><div className="error-message"><CircleHelp size={17}/><span>{entry.content}</span></div></div></div>;
  const m = entry.metadata || {};
  return <div className="message assistant-msg" data-testid="assistant-message"><div className="assistant-avatar"><Sparkles size={17}/></div><div className="assistant-body"><div className="assistant-message-header"><strong>Relay</strong><span>AI Assistant</span></div><div className="markdown-body"><ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.content}</ReactMarkdown></div><div className="message-toolbar"><button className="icon-button subtle" title="Copy reply" aria-label="Copy reply" onClick={() => onCopy(entry.content)}><Copy size={15}/></button><span className="toolbar-separator"/><SourceBadge source={m.resolution_source}/><span className="meta-chip"><Cpu size={13}/><span data-testid="meta-model">{m.model}</span></span><span className="meta-chip"><Clock3 size={13}/><span data-testid="meta-latency">{m.latency_ms} ms</span></span><span className="meta-chip"><ArrowDown size={13}/><span data-testid="meta-input-tokens">{m.input_tokens}</span> in</span><span className="meta-chip"><ArrowUp size={13}/><span data-testid="meta-output-tokens">{m.output_tokens}</span> out</span>{m.fallback_attempts > 0 && <span className="meta-chip fallback"><ShieldCheck size={13}/> {m.fallback_attempts} failover</span>}</div></div></div>;
}

function App() {
  const [sessionId, setSessionId] = useState(newSession);
  const [entries, setEntries] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showInspector, setShowInspector] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [failureMode, setFailureMode] = useState('none');
  const [copySuccess, setCopySuccess] = useState(false);
  const [lastResponse, setLastResponse] = useState(null);
  const [showScroll, setShowScroll] = useState(false);
  const bottomRef = useRef(null);
  const scrollRef = useRef(null);
  const abortRef = useRef(null);
  const { health, check } = useConnectivity();

  const scrollToBottom = (behavior = 'smooth') => bottomRef.current?.scrollIntoView({ behavior });
  useEffect(() => { scrollToBottom(entries.length ? 'smooth' : 'instant'); }, [entries, busy]);
  useEffect(() => () => abortRef.current?.abort(), []);

  const reset = () => { abortRef.current?.abort(); abortRef.current = null; setSessionId(newSession()); setEntries([]); setInput(''); setLastResponse(null); setBusy(false); setMobileNav(false); setFailureMode('none'); };
  const copyText = async text => { try { await navigator.clipboard.writeText(text); setCopySuccess(true); setTimeout(() => setCopySuccess(false), 1600); } catch {} };

  const send = async (raw = input) => {
    const message = raw.trim();
    if (!message || busy || message.length > 4000) return;
    setInput(''); setEntries(prev => [...prev, { role: 'user', content: message }]); setBusy(true);
    const controller = new AbortController(); abortRef.current = controller;
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (failureMode !== 'none') headers['X-Simulate-Failure'] = failureMode;
      const request = { session_id: sessionId, message };
      if (systemPrompt.trim()) request.system_prompt = systemPrompt.trim();
      const response = await fetch(`${API}/chat`, { method: 'POST', headers, body: JSON.stringify(request), signal: controller.signal });
      let data; try { data = await response.json(); } catch { throw new Error('The server returned an unreadable response. Please try again.'); }
      if (!response.ok) {
        if (response.status === 503) throw new Error(data.detail === 'all providers unavailable' ? 'All providers are temporarily unavailable. Your message was not saved. Try again or switch off failure simulation.' : 'The service is temporarily unavailable. Please try again.');
        if (response.status === 422) throw new Error('This message could not be sent. Check its length and try again.');
        throw new Error(data.detail && typeof data.detail === 'string' ? data.detail : `Request failed (${response.status}).`);
      }
      setEntries(prev => [...prev, { role: 'assistant', content: data.reply, metadata: data.metadata }]);
      setLastResponse(data);
    } catch (error) {
      if (error.name !== 'AbortError') setEntries(prev => [...prev, { role: 'error', content: error instanceof TypeError ? 'Could not reach the API. Check that your backend is online and your frontend API URL is configured.' : error.message }]);
    } finally { if (!controller.signal.aborted) setBusy(false); abortRef.current = null; }
  };

  const cachedCount = entries.filter(e => e.metadata?.resolution_source === 'LLM_CACHE').length;
  const liveCount = entries.filter(e => e.metadata?.resolution_source === 'LIVE_INFERENCE').length;
  const lastMetadata = lastResponse?.metadata;

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
      <div className="brand-row"><div className="logo-mark"><Layers3 size={23} strokeWidth={2.4}/></div><div className="brand-name">relay<span className="brand-period">.</span></div><span className="brand-tag">AI</span><button className="mobile-close icon-button" onClick={() => setMobileNav(false)} aria-label="Close menu"><X size={20}/></button></div>
      <div className="sidebar-main"><button className="new-chat-button" onClick={reset}><Plus size={17}/><span>New conversation</span><span className="shortcut">+</span></button><div className="nav-section-label">WORKSPACE</div><button className="nav-item active" onClick={() => setMobileNav(false)}><MessageSquareText size={18}/> <span>Playground</span><div className="active-rail"/></button><button className={`nav-item ${showInspector ? 'nav-soft-active' : ''}`} onClick={() => { setShowInspector(true); setMobileNav(false); }}><Activity size={18}/><span>Request inspector</span></button><button className="nav-item" onClick={() => { setShowSettings(true); setMobileNav(false); }}><Settings2 size={18}/><span>Configuration</span></button><div className="nav-section-label session-label">CURRENT SESSION</div><div className="current-session"><span className="session-symbol"><MessageSquareText size={16}/></span><span className="session-text">{entries.find(x => x.role === 'user')?.content.slice(0, 27) || 'Untitled conversation'}</span><span className="session-indicator"/></div></div>
      <div className="sidebar-bottom"><div className="infrastructure-panel"><div className="infra-top"><span className="infra-icon"><ShieldCheck size={16}/></span><strong>Resilience engine</strong><span className="infra-live">ACTIVE</span></div><div className="infra-line"><span>Automatic failover</span><Check size={15}/></div><div className="infra-line"><span>Intelligent caching</span><Check size={15}/></div><div className="infra-line"><span>Session persistence</span><Check size={15}/></div></div><div className="sidebar-footer"><div className="footer-avatar">R</div><div><strong>Relay Workspace</strong><span>Developer preview · v1.0</span></div><MoreHorizontal size={19}/></div></div>
    </aside>
    {mobileNav && <div className="mobile-overlay" onClick={() => setMobileNav(false)}/>}
    <main className="main-panel"><header className="topbar"><div className="topbar-left"><button className="icon-button hamburger" aria-label="Open menu" onClick={() => setMobileNav(true)}><Menu size={20}/></button><span className="breadcrumb">Workspace</span><span className="breadcrumb-divider">/</span><strong>Playground</strong><span className="header-caret"><ChevronDown size={14}/></span></div><div className="topbar-right"><div className={`connection-chip ${health.status === 'ok' ? 'online' : health.status === 'checking' ? 'checking' : 'offline'}`}><span className="connection-pulse"/>{health.status === 'ok' ? 'All systems operational' : health.status === 'checking' ? 'Connecting…' : 'Backend disconnected'}</div><span className="topbar-separator"/><button className="icon-button" title="Configuration" onClick={() => setShowSettings(true)}><Settings2 size={19}/></button><button className="icon-button" title="Request inspector" onClick={() => setShowInspector(true)}><Activity size={19}/></button></div></header>
      <div className="chat-scroll" ref={scrollRef} onScroll={e => { const el = e.currentTarget; setShowScroll(el.scrollHeight - el.scrollTop - el.clientHeight > 300); }}><div className="conversation-container">{entries.length === 0 ? <div className="welcome"><div className="welcome-emblem"><div className="emblem-halo halo-one"/><div className="emblem-halo halo-two"/><div className="welcome-logo"><Sparkles size={32} strokeWidth={1.7}/></div></div><div className="welcome-eyebrow"><span className="eyebrow-line"/> YOUR AI WORKSPACE <span className="eyebrow-line"/></div><h1>Every great idea<br/>starts with a <span>conversation.</span></h1><p className="welcome-subtitle">Meet your thinking partner. Thoughtful answers, seamless conversations, and reliable intelligence—every single time.</p><div className="suggestion-grid">{SUGGESTIONS.map(s => <button key={s.label} className="suggestion-card" onClick={() => send(s.prompt)}><div className="suggestion-icon"><s.icon size={20}/></div><span>{s.label}</span><ArrowRight className="suggestion-arrow" size={16}/></button>)}</div></div> : <div className="conversation-thread">{entries.map((entry, index) => <Message key={index} entry={entry} index={index} onCopy={copyText}/>)}{busy && <div className="message assistant-msg"><div className="assistant-avatar"><Sparkles size={17}/></div><div className="assistant-body"><div className="assistant-message-header"><strong>Relay</strong><span>Thinking...</span></div><div className="thinking-pulse"><span/><span/><span/></div></div></div>}</div>}<div ref={bottomRef}/></div></div>
      {showScroll && <button className="scroll-bottom" onClick={() => scrollToBottom()} aria-label="Scroll to bottom"><ArrowDown size={17}/></button>}
      <div className="composer-region"><div className="composer-wrap"><div className="composer-box"><textarea data-testid="chat-input" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }} rows={1} maxLength={4000} placeholder="Ask me anything..." aria-label="Message Relay" disabled={busy}/><div className="composer-bottom"><div className="composer-left"><span className="model-pill"><span className="model-dot"/><span>Relay AI</span><ChevronDown size={13}/></span><span className="composer-divider"/><span className="context-pill"><ShieldCheck size={14}/> Failover protected</span></div><div className="composer-right"><span className="char-counter">{input.length > 0 ? `${input.length}/4000` : '↵ to send'}</span><button data-testid="send-button" className="send-button" onClick={() => send()} disabled={busy || !input.trim()} aria-label="Send message"><ArrowUp size={19} strokeWidth={2.5}/></button></div></div></div><div className="composer-disclaimer">Built to stay reliable. Powered by LiteLLM, protected by automatic failover and response caching.</div></div></div>
    </main>
    <aside className="insights-sidebar"><div className="insights-header"><div><span className="insights-eyebrow">LIVE INTELLIGENCE</span><h2>At a glance</h2></div><div className="insights-header-icon"><Activity size={19}/></div></div><div className="insights-content"><div className="insight-status"><div className="status-heading"><span className={`small-live ${health.status === 'ok' ? '' : 'status-down'}`}/><span>System status</span><button title="Refresh status" aria-label="Refresh status" onClick={check}><RotateCcw size={14}/></button></div><div className="status-value">{health.status === 'ok' ? 'Operational' : health.status === 'checking' ? 'Checking...' : 'Unavailable'}</div><div className="status-caption">{health.status === 'ok' ? 'Your workspace is ready to go.' : 'Verify backend configuration.'}</div><div className="health-grid"><div><span>API KEYS</span><strong>{health.keys_configured ?? '—'}</strong></div><div><span>CACHE</span><strong>{health.cache_enabled ? 'On' : '—'}</strong></div></div></div><div className="insight-divider"/><div className="insights-section-heading"><span>SESSION ANALYTICS</span><Gauge size={16}/></div><div className="stat-card"><div className="stat-icon stat-violet"><MessageSquareText size={18}/></div><div><div className="stat-value">{liveCount + cachedCount}</div><div className="stat-label">AI responses</div></div></div><div className="stat-card"><div className="stat-icon stat-green"><Database size={18}/></div><div><div className="stat-value">{cachedCount}</div><div className="stat-label">Cache hits</div></div></div><div className="stat-card"><div className="stat-icon stat-blue"><Clock3 size={18}/></div><div><div className="stat-value">{lastMetadata ? `${lastMetadata.latency_ms}ms` : '—'}</div><div className="stat-label">Last response time</div></div></div><div className="insight-divider"/><div className="insights-section-heading"><span>LAST REQUEST</span><button className="text-link" onClick={() => setShowInspector(true)}>Details <ArrowRight size={13}/></button></div>{lastMetadata ? <div className="last-request"><SourceBadge source={lastMetadata.resolution_source}/><div className="request-data-row"><span>Model</span><strong>{lastMetadata.model}</strong></div><div className="request-data-row"><span>Tokens in / out</span><strong>{lastMetadata.input_tokens} / {lastMetadata.output_tokens}</strong></div><div className="request-data-row"><span>Key</span><strong>{lastMetadata.key_id || 'Cache'}</strong></div><div className="request-data-row"><span>Failed attempts</span><strong>{lastMetadata.fallback_attempts}</strong></div></div> : <div className="request-empty"><Terminal size={24}/><p>Send a message to see live request diagnostics here.</p></div>}<div className="insight-divider"/><div className="insights-section-heading"><span>DEVELOPER TOOLS</span></div><button className="developer-action" onClick={() => setShowInspector(true)}><div className="dev-icon"><Terminal size={18}/></div><div><strong>Request inspector</strong><span>Explore response metadata</span></div><ArrowRight size={16}/></button><button className="developer-action" onClick={() => setShowSettings(true)}><div className="dev-icon"><Settings2 size={18}/></div><div><strong>Test resilience</strong><span>Simulate provider failures</span></div><ArrowRight size={16}/></button></div><div className="insights-footer"><span className="footer-green"/> Engineered for reliability</div></aside>
    {showSettings && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setShowSettings(false); }}><div className="modal" role="dialog" aria-modal="true" aria-label="Configuration"><div className="modal-heading"><div className="modal-icon"><Settings2 size={21}/></div><div><h2>Workspace settings</h2><p>Customize your conversation and test resilience.</p></div><button className="icon-button" onClick={() => setShowSettings(false)} aria-label="Close"><X size={20}/></button></div><div className="modal-body"><label className="field-label" htmlFor="system-prompt">System instructions <span>OPTIONAL</span></label><p className="field-helper">Give Relay a role or tone. Applied to this session's future requests.</p><textarea id="system-prompt" data-testid="system-prompt-input" className="settings-textarea" rows={4} value={systemPrompt} onChange={e => setSystemPrompt(e.target.value)} maxLength={8000} placeholder="You are a helpful and concise assistant..."/><div className="settings-divider"/><div className="settings-section-header"><div className="settings-icon"><ShieldCheck size={18}/></div><div><strong>Failure simulation</strong><p>Force key failures to demonstrate automatic fallback.</p></div></div><label className="field-label" htmlFor="failure-mode">Simulation mode</label><select id="failure-mode" value={failureMode} onChange={e => setFailureMode(e.target.value)}><option value="none">Normal — all keys available</option><option value="key_1=429">key_1 → 429 (rate limit; fail to key_2)</option><option value="key_1=500">key_1 → 500 (server error; fail to key_2)</option><option value="*=429">All keys → 429 (expect clean 503)</option></select><div className="settings-note"><CircleHelp size={16}/><span>Simulated requests deliberately bypass cached responses so failover can be demonstrated. The backend must enable this feature.</span></div></div><div className="modal-actions"><button className="button-secondary" onClick={() => setShowSettings(false)}>Close</button><button className="button-primary" onClick={() => setShowSettings(false)}><Check size={16}/> Save settings</button></div></div></div>}
    {showInspector && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setShowInspector(false); }}><div className="modal inspector-modal" role="dialog" aria-modal="true" aria-label="Request inspector"><div className="modal-heading"><div className="modal-icon"><Activity size={21}/></div><div><h2>Request inspector</h2><p>Understand exactly how Relay answered.</p></div><button className="icon-button" aria-label="Close" onClick={() => setShowInspector(false)}><X size={20}/></button></div><div className="modal-body"><div className="inspector-session"><span>SESSION ID</span><code>{sessionId}</code><button className="icon-button" onClick={() => copyText(sessionId)} title="Copy session ID"><Copy size={15}/></button></div><div className="inspector-endpoint"><strong>History endpoint</strong><p>Stored messages for this conversation, directly from SQLite.</p><a href={`${API}/sessions/${encodeURIComponent(sessionId)}/messages`} target="_blank" rel="noreferrer">Open session history <ExternalLink size={14}/></a></div><div className="inspector-endpoint"><strong>Health endpoint</strong><p>Check key pool readiness, database connectivity and caching.</p><a href={`${API}/health`} target="_blank" rel="noreferrer">Open /health <ExternalLink size={14}/></a></div><div className="inspector-data-header"><strong>Latest response JSON</strong><button className="mini-copy" onClick={() => copyText(JSON.stringify(lastResponse, null, 2))}><Copy size={13}/> Copy JSON</button></div><pre className="json-preview">{lastResponse ? JSON.stringify(lastResponse, null, 2) : '// Send a message to inspect its response.'}</pre></div><div className="modal-actions"><button className="button-primary" onClick={() => setShowInspector(false)}>Done</button></div></div></div>}
    {copySuccess && <div className="toast"><CheckCircle2 size={16}/> Copied to clipboard</div>}
  </div>;
}
export default App;
