import React, { useState } from 'react';

export default function JsonInput({ onPastedData, onGenerateSample, onIngestSubmit, isIngesting }) {
  const [jsonText, setJsonText] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const handleTextChange = (e) => {
    const val = e.target.value;
    setJsonText(val);
    if (!val.trim()) {
      setErrorMsg('');
      return;
    }
    try {
      const parsed = JSON.parse(val);
      const emails = Array.isArray(parsed) ? parsed : (parsed.emails || [parsed]);
      onPastedData(emails);
      setErrorMsg('');
    } catch (err) {
      setErrorMsg('Invalid JSON format');
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target.result);
        const emails = Array.isArray(parsed) ? parsed : (parsed.emails || [parsed]);
        setJsonText(JSON.stringify(emails, null, 2));
        onPastedData(emails);
        setErrorMsg('');
      } catch (err) {
        setErrorMsg('Uploaded file is not valid JSON');
      }
    };
    reader.readAsText(file);
  };

  const handlePasteClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setJsonText(text);
        try {
          const parsed = JSON.parse(text);
          const emails = Array.isArray(parsed) ? parsed : (parsed.emails || [parsed]);
          onPastedData(emails);
          setErrorMsg('');
        } catch (err) {
          setErrorMsg('Pasted content is not valid JSON');
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-1 flex flex-col mb-8">
      {/* Header Toolbar matching code.html */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-outline-variant/50 bg-surface-bright rounded-t-lg">
        <span className="text-body-sm font-body-sm font-semibold text-on-surface-variant flex items-center gap-2">
          <span className="material-symbols-outlined text-[16px]">code</span>
          Raw Email JSON Payload
        </span>
        <div className="flex gap-2 items-center">
          <label className="px-3 py-1.5 border border-outline-variant text-on-surface rounded text-body-sm font-body-sm hover:bg-surface-variant transition-colors flex items-center gap-1 bg-surface-container-lowest cursor-pointer">
            <span className="material-symbols-outlined text-[14px]">upload_file</span>
            Upload JSON
            <input type="file" accept=".json" onChange={handleFileUpload} style={{ display: 'none' }} />
          </label>

          <button
            onClick={handlePasteClipboard}
            type="button"
            className="px-3 py-1.5 border border-outline-variant text-on-surface rounded text-body-sm font-body-sm hover:bg-surface-variant transition-colors flex items-center gap-1 bg-surface-container-lowest"
          >
            <span className="material-symbols-outlined text-[14px]">content_paste</span>
            Paste JSON
          </button>

          <button
            onClick={onIngestSubmit}
            disabled={isIngesting || !jsonText.trim()}
            type="button"
            className="px-4 py-1.5 bg-primary text-on-primary rounded text-body-sm font-body-sm hover:opacity-90 transition-opacity font-semibold flex items-center gap-1 disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[14px]">analytics</span>
            {isIngesting ? 'Analyzing...' : 'Analyze Payload'}
          </button>
        </div>
      </div>

      {/* Textarea matching code.html */}
      <textarea
        className="w-full h-40 p-4 bg-surface-container-lowest text-on-surface font-data-mono text-data-mono resize-none border-none focus:ring-0 focus:outline-none"
        placeholder='Paste raw JSON object array here...
{
  "emails": [
    { "email_id": "em_001", "thread_id": "th_001", "subject": "...", "body": "..." }
  ]
}'
        value={jsonText}
        onChange={handleTextChange}
      />

      {errorMsg && <p className="px-4 pb-2 text-[12px] text-error font-medium">{errorMsg}</p>}

      {/* Sub-bar matching spec 7.3 part 2 */}
      <div className="px-3 py-2 border-t border-outline-variant/30 bg-surface-bright/50 flex justify-between items-center rounded-b-lg">
        <span className="text-[12px] text-on-surface-variant">Synchronous routing via Gemini 2.5 Flash & Rules engine</span>
        <button
          onClick={onGenerateSample}
          type="button"
          className="text-[12px] text-secondary font-medium hover:underline flex items-center gap-1"
        >
          <span className="material-symbols-outlined text-[14px]">auto_awesome</span>
          Load 250 sample emails batch
        </button>
      </div>
    </div>
  );
}
