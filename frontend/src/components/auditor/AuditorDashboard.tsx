import React, { useState, useEffect, useRef } from 'react';
import './AuditorDashboard.css';
import {
  AuditReport,
  AuditResultItem,
  AuditStatusResponse,
  ConverterInfo,
  ExecuteSingleTestResponse,
  ProjectAnalysis,
  ProjectAnalysisResponse,
  ProjectInspectionResponse,
} from '../../types';
import {
  analyzeProject,
  checkBackendHealth,
  executeSingleTest,
  getApiBase,
  getAuditStatus,
  getAuditorConverters,
  getCustomAiApiKey,
  getRawCustomApiUrl,
  setCustomAiApiKey,
  setCustomApiUrl,
  triggerAuditRun,
  triggerProjectAuditRun,
  uploadProjectZip,
} from '../../api/client';
import { GraphCanvas } from '../graph/GraphCanvas';

const CATEGORIES_LIST = [
  { id: 'A_BASIC', name: 'Basic' },
  { id: 'B_EPSILON_HEAVY', name: 'Epsilon Heavy' },
  { id: 'C_ACCEPTANCE_SENSITIVE', name: 'Acceptance Sensitive' },
  { id: 'D_MULTIPLE_ACCEPTING', name: 'Multiple Accepting' },
  { id: 'E_CYCLIC', name: 'Cyclic' },
  { id: 'F_SPARSE', name: 'Sparse' },
  { id: 'G_DENSE', name: 'Dense' },
  { id: 'H_UNREACHABLE', name: 'Unreachable' },
  { id: 'I_DEAD_STATES', name: 'Dead States' },
  { id: 'J_MIXED_RANDOM', name: 'Mixed Random' },
];

const PRESET_AUDIT_OPTIONS = [
  { label: 'Quick Audit', count: 50, desc: '50 tests (~2s)' },
  { label: 'Standard Audit', count: 100, desc: '100 tests (~5s)' },
  { label: 'Deep Audit', count: 500, desc: '500 tests (~20s)' },
  { label: 'Full Audit', count: 1000, desc: '1000 tests (~40s)' },
];

