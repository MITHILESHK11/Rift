import React, { useState } from 'react';

export default function Settings({ candidateId, onClearDatabase }) {
  const [confirmInput, setConfirmInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const handleReset = async (e) => {
    e.preventDefault();
    if (confirmInput.trim().toLowerCase() !== 'confirm') {
      return;
    }
    
    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await onClearDatabase();
      if (res && res.status === 'error') {
        throw new Error(res.message);
      }
      setSuccessMsg(`Database for candidate '${candidateId}' wiped successfully.`);
      setConfirmInput('');
    } catch (err) {
      setErrorMsg(err.message || 'Failed to clear database');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
      <div className="px-cell-padding-h py-3 border-b border-outline-variant bg-surface-bright flex justify-between items-center shrink-0">
        <div>
          <h3 className="text-headline-sm font-headline-sm text-on-surface font-semibold">Settings & System Actions</h3>
          <p className="text-[12px] text-on-surface-variant">Manage database resources and candidate scopes</p>
        </div>
      </div>

      <div className="p-cell-padding-h py-cell-padding-v overflow-y-auto flex-1 flex flex-col justify-start items-center">
        <div className="max-w-xl w-full bg-white dark:bg-inverse-surface border border-outline-variant rounded-xl p-6 shadow-sm mt-8">
          <div className="flex items-center gap-3 mb-4 text-error">
            <span className="material-symbols-outlined text-[28px]">warning</span>
            <h4 className="text-[18px] font-semibold leading-tight">Danger Zone: Reset Database</h4>
          </div>

          <p className="text-body-sm text-on-surface-variant mb-6 leading-relaxed">
            This action will permanently delete all tasks, skipped email logs, thread timelines, and run logs
            scoped under the active candidate ID: <strong className="font-mono text-on-surface bg-surface-variant px-1 rounded">{candidateId}</strong>.
            This action is irreversible.
          </p>

          <form onSubmit={handleReset} className="space-y-4">
            <div>
              <label htmlFor="confirm-verify" className="block text-body-sm font-semibold text-on-surface mb-2">
                To verify, type <strong className="font-mono text-error">confirm</strong> in the input below:
              </label>
              <input
                id="confirm-verify"
                type="text"
                className="w-full bg-background border border-outline-variant rounded px-3 py-2 text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:outline-none"
                placeholder="Type 'confirm' here"
                value={confirmInput}
                onChange={(e) => setConfirmInput(e.target.value)}
                disabled={loading}
                autoComplete="off"
              />
            </div>

            {errorMsg && (
              <div className="p-3 bg-error-container text-error rounded text-body-sm font-medium border border-error/20">
                {errorMsg}
              </div>
            )}

            {successMsg && (
              <div className="p-3 bg-secondary-container text-on-secondary-container rounded text-body-sm font-medium border border-outline-variant">
                {successMsg}
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                disabled={confirmInput.trim().toLowerCase() !== 'confirm' || loading}
                className={`px-4 py-2 rounded text-body-sm font-semibold flex items-center gap-2 transition-colors ${
                  confirmInput.trim().toLowerCase() === 'confirm' && !loading
                    ? 'bg-error text-white hover:bg-red-700 cursor-pointer'
                    : 'bg-surface-variant text-on-surface-variant opacity-60 cursor-not-allowed'
                }`}
              >
                {loading ? (
                  <>Wiping data...</>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[16px]">delete_forever</span>
                    Reset Database
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
