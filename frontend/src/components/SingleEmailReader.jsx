import React, { useState } from 'react';

export default function SingleEmailReader({ onIngestSingle, isIngesting }) {
  const [singleFrom, setSingleFrom] = useState('Suresh Kulkarni');
  const [singleEmail, setSingleEmail] = useState('s.kulkarni@meridiansteel.co.in');
  const [singleSubject, setSingleSubject] = useState('RFP - Enterprise Document Management System');
  const [singleBody, setSingleBody] = useState('Dear Team,\n\nMeridian Steel invites proposals for an enterprise DMS covering 4 plants and ~1,200 users. Indicative budget is Rs. 25 lakhs. Proposals must reach us by 12th August 2026.\n\nRegards,\nSuresh Kulkarni');
  const [singleResult, setSingleResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!singleSubject.trim() || !singleBody.trim()) return;
    setSingleResult(null);
    const res = await onIngestSingle({
      from_name: singleFrom,
      from_email: singleEmail,
      subject: singleSubject,
      body: singleBody
    });
    setSingleResult(res);
  };

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-6 mb-8">
      <h3 className="text-headline-sm font-semibold text-on-surface mb-2">Real Email Reader & Router</h3>
      <p className="text-body-sm text-on-surface-variant mb-4">
        Compose or paste any real email to trigger live Gemini 2.5 Flash LLM extraction and business rule routing.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-body-sm font-medium text-on-surface block mb-1">From Name</label>
            <input
              type="text"
              className="w-full bg-background border border-outline-variant rounded p-2 text-body-md text-on-surface focus:outline-none"
              value={singleFrom}
              onChange={(e) => setSingleFrom(e.target.value)}
            />
          </div>
          <div>
            <label className="text-body-sm font-medium text-on-surface block mb-1">From Email</label>
            <input
              type="email"
              className="w-full bg-background border border-outline-variant rounded p-2 text-body-md text-on-surface focus:outline-none"
              value={singleEmail}
              onChange={(e) => setSingleEmail(e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="text-body-sm font-medium text-on-surface block mb-1">Subject</label>
          <input
            type="text"
            className="w-full bg-background border border-outline-variant rounded p-2 text-body-md text-on-surface focus:outline-none"
            value={singleSubject}
            onChange={(e) => setSingleSubject(e.target.value)}
          />
        </div>

        <div>
          <label className="text-body-sm font-medium text-on-surface block mb-1">Body</label>
          <textarea
            className="w-full h-32 bg-background border border-outline-variant rounded p-3 text-body-md text-on-surface focus:outline-none resize-none"
            value={singleBody}
            onChange={(e) => setSingleBody(e.target.value)}
          />
        </div>

        <button
          type="submit"
          disabled={isIngesting}
          className="px-4 py-2 bg-primary text-on-primary rounded text-body-sm font-semibold hover:opacity-90 transition-opacity flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-[16px]">send</span>
          {isIngesting ? 'Routing Email...' : 'Read & Route Real Email'}
        </button>

        {singleResult && (
          <div className="mt-4 p-4 bg-surface-container-low border border-outline-variant rounded text-body-sm">
            <h4 className="font-semibold text-on-surface mb-2">Action Result: {singleResult.action}</h4>
            {singleResult.task ? (
              <div className="grid grid-cols-2 gap-2 text-on-surface font-mono text-[12px]">
                <div>Assignee: {singleResult.task.assignee_id}</div>
                <div>Category: {singleResult.task.category}</div>
                <div>Priority: {singleResult.task.priority}</div>
                <div>Deal Value: {singleResult.task.deal_value_inr ? `₹${singleResult.task.deal_value_inr.toLocaleString('en-IN')}` : 'null'}</div>
              </div>
            ) : (
              <p className="text-error">Filtered as {singleResult.action} by Rule 4.</p>
            )}
            {singleResult.reasoning && (
              <p className="text-on-surface-variant text-[12px] italic mt-2">"{singleResult.reasoning}"</p>
            )}
          </div>
        )}
      </form>
    </div>
  );
}