export const AuditorDashboard: React.FC = () => {
  // Navigation / mode
  const [activeTab, setActiveTab] = useState<'upload' | 'benchmark'>('upload');

  // Step 1: Project Upload State
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [uploadLoading, setUploadLoading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [projectInspection, setProjectInspection] = useState<ProjectInspectionResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Step 2: AI Project Analysis State
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisResponse, setAnalysisResponse] = useState<ProjectAnalysisResponse | null>(null);
  const [selectedManualEntry, setSelectedManualEntry] = useState<string>('');

  // Step 3: Secure Execution Test State
  const [execLoading, setExecLoading] = useState<boolean>(false);
  const [execError, setExecError] = useState<string | null>(null);
  const [execResponse, setExecResponse] = useState<ExecuteSingleTestResponse | null>(null);
  const [showLogs, setShowLogs] = useState<boolean>(false);

  // Step 4: Batch Audit Config State
  const [testCount, setTestCount] = useState<number>(100);
  const [seed, setSeed] = useState<number>(42);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [timeoutSec, setTimeoutSec] = useState<number>(3.0);

  // Benchmark Converters State
  const [converters, setConverters] = useState<ConverterInfo[]>([]);
  const [selectedConverter, setSelectedConverter] = useState<string>('correct');

  // Audit Execution & Progress State
  const [activeAuditId, setActiveAuditId] = useState<string | null>(null);
  const [auditStatus, setAuditStatus] = useState<AuditStatusResponse | null>(null);
  const [report, setReport] = useState<AuditReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Selected failure for detail modal
  const [selectedFailure, setSelectedFailure] = useState<AuditResultItem | null>(null);
  const [copiedReport, setCopiedReport] = useState<boolean>(false);

  // Backend Server Settings Modal
  const [showServerModal, setShowServerModal] = useState<boolean>(false);
  const [serverUrlInput, setServerUrlInput] = useState<string>(getRawCustomApiUrl());
  const [aiKeyInput, setAiKeyInput] = useState<string>(getCustomAiApiKey());
  const [serverTestStatus, setServerTestStatus] = useState<string | null>(null);
  const [serverStatusPill, setServerStatusPill] = useState<'connected' | 'checking' | 'offline' | 'default'>('checking');

  const pollIntervalRef = useRef<number | null>(null);

  // Load converter options and check server health on mount
  useEffect(() => {
    getAuditorConverters().then((res: ConverterInfo[]) => setConverters(res));
    checkBackendHealth().then((res) => {
      if (res.healthy) {
        setServerStatusPill('connected');
      } else {
        setServerStatusPill(getRawCustomApiUrl() ? 'offline' : 'default');
      }
    });
  }, []);

  // Poll audit status while running
  useEffect(() => {
    if (activeAuditId && (!auditStatus || auditStatus.status === 'running')) {
      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const statusRes = await getAuditStatus(activeAuditId);
          setAuditStatus(statusRes);

          if (statusRes.status === 'completed') {
            setReport(statusRes.report || null);
            setLoading(false);
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          } else if (statusRes.status === 'failed') {
            setErrorMsg(statusRes.error || 'Audit execution failed');
            setLoading(false);
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          }
        } catch (err: any) {
          setErrorMsg(err.message || 'Error polling audit job');
          setLoading(false);
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      }, 350);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [activeAuditId, auditStatus]);

  // Handle Project ZIP Selection / Upload
  const handleZipFileSelected = async (file: File) => {
    if (!file) return;
    const nameLower = file.name.trim().toLowerCase();
    const typeLower = (file.type || '').toLowerCase();
    const isZip =
      nameLower.endsWith('.zip') ||
      typeLower.includes('zip') ||
      typeLower.includes('octet-stream');

    if (!isZip) {
      setUploadError(`Invalid file format: "${file.name}". Please select a .zip project archive.`);
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setUploadError('File exceeds the 50 MB size limit.');
      return;
    }

    setUploadLoading(true);
    setUploadError(null);
    setAnalysisResponse(null);
    setAnalysisError(null);
    setExecResponse(null);
    setExecError(null);
    setReport(null);
    setActiveAuditId(null);
    setAuditStatus(null);

    try {
      const resp = await uploadProjectZip(file);
      setProjectInspection(resp);
    } catch (err: any) {
      setUploadError(err.message || 'Failed to inspect project ZIP archive.');
      setProjectInspection(null);
    } finally {
      setUploadLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Drag & Drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleZipFileSelected(e.dataTransfer.files[0]);
    } else if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      const item = e.dataTransfer.items[0];
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file) handleZipFileSelected(file);
      }
    }
  };

  // Step 2: Trigger AI Project Analysis
  const handleRunAnalysis = async (manualEntryPointOverride?: string) => {
    if (!projectInspection) return;

    setAnalysisLoading(true);
    setAnalysisError(null);
    setExecResponse(null);
    setExecError(null);
    setReport(null);

    try {
      const resp = await analyzeProject(
        projectInspection.project_id,
        manualEntryPointOverride || selectedManualEntry || undefined,
        projectInspection,
        aiKeyInput ? aiKeyInput.trim() : undefined
      );
      setAnalysisResponse(resp);
      if (resp.analysis?.entry_point) {
        setSelectedManualEntry(resp.analysis.entry_point);
      }
    } catch (err: any) {
      setAnalysisError(err.message || 'Failed to analyze project code with AI.');
    } finally {
      setAnalysisLoading(false);
    }
  };

  // Step 3: Trigger Single Execution Test
  const handleRunSingleTest = async (analysisToRun?: ProjectAnalysis) => {
    const targetAnalysis = analysisToRun || analysisResponse?.analysis;
    if (!projectInspection || !targetAnalysis) return;

    setExecLoading(true);
    setExecError(null);

    try {
      const resp = await executeSingleTest(projectInspection.project_id, targetAnalysis);
      setExecResponse(resp);
    } catch (err: any) {
      setExecError(err.message || 'Failed to execute single test on project.');
    } finally {
      setExecLoading(false);
    }
  };

  // Step 4: Trigger Full Batch Audit on Student Project
  const handleRunProjectAudit = async () => {
    if (!projectInspection || !analysisResponse?.analysis) return;

    setLoading(true);
    setErrorMsg(null);
    setReport(null);
    setSelectedFailure(null);

    try {
      const resp = await triggerProjectAuditRun(
        projectInspection.project_id,
        analysisResponse.analysis,
        testCount,
        seed,
        selectedCategories.length > 0 ? selectedCategories : undefined,
        timeoutSec
      );
      setActiveAuditId(resp.audit_id);
      setAuditStatus(resp);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start student project audit.');
      setLoading(false);
    }
  };

  // Trigger Benchmark Reference Audit Run
  const handleRunBenchmarkAudit = async () => {
    setLoading(true);
    setErrorMsg(null);
    setReport(null);
    setSelectedFailure(null);

    try {
      const resp = await triggerAuditRun(
        selectedConverter,
        testCount,
        seed,
        selectedCategories.length > 0 ? selectedCategories : undefined
      );
      setActiveAuditId(resp.audit_id);
      setAuditStatus(resp);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start audit.');
      setLoading(false);
    }
  };

  // Toggle Category Filter
  const toggleCategory = (catId: string) => {
    setSelectedCategories((prev) =>
      prev.includes(catId) ? prev.filter((c) => c !== catId) : [...prev, catId]
    );
  };

  // Copy JSON report
  const handleCopyReportJson = () => {
    if (!report) return;
    navigator.clipboard.writeText(JSON.stringify(report, null, 2));
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2000);
  };

  // Download JSON report
  const handleDownloadReportJson = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit_report_${report.audit_id}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const vcr = report?.summary.verified_conversion_rate;
  const isPerfectVcr = vcr !== null && vcr !== undefined && vcr === 1.0;

  return (
    <div className="auditor-workspace">
      {/* Top Mode Navigation */}
      <div className="auditor-mode-tabs">
        <button
          className={`mode-tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          <span className="mode-tab-icon">📦</span>
          <span>Audit Student Project</span>
        </button>
        <button
          className={`mode-tab-btn ${activeTab === 'benchmark' ? 'active' : ''}`}
          onClick={() => setActiveTab('benchmark')}
        >
          <span className="mode-tab-icon">⚡</span>
          <span>Demo Converter Benchmarks</span>
        </button>
      </div>

      {/* ─── SECTION 1: STUDENT PROJECT UPLOAD & FULL AUDIT PIPELINE ─── */}
      {activeTab === 'upload' && (
        <div className="auditor-card project-upload-card">
          <div className="auditor-header">
            <div>
              <div className="auditor-title">Audit Student Project</div>
              <div className="auditor-subtitle">
                Complete pipeline: Upload → Static AI Analysis → Sandbox Execution → Formal Mathematical Verification
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                type="button"
                className="btn-secondary"
                style={{
                  fontSize: '11px',
                  padding: '5px 10px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  cursor: 'pointer',
                  borderRadius: '6px',
                }}
                onClick={() => setShowServerModal(true)}
                title="Configure backend server URL"
              >
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor:
                      serverStatusPill === 'connected'
                        ? '#10b981'
                        : serverStatusPill === 'offline'
                        ? '#ef4444'
                        : '#f59e0b',
                  }}
                />
                Backend Server
              </button>
              <span className="badge-tag enfa" style={{ padding: '4px 10px' }}>
                Full Automated Audit
              </span>
            </div>
          </div>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                handleZipFileSelected(e.target.files[0]);
              }
            }}
          />

          {!projectInspection ? (
            /* Upload Drop Area */
            <div
              className={`project-dropzone ${isDragging ? 'drag-over' : ''} ${
                uploadLoading ? 'loading' : ''
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="dropzone-inner">
                <span className="dropzone-icon">📁</span>
                <h3>Audit Student Project</h3>
                <p className="dropzone-instruction">
                  Drop a <strong>.zip</strong> project here <br />
                  or{' '}
                  <button
                    type="button"
                    className="choose-file-link"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                  >
                    Choose ZIP File
                  </button>
                </p>
                <div className="dropzone-meta">Maximum size: 50 MB (Accepts any standard .zip archive)</div>
                {uploadLoading && (
                  <div className="upload-spinner-row">
                    <span className="loading-spinner" />
                    <span>Extracting & inspecting project securely...</span>
                  </div>
                )}
              </div>
            </div>
          ) : !analysisResponse ? (
            /* Inspection Result Card (Step 1 Complete) */
            <div className="project-inspection-result">
              <div className="inspection-success-header">
                <div className="success-badge">✓ Project Uploaded</div>
                <div className="project-filename">{projectInspection.filename}</div>
              </div>

              <div className="project-stats-grid">
                <div className="stat-pill">
                  <span className="stat-pill-label">Files</span>
                  <span className="stat-pill-value">{projectInspection.file_count}</span>
                </div>
                <div className="stat-pill">
                  <span className="stat-pill-label">Languages</span>
                  <span className="stat-pill-value">
                    {projectInspection.languages.length > 0
                      ? projectInspection.languages.map((l) => l.toUpperCase()).join(', ')
                      : 'None detected'}
                  </span>
                </div>
                <div className="stat-pill">
                  <span className="stat-pill-label">Total Size</span>
                  <span className="stat-pill-value">
                    {(projectInspection.total_size_bytes / 1024).toFixed(1)} KB
                  </span>
                </div>
              </div>

              {/* Likely Source Files */}
              <div className="source-files-section">
                <div className="section-subtitle">Likely source files</div>
                {projectInspection.likely_source_files.length > 0 ? (
                  <ul className="source-files-list">
                    {projectInspection.likely_source_files.map((file) => (
                      <li key={file} className="source-file-item">
                        <span className="source-bullet">•</span>
                        <code className="source-path">{file}</code>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="empty-sources-msg">No recognized source code files found.</div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="inspection-actions-row">
                <button
                  type="button"
                  className="btn-primary continue-btn"
                  onClick={() => handleRunAnalysis()}
                  disabled={analysisLoading}
                >
                  {analysisLoading ? (
                    <>
                      <span className="loading-spinner mini" />
                      <span>Analyzing Project...</span>
                    </>
                  ) : (
                    'Continue to Analysis →'
                  )}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setProjectInspection(null);
                    setAnalysisResponse(null);
                    setExecResponse(null);
                    setUploadError(null);
                    setAnalysisError(null);
                  }}
                  disabled={analysisLoading}
                >
                  Upload Another Project
                </button>
              </div>

              {analysisLoading && (
                <div className="analysis-progress-banner">
                  <span className="loading-spinner" />
                  <div>
                    <strong>Analyzing Project Structure...</strong>
                    <div className="subtext">Inferring entry point, converter logic, and input/output contracts.</div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Step 2: AI Analysis Result, Step 3 Single Exec, and Step 4 Batch Audit */
            <div className="project-inspection-result">
              {analysisResponse.status === 'SUCCESS' && analysisResponse.analysis ? (
                /* High-Confidence Success Card */
                <div className="analysis-result-card success">
                  <div className="analysis-card-header">
                    <div className="success-badge">✓ Project Analysis Complete</div>
                    <div className="confidence-chip high">
                      Confidence: {(analysisResponse.analysis.confidence * 100).toFixed(0)}%
                    </div>
                  </div>

                  <div className="analysis-details-grid">
                    <div className="analysis-detail-row">
                      <span className="detail-label">Language</span>
                      <span className="detail-value font-bold">{analysisResponse.analysis.language.toUpperCase()}</span>
                    </div>
                    <div className="analysis-detail-row">
                      <span className="detail-label">Entry Point</span>
                      <code className="detail-value-code">{analysisResponse.analysis.entry_point || 'None'}</code>
                    </div>
                    <div className="analysis-detail-row">
                      <span className="detail-label">Converter</span>
                      <code className="detail-value-code">
                        {analysisResponse.analysis.converter_function
                          ? `${analysisResponse.analysis.converter_function}()`
                          : analysisResponse.analysis.converter_class || analysisResponse.analysis.converter_file || 'Inferred'}
                      </code>
                    </div>
                    <div className="analysis-detail-row">
                      <span className="detail-label">Input</span>
                      <span className="detail-value">{analysisResponse.analysis.input_format.toUpperCase()}</span>
                    </div>
                    <div className="analysis-detail-row">
                      <span className="detail-label">Output</span>
                      <span className="detail-value">{analysisResponse.analysis.output_format.toUpperCase()}</span>
                    </div>
                    <div className="analysis-detail-row">
                      <span className="detail-label">Conversion</span>
                      <span className="detail-value">
                        {analysisResponse.analysis.conversion_type === 'epsilon_nfa_to_dfa'
                          ? 'ε-NFA → DFA'
                          : analysisResponse.analysis.conversion_type}
                      </span>
                    </div>
                  </div>

                  {analysisResponse.analysis.invocation && (
                    <div className="invocation-box">
                      <span className="invocation-label">Inferred Invocation:</span>
                      <code>{analysisResponse.analysis.invocation}</code>
                    </div>
                  )}

                  <div className="analysis-status-message">
                    <span className="status-icon">✓</span>
                    <span>Execution interface identified</span>
                  </div>

                  {/* Actions: Single Test or Configure Full Audit */}
                  <div className="inspection-actions-row">
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => handleRunSingleTest(analysisResponse.analysis || undefined)}
                      disabled={execLoading || loading}
                    >
                      {execLoading ? 'Testing Sandbox...' : '▶ Run Single Test (Step 3)'}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => {
                        setAnalysisResponse(null);
                        setExecResponse(null);
                        setReport(null);
                      }}
                      disabled={execLoading || loading}
                    >
                      ← Back to Project Files
                    </button>
                  </div>
                </div>
              ) : (
                /* Low-Confidence / Ambiguity / Not Configured Card */
                <div className="analysis-result-card warning">
                  <div className="analysis-card-header">
                    <div className="warning-badge" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {analysisResponse.status === 'AI_NOT_CONFIGURED' ? (
                        <>
                          <span>⚡</span> Deterministic Code Adapter Active
                        </>
                      ) : (
                        <>
                          <span>ℹ</span> Confirmation Required
                        </>
                      )}
                    </div>
                    {analysisResponse.analysis && (
                      <div className="confidence-chip low">
                        Confidence: {(analysisResponse.analysis.confidence * 100).toFixed(0)}%
                      </div>
                    )}
                  </div>

                  <p className="ambiguity-explanation" style={{ lineHeight: 1.6 }}>
                    {analysisResponse.status === 'AI_NOT_CONFIGURED' ? (
                      <>
                        AutoVerify analyzed the project structure deterministically without needing an external AI API key.
                        Detected <strong>{(analysisResponse.analysis?.language || 'Python').toUpperCase()}</strong> entry point: <code>{analysisResponse.analysis?.entry_point || analysisResponse.candidate_entry_points?.[0] || 'main.py'}</code>.
                        Confirm below to proceed directly to testing, or optionally add a Gemini API key for deep LLM reasoning.
                      </>
                    ) : (
                      analysisResponse.analysis?.reasoning_summary ||
                      analysisResponse.message ||
                      'Multiple candidate entry points or converter functions were detected.'
                    )}
                  </p>

                  <div style={{ margin: '14px 0', padding: '12px 14px', background: 'var(--bg-surface-sunken)', borderRadius: '8px', border: '1px solid var(--border-default)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontSize: '12px', fontWeight: 600 }}>Optional: Gemini AI API Key</span>
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>For deep LLM code reasoning</span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input
                        type="password"
                        placeholder="Paste Gemini API Key (e.g. AIzaSy...)"
                        value={aiKeyInput}
                        onChange={(e) => {
                          setAiKeyInput(e.target.value);
                          setCustomAiApiKey(e.target.value);
                        }}
                        style={{ flex: 1, padding: '7px 10px', borderRadius: '6px', border: '1px solid var(--border-default)', fontSize: '12px', background: 'var(--bg-input, #fff)', color: 'inherit' }}
                      />
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ fontSize: '12px', padding: '6px 12px', whiteSpace: 'nowrap' }}
                        onClick={() => handleRunAnalysis(selectedManualEntry)}
                        disabled={analysisLoading}
                      >
                        {analysisLoading ? 'Analyzing...' : 'Analyze with AI'}
                      </button>
                    </div>
                  </div>

                  {analysisResponse.analysis?.ambiguities && analysisResponse.analysis.ambiguities.length > 0 && (
                    <div className="ambiguities-list-box">
                      <span className="ambiguities-label">Possible entry points / Ambiguities:</span>
                      <ul className="ambiguities-ul">
                        {analysisResponse.analysis.ambiguities.map((amb, i) => (
                          <li key={i}>• {amb}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="entry-point-picker">
                    <label className="config-label">Designate / Confirm Entry Point:</label>
                    <select
                      className="config-select"
                      value={selectedManualEntry || analysisResponse.analysis?.entry_point || (analysisResponse.candidate_entry_points?.[0] || '')}
                      onChange={(e) => setSelectedManualEntry(e.target.value)}
                    >
                      {analysisResponse.candidate_entry_points.length > 0 ? (
                        analysisResponse.candidate_entry_points.map((cand) => (
                          <option key={cand} value={cand}>
                            {cand}
                          </option>
                        ))
                      ) : (
                        <option value="main.py">main.py</option>
                      )}
                    </select>
                  </div>

                  <div className="inspection-actions-row">
                    <button
                      type="button"
                      className="btn-primary continue-btn"
                      onClick={() => {
                        const targetEntry =
                          selectedManualEntry ||
                          analysisResponse.analysis?.entry_point ||
                          analysisResponse.candidate_entry_points?.[0] ||
                          'main.py';
                        const dotIdx = targetEntry.lastIndexOf('.');
                        const ext = dotIdx !== -1 ? targetEntry.slice(dotIdx).toLowerCase() : '';
                        const lang = ext === '.py' ? 'python' : ext === '.java' ? 'java' : ext === '.cpp' ? 'cpp' : 'c';
                        const inv =
                          lang === 'python'
                            ? `python ${targetEntry} <input.json>`
                            : lang === 'java'
                            ? `java ${targetEntry} <input.json>`
                            : `./${targetEntry} <input.json>`;

                        const updatedAnalysis: ProjectAnalysis = analysisResponse.analysis
                          ? {
                              ...analysisResponse.analysis,
                              entry_point: targetEntry,
                              language: lang,
                              invocation: inv,
                              confidence: 1.0,
                              ambiguities: [],
                            }
                          : {
                              language: lang,
                              entry_point: targetEntry,
                              relevant_files: [targetEntry],
                              converter_file: targetEntry,
                              input_format: 'json',
                              output_format: 'stdout_json',
                              invocation: inv,
                              conversion_type: 'epsilon_nfa_to_dfa',
                              is_supported_language: true,
                              confidence: 1.0,
                              ambiguities: [],
                              reasoning_summary: `Confirmed ${lang.toUpperCase()} entry point at "${targetEntry}".`,
                            };

                        setAnalysisResponse({
                          ...analysisResponse,
                          status: 'SUCCESS',
                          analysis: updatedAnalysis,
                        });
                      }}
                      disabled={analysisLoading || loading}
                    >
                      Confirm Entry Point & Proceed to Audit →
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => handleRunAnalysis(selectedManualEntry)}
                      disabled={analysisLoading || loading}
                      title="Re-run static analysis"
                    >
                      {analysisLoading ? 'Re-analyzing...' : 'Re-run Analysis'}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => setAnalysisResponse(null)}
                      disabled={analysisLoading || loading}
                    >
                      ← Back to Project Files
                    </button>
                  </div>
                </div>
              )}

              {/* ─── STEP 3: EXECUTION TEST RESULT PANEL (Optional Quick Check) ─── */}
              {execResponse && (
                <div className={`execution-test-panel status-${execResponse.status.toLowerCase()}`}>
                  <div className="exec-header">
                    <div className="exec-title-row">
                      <h4 className="exec-title">Single Test Execution</h4>
                      <span className={`exec-status-badge ${execResponse.status.toLowerCase()}`}>
                        {execResponse.status === 'SUCCESS' && '✓ Program executed successfully'}
                        {execResponse.status === 'TIMEOUT' && '✗ Timeout'}
                        {execResponse.status === 'CRASH' && '✗ Crash'}
                        {execResponse.status === 'INVALID_OUTPUT' && '✗ Invalid output'}
                        {execResponse.status === 'NEEDS_CONFIGURATION' && '⚠ Needs configuration'}
                        {execResponse.status === 'SANDBOX_ERROR' && '⚠ Sandbox error'}
                      </span>
                    </div>
                    <div className="exec-meta-stats">
                      <span>Time: <strong>{execResponse.execution_time_ms.toFixed(1)} ms</strong></span>
                      {execResponse.exit_code !== null && execResponse.exit_code !== undefined && (
                        <span>Exit Code: <strong>{execResponse.exit_code}</strong></span>
                      )}
                    </div>
                  </div>

                  {execResponse.error_message && (
                    <div className="exec-error-box">
                      <span className="error-icon">⚠</span>
                      <pre className="error-msg-pre">{execResponse.error_message}</pre>
                    </div>
                  )}

                  {execResponse.generated_dfa && (
                    <div className="exec-dfa-preview">
                      <div className="exec-dfa-header">
                        <span>Generated Canonical DFA Preview</span>
                        <span className="badge-tag dfa">
                          {execResponse.generated_dfa.states?.length || 0} States ·{' '}
                          {execResponse.generated_dfa.transitions?.length || 0} Transitions
                        </span>
                      </div>
                      <div className="exec-canvas-wrapper">
                        <GraphCanvas
                          automaton={execResponse.generated_dfa}
                          activeTool="select"
                        />
                      </div>
                    </div>
                  )}

                  <div className="exec-logs-section">
                    <button
                      type="button"
                      className="exec-logs-toggle"
                      onClick={() => setShowLogs(!showLogs)}
                    >
                      {showLogs ? '▼ Hide Logs' : '▶ Show Logs (stdout / stderr)'}
                    </button>

                    {showLogs && (
                      <div className="exec-logs-content">
                        {execResponse.stdout && (
                          <div className="log-block">
                            <span className="log-label">STDOUT:</span>
                            <pre className="log-pre">{execResponse.stdout}</pre>
                          </div>
                        )}
                        {execResponse.stderr && (
                          <div className="log-block">
                            <span className="log-label stderr">STDERR:</span>
                            <pre className="log-pre stderr">{execResponse.stderr}</pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ─── STEP 4: BATCH AUDIT CONTROLS & SUITE CONFIGURATION ─── */}
              {analysisResponse.analysis && (
                <div className="batch-audit-card">
                  <div className="auditor-header">
                    <div>
                      <div className="auditor-title">Automated Batch Audit</div>
                      <div className="auditor-subtitle">
                        Run rigorous metamorphic evaluation with formal equivalence verification
                      </div>
                    </div>
                    <span className="badge-tag dfa" style={{ padding: '4px 10px' }}>
                      Step 4: Formal Audit
                    </span>
                  </div>

                  {/* Preset Audit Selection */}
                  <div className="config-group" style={{ marginBottom: 16 }}>
                    <label className="config-label">Audit Presets</label>
                    <div className="preset-audit-grid">
                      {PRESET_AUDIT_OPTIONS.map((opt) => (
                        <button
                          key={opt.count}
                          type="button"
                          className={`preset-audit-btn ${testCount === opt.count ? 'active' : ''}`}
                          onClick={() => setTestCount(opt.count)}
                          disabled={loading}
                        >
                          <span className="preset-name">{opt.label}</span>
                          <span className="preset-count">{opt.count} Tests</span>
                          <span className="preset-desc">{opt.desc}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="config-grid">
                    {/* Seed Selection */}
                    <div className="config-group">
                      <label className="config-label">Generator Seed</label>
                      <input
                        type="number"
                        className="config-input"
                        value={seed}
                        onChange={(e) => setSeed(parseInt(e.target.value, 10) || 0)}
                        disabled={loading}
                      />
                      <span className="hint-text">Deterministic seed ensures identical test suite across runs.</span>
                    </div>

                    {/* Per-test Timeout */}
                    <div className="config-group">
                      <label className="config-label">Per-Test Timeout (seconds)</label>
                      <input
                        type="number"
                        step="0.5"
                        min="0.5"
                        max="10.0"
                        className="config-input"
                        value={timeoutSec}
                        onChange={(e) => setTimeoutSec(parseFloat(e.target.value) || 3.0)}
                        disabled={loading}
                      />
                      <span className="hint-text">Maximum sandbox runtime per generated automaton.</span>
                    </div>
                  </div>

                  {/* Category Selection Filter */}
                  <div className="config-group" style={{ marginTop: 12 }}>
                    <label className="config-label">
                      Filter by Category ({selectedCategories.length === 0 ? 'All 10 Included' : `${selectedCategories.length} selected`})
                    </label>
                    <div className="categories-filter-grid">
                      {CATEGORIES_LIST.map((cat) => {
                        const isSelected = selectedCategories.includes(cat.id);
                        return (
                          <button
                            key={cat.id}
                            type="button"
                            className={`category-toggle-chip ${isSelected ? 'selected' : ''}`}
                            onClick={() => toggleCategory(cat.id)}
                            disabled={loading}
                          >
                            <span className="cat-chip-check">{isSelected ? '✓' : '+'}</span>
                            <span>{cat.name}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Run Audit Action */}
                  <div className="config-actions" style={{ marginTop: 16 }}>
                    <button
                      type="button"
                      className="btn-primary continue-btn"
                      onClick={handleRunProjectAudit}
                      disabled={loading}
                    >
                      {loading ? (
                        <>
                          <span className="loading-spinner mini" />
                          <span>Auditing Student Project ({testCount} Tests)...</span>
                        </>
                      ) : (
                        `▶ Run Full Audit (${testCount} Tests)`
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {uploadError && (
            <div className="auditor-error-banner" style={{ marginTop: 12 }}>
              ⚠ {uploadError}
            </div>
          )}

          {analysisError && (
            <div className="auditor-error-banner" style={{ marginTop: 12 }}>
              ⚠ {analysisError}
            </div>
          )}

          {execError && (
            <div className="auditor-error-banner" style={{ marginTop: 12 }}>
              ⚠ {execError}
            </div>
          )}
        </div>
      )}

      {/* ─── SECTION 2: REFERENCE BENCHMARK SUITE ─── */}
      {activeTab === 'benchmark' && (
        <div className="auditor-card">
          <div className="auditor-header">
            <div>
              <div className="auditor-title">Demo Converter Benchmark Suite</div>
              <div className="auditor-subtitle">
                Evaluate reference converters against 10 rigorous metamorphic automaton test categories
              </div>
            </div>
            <span className="badge-tag dfa" style={{ padding: '4px 10px' }}>
              Reference Engine
            </span>
          </div>

          <div className="config-form">
            <div className="config-grid">
              {/* Converter Selection */}
              <div className="config-group">
                <label className="config-label">Target Converter</label>
                <select
                  className="config-select"
                  value={selectedConverter}
                  onChange={(e) => setSelectedConverter(e.target.value)}
                  disabled={loading}
                >
                  {converters.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                <span className="hint-text">
                  {selectedConverter === 'correct'
                    ? 'Reference engine with 100% verified correctness.'
                    : 'Flawed demo converter with deliberate multi-hop epsilon bug.'}
                </span>
              </div>

              {/* Test Count Selection */}
              <div className="config-group">
                <label className="config-label">Test Suite Size</label>
                <div className="preset-counts-row">
                  {[10, 50, 100, 500, 1000].map((cnt) => (
                    <button
                      key={cnt}
                      type="button"
                      className={`count-chip ${testCount === cnt ? 'active' : ''}`}
                      onClick={() => setTestCount(cnt)}
                      disabled={loading}
                    >
                      {cnt}
                    </button>
                  ))}
                </div>
              </div>

              {/* Seed Input */}
              <div className="config-group">
                <label className="config-label">Generator Seed</label>
                <input
                  type="number"
                  className="config-input"
                  value={seed}
                  onChange={(e) => setSeed(parseInt(e.target.value, 10) || 0)}
                  disabled={loading}
                />
                <span className="hint-text">Guarantees deterministic, reproducible test generation.</span>
              </div>
            </div>

            {/* Category Filter Checkboxes */}
            <div className="config-group">
              <label className="config-label">
                Filter by Category ({selectedCategories.length === 0 ? 'All 10 Included' : `${selectedCategories.length} selected`})
              </label>
              <div className="categories-filter-grid">
                {CATEGORIES_LIST.map((cat) => {
                  const isSelected = selectedCategories.includes(cat.id);
                  return (
                    <button
                      key={cat.id}
                      type="button"
                      className={`category-toggle-chip ${isSelected ? 'selected' : ''}`}
                      onClick={() => toggleCategory(cat.id)}
                      disabled={loading}
                    >
                      <span className="cat-chip-check">{isSelected ? '✓' : '+'}</span>
                      <span>{cat.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Action Bar */}
            <div className="config-actions">
              <button
                type="button"
                className="btn-primary"
                onClick={handleRunBenchmarkAudit}
                disabled={loading}
              >
                {loading ? 'Running Metamorphic Audit...' : `▶ Run Audit (${testCount} Tests)`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Error Notification ─── */}
      {errorMsg && <div className="auditor-error-banner">⚠ {errorMsg}</div>}

      {/* ─── Progress Indicator (When Running Audit) ─── */}
      {loading && auditStatus && (
        <div className="auditor-card progress-card">
          <div className="progress-header">
            <div className="progress-title-block">
              <span className="loading-spinner" />
              <span className="progress-title">
                Auditing test <strong>{auditStatus.progress.current}</strong> of <strong>{auditStatus.progress.total}</strong>
              </span>
            </div>
            <span className="badge-tag nfa">{auditStatus.progress.current_category}</span>
          </div>

          <div className="progress-bar-container">
            <div
              className="progress-bar-fill"
              style={{
                width: `${(auditStatus.progress.current / Math.max(1, auditStatus.progress.total)) * 100}%`,
              }}
            />
          </div>

          <div className="progress-live-stats-row">
            <span className="stat-live-item verified">
              ✓ Passed: {auditStatus.progress.verified_count || 0}
            </span>
            <span className="stat-live-item failed">
              ✗ Failed: {auditStatus.progress.failed_count || 0}
            </span>
            <span className="stat-live-item crashes">
              💥 Crashes: {auditStatus.progress.crash_count || 0}
            </span>
            <span className="stat-live-item timeouts">
              ⏱ Timeouts: {auditStatus.progress.timeout_count || 0}
            </span>
            <span className="stat-live-item invalid">
              ⚠ Invalid: {auditStatus.progress.invalid_output_count || 0}
            </span>
            <span className="stat-live-item status">
              Status: <strong>{auditStatus.progress.current_status}</strong>
            </span>
          </div>
        </div>
      )}

      {/* ─── Final Audit Report Dashboard ─── */}
      {report && (
        <>
          {/* Disclaimer Banner */}
          <div className="audit-disclaimer-banner">
            <span className="disclaimer-icon">ℹ</span>
            <div>
              <strong>Testing-Based Audit Evaluation:</strong>{' '}
              {report.summary.verified_count} / {report.summary.total_tests} tested cases were formally verified.
              Formal equivalence check proves each tested DFA equivalent to the reference language, but finite test
              coverage does not mathematically prove correctness for all possible inputs.
            </div>
          </div>

          {/* Summary Metric Cards */}
          <div className="auditor-summary-grid">
            <div className={`metric-card ${isPerfectVcr ? 'metric-perfect' : 'metric-flawed'}`}>
              <div className="metric-title">Verified Conversion Rate (VCR)</div>
              <div className="metric-value-huge">
                {vcr !== null && vcr !== undefined ? `${(vcr * 100).toFixed(1)}%` : 'N/A'}
              </div>
              <div className="metric-subtitle">
                {report.summary.verified_count} / {report.summary.total_tests} mathematically verified
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-title">Test Results Breakdown</div>
              <div className="metric-counts-row">
                <div className="count-col verified">
                  <span className="count-num">{report.summary.verified_count}</span>
                  <span className="count-label">Verified</span>
                </div>
                <div className="count-col failed">
                  <span className="count-num">{report.summary.failed_count}</span>
                  <span className="count-label">Not Equiv</span>
                </div>
                <div className="count-col invalid">
                  <span className="count-num">{report.summary.invalid_output_count}</span>
                  <span className="count-label">Invalid</span>
                </div>
                <div className="count-col crashes">
                  <span className="count-num">{report.summary.execution_error_count}</span>
                  <span className="count-label">Crashes</span>
                </div>
                <div className="count-col timeouts">
                  <span className="count-num">{report.summary.timeout_count}</span>
                  <span className="count-label">Timeouts</span>
                </div>
              </div>
              <div className="metric-subtitle">
                Total Evaluated: {report.summary.total_tests} Tests (Seed: {report.seed})
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-title">Execution Timing</div>
              <div className="metric-value-large">
                {(report.summary.total_execution_time_seconds * 1000).toFixed(0)} ms
              </div>
              <div className="metric-subtitle">
                Avg: {(report.summary.average_execution_time_seconds * 1000).toFixed(2)} ms / test
              </div>
            </div>
          </div>

          {/* Export / Copy Toolbar */}
          <div className="report-toolbar">
            <div className="report-toolbar-title">
              Audit Run Report: <code>{report.audit_id}</code> (Seed: <strong>{report.seed}</strong>)
            </div>
            <div className="report-toolbar-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={handleCopyReportJson}
              >
                {copiedReport ? '✓ Copied JSON' : '📋 Copy JSON Report'}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleDownloadReportJson}
              >
                💾 Download JSON Report
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => window.print()}
              >
                🖨️ Print Report
              </button>
            </div>
          </div>

          {/* Category Statistics Breakdown Table */}
          <div className="auditor-card">
            <div className="auditor-title" style={{ marginBottom: 12 }}>
              Category-by-Category Reliability Breakdown
            </div>
            <div className="category-table-wrapper">
              <table className="category-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Tests</th>
                    <th>Verified</th>
                    <th>Not Equiv</th>
                    <th>Invalid Output</th>
                    <th>Crashes</th>
                    <th>Timeouts</th>
                    <th>VCR</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.values(report.category_statistics).map((cat) => {
                    const catVcr = cat.verified_conversion_rate;
                    const catPerfect = catVcr !== null && catVcr === 1.0;
                    return (
                      <tr key={cat.category}>
                        <td className="cat-name-cell">
                          <strong>{cat.category}</strong>
                        </td>
                        <td>{cat.total_tests}</td>
                        <td className="verified-text">{cat.verified_count}</td>
                        <td className={cat.failed_count > 0 ? 'failed-text' : ''}>
                          {cat.failed_count}
                        </td>
                        <td className={cat.invalid_output_count > 0 ? 'invalid-text' : ''}>
                          {cat.invalid_output_count}
                        </td>
                        <td className={cat.execution_error_count > 0 ? 'crash-text' : ''}>
                          {cat.execution_error_count}
                        </td>
                        <td className={cat.timeout_count > 0 ? 'timeout-text' : ''}>
                          {cat.timeout_count}
                        </td>
                        <td>
                          <span
                            className={`badge-tag ${
                              catPerfect ? 'badge-verified' : 'badge-flawed'
                            }`}
                          >
                            {catVcr !== null ? `${(catVcr * 100).toFixed(1)}%` : 'N/A'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Failure Deep-Dive Table (If any failures detected) */}
          {report.failures.length > 0 && (
            <div className="auditor-card failures-card">
              <div className="auditor-title" style={{ marginBottom: 12 }}>
                Identified Flaws & Counterexamples ({report.failures.length})
              </div>
              <div className="failures-table-wrapper">
                <table className="failures-table">
                  <thead>
                    <tr>
                      <th>Test ID</th>
                      <th>Category</th>
                      <th>Status</th>
                      <th>Distinguishing Counterexample (w)</th>
                      <th>Reference</th>
                      <th>Student</th>
                      <th>Time</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.failures.map((f) => (
                      <tr key={f.test_id}>
                        <td><code>{f.test_id}</code></td>
                        <td><span className="badge-tag nfa">{f.category}</span></td>
                        <td>
                          <span className={`status-pill ${f.status.toLowerCase()}`}>
                            {f.status}
                          </span>
                        </td>
                        <td>
                          {f.counterexample !== null && f.counterexample !== undefined ? (
                            <code className="counterexample-chip">
                              {f.counterexample === '' ? 'ε (empty string)' : `"${f.counterexample}"`}
                            </code>
                          ) : (
                            <span className="no-counterexample">N/A</span>
                          )}
                        </td>
                        <td>
                          {f.expected_acceptance !== null && f.expected_acceptance !== undefined ? (
                            <span className={`decision-tag ${f.expected_acceptance ? 'accept' : 'reject'}`}>
                              {f.expected_acceptance ? 'ACCEPT' : 'REJECT'}
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td>
                          {f.generated_acceptance !== null && f.generated_acceptance !== undefined ? (
                            <span className={`decision-tag ${f.generated_acceptance ? 'accept' : 'reject'}`}>
                              {f.generated_acceptance ? 'ACCEPT' : 'REJECT'}
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td>{(f.execution_time_seconds * 1000).toFixed(1)} ms</td>
                        <td>
                          <button
                            type="button"
                            className="btn-small"
                            onClick={() => setSelectedFailure(f)}
                          >
                            Inspect Pair →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* ─── Modal: Failure Visual Inspection & Pair Comparison ─── */}
      {selectedFailure && (
        <div className="auditor-modal-backdrop" onClick={() => setSelectedFailure(null)}>
          <div className="auditor-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="auditor-modal-header">
              <div>
                <div className="auditor-title">
                  Flaw Investigation: <code>{selectedFailure.test_id}</code>
                </div>
                <div className="auditor-subtitle">
                  Category: <strong>{selectedFailure.category}</strong> · Status: <strong>{selectedFailure.status}</strong>
                </div>
              </div>
              <button
                type="button"
                className="close-btn"
                onClick={() => setSelectedFailure(null)}
              >
                ✕
              </button>
            </div>

            <div className="auditor-modal-body">
              {/* Counterexample Banner if NOT_EQUIVALENT */}
              {selectedFailure.counterexample !== null && selectedFailure.counterexample !== undefined && (
                <div className="counterexample-banner">
                  <div>
                    <strong>Distinguishing String (w):</strong>{' '}
                    <code className="counterexample-large">
                      {selectedFailure.counterexample === ''
                        ? 'ε (empty string)'
                        : `"${selectedFailure.counterexample}"`}
                    </code>
                  </div>
                  <div className="counterexample-details">
                    Original Reference ε-NFA: <strong className="accept-color">{selectedFailure.expected_acceptance ? 'ACCEPTS' : 'REJECTS'}</strong>
                    {' vs '}
                    Student DFA: <strong className="reject-color">{selectedFailure.generated_acceptance ? 'ACCEPTS' : 'REJECTS'}</strong>
                    {selectedFailure.states_explored ? ` (${selectedFailure.states_explored} product states explored)` : ''}
                  </div>
                </div>
              )}

              {/* Error Message if operational failure */}
              {selectedFailure.error_message && (
                <div className="exec-error-box" style={{ marginBottom: 14 }}>
                  <span className="error-icon">⚠</span>
                  <pre className="error-msg-pre">{selectedFailure.error_message}</pre>
                </div>
              )}

              {/* Side-by-side Dual Graph View */}
              <div className="dual-graph-container">
                {/* Original ε-NFA */}
                <div className="dual-graph-pane">
                  <div className="graph-pane-header">
                    <span>1. Input ε-NFA</span>
                    <span className="badge-tag enfa">Original Spec</span>
                  </div>
                  <div className="dual-graph-canvas-wrapper">
                    {selectedFailure.original_enfa ? (
                      <GraphCanvas
                        automaton={selectedFailure.original_enfa}
                        activeTool="select"
                      />
                    ) : (
                      <div className="no-graph-msg">Automaton data unavailable</div>
                    )}
                  </div>
                </div>

                {/* Generated DFA */}
                <div className="dual-graph-pane">
                  <div className="graph-pane-header">
                    <span>2. Student Output DFA</span>
                    <span className="badge-tag dfa">Generated by Student</span>
                  </div>
                  <div className="dual-graph-canvas-wrapper">
                    {selectedFailure.generated_dfa ? (
                      <GraphCanvas
                        automaton={selectedFailure.generated_dfa}
                        activeTool="select"
                      />
                    ) : (
                      <div className="no-graph-msg">Output DFA unavailable (Crash or Invalid Output)</div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="auditor-modal-footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setSelectedFailure(null)}
              >
                Close Investigation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── SERVER SETTINGS MODAL ─── */}
      {showServerModal && (
        <div
          className="modal-backdrop"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
          }}
          onClick={() => setShowServerModal(false)}
        >
          <div
            className="auditor-card"
            style={{
              maxWidth: '480px',
              width: '92%',
              padding: '24px',
              background: 'var(--bg-surface, #ffffff)',
              borderRadius: '12px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 8px 0', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>⚙️</span> Backend Server Settings
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 16px 0', lineHeight: 1.5 }}>
              If your backend is hosted on Render (or running locally), specify its URL below. AutoVerify will connect directly to it.
            </p>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                Backend API URL:
              </label>
              <input
                type="text"
                value={serverUrlInput}
                onChange={(e) => {
                  setServerUrlInput(e.target.value);
                  setServerTestStatus(null);
                }}
                placeholder="e.g. https://autoverify-backend.onrender.com"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-default)',
                  fontSize: '13px',
                  boxSizing: 'border-box',
                  background: 'var(--bg-input, #ffffff)',
                  color: 'inherit',
                }}
              />
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                Active URL: <code style={{ wordBreak: 'break-all' }}>{getApiBase()}</code>
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                Gemini AI API Key (Optional):
              </label>
              <input
                type="password"
                value={aiKeyInput}
                onChange={(e) => {
                  setAiKeyInput(e.target.value);
                  setCustomAiApiKey(e.target.value);
                }}
                placeholder="Paste your Gemini API Key (e.g. AIzaSy...)"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-default)',
                  fontSize: '13px',
                  boxSizing: 'border-box',
                  background: 'var(--bg-input, #ffffff)',
                  color: 'inherit',
                }}
              />
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                Optional. If left blank, AutoVerify uses the built-in deterministic code adapter.
              </div>
            </div>

            {serverTestStatus && (
              <div
                style={{
                  padding: '10px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  marginBottom: '16px',
                  background: serverTestStatus === 'success' ? '#ecfdf5' : serverTestStatus === 'testing' ? '#eff6ff' : '#fef2f2',
                  color: serverTestStatus === 'success' ? '#065f46' : serverTestStatus === 'testing' ? '#1e40af' : '#991b1b',
                  border: `1px solid ${serverTestStatus === 'success' ? '#a7f3d0' : serverTestStatus === 'testing' ? '#bfdbfe' : '#fecaca'}`,
                }}
              >
                {serverTestStatus === 'success'
                  ? '✓ Backend is online and responding!'
                  : serverTestStatus === 'testing'
                  ? 'Testing connection to backend...'
                  : '⚠ Could not connect to backend at this URL. Please verify the URL and ensure your backend is awake.'}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', marginTop: '20px' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={async () => {
                  setServerTestStatus('testing');
                  setCustomApiUrl(serverUrlInput);
                  const res = await checkBackendHealth();
                  if (res.healthy) {
                    setServerTestStatus('success');
                    setServerStatusPill('connected');
                  } else {
                    setServerTestStatus('failed');
                    setServerStatusPill('offline');
                  }
                }}
              >
                Test Connection
              </button>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setServerUrlInput('');
                    setCustomApiUrl('');
                    setServerTestStatus(null);
                    setServerStatusPill('default');
                  }}
                >
                  Reset
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => {
                    setCustomApiUrl(serverUrlInput);
                    setShowServerModal(false);
                    checkBackendHealth().then((res) => {
                      setServerStatusPill(res.healthy ? 'connected' : 'offline');
                    });
                  }}
                >
                  Save & Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
