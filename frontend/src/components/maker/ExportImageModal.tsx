import React, { useState } from 'react';
import './ExportImageModal.css';
import { AutomatonType } from '../../types';
import { ExportOptions } from '../graph/GraphCanvas';

interface ExportImageModalProps {
  isOpen: boolean;
  onClose: () => void;
  automatonType: AutomatonType;
  onExport: (options: ExportOptions) => Promise<void>;
}

export const ExportImageModal: React.FC<ExportImageModalProps> = ({
  isOpen,
  onClose,
  automatonType,
  onExport,
}) => {
  const [format, setFormat] = useState<'png' | 'svg'>('png');
  const [background, setBackground] = useState<'white' | 'theme' | 'transparent'>('white');
  const [exporting, setExporting] = useState(false);

  if (!isOpen) return null;

  const typeSuffix =
    automatonType === 'EPSILON_NFA' ? 'eNFA' : automatonType === 'NFA' ? 'NFA' : 'DFA';
  const filename = `AutoVerify-${typeSuffix}.${format}`;

  const handleDownload = async () => {
    setExporting(true);
    try {
      await onExport({
        format,
        background,
        scale: 3,
        filename,
      });
      onClose();
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="export-modal-backdrop" onClick={onClose}>
      <div className="export-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="export-modal-header">
          <div className="export-modal-title">
            <span>🖼</span>
            <span>Export Diagram Image</span>
          </div>
          <button className="tool-btn icon-only" onClick={onClose} title="Close">
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="export-modal-body">
          {/* Format Selection */}
          <div className="export-option-group">
            <div className="export-group-label">Format</div>
            <div className="format-segmented-control">
              <button
                type="button"
                className={`format-btn ${format === 'png' ? 'active' : ''}`}
                onClick={() => setFormat('png')}
              >
                <span className="format-name">PNG</span>
                <span className="format-desc">High-Res Bitmap (3x DPI)</span>
              </button>
              <button
                type="button"
                className={`format-btn ${format === 'svg' ? 'active' : ''}`}
                onClick={() => setFormat('svg')}
              >
                <span className="format-name">SVG</span>
                <span className="format-desc">Vector Graphics</span>
              </button>
            </div>
          </div>

          {/* Background Selection */}
          <div className="export-option-group">
            <div className="export-group-label">Background</div>
            <div className="bg-options-list">
              <label
                className={`bg-option-item ${background === 'white' ? 'active' : ''}`}
                onClick={() => setBackground('white')}
              >
                <div className="bg-option-label">
                  <input
                    type="radio"
                    name="bgOption"
                    className="bg-radio"
                    checked={background === 'white'}
                    onChange={() => setBackground('white')}
                  />
                  <span>White Background</span>
                </div>
                <span className="bg-badge">Default</span>
              </label>

              <label
                className={`bg-option-item ${background === 'theme' ? 'active' : ''}`}
                onClick={() => setBackground('theme')}
              >
                <div className="bg-option-label">
                  <input
                    type="radio"
                    name="bgOption"
                    className="bg-radio"
                    checked={background === 'theme'}
                    onChange={() => setBackground('theme')}
                  />
                  <span>Current Theme</span>
                </div>
              </label>

              <label
                className={`bg-option-item ${background === 'transparent' ? 'active' : ''}`}
                onClick={() => setBackground('transparent')}
              >
                <div className="bg-option-label">
                  <input
                    type="radio"
                    name="bgOption"
                    className="bg-radio"
                    checked={background === 'transparent'}
                    onChange={() => setBackground('transparent')}
                  />
                  <span>Transparent</span>
                </div>
              </label>
            </div>
          </div>

          <p className="export-info-text">
            Output will be exported as <strong>{filename}</strong> with clean padding around all states and transition arrows.
          </p>
        </div>

        {/* Footer */}
        <div className="export-modal-footer">
          <button className="btn-secondary" onClick={onClose} disabled={exporting}>
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={handleDownload}
            disabled={exporting}
          >
            <span>↓</span>
            <span>Download {format.toUpperCase()}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
