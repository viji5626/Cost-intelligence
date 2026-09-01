import React, { useState } from 'react';
import {
  Upload,
  FileText,
  Layers,
  Zap,
} from 'lucide-react';
import { aistudioApi } from '../../api/aistudio';
import { CapabilityStatus, DrawingExtractionResult } from '../../types/aistudio';

export const VisualDocumentInspector: React.FC = () => {
  const [, setDocType] = useState('ENGINEERING_DRAWING');
  const [isProcessing, setIsProcessing] = useState(false);
  const [extractionResult, setExtractionResult] = useState<DrawingExtractionResult | null>(null);
  const [activeFileName, setActiveFileName] = useState<string>('Sample_Cylinder_Head_DWG_12101.png');

  const handleRunSampleExtraction = async (sampleName: string, type: string) => {
    setIsProcessing(true);
    setActiveFileName(sampleName);
    setDocType(type);
    try {
      const res = await aistudioApi.extractVisualDocument(sampleName, 1_450_000, type);
      setExtractionResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const getBadgeStyle = (status: CapabilityStatus) => {
    switch (status) {
      case 'REAL_OCR':
      case 'REAL_VISION_MODEL':
        return {
          bg: 'rgba(16, 185, 129, 0.1)',
          color: 'var(--status-healthy)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
        };
      case 'CONTRACT_ONLY':
        return {
          bg: 'rgba(59, 130, 246, 0.1)',
          color: 'var(--status-info)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
        };
      case 'NOT_VERIFIED':
      default:
        return {
          bg: 'rgba(102, 102, 117, 0.1)',
          color: 'var(--text-muted)',
          border: '1px solid var(--border-subtle)',
        };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Capability Classification Matrix (Correction 2, 3, 4, 19) */}
      <div
        style={{
          padding: '12px 16px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
        }}
      >
        <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
          Air-Gapped Visual & OCR Capability Verification State
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
          <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Printed Digital OCR</div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ fontWeight: '600', fontSize: '12px', color: 'var(--text-primary)' }}>PDF Text Extractor</span>
              <span style={{ ...getBadgeStyle('REAL_OCR'), fontSize: '9px', fontWeight: '700', padding: '1px 5px', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)' }}>
                REAL_OCR
              </span>
            </div>
          </div>

          <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Drawing Title Block</div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ fontWeight: '600', fontSize: '12px', color: 'var(--text-primary)' }}>CAD Regex Parser</span>
              <span style={{ ...getBadgeStyle('REAL_OCR'), fontSize: '9px', fontWeight: '700', padding: '1px 5px', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)' }}>
                REAL_OCR
              </span>
            </div>
          </div>

          <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Handwriting Recognition</div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ fontWeight: '600', fontSize: '12px', color: 'var(--text-muted)' }}>VLM Offline Model</span>
              <span style={{ ...getBadgeStyle('NOT_VERIFIED'), fontSize: '9px', fontWeight: '700', padding: '1px 5px', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)' }}>
                NOT_VERIFIED
              </span>
            </div>
          </div>

          <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>GD&T & Weld Symbols</div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ fontWeight: '600', fontSize: '12px', color: 'var(--text-muted)' }}>Geometric Detector</span>
              <span style={{ ...getBadgeStyle('NOT_VERIFIED'), fontSize: '9px', fontWeight: '700', padding: '1px 5px', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)' }}>
                NOT_VERIFIED
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Split Interface */}
      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: '16px' }}>
        {/* Left Column: Upload & Sample Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Dropzone Container */}
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px dashed var(--border-strong)',
              borderRadius: 'var(--radius-sm)',
              padding: '24px 16px',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all var(--transition-fast)',
            }}
          >
            <Upload size={28} color="var(--status-info)" style={{ margin: '0 auto 10px' }} />
            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '4px' }}>
              Upload CAD Drawing or PDF
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
              Supports PNG, JPEG, PDF, TIFF, BMP, WebP
              <br />
              Max: 25 MB &bull; Max: 50 Pages &bull; In-Memory Only
            </div>
          </div>

          {/* Quick Preloaded Engineering Test Assets */}
          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
              Engineering Test Samples
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <button
                onClick={() => handleRunSampleExtraction('Sample_Cylinder_Head_DWG_12101.png', 'ENGINEERING_DRAWING')}
                disabled={isProcessing}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 10px',
                  backgroundColor: activeFileName.includes('Cylinder') ? 'var(--bg-tertiary)' : 'var(--bg-input)',
                  border: activeFileName.includes('Cylinder') ? '1px solid var(--status-info)' : '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--text-primary)',
                  fontSize: '11px',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <div>
                  <div style={{ fontWeight: '600' }}>Cylinder Head 100cc CAD Drawing</div>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>DWG-12101-AAH &bull; ADC12 &bull; Rev B</div>
                </div>
                <FileText size={14} color="var(--text-muted)" />
              </button>

              <button
                onClick={() => handleRunSampleExtraction('Sample_Haridwar_Ideathon_Slip_4921.png', 'IDEATHON_SLIP')}
                disabled={isProcessing}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 10px',
                  backgroundColor: activeFileName.includes('Ideathon') ? 'var(--bg-tertiary)' : 'var(--bg-input)',
                  border: activeFileName.includes('Ideathon') ? '1px solid var(--status-info)' : '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--text-primary)',
                  fontSize: '11px',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <div>
                  <div style={{ fontWeight: '600' }}>Haridwar Ideathon Paper Slip</div>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Borewell Water Recovery &bull; EMP-4921</div>
                </div>
                <FileText size={14} color="var(--text-muted)" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Structured Title Block & Annotation Cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {isProcessing ? (
            <div style={{ padding: '40px', backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', textAlign: 'center', color: 'var(--text-muted)' }}>
              <Zap size={24} color="var(--status-info)" className="animate-spin" style={{ margin: '0 auto 10px' }} />
              <div>Running DocumentDecoder & CompositeOCRManager...</div>
            </div>
          ) : extractionResult ? (
            <>
              {/* Extracted Title Block Metadata */}
              <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', paddingBottom: '8px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Layers size={13} color="var(--status-info)" />
                    Extracted Drawing Title Block & Engineering Attributes
                  </span>
                  <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--status-healthy)', backgroundColor: 'rgba(16, 185, 129, 0.1)', padding: '2px 6px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                    OCR Conf: {(extractionResult.ocr_confidence * 100).toFixed(1)}%
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
                  <div className="kv-row" style={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: 'none', backgroundColor: 'var(--bg-tertiary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
                    <span className="kv-key">Part Number</span>
                    <span className="kv-val" style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
                      {extractionResult.title_block.part_number || 'N/A'}
                    </span>
                  </div>

                  <div className="kv-row" style={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: 'none', backgroundColor: 'var(--bg-tertiary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
                    <span className="kv-key">Drawing Number</span>
                    <span className="kv-val">{extractionResult.title_block.drawing_number || 'N/A'}</span>
                  </div>

                  <div className="kv-row" style={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: 'none', backgroundColor: 'var(--bg-tertiary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
                    <span className="kv-key">Revision</span>
                    <span className="kv-val" style={{ color: 'var(--status-info)' }}>{extractionResult.title_block.revision || 'N/A'}</span>
                  </div>

                  <div className="kv-row" style={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: 'none', backgroundColor: 'var(--bg-tertiary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
                    <span className="kv-key">Material Specification</span>
                    <span className="kv-val">{extractionResult.title_block.material_grade || 'N/A'}</span>
                  </div>

                  <div className="kv-row" style={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: 'none', backgroundColor: 'var(--bg-tertiary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
                    <span className="kv-key">Surface Treatment</span>
                    <span className="kv-val">{extractionResult.title_block.surface_treatment || 'N/A'}</span>
                  </div>

                  <div className="kv-row" style={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: 'none', backgroundColor: 'var(--bg-tertiary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)' }}>
                    <span className="kv-key">General Tolerance</span>
                    <span className="kv-val">{extractionResult.title_block.general_tolerance || 'N/A'}</span>
                  </div>
                </div>
              </div>

              {/* Dimensions & Notes Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>
                    Dimensions & Tolerances ({extractionResult.dimensions.length})
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {extractionResult.dimensions.length > 0 ? (
                      extractionResult.dimensions.map((dim, idx) => (
                        <span
                          key={idx}
                          style={{
                            fontSize: '11px',
                            fontFamily: 'var(--font-mono)',
                            padding: '3px 8px',
                            backgroundColor: 'var(--bg-tertiary)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-sm)',
                            color: 'var(--text-primary)',
                          }}
                        >
                          {dim}
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>No dimension callouts detected.</span>
                    )}
                  </div>
                </div>

                <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>
                    Engineering Drawing Notes ({extractionResult.notes.length})
                  </div>
                  <ul style={{ listStyleType: 'none', padding: 0, margin: 0, fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {extractionResult.notes.map((n, idx) => (
                      <li key={idx} style={{ padding: '4px 6px', backgroundColor: 'var(--bg-input)', borderRadius: 'var(--radius-sm)' }}>
                        {n}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Raw OCR Text Preview */}
              <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
                <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>
                  Raw Document Text Output
                </div>
                <pre
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)',
                    whiteSpace: 'pre-wrap',
                    maxHeight: '120px',
                    overflowY: 'auto',
                  }}
                >
                  {extractionResult.raw_text}
                </pre>
              </div>
            </>
          ) : (
            <div style={{ padding: '60px 20px', backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
              Select an engineering test sample or drop a CAD/PDF document to view parsed attributes.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
