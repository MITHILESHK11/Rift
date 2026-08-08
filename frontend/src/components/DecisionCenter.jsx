import React, { useState, useEffect } from 'react';

export default function DecisionCenter({ candidateId, API_BASE }) {
  const [stats, setStats] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [selectedDecision, setSelectedDecision] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchDecisionData = async () => {
    if (!candidateId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/decision-center?candidate_id=${encodeURIComponent(candidateId)}`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats);
        setDecisions(data.recent_decisions || []);
      }
    } catch (err) {
      console.error("Error fetching decision center data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDecisionData();
  }, [candidateId]);

  const getPriorityBadgeClass = (prio) => {
    switch (String(prio).toLowerCase()) {
      case 'high': return 'bg-error-container text-error font-semibold';
      case 'medium': return 'bg-warning-container text-warning font-semibold';
      case 'low': return 'bg-secondary-container text-on-secondary-container';
      default: return 'bg-surface-container-high text-on-surface-variant';
    }
  };

  const getConfidenceLevel = (score) => {
    const val = parseFloat(score);
    if (val >= 0.85) return { text: "HIGH", cls: "text-success bg-success-container/20 border border-success/30" };
    if (val >= 0.65) return { text: "MEDIUM", cls: "text-warning bg-warning-container/20 border border-warning/30" };
    return { text: "LOW", cls: "text-error bg-error-container/20 border border-error/30" };
  };

  return (
    <div className="flex-1 flex flex-col gap-6 p-6 overflow-y-auto bg-surface-container-lowest">
      <div>
        <h1 className="text-display-sm font-bold text-on-surface">Decision Center</h1>
        <p className="text-body-md text-on-surface-variant">Analyze, audit, and trace RIFT's automated routing logic.</p>
      </div>

      {loading && !stats ? (
        <div className="text-center py-12 text-on-surface-variant">Loading decision center telemetry...</div>
      ) : (
        <>
          {/* Telemetry Cards Grid */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-surface-container border border-outline-variant/30 rounded-xl p-4 flex flex-col gap-1">
              <span className="text-[11px] font-bold text-on-surface-variant tracking-wider uppercase">Total Decisions</span>
              <span className="text-headline-md font-bold text-on-surface">{stats?.total_decisions || 0}</span>
            </div>
            <div className="bg-surface-container border border-outline-variant/30 rounded-xl p-4 flex flex-col gap-1">
              <span className="text-[11px] font-bold text-success tracking-wider uppercase">High Confidence</span>
              <span className="text-headline-md font-bold text-success">{stats?.high_confidence || 0}</span>
            </div>
            <div className="bg-surface-container border border-outline-variant/30 rounded-xl p-4 flex flex-col gap-1">
              <span className="text-[11px] font-bold text-warning tracking-wider uppercase">Med Confidence</span>
              <span className="text-headline-md font-bold text-warning">{stats?.medium_confidence || 0}</span>
            </div>
            <div className="bg-surface-container border border-outline-variant/30 rounded-xl p-4 flex flex-col gap-1">
              <span className="text-[11px] font-bold text-error tracking-wider uppercase">Low Confidence</span>
              <span className="text-headline-md font-bold text-error">{stats?.low_confidence || 0}</span>
            </div>
            <div className="bg-surface-container border border-outline-variant/30 rounded-xl p-4 flex flex-col gap-1">
              <span className="text-[11px] font-bold text-primary tracking-wider uppercase">Spurious Rate</span>
              <span className="text-headline-md font-bold text-primary">
                {stats?.spurious_rate ? `${(stats.spurious_rate * 100).toFixed(1)}%` : '0.0%'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-surface-container-high rounded-xl p-3 text-center">
              <div className="text-[11px] font-bold text-on-surface-variant uppercase">Tasks Created</div>
              <div className="text-title-lg font-bold text-on-surface mt-1">{stats?.tasks_created || 0}</div>
            </div>
            <div className="bg-surface-container-high rounded-xl p-3 text-center">
              <div className="text-[11px] font-bold text-on-surface-variant uppercase">Tasks Updated</div>
              <div className="text-title-lg font-bold text-on-surface mt-1">{stats?.tasks_updated || 0}</div>
            </div>
            <div className="bg-surface-container-high rounded-xl p-3 text-center">
              <div className="text-[11px] font-bold text-on-surface-variant uppercase">Emails Skipped</div>
              <div className="text-title-lg font-bold text-on-surface mt-1">{stats?.emails_skipped || 0}</div>
            </div>
            <div className="bg-surface-container-high rounded-xl p-3 text-center">
              <div className="text-[11px] font-bold text-on-surface-variant uppercase">Average Confidence</div>
              <div className="text-title-lg font-bold text-on-surface mt-1">
                {stats?.avg_confidence ? `${(stats.avg_confidence * 100).toFixed(0)}%` : '100%'}
              </div>
            </div>
          </div>

          {/* Decisions Table & Drawer Split Layout */}
          <div className="flex flex-col lg:flex-row gap-6 items-start">
            <div className="flex-1 bg-surface-container border border-outline-variant/30 rounded-xl overflow-hidden w-full">
              <div className="px-4 py-3 bg-surface-container-high border-b border-outline-variant/30 flex justify-between items-center">
                <h2 className="text-title-sm font-bold text-on-surface">Recent Routing Decisions</h2>
                <button 
                  onClick={fetchDecisionData}
                  className="p-1.5 hover:bg-surface-container-highest rounded transition-colors"
                  title="Refresh decisions"
                >
                  <span className="material-symbols-outlined text-[18px]">refresh</span>
                </button>
              </div>

              {decisions.length === 0 ? (
                <div className="p-8 text-center text-on-surface-variant">No routing decisions logged yet. Ingest emails to populate.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-body-sm">
                    <thead>
                      <tr className="bg-surface-bright border-b border-outline-variant/20 text-on-surface-variant font-bold">
                        <th className="px-4 py-2.5">Email / Sender</th>
                        <th className="px-4 py-2.5">Intent / Dir</th>
                        <th className="px-4 py-2.5">Outcome / Owner</th>
                        <th className="px-4 py-2.5">Confidence</th>
                        <th className="px-4 py-2.5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant/10">
                      {decisions.map((d) => {
                        const conf = getConfidenceLevel(d.confidence);
                        const isSelected = selectedDecision?.email_id === d.email_id;
                        return (
                          <tr 
                            key={d.email_id}
                            className={`hover:bg-surface-container-high transition-colors ${isSelected ? 'bg-secondary-container/20' : ''}`}
                          >
                            <td className="px-4 py-3 max-w-[200px]">
                              <div className="font-semibold text-on-surface truncate" title={d.subject}>{d.subject || '(No Subject)'}</div>
                              <div className="text-[11px] text-on-surface-variant truncate">{d.from_name || d.from_email}</div>
                            </td>
                            <td className="px-4 py-3">
                              <div className="font-semibold text-on-surface text-[12px]">{d.intent}</div>
                              <div className="text-[11px] text-on-surface-variant/80 uppercase tracking-wider">{d.direction}</div>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold uppercase mr-2 ${
                                d.status === 'created_task' ? 'bg-success-container text-success' :
                                d.status === 'updated_task' ? 'bg-primary-container text-primary' : 'bg-surface-container-highest text-on-surface-variant'
                              }`}>
                                {d.status.replace('skipped_', 'skip_')}
                              </span>
                              {d.assignee_id && (
                                <span className="text-[11px] font-medium text-on-surface-variant">{d.assignee_id}</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <span className={`inline-block px-1.5 py-0.5 rounded text-[11px] font-bold ${conf.cls}`}>
                                {Math.round(d.confidence * 100)}% {conf.text}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <button
                                onClick={() => setSelectedDecision(d)}
                                className="px-3 py-1 bg-surface-container-highest text-on-surface hover:bg-secondary-container hover:text-on-secondary-container rounded text-xs font-semibold transition-colors"
                              >
                                Trace
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Decision Trace Detail Drawer (Right side) */}
            {selectedDecision && (
              <div className="w-full lg:w-[380px] bg-surface-container border border-outline-variant/30 rounded-xl p-5 flex flex-col gap-4 sticky top-6 shadow-md">
                <div className="flex justify-between items-center border-b border-outline-variant/30 pb-3">
                  <h3 className="text-title-sm font-bold text-on-surface">Decision Trace</h3>
                  <button 
                    onClick={() => setSelectedDecision(null)}
                    className="p-1 hover:bg-surface-container-high rounded transition-colors"
                  >
                    <span className="material-symbols-outlined text-[18px]">close</span>
                  </button>
                </div>

                <div className="flex flex-col gap-3">
                  <div className="bg-surface-container-high p-3 rounded-lg border border-outline-variant/20">
                    <div className="text-[10px] text-on-surface-variant uppercase font-bold tracking-wider">Outcome Decision</div>
                    <div className="text-title-md font-bold text-on-surface uppercase mt-1">
                      {selectedDecision.status.replace('skipped_', 'skip_').replace('_', ' ')}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-surface-container-high p-2 rounded">
                      <div className="text-[9px] text-on-surface-variant uppercase">Assignee</div>
                      <div className="font-bold text-on-surface mt-0.5">{selectedDecision.assignee_id || 'None (Skipped)'}</div>
                    </div>
                    <div className="bg-surface-container-high p-2 rounded">
                      <div className="text-[9px] text-on-surface-variant uppercase">Priority</div>
                      <div className="font-bold text-on-surface mt-0.5 uppercase">{selectedDecision.priority || 'medium'}</div>
                    </div>
                    <div className="bg-surface-container-high p-2 rounded">
                      <div className="text-[9px] text-on-surface-variant uppercase">Intent Type</div>
                      <div className="font-bold text-on-surface mt-0.5">{selectedDecision.intent}</div>
                    </div>
                    <div className="bg-surface-container-high p-2 rounded">
                      <div className="text-[9px] text-on-surface-variant uppercase">Direction</div>
                      <div className="font-bold text-on-surface mt-0.5 uppercase">{selectedDecision.direction}</div>
                    </div>
                  </div>

                  {/* Why RIFT Decided This */}
                  <div>
                    <h4 className="text-body-sm font-bold text-on-surface mb-1">Why RIFT Decided This</h4>
                    <p className="text-body-xs text-on-surface-variant bg-surface-bright p-3 rounded-lg border border-outline-variant/10 leading-relaxed">
                      {selectedDecision.reasoning || "Evaluation processed via rules criteria."}
                    </p>
                  </div>

                  {/* Signals Detected */}
                  {selectedDecision.signals && selectedDecision.signals.length > 0 && (
                    <div>
                      <h4 className="text-body-sm font-bold text-on-surface mb-1">Signals Detected</h4>
                      <div className="flex flex-col gap-1">
                        {selectedDecision.signals.map((sig, idx) => (
                          <div key={idx} className="flex items-center gap-1.5 text-body-xs text-on-surface-variant">
                            <span className="material-symbols-outlined text-[14px] text-success font-bold">check</span>
                            <span>{sig}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Rules Triggered */}
                  {selectedDecision.rules_triggered && selectedDecision.rules_triggered.length > 0 && (
                    <div>
                      <h4 className="text-body-sm font-bold text-on-surface mb-1">Rules Triggered</h4>
                      <div className="flex flex-wrap gap-1">
                        {selectedDecision.rules_triggered.map((rule, idx) => (
                          <span 
                            key={idx} 
                            className="text-[10px] font-mono px-2 py-0.5 bg-secondary-container/20 text-on-secondary-container border border-outline-variant/30 rounded"
                          >
                            {rule}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
