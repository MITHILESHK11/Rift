import React, { useState, useRef, useEffect } from 'react';

const PRESET_QUESTIONS = [
  "task",
  "what needs my attention?",
  "how many RFPs do we have?",
  "show high priority tasks",
  "what is the total potential revenue?",
  "show skipped emails",
  "how many spam emails were ignored?",
  "show emails from Orbit Finance",
  "summarize my inbox",
  "what happened in thread th_0091?"
];

export default function ChatPanel({ candidateId, onSendQuery }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      sender: 'agent',
      text: 'Analysis context set to recent database. Ask follow-up questions about tasks, skipped emails, or thread routing history.',
      supportingData: null,
      time: 'Just now'
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOpen]);

  // Reset chat context when candidate changes
  useEffect(() => {
    setMessages([
      {
        sender: 'agent',
        text: 'Analysis context reset to new candidate database. Ask follow-up questions about tasks, skipped emails, or thread routing history.',
        supportingData: null,
        time: 'Just now'
      }
    ]);
  }, [candidateId]);

  const handleSend = async (queryToSend) => {
    const query = queryToSend || inputQuery;
    if (!query.trim() || isLoading) return;

    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsg = { sender: 'user', text: query, supportingData: null, time: nowStr };
    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      // Gather conversation history (excluding the one we just added)
      const historyPayload = messages.map(m => ({
        sender: m.sender,
        text: m.text,
        supporting_data: m.supportingData || null
      }));

      const res = await onSendQuery(query, historyPayload);
      const agentMsg = {
        sender: 'agent',
        text: res.answer || 'No response returned.',
        supportingData: res.supporting_data || null,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'agent',
          text: 'Error executing grounded query against database.',
          supportingData: { error: err.message },
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMinimize = () => {
    setIsOpen(false);
  };

  const handleClose = () => {
    setIsOpen(false);
    // Reset conversation on close
    setMessages([
      {
        sender: 'agent',
        text: 'Analysis context set to recent database. Ask follow-up questions about tasks, skipped emails, or thread routing history.',
        supportingData: null,
        time: 'Just now'
      }
    ]);
  };

  return (
    <>
      {/* Floating Circular RIFT AI Blob Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-inverse-surface border border-outline-variant hover:bg-surface-container-highest shadow-2xl rounded-full flex items-center justify-center cursor-pointer transition-all duration-300 hover:scale-110 active:scale-95 group focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          aria-label="Ask RIFT AI"
          title="Ask RIFT"
        >
          <div className="w-9 h-9 rounded-full overflow-hidden flex items-center justify-center p-0.5 bg-surface-container-lowest shadow-sm">
            <img src="/rift_logo.png" alt="Rift Logo" className="w-full h-full object-contain" />
          </div>
          {/* Subtle floating badge */}
          <span className="absolute -top-1 -right-1 flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-4 w-4 bg-primary text-[8px] text-white font-bold items-center justify-center">ai</span>
          </span>
        </button>
      )}

      {/* Floating Chat Panel */}
      {isOpen && (
        <aside className="fixed bottom-24 right-6 w-[440px] h-[660px] z-50 flex flex-col bg-surface-bright rounded-2xl border border-outline-variant shadow-2xl overflow-hidden transition-all duration-300 animate-slide-up max-w-[calc(100vw-32px)] max-h-[calc(100vh-120px)]">
          {/* Header */}
          <div className="px-6 py-4 border-b border-outline-variant bg-surface-container-lowest shrink-0 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-6 h-6 rounded overflow-hidden flex items-center justify-center p-0.5 bg-surface-container-low border border-outline-variant">
                <img src="/rift_logo.png" alt="Rift" className="w-full h-full object-contain" />
              </div>
              <div>
                <h2 className="text-body-lg font-bold text-on-surface leading-tight">Rift AI</h2>
                <span className="text-[10px] text-on-surface-variant leading-none">Database Grounded Assistant</span>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {/* Minimize button */}
              <button
                onClick={handleMinimize}
                title="Minimize Chat"
                className="p-1.5 hover:bg-surface-variant rounded text-on-surface-variant hover:text-on-surface transition-colors flex items-center justify-center"
              >
                <span className="material-symbols-outlined text-[18px]">remove</span>
              </button>
              {/* Close button */}
              <button
                onClick={handleClose}
                title="Close & Clear Chat"
                className="p-1.5 hover:bg-surface-variant rounded text-on-surface-variant hover:text-on-surface transition-colors flex items-center justify-center"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>
          </div>

          {/* Preset Suggestion Chips */}
          <div className="px-4 py-2 bg-surface-bright border-b border-outline-variant/40 flex flex-wrap gap-1.5 shrink-0 max-h-24 overflow-y-auto">
            {PRESET_QUESTIONS.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(q)}
                className="text-[11px] bg-surface-container-lowest border border-outline-variant hover:bg-surface-variant text-on-surface px-2.5 py-0.5 rounded-full transition-colors truncate max-w-full font-medium"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Chat Messaging Area */}
          <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-5">
            {messages.map((m, idx) => (
              <div key={idx} className="w-full">
                {m.sender === 'user' ? (
                  <div className="flex flex-col items-end gap-1 w-full pl-12">
                    <div className="bg-surface-variant text-on-surface px-4 py-2.5 rounded-2xl rounded-tr-sm text-body-md shadow-sm border border-outline-variant/20">
                      {m.text}
                    </div>
                    <span className="text-[10px] font-body-sm text-on-surface-variant">{m.time}</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-start gap-1.5 w-full pr-4">
                    <div className="flex items-center gap-1.5 text-primary font-bold text-[12px] uppercase tracking-wider">
                      <div className="w-4 h-4 rounded shrink-0 overflow-hidden flex items-center justify-center p-0.5 bg-surface-container-low border border-outline-variant">
                        <img src="/rift_logo.png" alt="Rift" className="w-full h-full object-contain" />
                      </div>
                      Rift Response
                    </div>
                    <div className="bg-surface-container-lowest border border-outline-variant text-on-surface px-4 py-3 rounded-2xl rounded-tl-sm text-body-md shadow-sm w-full">
                      <p className="leading-relaxed whitespace-pre-wrap">{m.text}</p>
                      
                      {/* Dynamic Grounded Supporting Data Rendering */}
                      {m.supportingData && (
                        <SupportingDataView data={m.supportingData} />
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex flex-col items-start gap-1.5 w-full pr-12 animate-pulse">
                <div className="flex items-center gap-1.5 text-primary font-bold text-[12px] uppercase tracking-wider">
                  <div className="w-4 h-4 rounded shrink-0 overflow-hidden flex items-center justify-center p-0.5 bg-surface-container-low border border-outline-variant">
                    <img src="/rift_logo.png" alt="Rift" className="w-full h-full object-contain" />
                  </div>
                  Rift AI
                </div>
                <div className="bg-surface-container-lowest border border-outline-variant text-on-surface-variant px-4 py-3 rounded-2xl rounded-tl-sm text-body-md italic shadow-sm w-full flex items-center gap-2">
                  <span className="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
                  Querying database and analyzing inbox...
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div className="p-4 border-t border-outline-variant bg-surface-container-lowest shrink-0">
            <div className="relative flex items-end bg-background border border-outline-variant rounded-xl focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-shadow">
              <textarea
                className="w-full max-h-24 min-h-[40px] bg-transparent border-none text-on-surface text-body-md p-3 py-2 resize-none focus:ring-0 focus:outline-none"
                placeholder="Ask RIFT..."
                rows={1}
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
              />
              <div className="p-1.5 shrink-0">
                <button
                  onClick={() => handleSend()}
                  disabled={isLoading || !inputQuery.trim()}
                  className="w-8 h-8 flex items-center justify-center rounded-lg bg-primary text-on-primary hover:opacity-95 transition-opacity disabled:opacity-40"
                >
                  <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                    send
                  </span>
                </button>
              </div>
            </div>
            <div className="text-center mt-2.5">
              <span className="text-[9px] font-bold text-on-surface-variant/80 uppercase tracking-widest">
                Grounded Database Analysis
              </span>
            </div>
          </div>
        </aside>
      )}
    </>
  );
}

function SupportingDataView({ data }) {
  if (!data) return null;

  // 1. Task List
  if (data.tasks && Array.isArray(data.tasks)) {
    return (
      <div className="mt-3 bg-surface-container-low border border-outline-variant rounded-lg overflow-hidden">
        <div className="px-3 py-1.5 bg-surface-container border-b border-outline-variant text-[10px] font-bold text-on-surface uppercase tracking-wider">
          Supporting Data: Tasks ({data.count})
        </div>
        <div className="overflow-x-auto max-h-48">
          <table className="w-full text-left text-[11px] border-collapse">
            <thead>
              <tr className="bg-surface-container-high border-b border-outline-variant font-semibold">
                <th className="px-3 py-1.5">Task ID</th>
                <th className="px-3 py-1.5">Title</th>
                <th className="px-3 py-1.5">Priority</th>
                <th className="px-3 py-1.5">Assignee</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/40">
              {data.tasks.map((t) => (
                <tr key={t.task_id} className="hover:bg-surface-variant/30">
                  <td className="px-3 py-1.5 font-mono text-[10px] text-on-surface-variant">{t.task_id}</td>
                  <td className="px-3 py-1.5 font-medium truncate max-w-[120px]" title={t.title}>{t.title}</td>
                  <td className="px-3 py-1.5">
                    <span className={`px-1 py-0.5 rounded text-[9px] font-bold uppercase ${
                      t.priority === 'high' ? 'bg-error-container text-error' :
                      t.priority === 'medium' ? 'bg-secondary-container text-on-secondary-container' :
                      'bg-surface-variant text-on-surface-variant'
                    }`}>
                      {t.priority}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-on-surface-variant">{t.assignee_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <RawJsonView raw={data} />
      </div>
    );
  }

  // 2. Skipped Emails List
  if (data.skipped_emails && Array.isArray(data.skipped_emails)) {
    return (
      <div className="mt-3 bg-surface-container-low border border-outline-variant rounded-lg overflow-hidden">
        <div className="px-3 py-1.5 bg-surface-container border-b border-outline-variant text-[10px] font-bold text-on-surface uppercase tracking-wider">
          Supporting Data: Skipped Emails ({data.count})
        </div>
        <div className="overflow-x-auto max-h-48">
          <table className="w-full text-left text-[11px] border-collapse">
            <thead>
              <tr className="bg-surface-container-high border-b border-outline-variant font-semibold">
                <th className="px-3 py-1.5">Sender</th>
                <th className="px-3 py-1.5">Subject</th>
                <th className="px-3 py-1.5">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/40">
              {data.skipped_emails.map((s, idx) => (
                <tr key={s.email_id || idx} className="hover:bg-surface-variant/30">
                  <td className="px-3 py-1.5 truncate max-w-[100px] text-on-surface-variant">{s.from_email}</td>
                  <td className="px-3 py-1.5 font-medium truncate max-w-[140px]" title={s.subject}>{s.subject}</td>
                  <td className="px-3 py-1.5">
                    <span className="px-1 py-0.5 rounded bg-error-container text-error text-[9px] font-bold uppercase">
                      {s.skip_reason || s.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <RawJsonView raw={data} />
      </div>
    );
  }

  // 3. Thread History List
  if (data.thread_id && data.emails && Array.isArray(data.emails)) {
    return (
      <div className="mt-3 bg-surface-container-low border border-outline-variant rounded-lg overflow-hidden">
        <div className="px-3 py-1.5 bg-surface-container border-b border-outline-variant text-[10px] font-bold text-on-surface uppercase tracking-wider">
          Thread History: {data.thread_id} ({data.count})
        </div>
        <div className="p-3 flex flex-col gap-2 max-h-48 overflow-y-auto">
          {data.emails.map((e, idx) => (
            <div key={idx} className="bg-surface-bright p-2 rounded border border-outline-variant/40 text-[11px]">
              <div className="flex justify-between text-[9px] text-on-surface-variant mb-1">
                <span>From: {e.from_email}</span>
                <span>{e.processed_at}</span>
              </div>
              <div className="font-semibold truncate" title={e.subject}>{e.subject}</div>
              <div className="text-[10px] text-primary font-medium mt-1">Status: {e.status}</div>
            </div>
          ))}
        </div>
        <RawJsonView raw={data} />
      </div>
    );
  }

  // 4. Revenue / Total value card
  if (data.total_deal_value_inr !== undefined) {
    return (
      <div className="mt-3 bg-surface-container-low border border-outline-variant rounded-lg p-3">
        <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-1">
          Total Opportunity Value
        </div>
        <div className="text-[20px] font-bold text-primary">
          ₹{data.total_deal_value_inr.toLocaleString('en-IN')}
        </div>
        <RawJsonView raw={data} />
      </div>
    );
  }

  // 5. Stats Breakdown Card
  if (data.total_tasks !== undefined && data.total_skipped !== undefined) {
    return (
      <div className="mt-3 bg-surface-container-low border border-outline-variant rounded-lg p-3">
        <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-2">
          System Overview Statistics
        </div>
        <div className="grid grid-cols-2 gap-2 text-[11px]">
          <div className="bg-surface-bright p-2 rounded border border-outline-variant/50">
            <span className="text-on-surface-variant block text-[9px]">Tasks Created</span>
            <span className="text-[13px] font-bold">{data.total_tasks}</span>
          </div>
          <div className="bg-surface-bright p-2 rounded border border-outline-variant/50">
            <span className="text-on-surface-variant block text-[9px]">Emails Ignored</span>
            <span className="text-[13px] font-bold">{data.total_skipped}</span>
          </div>
          <div className="bg-surface-bright p-2 rounded border border-outline-variant/50">
            <span className="text-on-surface-variant block text-[9px]">Spurious Task Count</span>
            <span className="text-[13px] font-bold">{data.spurious_count}</span>
          </div>
          <div className="bg-surface-bright p-2 rounded border border-outline-variant/50">
            <span className="text-on-surface-variant block text-[9px]">Spurious Rate</span>
            <span className="text-[13px] font-bold">{(data.spurious_rate * 100).toFixed(1)}%</span>
          </div>
        </div>
        <RawJsonView raw={data} />
      </div>
    );
  }

  // 6. General Count card
  if (data.count !== undefined) {
    return (
      <div className="mt-3 bg-surface-container-low border border-outline-variant rounded-lg p-3">
        <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-1">
          Record Count
        </div>
        <div className="text-[20px] font-bold text-primary">
          {data.count}
        </div>
        <RawJsonView raw={data} />
      </div>
    );
  }

  // 7. Generic data block
  return <RawJsonView raw={data} />;
}

function RawJsonView({ raw }) {
  return (
    <details className="group bg-surface-container-high/40 border-t border-outline-variant/50 overflow-hidden">
      <summary className="cursor-pointer px-3 py-1.5 text-[10px] font-medium text-on-surface hover:bg-surface-variant transition-colors flex items-center justify-between list-none">
        <span className="flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[12px] text-on-surface-variant group-open:rotate-90 transition-transform">
            chevron_right
          </span>
          Show Raw JSON
        </span>
      </summary>
      <div className="p-3 bg-surface-container-lowest border-t border-outline-variant/50 overflow-x-auto text-[10px]">
        <pre className="text-data-mono font-data-mono text-on-surface-variant m-0">
          <code>{JSON.stringify(raw, null, 2)}</code>
        </pre>
      </div>
    </details>
  );
}
