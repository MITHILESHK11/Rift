import React, { useState } from 'react';

export default function Sidebar({ activeTab, setActiveTab, candidateId, setCandidateId, onClearDatabase }) {
  const [isEditingCand, setIsEditingCand] = useState(false);

  return (
    <nav className="fixed left-0 top-0 h-screen w-64 flex flex-col py-6 px-4 bg-surface-container-low dark:bg-inverse-surface border-r border-outline-variant dark:border-on-surface-variant z-10">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4 px-2">
        <div className="w-10 h-10 rounded-lg bg-surface-container-lowest border border-outline-variant flex items-center justify-center shrink-0 overflow-hidden p-1">
          <img src="/rift_logo.png" alt="Rift Logo" className="w-full h-full object-contain" />
        </div>
        <div>
          <h1 className="text-headline-sm font-headline-sm font-bold text-on-surface dark:text-inverse-on-surface leading-tight">Rift</h1>
          <p className="text-body-sm font-body-sm text-on-surface-variant leading-tight">Enterprise Tier</p>
        </div>
      </div>

      {/* Candidate ID Header Badge */}
      <div className="mb-6 px-2 py-2 bg-surface-bright rounded border border-outline-variant/60 text-[12px] flex items-center justify-between">
        <span className="text-on-surface-variant font-medium">candidate_id:</span>
        {isEditingCand ? (
          <input
            type="email"
            className="w-32 bg-white border border-primary px-1 py-0.5 text-[11px] rounded text-on-surface outline-none"
            value={candidateId}
            onChange={(e) => setCandidateId(e.target.value)}
            onBlur={() => setIsEditingCand(false)}
            onKeyDown={(e) => e.key === 'Enter' && setIsEditingCand(false)}
            autoFocus
          />
        ) : (
          <button
            onClick={() => setIsEditingCand(true)}
            className="font-mono text-primary font-semibold truncate max-w-[120px] hover:underline"
            title="Click to edit candidate_id email"
          >
            {candidateId}
          </button>
        )}
      </div>

      {/* Database Reset Action */}
      <button
        onClick={onClearDatabase}
        className="w-full mb-6 py-2 px-3 bg-surface-container-lowest border border-outline-variant text-on-surface rounded font-body-sm text-body-sm flex items-center justify-center gap-2 hover:bg-error-container hover:text-error transition-colors"
      >
        <span className="material-symbols-outlined text-[16px]">delete</span>
        Reset Database
      </button>

      {/* Navigation */}
      <div className="flex flex-col gap-1 flex-1">
        <button
          onClick={() => setActiveTab('inbox')}
          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-body-md font-body-md transition-all text-left w-full ${
            activeTab === 'inbox'
              ? 'bg-secondary-container text-on-secondary-container font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container-high'
          }`}
        >
          <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
            inbox
          </span>
          Ingest & Triage
        </button>

        <button
          onClick={() => setActiveTab('tasks')}
          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-body-md font-body-md transition-all text-left w-full ${
            activeTab === 'tasks'
              ? 'bg-secondary-container text-on-secondary-container font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container-high'
          }`}
        >
          <span className="material-symbols-outlined text-[20px]">task</span>
          Task Queue
        </button>

        <button
          onClick={() => setActiveTab('single')}
          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-body-md font-body-md transition-all text-left w-full ${
            activeTab === 'single'
              ? 'bg-secondary-container text-on-secondary-container font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container-high'
          }`}
        >
          <span className="material-symbols-outlined text-[20px]">edit_note</span>
          Real Email Reader
        </button>

        <button
          onClick={() => setActiveTab('archives')}
          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-body-md font-body-md transition-all text-left w-full ${
            activeTab === 'archives'
              ? 'bg-secondary-container text-on-secondary-container font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container-high'
          }`}
        >
          <span className="material-symbols-outlined text-[20px]">inventory_2</span>
          Skipped Noise Log
        </button>
      </div>

      {/* Footer Nav - Working API Docs Link */}
      <div className="flex flex-col gap-1 mt-auto pt-4 border-t border-outline-variant">
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:bg-surface-container-high rounded-lg text-body-md font-body-md"
        >
          <span className="material-symbols-outlined text-[20px]">help</span>
          API Docs (/docs)
        </a>
      </div>
    </nav>
  );
}
