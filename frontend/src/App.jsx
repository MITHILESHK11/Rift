import React, { useState, useEffect } from 'react';

import Sidebar from './components/Sidebar';
import JsonInput from './components/JsonInput';
import TaskDashboard from './components/TaskDashboard';
import SingleEmailReader from './components/SingleEmailReader';
import SkippedLog from './components/SkippedLog';
import ChatPanel from './components/ChatPanel';
import DecisionCenter from './components/DecisionCenter';
import ReviewQueue from './components/ReviewQueue';
import RunHistory from './components/RunHistory';
import Settings from './components/Settings';

const DEFAULT_CANDIDATE_ID = "priya.sharma@gmail.com";
const API_BASE = import.meta.env.VITE_BACKEND_URL || "";

export default function App() {
  const [candidateId, setCandidateId] = useState(() => {
    return localStorage.getItem("candidate_id") || DEFAULT_CANDIDATE_ID;
  });

  const [activeTab, setActiveTab] = useState('inbox');
  const [rawEmails, setRawEmails] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [skippedEmails, setSkippedEmails] = useState([]);
  const [stats, setStats] = useState({});
  const [isIngesting, setIsIngesting] = useState(false);
  const [statusBanner, setStatusBanner] = useState(null);

  const updateCandidateId = (newId) => {
    setCandidateId(newId);
    localStorage.setItem("candidate_id", newId);
  };

  const fetchTasksAndStats = async (candToFetch = candidateId) => {
    if (!candToFetch) return;
    try {
      const statsRes = await fetch(`${API_BASE}/api/stats?candidate_id=${encodeURIComponent(candToFetch)}`);
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      const tasksRes = await fetch(`${API_BASE}/api/tasks?candidate_id=${encodeURIComponent(candToFetch)}`);
      if (tasksRes.ok) {
        const tasksData = await tasksRes.json();
        const finalTasksList = Array.isArray(tasksData) ? tasksData : (tasksData.tasks || []);
        setTasks(finalTasksList);
      }

      const skippedRes = await fetch(`${API_BASE}/api/skipped?candidate_id=${encodeURIComponent(candToFetch)}`);
      if (skippedRes.ok) {
        const skippedData = await skippedRes.json();
        setSkippedEmails(skippedData || []);
      }
    } catch (err) {
      console.error("Error fetching tasks/stats/skipped:", err);
    }
  };

  useEffect(() => {
    setStatusBanner(null);
    setTasks([]);
    setSkippedEmails([]);
    setStats({});
    fetchTasksAndStats(candidateId);
  }, [candidateId]);

  const handlePastedData = (emails) => {
    setRawEmails(emails);
  };

  const handleGenerateSample = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sample-emails?count=250`);
      if (res.ok) {
        const data = await res.json();
        setRawEmails(data.emails || []);
        setStatusBanner({ type: 'success', message: 'Loaded 250 sample emails into payload input.' });
      }
    } catch (err) {
      setStatusBanner({ type: 'error', message: 'Failed to fetch sample emails from backend.' });
    }
  };

  const handleClearDatabase = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/clear-database?candidate_id=${encodeURIComponent(candidateId)}`, { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.status !== 'error') {
        setStatusBanner({ type: 'success', message: `Database for candidate '${candidateId}' wiped clean successfully.` });
        await fetchTasksAndStats();
        return data;
      } else {
        throw new Error(data.message || 'Failed to clear database');
      }
    } catch (err) {
      setStatusBanner({ type: 'error', message: 'Failed to clear database: ' + err.message });
      throw err;
    }
  };

  const handleIngestSubmit = async () => {
    if (!rawEmails || rawEmails.length === 0) {
      setStatusBanner({ type: 'error', message: 'Please paste or upload an email payload first.' });
      return;
    }

    setIsIngesting(true);
    const chunkSize = 25;
    let totalProcessed = 0, totalTasksCreated = 0, totalTasksUpdated = 0, totalSkipped = 0;

    try {
      for (let i = 0; i < rawEmails.length; i += chunkSize) {
        const chunk = rawEmails.slice(i, i + chunkSize);
        setStatusBanner({
          type: 'info',
          message: `Routing payload in serverless chunks... (${Math.min(i + chunkSize, rawEmails.length)} / ${rawEmails.length} emails)`
        });

        const res = await fetch(`${API_BASE}/api/ingest?candidate_id=${encodeURIComponent(candidateId)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            candidate_id: candidateId,
            emails: chunk
          })
        });

        if (res.ok) {
          const result = await res.json();
          totalProcessed += result.processed || 0;
          totalTasksCreated += result.tasks_created || 0;
          totalTasksUpdated += result.tasks_updated || 0;
          totalSkipped += result.skipped || 0;
        }
      }

      setStatusBanner({
        type: 'success',
        message: `Ingest Complete! Total Processed: ${totalProcessed}, Tasks Created: ${totalTasksCreated}, Tasks Updated: ${totalTasksUpdated}, Skipped Noise: ${totalSkipped}`
      });
      await fetchTasksAndStats();
      setActiveTab('tasks');
    } catch (err) {
      setStatusBanner({ type: 'error', message: 'Ingest error: ' + err.message });
    } finally {
      setIsIngesting(false);
    }
  };

  const handleIngestSingle = async (singleEmailObj) => {
    setIsIngesting(true);
    try {
      const res = await fetch(`${API_BASE}/api/ingest-single`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_id: candidateId,
          ...singleEmailObj
        })
      });

      if (res.ok) {
        const data = await res.json();
        await fetchTasksAndStats();
        return data;
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsIngesting(false);
    }
  };

  const handleSendChatQuery = async (query, history = []) => {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate_id: candidateId,
        query: query,
        history: history
      })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  };

  return (
    <div className="w-full h-screen overflow-hidden flex bg-background text-on-background font-body-md text-body-md">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        candidateId={candidateId}
        setCandidateId={updateCandidateId}
        onClearDatabase={handleClearDatabase}
      />

      {/* Main Content Wrapper */}
      <main className="ml-64 flex-1 flex h-screen overflow-hidden">
        {/* Left Pane: Data Ingestion & Table */}
        <div className="flex-1 flex flex-col overflow-hidden bg-background">
          <div className="p-container-margin flex flex-col h-full overflow-y-auto">
            {/* Header */}
            <div className="mb-6 flex justify-between items-end shrink-0">
              <div>
                <h2 className="text-headline-md font-headline-md text-on-surface font-semibold">
                  {activeTab === 'inbox' && 'Inbox Data Ingestion'}
                  {activeTab === 'tasks' && 'Routed Task Queue'}
                  {activeTab === 'single' && 'Real Email Reader & Tester'}
                  {activeTab === 'archives' && 'Skipped Noise Log (Rule 4)'}
                  {activeTab === 'decision-center' && 'Operations Decision Center'}
                  {activeTab === 'review-queue' && 'Human Triage Review Queue'}
                  {activeTab === 'run-history' && 'Ingestion Run Telemetry'}
                  {activeTab === 'settings' && 'Settings & System Actions'}
                </h2>
                <p className="text-body-md font-body-md text-on-surface-variant mt-1">
                  {activeTab === 'inbox' && 'Process raw payload data for automated triage and CRM sync.'}
                  {activeTab === 'tasks' && 'Active section 5 tasks created in database store.'}
                  {activeTab === 'single' && 'Read and test single inbound sales emails.'}
                  {activeTab === 'archives' && 'Noise filters auditing and skipped inbox logs.'}
                  {activeTab === 'decision-center' && 'Analyze confidence telemetry, spurious rates, and decision traces.'}
                  {activeTab === 'review-queue' && 'Audit, calibrate, and override ambiguous classification decisions.'}
                  {activeTab === 'run-history' && 'Track and trace batch processing execution runs.'}
                  {activeTab === 'settings' && 'Manage database resources and candidate scopes.'}
                </p>
              </div>
            </div>

            {/* Status Notifications */}
            {statusBanner && (
              <div className={`mb-4 px-4 py-3 rounded text-body-sm font-medium border shrink-0 ${
                statusBanner.type === 'success'
                  ? 'bg-secondary-container text-on-secondary-container border-outline-variant'
                  : statusBanner.type === 'error'
                  ? 'bg-error-container text-error border-error/30'
                  : 'bg-surface-container-high text-on-surface border-outline-variant'
              }`}>
                {statusBanner.message}
              </div>
            )}

            {/* Tab Views */}
            {activeTab === 'inbox' && (
              <div className="flex-1 flex flex-col min-h-0">
                <JsonInput
                  onPastedData={handlePastedData}
                  onGenerateSample={handleGenerateSample}
                  onIngestSubmit={handleIngestSubmit}
                  isIngesting={isIngesting}
                />
                <TaskDashboard
                  tasks={tasks}
                  skippedEmails={skippedEmails}
                  stats={stats}
                  onRefresh={() => fetchTasksAndStats(candidateId)}
                  API_BASE={API_BASE}
                />
              </div>
            )}

            {activeTab === 'tasks' && (
              <div className="flex-1 flex flex-col min-h-0">
                <TaskDashboard
                  tasks={tasks}
                  skippedEmails={skippedEmails}
                  stats={stats}
                  onRefresh={() => fetchTasksAndStats(candidateId)}
                  API_BASE={API_BASE}
                />
              </div>
            )}

            {activeTab === 'single' && (
              <div className="flex-1 overflow-y-auto">
                <SingleEmailReader
                  key={candidateId}
                  onIngestSingle={handleIngestSingle}
                  isIngesting={isIngesting}
                />
              </div>
            )}

            {activeTab === 'archives' && (
              <div className="flex-1 flex flex-col min-h-0">
                <SkippedLog skippedEmails={skippedEmails} />
              </div>
            )}

            {activeTab === 'decision-center' && (
              <DecisionCenter
                candidateId={candidateId}
                API_BASE={API_BASE}
              />
            )}

            {activeTab === 'review-queue' && (
              <ReviewQueue
                candidateId={candidateId}
                API_BASE={API_BASE}
              />
            )}

            {activeTab === 'run-history' && (
              <RunHistory
                candidateId={candidateId}
                API_BASE={API_BASE}
              />
            )}

            {activeTab === 'settings' && (
              <Settings
                candidateId={candidateId}
                onClearDatabase={handleClearDatabase}
              />
            )}
          </div>
        </div>
      </main>

      {/* Floating Intelligent Chat Assistant */}
      <ChatPanel
        candidateId={candidateId}
        onSendQuery={handleSendChatQuery}
      />
    </div>
  );
}
