import React from 'react';

export default function RawTable({ rawEmails }) {
  if (!rawEmails || rawEmails.length === 0) {
    return (
      <div className="glass-card" style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
        <p>No email batch loaded yet. Paste JSON or click "Generate 250 Sample Emails" above.</p>
      </div>
    );
  }

  return (
    <div className="glass-card" style={{ marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>2. Raw Email Input Table (Pre-Routing Sanity View)</h3>
        <span className="badge badge-medium">{rawEmails.length} Emails</span>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>From Name</th>
              <th>From Email</th>
              <th>Subject</th>
              <th>Received At</th>
              <th>Thread ID</th>
              <th>Body Preview</th>
            </tr>
          </thead>
          <tbody>
            {rawEmails.slice(0, 50).map((em, idx) => (
              <tr key={em.email_id || idx}>
                <td style={{ fontWeight: 500 }}>{em.from_name || 'N/A'}</td>
                <td style={{ color: 'var(--text-secondary)' }}>{em.from_email || 'N/A'}</td>
                <td style={{ fontWeight: 500 }}>{em.subject}</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {em.received_at ? em.received_at.split('T')[0] : 'N/A'}
                </td>
                <td>
                  <code style={{ fontSize: '0.78rem', color: '#93c5fd' }}>{em.thread_id}</code>
                </td>
                <td style={{ color: 'var(--text-secondary)', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {em.body ? em.body.substring(0, 80) + '...' : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rawEmails.length > 50 && (
        <p style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '12px' }}>
          Showing first 50 of {rawEmails.length} emails.
        </p>
      )}
    </div>
  );
}
