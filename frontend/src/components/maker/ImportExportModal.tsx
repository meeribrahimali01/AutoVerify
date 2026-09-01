import React, { useState } from 'react';
import { AutomatonData } from '../../types';
import { validateAutomaton } from '../../api/client';

export interface ImportExportModalProps {
  automaton: AutomatonData;
  isOpen: boolean;
  onClose: () => void;
  onImport: (automaton: AutomatonData) => void;
}

export const ImportExportModal: React.FC<ImportExportModalProps> = ({
  automaton, isOpen, onClose, onImport,
}) => {
  const [tab, setTab] = useState<'export' | 'import'>('export');
  const [importText, setImportText] = useState('');
  const [importError, setImportError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const jsonString = JSON.stringify(automaton, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `automaton_${automaton.type.toLowerCase()}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportSubmit = async () => {
    setImportError(null);
    try {
      const parsed = JSON.parse(importText);
      const val = await validateAutomaton(parsed);
      if (!val.valid) {
        setImportError(val.errors.join('\n') || 'Validation failed.');
        return;
      }
      onImport(parsed);
      onClose();
    } catch (err: any) {
      setImportError(`JSON Syntax Error: ${err.message}`);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      setImportText(event.target?.result as string);
    };
    reader.readAsText(file);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Import / Export</h3>
          <button className="btn-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-tabs">
          <button className={`modal-tab ${tab === 'export' ? 'active' : ''}`} onClick={() => setTab('export')}>
            Export JSON
          </button>
          <button className={`modal-tab ${tab === 'import' ? 'active' : ''}`} onClick={() => setTab('import')}>
            Import JSON
          </button>
        </div>

        <div className="modal-body">
          {tab === 'export' ? (
            <>
              <textarea readOnly value={jsonString} className="json-textarea" rows={12} />
              <div className="modal-actions">
                <button className="btn-outline-modal" onClick={handleCopy}>
                  {copied ? '✓ Copied' : 'Copy'}
                </button>
                <button className="btn-primary-modal" onClick={handleDownload}>
                  Download .json
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="hint-text mb-2">Paste automaton JSON or select a file:</p>
              <input type="file" accept=".json" onChange={handleFileUpload} className="file-input mb-2" />
              <textarea
                placeholder='{"type": "DFA", "states": ["q0"], ...}'
                value={importText}
                onChange={e => setImportText(e.target.value)}
                className="json-textarea"
                rows={10}
              />
              {importError && <pre className="error-box">{importError}</pre>}
              <div className="modal-actions">
                <button className="btn-outline-modal" onClick={onClose}>Cancel</button>
                <button className="btn-primary-modal" onClick={handleImportSubmit} disabled={!importText.trim()}>
                  Load Automaton
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
