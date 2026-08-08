import React, { useState, useEffect } from 'react';

export default function ReviewQueue({ candidateId, API_BASE }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  
  // Filters
  const [confidenceFilter, setConfidenceFilter] = useState('all'); // all, low, medium, high
  const [statusFilter, setStatusFilter] = useState('needs_review'); // needs_review, reviewed, all
  
  // Edit Form State
  const [assigneeId, setAssigneeId] = useState('u_triage');
  const [category, setCategory] = useState('triage');
  const [priority, setPriority] = useState('medium');
  const [notes, setNotes] = useState('');
  const [updating, setUpdating] = useState(false);

  const fetchTriageItems = async () => {
    if (!candidateId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/triage?candidate_id=${encodeURIComponent(candidateId)}`);
      if (res.ok) {
        const data = await res.json();
        setItems(data || []);
      }
    } catch (err) {
      console.error("Error fetching triage queue:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTriageItems();
  }, [candidateId]);

  useEffect(() => {
    if (selectedItem) {
      setAssigneeId(selectedItem.assignee_id || 'u_triage');
      setCategory(selectedItem.category || 'triage');
      setPriority(selectedItem.priority || 'medium');
      setNotes(selectedItem.review_notes || '');
    }
  }, [selectedItem]);

  const handleReviewSubmit = async (e) => {
    e.preventDefault();
    if (!selectedItem) return;
    setUpdating(true);
    try {
      const res = await fetch(`${API_BASE}/api/triage/${selectedItem.email_id}/review?candidate_id=${encodeURIComponent(candidateId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: json_payload()
      });
      if (res.ok) {
        // Refresh
        setSelectedItem(null);
        await fetchTriageItems();
      }
    } catch (err) {
      console.error("Error submitting human review decision:", err);
    } finally {
      setUpdating(false);
    }
  };

  const json_payload = () => {
    return JSON.stringify({
      assignee_id: assigneeId,
      category: category,
      priority: priority,
      notes: notes
    });
  };

  const getFilteredItems = () => {
    return items.filter(item => {
      // 1. Status Filter
      if (statusFilter === 'needs_review' && item.review_status !== 'needs_review') return false;
      if (statusFilter === 'reviewed' && item.review_status !== 'reviewed') return false;

      // 2. Confidence Filter
      const score = item.confidence;
      if (confidenceFilter === 'low' && score >= 0.65) return false;
      if (confidenceFilter === 'medium' && (score < 0.65 || score >= 0.85)) return false;
      if (confidenceFilter === 'high' && score < 0.85) return false;

      return true;
    });
  };

  const filteredItems = getFilteredItems();

  return (
    <div className="flex-1 flex flex-col gap-6 p-6 overflow-y-auto bg-surface-container-lowest">
      <div>
        <h1 className="text-display-sm font-bold text-on-surface">Review Queue</h1>
        <p className="text-body-md text-on-surface-variant">Provide human review for ambiguous, incomplete, or low-confidence routing outcomes.</p>
      </div>

      {/* Filter Options bar */}
      <div className="flex flex-wrap gap-4 items-center bg-surface-container border border-outline-variant/30 px-4 py-3 rounded-xl">
        <div className="flex items-center gap-2">
          <span className="text-body-xs font-semibold text-on-surface-variant uppercase">Confidence</span>
          <select 
            value={confidenceFilter} 
            onChange={(e) => setConfidenceFilter(e.target.value)}
            className="bg-surface-container-high border border-outline-variant rounded px-2 py-1 text-xs"
          >
            <option value="all">All Confidence Tiers</option>
            <option value="low">Low (&lt; 65%)</option>
            <option value="medium">Medium (65% - 84%)</option>
            <option value="high">High (85%+)</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-body-xs font-semibold text-on-surface-variant uppercase">Status</span>
          <select 
            value={statusFilter} 
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-surface-container-high border border-outline-variant rounded px-2 py-1 text-xs"
          >
            <option value="needs_review">Pending Review</option>
            <option value="reviewed">Reviewed</option>
            <option value="all">All Items</option>
          </select>
        </div>

        <button 
          onClick={fetchTriageItems}
          className="ml-auto flex items-center gap-1.5 px-3 py-1 bg-surface-container-highest text-on-surface hover:bg-secondary-container hover:text-on-secondary-container rounded text-xs font-bold transition-all"
        >
          <span className="material-symbols-outlined text-[14px]">refresh</span>
          Sync Queue
        </button>
      </div>

      {loading && items.length === 0 ? (
        <div className="text-center py-12 text-on-surface-variant">Loading review items...</div>
      ) : (
        <div className="flex flex-col lg:flex-row gap-6 items-start">
          {/* Main List */}
          <div className="flex-1 flex flex-col gap-4 w-full">
            {filteredItems.length === 0 ? (
              <div className="bg-surface-container border border-outline-variant/30 rounded-xl p-8 text-center text-on-surface-variant">
                No items require review matching filters. All inbox routing calibrated!
              </div>
            ) : (
              filteredItems.map(item => {
                const confScore = Math.round(item.confidence * 100);
                const isLow = item.confidence < 0.65;
                const isSelected = selectedItem?.email_id === item.email_id;
                
                return (
                  <div 
                    key={item.email_id} 
                    className={`bg-surface-container border rounded-xl p-5 flex flex-col gap-3 transition-all ${
                      isSelected ? 'border-primary shadow-sm bg-secondary-container/10' : 'border-outline-variant/20 hover:border-outline-variant/50'
                    }`}
                  >
                    <div className="flex justify-between items-start gap-4">
                      <div>
                        <h3 className="text-title-sm font-bold text-on-surface leading-snug">{item.subject || '(No Subject)'}</h3>
                        <p className="text-body-xs text-on-surface-variant mt-1">From: <span className="font-semibold">{item.from_name || item.from_email}</span> &lt;{item.from_email}&gt;</p>
                      </div>

                      <div className="flex flex-col items-end gap-1.5 shrink-0">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                          isLow ? 'bg-error-container text-error border border-error/25' : 'bg-warning-container text-warning border border-warning/25'
                        }`}>
                          {confScore}% CONFIDENCE
                        </span>
                        {item.review_status === 'reviewed' && (
                          <span className="bg-success-container text-success px-2 py-0.5 rounded text-[10px] font-bold uppercase">Reviewed</span>
                        )}
                      </div>
                    </div>

                    <div className="text-body-xs text-on-surface-variant line-clamp-2 bg-surface-bright/50 p-2.5 rounded border border-outline-variant/15 font-mono">
                      {item.reasoning || "Triage processing reason not captured."}
                    </div>

                    <div className="flex items-center gap-4 mt-1 border-t border-outline-variant/10 pt-3">
                      <div className="text-body-xs text-on-surface-variant">
                        Detected: <span className="font-semibold text-on-surface">{item.intent}</span> ({item.direction})
                      </div>
                      <div className="text-body-xs text-on-surface-variant">
                        Current: <span className="font-semibold text-on-surface">{item.category}</span> owned by <span className="font-semibold text-on-surface">{item.assignee_id || 'unassigned'}</span>
                      </div>

                      <button
                        onClick={() => setSelectedItem(item)}
                        className="ml-auto px-4 py-1.5 bg-primary text-on-primary hover:bg-primary/90 font-bold rounded text-xs transition-colors"
                      >
                        Review Routing
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Form Side Drawer */}
          {selectedItem && (
            <div className="w-full lg:w-[400px] bg-surface-container border border-outline-variant/30 rounded-xl p-5 flex flex-col gap-4 sticky top-6 shadow-md">
              <div className="flex justify-between items-center border-b border-outline-variant/30 pb-3">
                <div>
                  <h3 className="text-title-sm font-bold text-on-surface">Audit & Reassign</h3>
                  <span className="text-[10px] font-mono text-on-surface-variant/80 block mt-0.5">{selectedItem.email_id}</span>
                </div>
                <button 
                  onClick={() => setSelectedItem(null)}
                  className="p-1 hover:bg-surface-container-high rounded transition-colors"
                >
                  <span className="material-symbols-outlined text-[18px]">close</span>
                </button>
              </div>

              <div className="text-xs bg-surface-bright p-3 rounded-lg border border-outline-variant/15 flex flex-col gap-2">
                <div>
                  <span className="text-[10px] text-on-surface-variant font-bold uppercase block">Subject</span>
                  <span className="font-semibold text-on-surface">{selectedItem.subject}</span>
                </div>
                <div>
                  <span className="text-[10px] text-on-surface-variant font-bold uppercase block">Reasoning for triage</span>
                  <span className="text-on-surface-variant mt-0.5 block italic leading-relaxed">
                    {selectedItem.reasoning || "Marked for review because RIFT classified the query as triage/low-confidence."}
                  </span>
                </div>
              </div>

              <form onSubmit={handleReviewSubmit} className="flex flex-col gap-4 text-body-sm">
                <div className="flex flex-col gap-1">
                  <label className="font-bold text-on-surface">Assignee / Owner</label>
                  <select 
                    value={assigneeId} 
                    onChange={(e) => setAssigneeId(e.target.value)}
                    className="w-full bg-surface-bright border border-outline-variant rounded p-2 text-xs text-on-surface focus:outline-primary"
                  >
                    <option value="u_aarti">Aarti Menon (Enterprise deals &gt; 10L, PSU/Govt)</option>
                    <option value="u_rohit">Rohit Sharma (SMB deals &lt;= 10L)</option>
                    <option value="u_meera">Meera Iyer (Webinars, Sponsorships, PR)</option>
                    <option value="u_karan">Karan Doshi (Channel integrations, Resellers)</option>
                    <option value="u_divya">Divya Rao (Finance, Invoices, Billing)</option>
                    <option value="u_triage">Triage Queue (Needs human review)</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="font-bold text-on-surface">Task Category</label>
                  <select 
                    value={category} 
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full bg-surface-bright border border-outline-variant rounded p-2 text-xs text-on-surface focus:outline-primary"
                  >
                    <option value="enterprise_rfp">Enterprise RFP</option>
                    <option value="smb_enquiry">SMB Enquiry</option>
                    <option value="marketing">Marketing & Webinars</option>
                    <option value="alliances">Alliances & Partnerships</option>
                    <option value="finance">Finance & Billing</option>
                    <option value="triage">Triage (Ambiguous)</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="font-bold text-on-surface">Priority</label>
                  <select 
                    value={priority} 
                    onChange={(e) => setPriority(e.target.value)}
                    className="w-full bg-surface-bright border border-outline-variant rounded p-2 text-xs text-on-surface focus:outline-primary"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High (Urgent &lt; 72h)</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="font-bold text-on-surface">Review Notes (Audit Log)</label>
                  <textarea
                    rows={3}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Enter manual override reasoning here..."
                    className="w-full bg-surface-bright border border-outline-variant rounded p-2 text-xs text-on-surface resize-none focus:outline-primary"
                  />
                </div>

                <button
                  type="submit"
                  disabled={updating}
                  className="w-full py-2 bg-primary text-on-primary hover:bg-primary/90 font-bold rounded text-xs transition-all disabled:opacity-50 mt-2"
                >
                  {updating ? 'Commiting changes...' : 'Submit Decision & Resolve'}
                </button>
              </form>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
