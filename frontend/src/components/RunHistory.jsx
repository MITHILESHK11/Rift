import React, { useState, useEffect } from 'react';

export default function RunHistory({ candidateId, API_BASE }) {
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [runDetails, setRunDetails] = useState(null);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  
  // Decision Trace inside RunDetails
  const [traceEmail, setTraceEmail] = useState(null);

  const fetchRuns = async () => {
    if (!candidateId) return;
    setLoadingRuns(true);
    try {
      const res = await fetch(`${API_BASE}/api/runs?candidate_id=${encodeURIComponent(candidateId)}`);
      if (res.ok) {
        const data = await res.json();
        setRuns(data || []);
      }
    } catch (err) {
      console.error("Error fetching runs:", err);
    } finally {
      setLoadingRuns(false);
    }
  };

  const fetchRunDetails = async (runId) => {
    if (!candidateId || !runId) return;
    setLoadingDetails(true);
    setTraceEmail(null);
    try {
      const res = await fetch(`${API_BASE}/api/runs/${runId}?candidate_id=${encodeURIComponent(candidateId)}`);
      if (res.ok) {
        const data = await res.json();
        setRunDetails(data);
      }
    } catch (err) {
      console.error(`Error fetching details for run ${runId}:`, err);
    } finally {
      setLoadingDetails(false);
    }
  };

  useEffect(() => {
    fetchRuns();
    setSelectedRunId(null);
    setRunDetails(null);
  }, [candidateId]);

  useEffect(() => {
    if (selectedRunId) {
      fetchRunDetails(selectedRunId);
    }
  }, [selectedRunId]);

  const formatDate = (dateStr) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: true });
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div className="flex-1 flex flex-col gap-6 p-6 overflow-y-auto bg-surface-container-lowest">
      <div>
        <h1 className="text-display-sm font-bold text-on-surface">Ingestion Run History</h1>
        <p className="text-body-md text-on-surface-variant">Track processing batches, data volumes, and spurious routing rates over time.</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6 items-start w-full">
        {/* Left Side: Runs List */}
        <div className={`w-full lg:w-[350px] bg-surface-container border border-outline-variant/30 rounded-xl overflow-hidden shrink-0 ${selectedRunId ? 'hidden lg:flex flex-col' : 'flex flex-col'}`}>
          <div className="px-4 py-3 bg-surface-container-high border-b border-outline-variant/30 flex justify-between items-center">
            <h2 className="text-title-sm font-bold text-on-surface">Ingestion Batches</h2>
            <button 
              onClick={fetchRuns}
              className="p-1.5 hover:bg-surface-container-highest rounded transition-colors"
            >
              <span className="material-symbols-outlined text-[18px]">refresh</span>
            </button>
          </div>

          {loadingRuns && runs.length === 0 ? (
            <div className="p-8 text-center text-on-surface-variant">Loading run history...</div>
          ) : runs.length === 0 ? (
            <div className="p-8 text-center text-on-surface-variant">No ingestion runs recorded. Load JSON batch payload to start.</div>
          ) : (
            <div className="divide-y divide-outline-variant/15 max-h-[600px] overflow-y-auto">
              {runs.map((r, idx) => {
                const runNo = runs.length - idx;
                const isSelected = selectedRunId === r.run_id;
                const spuriousPercent = r.processed_count > 0 ? ((r.spurious_count / r.processed_count) * 100).toFixed(0) : '0';
                
                return (
                  <button
                    key={r.run_id}
                    onClick={() => setSelectedRunId(r.run_id)}
                    className={`w-full p-4 text-left transition-colors flex flex-col gap-1.5 border-l-4 ${
                      isSelected ? 'bg-secondary-container/20 border-l-primary' : 'border-l-transparent hover:bg-surface-container-high'
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-on-surface">Run #{runNo}</span>
                      <span className="text-[11px] font-mono text-on-surface-variant/80">{r.run_id}</span>
                    </div>

                    <div className="text-[11px] text-on-surface-variant">{formatDate(r.processed_at)}</div>

                    <div className="flex gap-3 text-body-xs font-medium text-on-surface-variant/90 mt-1">
                      <span>Inp: <b className="text-on-surface">{r.processed_count}</b></span>
                      <span>Cre: <b className="text-on-surface">{r.tasks_created}</b></span>
                      <span>Skip: <b className="text-on-surface">{r.emails_skipped}</b></span>
                      <span className="text-error font-bold">Spurious: {spuriousPercent}%</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Side: Run Details View */}
        {selectedRunId ? (
          <div className="flex-1 w-full flex flex-col gap-6">
            {/* Top Bar for Mobile view Back action */}
            <div className="flex items-center gap-3 lg:hidden">
              <button 
                onClick={() => setSelectedRunId(null)}
                className="flex items-center gap-1 text-xs font-bold text-primary"
              >
                <span className="material-symbols-outlined text-[16px]">arrow_back</span>
                Back to Runs List
              </button>
            </div>

            {loadingDetails ? (
              <div className="text-center py-12 text-on-surface-variant">Loading run details...</div>
            ) : runDetails ? (
              <>
                {/* Aggregate Summary Header */}
                <div className="bg-surface-container border border-outline-variant/30 rounded-xl p-5 flex flex-col gap-3">
                  <div className="flex justify-between items-center">
                    <div>
                      <h2 className="text-title-md font-bold text-on-surface">Run {runDetails.run.run_id} Details</h2>
                      <span className="text-body-xs text-on-surface-variant">{formatDate(runDetails.run.processed_at)}</span>
                    </div>
                    
                    <div className="text-right flex flex-col items-end">
                      <span className="text-body-xs font-bold text-error uppercase">Spurious Rate</span>
                      <span className="text-headline-sm font-bold text-error">
                        {runDetails.run.processed_count > 0 
                          ? `${((runDetails.run.spurious_count / runDetails.run.processed_count) * 100).toFixed(1)}%` 
                          : '0.0%'}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-2">
                    <div className="bg-surface-container-high p-3 rounded-lg text-center">
                      <div className="text-[10px] text-on-surface-variant uppercase font-bold">Processed</div>
                      <div className="text-headline-xs font-bold text-on-surface">{runDetails.run.processed_count}</div>
                    </div>
                    <div className="bg-surface-container-high p-3 rounded-lg text-center">
                      <div className="text-[10px] text-on-surface-variant uppercase font-bold">Created Tasks</div>
                      <div className="text-headline-xs font-bold text-on-surface">{runDetails.run.tasks_created}</div>
                    </div>
                    <div className="bg-surface-container-high p-3 rounded-lg text-center">
                      <div className="text-[10px] text-on-surface-variant uppercase font-bold">Updated Tasks</div>
                      <div className="text-headline-xs font-bold text-on-surface">{runDetails.run.tasks_updated}</div>
                    </div>
                    <div className="bg-surface-container-high p-3 rounded-lg text-center">
                      <div className="text-[10px] text-on-surface-variant uppercase font-bold">Skipped Mails</div>
                      <div className="text-headline-xs font-bold text-on-surface">{runDetails.run.emails_skipped}</div>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col xl:flex-row gap-6 items-start">
                  {/* Processed Item List */}
                  <div className="flex-1 bg-surface-container border border-outline-variant/30 rounded-xl overflow-hidden w-full">
                    <div className="px-4 py-3 bg-surface-container-high border-b border-outline-variant/30 font-bold text-title-sm text-on-surface">
                      Processed Emails Log
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-body-sm">
                        <thead>
                          <tr className="bg-surface-bright border-b border-outline-variant/20 text-on-surface-variant font-bold">
                            <th className="px-4 py-2.5">Email Subject</th>
                            <th className="px-4 py-2.5">Intent / Dir</th>
                            <th className="px-4 py-2.5">Action Outcome</th>
                            <th className="px-4 py-2.5 text-right">Trace</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-outline-variant/10">
                          {runDetails.items.map((i) => {
                            const isSelected = traceEmail?.email_id === i.email_id;
                            return (
                              <tr 
                                key={i.email_id} 
                                className={`hover:bg-surface-container-high transition-colors ${isSelected ? 'bg-secondary-container/20' : ''}`}
                              >
                                <td className="px-4 py-3 max-w-[240px]">
                                  <div className="font-semibold text-on-surface truncate" title={i.subject}>{i.subject || '(No Subject)'}</div>
                                  <div className="text-[11px] text-on-surface-variant truncate">{i.from_name || i.from_email}</div>
                                </td>
                                <td className="px-4 py-3">
                                  <div className="font-semibold text-on-surface text-[12px]">{i.intent}</div>
                                  <div className="text-[11px] text-on-surface-variant/80 uppercase">{i.direction}</div>
                                </td>
                                <td className="px-4 py-3">
                                  <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold uppercase ${
                                    i.status === 'created_task' ? 'bg-success-container text-success' :
                                    i.status === 'updated_task' ? 'bg-primary-container text-primary' : 'bg-surface-container-highest text-on-surface-variant'
                                  }`}>
                                    {i.status.replace('skipped_', 'skip_')}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-right">
                                  <button
                                    onClick={() => setTraceEmail(i)}
                                    className="px-3 py-1 bg-surface-container-highest hover:bg-secondary-container hover:text-on-secondary-container rounded text-xs font-semibold transition-colors"
                                  >
                                    View
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Item Decision Trace Panel (Inside run details page) */}
                  {traceEmail && (
                    <div className="w-full xl:w-[350px] bg-surface-container border border-outline-variant/30 rounded-xl p-5 flex flex-col gap-4 sticky top-6 shadow-md shrink-0">
                      <div className="flex justify-between items-center border-b border-outline-variant/30 pb-3">
                        <h3 className="text-title-sm font-bold text-on-surface">Item Decision Trace</h3>
                        <button 
                          onClick={() => setTraceEmail(null)}
                          className="p-1 hover:bg-surface-container-high rounded transition-colors"
                        >
                          <span className="material-symbols-outlined text-[18px]">close</span>
                        </button>
                      </div>

                      <div className="flex flex-col gap-3">
                        <div className="bg-surface-container-high p-3 rounded-lg border border-outline-variant/20">
                          <div className="text-[10px] text-on-surface-variant uppercase font-bold tracking-wider font-mono">Routing Decision</div>
                          <div className="text-title-md font-bold text-on-surface uppercase mt-1">
                            {traceEmail.status.replace('skipped_', 'skip_').replace('_', ' ')}
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="bg-surface-container-high p-2 rounded">
                            <div className="text-[9px] text-on-surface-variant uppercase">Assignee</div>
                            <div className="font-bold text-on-surface mt-0.5">{traceEmail.assignee_id || 'None (Skipped)'}</div>
                          </div>
                          <div className="bg-surface-container-high p-2 rounded">
                            <div className="text-[9px] text-on-surface-variant uppercase">Confidence</div>
                            <div className="font-bold text-on-surface mt-0.5">{Math.round(traceEmail.confidence * 100)}%</div>
                          </div>
                          <div className="bg-surface-container-high p-2 rounded">
                            <div className="text-[9px] text-on-surface-variant uppercase">Intent</div>
                            <div className="font-bold text-on-surface mt-0.5">{traceEmail.intent}</div>
                          </div>
                          <div className="bg-surface-container-high p-2 rounded">
                            <div className="text-[9px] text-on-surface-variant uppercase">Direction</div>
                            <div className="font-bold text-on-surface mt-0.5 uppercase">{traceEmail.direction}</div>
                          </div>
                        </div>

                        <div>
                          <h4 className="text-body-sm font-bold text-on-surface mb-1">Trace Explanation</h4>
                          <p className="text-body-xs text-on-surface-variant bg-surface-bright p-3 rounded-lg border border-outline-variant/10 leading-relaxed leading-snug">
                            {traceEmail.reasoning || "Trace logs generated by rules/classifier fallback."}
                          </p>
                        </div>

                        {traceEmail.signals && traceEmail.signals.length > 0 && (
                          <div>
                            <h4 className="text-body-sm font-bold text-on-surface mb-1">Signals Extracted</h4>
                            <div className="flex flex-col gap-1">
                              {traceEmail.signals.map((sig, idx) => (
                                <div key={idx} className="flex items-center gap-1.5 text-body-xs text-on-surface-variant">
                                  <span className="material-symbols-outlined text-[14px] text-success font-bold">check</span>
                                  <span>{sig}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {traceEmail.rules_triggered && traceEmail.rules_triggered.length > 0 && (
                          <div>
                            <h4 className="text-body-sm font-bold text-on-surface mb-1">Rules Triggered</h4>
                            <div className="flex flex-wrap gap-1">
                              {traceEmail.rules_triggered.map((rule, idx) => (
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
            ) : null}
          </div>
        ) : (
          <div className="flex-1 bg-surface-container border border-outline-variant/30 rounded-xl p-8 text-center text-on-surface-variant justify-center items-center flex flex-col gap-3 min-h-[300px]">
            <span className="material-symbols-outlined text-[48px] text-on-surface-variant/40">history_toggle_off</span>
            <div>
              <h3 className="text-title-sm font-bold text-on-surface">No Run Selected</h3>
              <p className="text-body-xs text-on-surface-variant/80 mt-1">Select an ingestion run batch on the left panel to inspect detailed logs and trace execution.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
