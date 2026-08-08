import React from 'react';

export default function SkippedLog({ skippedEmails }) {
  return (
    <div className="flex-1 flex flex-col min-h-0 bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
      <div className="px-cell-padding-h py-3 border-b border-outline-variant bg-surface-bright flex justify-between items-center shrink-0">
        <div>
          <h3 className="text-headline-sm font-headline-sm text-on-surface font-semibold">Skipped Noise Log</h3>
          <p className="text-[12px] text-on-surface-variant">Rule 4 ignored emails (Spam, Out of Office, Newsletters)</p>
        </div>
        <span className="px-2 py-1 bg-surface-variant text-on-surface-variant rounded text-label-caps font-bold">
          {skippedEmails.length} Items
        </span>
      </div>

      <div className="overflow-y-auto flex-1">
        {skippedEmails.length === 0 ? (
          <div className="p-8 text-center text-on-surface-variant text-body-md">
            No noise emails skipped yet.
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead className="sticky top-0 bg-surface-container border-b border-outline-variant z-10">
              <tr>
                <th className="px-cell-padding-h py-cell-padding-v text-body-sm font-semibold text-on-surface">Email ID</th>
                <th className="px-cell-padding-h py-cell-padding-v text-body-sm font-semibold text-on-surface">Sender</th>
                <th className="px-cell-padding-h py-cell-padding-v text-body-sm font-semibold text-on-surface">Subject</th>
                <th className="px-cell-padding-h py-cell-padding-v text-body-sm font-semibold text-on-surface text-right">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/50">
              {skippedEmails.map((s, idx) => (
                <tr key={s.email_id || idx} className="hover:bg-surface-variant/50 transition-colors">
                  <td className="px-cell-padding-h py-cell-padding-v font-mono text-[12px] text-on-surface">{s.email_id}</td>
                  <td className="px-cell-padding-h py-cell-padding-v text-body-sm text-on-surface">{s.from_email || 'N/A'}</td>
                  <td className="px-cell-padding-h py-cell-padding-v text-body-sm text-on-surface font-medium">{s.subject}</td>
                  <td className="px-cell-padding-h py-cell-padding-v text-right">
                    <span className="px-2 py-0.5 rounded bg-error-container text-error text-[11px] font-bold uppercase">
                      {s.skip_reason || s.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
