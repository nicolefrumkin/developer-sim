'use client';

import React from 'react';
import Editor from '@monaco-editor/react';

type Ticket = {
  id: string;
  title: string;
  brief: string;
  files_seed: { path: string; content: string }[];
  language: string;
  runtime: string;
};

type RunResult = {
  run_id: string;
  ticket_id: string;
  status: 'passed' | 'failed' | 'error';
  feedback: { path: string; line: number; kind: string; msg: string }[];
  stats: { tests_total: number; tests_passed: number; time_ms: number };
  artifacts?: { stdout?: string; stderr?: string };
  started_at?: string;
  finished_at?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

export default function Page() {
  const [loadingTicket, setLoadingTicket] = React.useState(false);
  const [running, setRunning] = React.useState(false);
  const [ticket, setTicket] = React.useState<Ticket | null>(null);
  const [code, setCode] = React.useState<string>('');
  const [result, setResult] = React.useState<RunResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  // Load seed ticket on mount
  React.useEffect(() => {
    (async () => {
      try {
        setLoadingTicket(true);
        setError(null);
        const res = await fetch(`${API_BASE}/v1/tickets/next`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as Ticket;
        setTicket(data);
        // take first seed file content as the editor content
        const first = data.files_seed?.[0];
        setCode(first?.content ?? '');
      } catch (e: any) {
        setError(`Failed to load ticket: ${e.message || e.toString()}`);
      } finally {
        setLoadingTicket(false);
      }
    })();
  }, []);

  async function runTests() {
    if (!ticket) return;
    try {
      setRunning(true);
      setResult(null);
      setError(null);

      const body = {
        ticket_id: ticket.id,
        code,
        target_path: ticket.files_seed?.[0]?.path || 'app/main.py',
        timeout_ms: 15000,
      };

      const res = await fetch(`${API_BASE}/v1/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const json = (await res.json()) as RunResult;
      setResult(json);
    } catch (e: any) {
      setError(`Run failed: ${e.message || e.toString()}`);
    } finally {
      setRunning(false);
    }
  }

  const statusBadge = result ? (
    <span
      style={{
        padding: '4px 8px',
        borderRadius: 6,
        fontWeight: 600,
        background:
          result.status === 'passed'
            ? '#d1fae5'
            : result.status === 'failed'
            ? '#fee2e2'
            : '#fde68a',
        color:
          result.status === 'passed'
            ? '#065f46'
            : result.status === 'failed'
            ? '#991b1b'
            : '#92400e',
      }}
    >
      {result.status.toUpperCase()}
    </span>
  ) : null;

  return (
    <main style={{ maxWidth: 1100, margin: '24px auto', padding: '0 16px' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>Job Simulator</h1>
        {statusBadge}
      </header>

      {error && (
        <div style={{ marginTop: 12, padding: 12, borderRadius: 8, background: '#fee2e2', color: '#991b1b' }}>
          {error}
        </div>
      )}

      <section style={{ marginTop: 16 }}>
        {loadingTicket && <div>Loading ticket…</div>}
        {ticket && (
          <>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{ticket.title}</h2>
            <p style={{ marginBottom: 12, color: '#374151' }}>{ticket.brief}</p>

            <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
              <Editor
                height="420px"
                defaultLanguage={ticket.language === 'python' ? 'python' : 'plaintext'}
                value={code}
                onChange={(v) => setCode(v ?? '')}
                options={{
                  fontSize: 14,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button
                onClick={runTests}
                disabled={running}
                style={{
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid #2563eb',
                  background: running ? '#93c5fd' : '#3b82f6',
                  color: 'white',
                  fontWeight: 600,
                  cursor: running ? 'not-allowed' : 'pointer',
                }}
              >
                {running ? 'Running…' : 'Run Tests'}
              </button>
            </div>
          </>
        )}
      </section>

      {result && (
        <section style={{ marginTop: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Result</h3>
          <pre
            style={{
              background: '#f9fafb',
              padding: 12,
              borderRadius: 8,
              border: '1px solid #e5e7eb',
              maxHeight: 240,
              overflow: 'auto',
            }}
          >
{JSON.stringify(
  {
    status: result.status,
    stats: result.stats,
    started_at: result.started_at,
    finished_at: result.finished_at,
  },
  null,
  2
)}
          </pre>

          {result.feedback && result.feedback.length > 0 && (
            <>
              <h4 style={{ fontWeight: 700, marginTop: 10, marginBottom: 8 }}>Feedback</h4>
              <ul style={{ display: 'grid', gap: 6 }}>
                {result.feedback.map((f, idx) => (
                  <li key={idx} style={{ padding: 8, border: '1px solid #e5e7eb', borderRadius: 8 }}>
                    <div style={{ fontFamily: 'monospace' }}>
                      <strong>{f.kind}</strong> at {f.path}:{f.line}
                    </div>
                    <div style={{ color: '#374151', whiteSpace: 'pre-wrap' }}>{f.msg}</div>
                  </li>
                ))}
              </ul>
            </>
          )}

          {result.artifacts?.stdout && (
            <>
              <h4 style={{ fontWeight: 700, marginTop: 10, marginBottom: 8 }}>Pytest Output</h4>
              <pre
                style={{
                  background: '#111827',
                  color: '#e5e7eb',
                  padding: 12,
                  borderRadius: 8,
                  maxHeight: 240,
                  overflow: 'auto',
                }}
              >
{result.artifacts.stdout}
              </pre>
            </>
          )}
        </section>
      )}
    </main>
  );
}
