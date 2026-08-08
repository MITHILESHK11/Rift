import React, { useState, useRef, useEffect } from 'react';

const PRESET_QUESTIONS = [
  "How many emails were proposal or RFP related?",
  "How many were marketing versus actual spam we correctly ignored?",
  "Show me everything sitting in triage and why.",
  "What's our spurious rate so far?",
  "Which tasks are high priority but low confidence?",
  "How many emails were about GST refunds?",
  "Send Aarti an email about the Meridian Steel RFP.",
  "What's the total deal value of all open RFPs?",
  "Did any thread get updated more than once?"
];

export default function ChatPanel({ candidateId, onSendQuery }) {
  const [messages, setMessages] = useState([
    {
      sender: 'agent',
      text: 'Analysis context set to recent ingestion payload. Ask follow-up questions about processed emails, task counts, or team queues.',
      supportingData: null,
      time: 'Just now'
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (queryToSend) => {
    const query = queryToSend || inputQuery;
    if (!query.trim() || isLoading) return;

    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsg = { sender: 'user', text: query, supportingData: null, time: nowStr };
    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const res = await onSendQuery(query);
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

  return (
    <aside className="w-[400px] shrink-0 border-l border-outline-variant bg-surface-bright flex flex-col h-full shadow-[-4px_0_12px_rgba(15,23,42,0.02)] z-10 relative">
      {/* Header matching code.html */}
      <div className="px-6 py-5 border-b border-outline-variant bg-surface-container-lowest shrink-0 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
            smart_toy
          </span>
          <h2 className="text-headline-sm font-headline-sm text-on-surface font-semibold">Copilot Analysis</h2>
        </div>
        <button
          onClick={() => setMessages([{ sender: 'agent', text: 'Chat history cleared.', supportingData: null, time: 'Just now' }])}
          title="Clear History"
          className="p-1 hover:bg-surface-variant rounded text-on-surface-variant transition-colors"
        >
          <span className="material-symbols-outlined text-[20px]">delete_sweep</span>
        </button>
      </div>

      {/* Preset Suggestion Chips */}
      <div className="px-4 py-2 bg-surface-bright border-b border-outline-variant/40 flex flex-wrap gap-1.5 max-h-28 overflow-y-auto">
        {PRESET_QUESTIONS.map((q, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(q)}
            className="text-[11px] bg-surface-container-lowest border border-outline-variant hover:bg-surface-variant text-on-surface px-2 py-0.5 rounded-full transition-colors text-left truncate max-w-full"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Chat Area matching code.html */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
        <div className="text-center text-label-caps font-label-caps text-on-surface-variant uppercase tracking-wider">
          Analysis context set to recent ingestion payload
        </div>

        {messages.map((m, idx) => (
          <div key={idx} className="w-full">
            {m.sender === 'user' ? (
              <div className="flex flex-col items-end gap-1 w-full pl-8">
                <div className="bg-surface-variant text-on-surface px-4 py-3 rounded-lg rounded-tr-sm text-body-md font-body-md">
                  {m.text}
                </div>
                <span className="text-[11px] font-body-sm text-on-surface-variant">{m.time}</span>
              </div>
            ) : (
              <div className="flex flex-col items-start gap-2 w-full pr-4">
                <div className="flex items-center gap-2 text-primary font-semibold text-body-sm font-body-sm">
                  <div className="w-4 h-4 rounded shrink-0 overflow-hidden flex items-center justify-center">
                    <img src="/rift_logo.png" alt="Rift" className="w-full h-full object-contain" />
                  </div>
                  Rift AI
                </div>
                <div className="bg-surface-container-lowest border border-outline-variant text-on-surface px-4 py-3 rounded-lg rounded-tl-sm text-body-md font-body-md shadow-sm w-full">
                  <p className="mb-2">{m.text}</p>

                  {/* Collapsible JSON Data Grounding matching code.html details element */}
                  {m.supportingData && (
                    <details className="group bg-surface-container-low rounded border border-outline-variant/50 overflow-hidden mt-3" open>
                      <summary className="cursor-pointer px-3 py-2 text-body-sm font-body-sm font-medium text-on-surface hover:bg-surface-variant transition-colors flex items-center justify-between list-none">
                        <span className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-[16px] text-on-surface-variant group-open:rotate-90 transition-transform">
                            chevron_right
                          </span>
                          <span className="material-symbols-outlined text-[14px]">data_object</span>
                          View Extracted Entities (supporting_data)
                        </span>
                      </summary>
                      <div className="p-3 bg-surface-container-lowest border-t border-outline-variant/50 overflow-x-auto">
                        <pre className="text-data-mono font-data-mono text-on-surface-variant m-0">
                          <code>{JSON.stringify(m.supportingData, null, 2)}</code>
                        </pre>
                      </div>
                    </details>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex flex-col items-start gap-2 w-full pr-8">
            <div className="flex items-center gap-2 text-primary font-semibold text-body-sm font-body-sm">
              <div className="w-4 h-4 rounded shrink-0 overflow-hidden flex items-center justify-center">
                <img src="/rift_logo.png" alt="Rift" className="w-full h-full object-contain" />
              </div>
              Rift AI
            </div>
            <div className="bg-surface-container-lowest border border-outline-variant text-on-surface px-4 py-3 rounded-lg rounded-tl-sm text-body-md font-body-md text-on-surface-variant italic">
              Executing grounded SQL database query...
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Chat Input matching code.html */}
      <div className="p-4 border-t border-outline-variant bg-surface-container-lowest shrink-0">
        <div className="relative flex items-end bg-background border border-outline-variant rounded-lg focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-shadow">
          <textarea
            className="w-full max-h-32 min-h-[44px] bg-transparent border-none text-on-surface text-body-md font-body-md p-3 py-2.5 resize-none focus:ring-0 focus:outline-none"
            placeholder="Ask follow-up questions..."
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
              className="w-8 h-8 flex items-center justify-center rounded bg-primary text-on-primary hover:opacity-90 transition-opacity disabled:opacity-40"
            >
              <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                send
              </span>
            </button>
          </div>
        </div>
        <div className="text-center mt-2">
          <span className="text-[10px] font-body-sm text-on-surface-variant uppercase tracking-wider">
            AI analysis grounded in computed database results
          </span>
        </div>
      </div>
    </aside>
  );
}
