import React, { useState, useEffect } from 'react';

export default function TaskDashboard({ tasks, skippedEmails, stats, onRefresh, API_BASE = "" }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [assigneeFilter, setAssigneeFilter] = useState('ALL');
  const [priorityFilter, setPriorityFilter] = useState('ALL');
  const [selectedTask, setSelectedTask] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [loadingTimeline, setLoadingTimeline] = useState(false);

  useEffect(() => {
    if (selectedTask) {
      setLoadingTimeline(true);
      fetch(`${API_BASE}/api/thread-timeline/${selectedTask.thread_id}?candidate_id=${encodeURIComponent(selectedTask.candidate_id)}`)
        .then(res => {
          if (res.ok) return res.json();
          return [];
        })
        .then(data => {
          setTimeline(data || []);
        })
        .catch(err => console.error("Error fetching thread timeline:", err))
        .finally(() => setLoadingTimeline(false));
    } else {
      setTimeline([]);
    }
  }, [selectedTask]);

  const filteredTasks = tasks.filter((t) => {
    const matchesSearch =
      !searchTerm ||
      (t.title && t.title.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (t.description && t.description.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (t.company_name && t.company_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (t.task_id && t.task_id.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesAssignee = assigneeFilter === 'ALL' || t.assignee_id === assigneeFilter;
    const matchesPriority = priorityFilter === 'ALL' || t.priority === priorityFilter;

    return matchesSearch && matchesAssignee && matchesPriority;
  });

  const getPriorityBadge = (priority) => {
    const p = (priority || 'medium').toLowerCase();
    if (p === 'high') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-error-container text-error font-label-caps text-label-caps uppercase font-bold">
          High
        </span>
      );
    }
    if (p === 'low') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-surface-variant text-on-surface-variant font-label-caps text-label-caps uppercase font-bold">
          Low
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-caps text-label-caps uppercase font-bold">
        Medium
      </span>
    );
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
      {/* Header & Filter Controls matching code.html */}
      <div className="px-cell-padding-h py-3 border-b border-outline-variant bg-surface-bright flex flex-col md:flex-row justify-between items-start md:items-center gap-3 shrink-0">
        <div>
          <h3 className="text-headline-sm font-headline-sm text-on-surface font-semibold">Routed Task Queue</h3>
          <p className="text-[12px] text-on-surface-variant">Active section 5 tasks created in database store</p>
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {/* Search Input */}
          <div className="relative flex-1 md:w-64">
            <input
              type="text"
              className="w-full bg-background border border-outline-variant rounded px-3 py-1.5 text-body-sm text-on-surface focus:ring-1 focus:ring-primary focus:outline-none"
              placeholder="Filter tasks..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {/* Assignee Filter */}
          <select
            className="bg-background border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none"
            value={assigneeFilter}
            onChange={(e) => setAssigneeFilter(e.target.value)}
          >
            <option value="ALL">All Assignees</option>
            <option value="u_aarti">u_aarti (Enterprise)</option>
            <option value="u_rohit">u_rohit (SMB)</option>
            <option value="u_meera">u_meera (Marketing)</option>
            <option value="u_karan">u_karan (Alliances)</option>
            <option value="u_divya">u_divya (Finance)</option>
            <option value="u_triage">u_triage (Triage)</option>
          </select>

          {/* Priority Filter */}
          <select
            className="bg-background border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
          >
            <option value="ALL">All Priorities</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="low">Low Priority</option>
          </select>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            title="Refresh Tasks"
            className="p-1.5 hover:bg-surface-variant rounded border border-outline-variant text-on-surface-variant transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">refresh</span>
          </button>
        </div>
      </div>

      {/* Processed Data Table matching code.html */}
      <div className="overflow-y-auto flex-1">
        {filteredTasks.length === 0 ? (
          <div className="p-8 text-center text-on-surface-variant text-body-md">
            {tasks.length === 0
              ? 'No tasks found for this candidate.'
              : 'No tasks match your active filter parameters.'}
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead className="sticky top-0 bg-surface-container border-b border-outline-variant z-10">
              <tr>
                <th className="px-cell-padding-h py-cell-padding-v text-body-sm font-body-sm font-semibold text-on-surface w-1/4">
                  Sender & Company
                </th>
                <th className="px-cell-padding-h py-cell-padding-v text-body-sm font-body-sm font-semibold text-on-surface w-2/5">
                  Subject & Title
                </th>
                <th className="px-cell-padding-h py-cell-padding-v text-body-sm font-body-sm font-semibold text-on-surface">
                  Priority
                </th>
                <th className="px-cell-padding-h py-cell-padding-v text-body-sm font-body-sm font-semibold text-on-surface text-right">
                  Assignee & Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/50">
              {filteredTasks.map((t) => (
                <tr
                  key={t.task_id}
                  onClick={() => setSelectedTask(t)}
                  className="hover:bg-surface-variant/50 transition-colors cursor-pointer group"
                >
                  <td className="px-cell-padding-h py-cell-padding-v">
                    <div className="text-body-md font-body-md text-on-surface font-medium truncate">
                      {t.company_name || t.source_email_id}
                    </div>
                    <div className="text-body-sm font-body-sm text-on-surface-variant truncate">
                      {t.task_id} | {t.category}
                    </div>
                  </td>
                  <td className="px-cell-padding-h py-cell-padding-v pr-8">
                    <div className="text-body-md font-body-md text-on-surface truncate font-semibold">
                      {t.title}
                    </div>
                    <div className="text-body-sm font-body-sm text-on-surface-variant truncate">
                      {t.description || 'No description'}
                    </div>
                  </td>
                  <td className="px-cell-padding-h py-cell-padding-v">
                    {getPriorityBadge(t.priority)}
                  </td>
                  <td className="px-cell-padding-h py-cell-padding-v text-right">
                    <span className="text-body-sm font-body-sm text-on-surface font-semibold bg-surface-container-high px-2 py-0.5 rounded">
                      {t.assignee_id}
                    </span>
                    {t.deal_value_inr && (
                      <div className="text-[11px] font-data-mono text-secondary font-medium mt-0.5">
                        ₹{t.deal_value_inr.toLocaleString('en-IN')}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Task Inspection Drawer / Modal */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg max-w-2xl w-full p-6 max-h-[85vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-outline-variant pb-3 mb-4">
              <div>
                <h3 className="text-headline-sm font-bold text-on-surface">Task Inspection - {selectedTask.task_id}</h3>
                <p className="text-body-sm text-on-surface-variant">source_email_id: {selectedTask.source_email_id} | thread_id: {selectedTask.thread_id}</p>
              </div>
              <button
                onClick={() => setSelectedTask(null)}
                className="p-1 hover:bg-surface-variant rounded text-on-surface-variant"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="space-y-4 text-body-md text-on-surface">
              <div>
                <strong className="text-on-surface-variant text-body-sm">Title:</strong>
                <p className="font-semibold text-body-lg mt-0.5">{selectedTask.title}</p>
              </div>

              <div>
                <strong className="text-on-surface-variant text-body-sm">Description:</strong>
                <p className="bg-surface-container-low p-3 rounded border border-outline-variant/50 text-body-sm mt-1">
                  {selectedTask.description || 'No description provided.'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 bg-surface-bright p-3 rounded border border-outline-variant/40 text-body-sm">
                <div><strong>Assignee ID:</strong> <span className="font-mono text-primary font-semibold">{selectedTask.assignee_id}</span></div>
                <div><strong>Category:</strong> <span className="font-mono text-secondary font-semibold">{selectedTask.category}</span></div>
                <div><strong>Priority:</strong> {getPriorityBadge(selectedTask.priority)}</div>
                <div><strong>Due Date:</strong> {selectedTask.due_date || 'null'}</div>
                <div><strong>Deal Value:</strong> {selectedTask.deal_value_inr ? `₹${selectedTask.deal_value_inr.toLocaleString('en-IN')}` : 'null'}</div>
                <div><strong>Company:</strong> {selectedTask.company_name || 'null'}</div>
              </div>

              {/* Decision Trace details inside Task Inspection */}
              <div className="border-t border-outline-variant/40 pt-4 mt-4 space-y-3">
                <h4 className="text-title-sm font-bold text-on-surface flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[18px]">saved_search</span>
                  Decision Trace Details
                </h4>

                <div className="grid grid-cols-2 gap-2 text-xs bg-surface-bright p-3 rounded border border-outline-variant/30">
                  <div><strong>Intent Classification:</strong> <span className="font-semibold">{selectedTask.intent || selectedTask.category || 'ambiguous'}</span></div>
                  <div><strong>Directionality:</strong> <span className="font-semibold uppercase">{selectedTask.direction || 'inbound'}</span></div>
                </div>

                {selectedTask.reasoning && (
                  <div>
                    <strong className="text-on-surface-variant text-[11px] uppercase tracking-wider">Evaluation Reasoning:</strong>
                    <p className="text-body-sm text-on-surface bg-secondary-container/20 p-2.5 rounded mt-1 border border-outline-variant/20 italic">
                      "{selectedTask.reasoning}"
                    </p>
                  </div>
                )}

                {(() => {
                  const parseArray = (val) => {
                    if (!val) return [];
                    if (Array.isArray(val)) return val;
                    try { return JSON.parse(val); } catch(e) { return [val]; }
                  };
                  const sigs = parseArray(selectedTask.signals);
                  const rules = parseArray(selectedTask.rules_triggered);

                  return (
                    <>
                      {sigs.length > 0 && (
                        <div>
                          <strong className="text-on-surface-variant text-[11px] uppercase tracking-wider block mb-1">Signals Detected:</strong>
                          <div className="flex flex-col gap-1">
                            {sigs.map((sig, idx) => (
                              <div key={idx} className="flex items-center gap-1 text-body-xs text-on-surface-variant">
                                <span className="material-symbols-outlined text-[14px] text-success">check</span>
                                <span>{sig}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {rules.length > 0 && (
                        <div>
                          <strong className="text-on-surface-variant text-[11px] uppercase tracking-wider block mb-1">Rules Triggered:</strong>
                          <div className="flex flex-wrap gap-1">
                            {rules.map((rule, idx) => (
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
                    </>
                  );
                })()}
              </div>

              {/* Thread Timeline Section */}
              <div className="border-t border-outline-variant pt-4 mt-4">
                <h4 className="text-title-sm font-bold text-on-surface mb-3 flex items-center gap-2">
                  <span className="material-symbols-outlined text-[20px]">forum</span>
                  Thread Timeline ({selectedTask.thread_id})
                </h4>
                
                {loadingTimeline ? (
                  <div className="text-body-xs text-on-surface-variant italic">Loading thread emails...</div>
                ) : timeline.length === 0 ? (
                  <div className="text-body-xs text-on-surface-variant italic">No emails found for this thread.</div>
                ) : (
                  <div className="relative pl-6 border-l border-outline-variant/60 ml-2 space-y-5 py-1">
                    {timeline.map((email, idx) => {
                      const statusText = email.status.replace('skipped_', 'skip_').replace('_', ' ');
                      const parseSignals = (val) => {
                        if (!val) return [];
                        if (Array.isArray(val)) return val;
                        try { return JSON.parse(val); } catch(e) { return [val]; }
                      };
                      const sigs = parseSignals(email.signals);

                      return (
                        <div key={email.email_id} className="relative">
                          {/* Dot marker */}
                          <div className="absolute -left-[30px] top-1.5 w-3.5 h-3.5 rounded-full bg-surface-container border-2 border-primary z-10" />
                          
                          <div className="text-body-xs text-on-surface-variant flex items-center gap-2">
                            <span className="font-semibold text-on-surface">{email.from_name || email.from_email}</span>
                            <span>·</span>
                            <span>{new Date(email.received_at).toLocaleString('en-IN')}</span>
                          </div>
                          
                          <div className="text-body-sm font-semibold text-on-surface mt-0.5">
                            {email.subject}
                          </div>

                          <div className="mt-1 flex flex-wrap items-center gap-2">
                            <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                              email.status === 'created_task' ? 'bg-success-container text-success' :
                              email.status === 'updated_task' ? 'bg-primary-container text-primary' : 'bg-surface-container-high text-on-surface-variant'
                            }`}>
                              {statusText}
                            </span>
                            {email.direction && (
                              <span className="text-[10px] text-on-surface-variant bg-surface-bright border border-outline-variant/30 px-1.5 py-0.5 rounded uppercase">
                                {email.direction}
                              </span>
                            )}
                          </div>

                          {sigs.length > 0 && (
                            <div className="mt-1.5 bg-surface-bright/50 p-2 rounded border border-outline-variant/10 text-[11px] text-on-surface-variant space-y-0.5">
                              {sigs.map((sig, sidx) => (
                                <div key={sidx} className="flex items-center gap-1.5">
                                  <span className="material-symbols-outlined text-[12px] text-success">check</span>
                                  <span>{sig}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div>
                <strong className="text-on-surface-variant text-body-sm">Raw Entity Extraction (JSON):</strong>
                <pre className="bg-surface-container-low p-3 rounded text-data-mono font-data-mono text-[11px] overflow-x-auto mt-1 border border-outline-variant/50">
                  {JSON.stringify(selectedTask, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
