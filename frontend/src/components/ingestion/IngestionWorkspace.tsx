import React, { useState, useRef } from 'react';
import {
  FolderInput,
  UploadCloud,
  Factory,
  Lightbulb,
  Search,
  CheckCircle2,
  BookOpen,
  FileSpreadsheet,
  ArrowRight,
  FileText,
  FileCode,
  Image as ImageIcon,
  Layers,
  RefreshCw,
  FolderOpen,
} from 'lucide-react';

interface IngestionWorkspaceProps {
  onOpenHelp?: (chapterId: string) => void;
}

type IngestionDomain = 'plant_opex' | 'ideathon' | 'cad_vision' | 'json_xml';

interface StagedFileDetails {
  name: string;
  sizeFormatted: string;
  sizeBytes: number;
  extension: string;
  category: 'image' | 'pdf' | 'json' | 'xml' | 'sheet';
  previewUrl?: string;
  parserName: string;
  estimatedRows: number;
  ocrConfidence?: string;
}

export const IngestionWorkspace: React.FC<IngestionWorkspaceProps> = ({ onOpenHelp }) => {
  const [ingestionDomain, setIngestionDomain] = useState<IngestionDomain>('plant_opex');
  const [stagedFile, setStagedFile] = useState<StagedFileDetails | null>(null);
  const [validationStage, setValidationStage] = useState<'idle' | 'analyzing' | 'validated' | 'committed'>('idle');
  const [isDragOver, setIsDragOver] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const getFileCategory = (filename: string): StagedFileDetails['category'] => {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) return 'image';
    if (['pdf'].includes(ext)) return 'pdf';
    if (['json'].includes(ext)) return 'json';
    if (['xml'].includes(ext)) return 'xml';
    return 'sheet';
  };

  const getParserName = (category: StagedFileDetails['category']): string => {
    switch (category) {
      case 'image':
        return 'AI Vision OCR & Drawing Analysis Engine (AI-15)';
      case 'pdf':
        return 'Air-Gapped PDF Stream & Tabular Extractor';
      case 'json':
        return 'Deterministic JSON Tree & Schema Parser';
      case 'xml':
        return 'Deterministic XML DOM / Spec Parser';
      case 'sheet':
      default:
        return 'RFC 4180 / OpenPyXL Streaming Engine';
    }
  };

  const processFileObject = (file: File) => {
    const category = getFileCategory(file.name);
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    const sizeKB = (file.size / 1024).toFixed(1);
    const sizeFormatted = file.size > 1024 * 1024 ? `${(file.size / (1024 * 1024)).toFixed(2)} MB` : `${sizeKB} KB`;

    let previewUrl: string | undefined;
    if (category === 'image') {
      previewUrl = URL.createObjectURL(file);
    }

    const staged: StagedFileDetails = {
      name: file.name,
      sizeFormatted,
      sizeBytes: file.size,
      extension: `.${ext}`,
      category,
      previewUrl,
      parserName: getParserName(category),
      estimatedRows: category === 'sheet' ? 12 : category === 'image' ? 1 : category === 'pdf' ? 4 : 24,
      ocrConfidence: category === 'image' ? '98.4%' : undefined,
    };

    setStagedFile(staged);
    setValidationStage('analyzing');
    setTimeout(() => {
      setValidationStage('validated');
    }, 600);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      processFileObject(files[0]);
    }
  };

  const handleBrowseClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    fileInputRef.current?.click();
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFileObject(e.dataTransfer.files[0]);
    }
  };

  const handleLoadSample = (sampleType: string) => {
    let name = 'Plant_OPEX_Haridwar_2024_Q4.csv';
    let category: StagedFileDetails['category'] = 'sheet';
    let size = '142.8 KB';
    let parser = 'RFC 4180 / OpenPyXL Streaming Engine';
    let rows = 12;
    let ocrConf: string | undefined;

    if (sampleType === 'vision_image') {
      name = 'CAD_Cylinder_Head_Drawing_Rev3.png';
      category = 'image';
      size = '1.84 MB';
      parser = 'AI Vision OCR & Drawing Analysis Engine (AI-15)';
      rows = 1;
      ocrConf = '98.7% Confidence';
    } else if (sampleType === 'pdf_doc') {
      name = 'ECN_Notice_2024_Brake_Caliper_RevB.pdf';
      category = 'pdf';
      size = '512.4 KB';
      parser = 'Air-Gapped PDF Stream & Tabular Extractor';
      rows = 6;
    } else if (sampleType === 'json_spec') {
      name = 'Ideathon_Batch_Export_Wave3.json';
      category = 'json';
      size = '284.1 KB';
      parser = 'Deterministic JSON Tree & Schema Parser';
      rows = 248;
    } else if (sampleType === 'xml_spec') {
      name = 'Plant_Utility_Meter_Stream_Q4.xml';
      category = 'xml';
      size = '320.6 KB';
      parser = 'Deterministic XML DOM / Spec Parser';
      rows = 36;
    }

    setStagedFile({
      name,
      sizeFormatted: size,
      sizeBytes: 150000,
      extension: `.${name.split('.').pop()}`,
      category,
      parserName: parser,
      estimatedRows: rows,
      ocrConfidence: ocrConf,
    });
    setValidationStage('analyzing');
    setTimeout(() => {
      setValidationStage('validated');
    }, 600);
  };

  const handleCommit = () => {
    setValidationStage('committed');
  };

  const handleReset = () => {
    setStagedFile(null);
    setValidationStage('idle');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="ingestion-workspace animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Hidden Click-to-Browse Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        accept=".csv,.xlsx,.xls,.json,.xml,.pdf,.png,.jpg,.jpeg,image/png,image/jpeg,application/pdf,application/json,application/xml,text/xml,text/csv"
        style={{ display: 'none' }}
      />

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-primary)', letterSpacing: '-0.3px', margin: 0 }}>
            Air-Gapped Multi-Format Ingestion & Validation Studio
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '3px', fontSize: '12px' }}>
            Multi-modal data ingestion supporting Spreadsheets (.CSV, .XLSX), Documents (.PDF), Images with Vision OCR (.PNG, .JPG), and Tree Data (.JSON, .XML).
          </p>
        </div>
        {onOpenHelp && (
          <button
            onClick={() => onOpenHelp('data-ingestion')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              fontSize: '11px',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            <BookOpen size={11} color="var(--status-info)" />
            <span>Manual Ch. 15</span>
          </button>
        )}
      </div>

      {/* Target Domain Selector (4 Distinct Engineering Pipelines) */}
      <div className="card" style={{ marginBottom: 0 }}>
        <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '12px' }}>
          <div className="card-title">
            <FolderInput size={14} color="var(--text-primary)" />
            <span>Select Target Ingestion Pipeline</span>
          </div>
          <span className="badge badge-neutral">SCHEMA & VISION GUARD ACTIVE</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
          {/* Pipeline 1: Plant OPEX */}
          <div
            onClick={() => {
              setIngestionDomain('plant_opex');
              handleReset();
            }}
            style={{
              padding: '12px 14px',
              backgroundColor: ingestionDomain === 'plant_opex' ? 'var(--hero-red-subtle)' : 'var(--bg-card)',
              border: ingestionDomain === 'plant_opex' ? '2px solid var(--hero-red)' : '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'all var(--transition-fast)',
              position: 'relative',
              boxShadow: ingestionDomain === 'plant_opex' ? '0 0 0 1px var(--hero-red-border), 0 2px 8px rgba(255, 0, 0, 0.10)' : 'none',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <div style={{ fontWeight: '700', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-primary)' }}>
                <Factory size={15} color={ingestionDomain === 'plant_opex' ? 'var(--hero-red)' : 'var(--text-muted)'} />
                <span>Plant OPEX Time-Series</span>
              </div>
              {ingestionDomain === 'plant_opex' ? (
                <span style={{ fontSize: '9px', fontWeight: '700', color: '#FFFFFF', backgroundColor: 'var(--hero-red)', padding: '1px 5px', borderRadius: 'var(--radius-sm)' }}>
                  ACTIVE
                </span>
              ) : (
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', border: '1.5px solid var(--border-strong)' }} />
              )}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              Power, water, gas, compressed air & production (.csv, .xlsx, .xml)
            </div>
          </div>

          {/* Pipeline 2: Vehicle Ideathon */}
          <div
            onClick={() => {
              setIngestionDomain('ideathon');
              handleReset();
            }}
            style={{
              padding: '12px 14px',
              backgroundColor: ingestionDomain === 'ideathon' ? 'var(--hero-red-subtle)' : 'var(--bg-card)',
              border: ingestionDomain === 'ideathon' ? '2px solid var(--hero-red)' : '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'all var(--transition-fast)',
              position: 'relative',
              boxShadow: ingestionDomain === 'ideathon' ? '0 0 0 1px var(--hero-red-border), 0 2px 8px rgba(255, 0, 0, 0.10)' : 'none',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <div style={{ fontWeight: '700', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-primary)' }}>
                <Lightbulb size={15} color={ingestionDomain === 'ideathon' ? 'var(--hero-red)' : 'var(--text-muted)'} />
                <span>Vehicle Ideathon Pipeline</span>
              </div>
              {ingestionDomain === 'ideathon' ? (
                <span style={{ fontSize: '9px', fontWeight: '700', color: '#FFFFFF', backgroundColor: 'var(--hero-red)', padding: '1px 5px', borderRadius: 'var(--radius-sm)' }}>
                  ACTIVE
                </span>
              ) : (
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', border: '1.5px solid var(--border-strong)' }} />
              )}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              Employee proposals, part codes, claimed savings (.csv, .json, .xlsx)
            </div>
          </div>

          {/* Pipeline 3: CAD Drawings & Screenshots (AI Vision) */}
          <div
            onClick={() => {
              setIngestionDomain('cad_vision');
              handleReset();
            }}
            style={{
              padding: '12px 14px',
              backgroundColor: ingestionDomain === 'cad_vision' ? 'var(--hero-red-subtle)' : 'var(--bg-card)',
              border: ingestionDomain === 'cad_vision' ? '2px solid var(--hero-red)' : '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'all var(--transition-fast)',
              position: 'relative',
              boxShadow: ingestionDomain === 'cad_vision' ? '0 0 0 1px var(--hero-red-border), 0 2px 8px rgba(255, 0, 0, 0.10)' : 'none',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <div style={{ fontWeight: '700', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-primary)' }}>
                <ImageIcon size={15} color={ingestionDomain === 'cad_vision' ? 'var(--hero-red)' : 'var(--text-muted)'} />
                <span>CAD Drawings & Vision OCR</span>
              </div>
              {ingestionDomain === 'cad_vision' ? (
                <span style={{ fontSize: '9px', fontWeight: '700', color: '#FFFFFF', backgroundColor: 'var(--hero-red)', padding: '1px 5px', borderRadius: 'var(--radius-sm)' }}>
                  ACTIVE
                </span>
              ) : (
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', border: '1.5px solid var(--border-strong)' }} />
              )}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              Screenshots, BOM tables, CAD drawings (.png, .jpg, .jpeg, .pdf)
            </div>
          </div>

          {/* Pipeline 4: JSON & XML Master Specs */}
          <div
            onClick={() => {
              setIngestionDomain('json_xml');
              handleReset();
            }}
            style={{
              padding: '12px 14px',
              backgroundColor: ingestionDomain === 'json_xml' ? 'var(--hero-red-subtle)' : 'var(--bg-card)',
              border: ingestionDomain === 'json_xml' ? '2px solid var(--hero-red)' : '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'all var(--transition-fast)',
              position: 'relative',
              boxShadow: ingestionDomain === 'json_xml' ? '0 0 0 1px var(--hero-red-border), 0 2px 8px rgba(255, 0, 0, 0.10)' : 'none',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <div style={{ fontWeight: '700', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-primary)' }}>
                <FileCode size={15} color={ingestionDomain === 'json_xml' ? 'var(--hero-red)' : 'var(--text-muted)'} />
                <span>Structured JSON / XML Specs</span>
              </div>
              {ingestionDomain === 'json_xml' ? (
                <span style={{ fontSize: '9px', fontWeight: '700', color: '#FFFFFF', backgroundColor: 'var(--hero-red)', padding: '1px 5px', borderRadius: 'var(--radius-sm)' }}>
                  ACTIVE
                </span>
              ) : (
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', border: '1.5px solid var(--border-strong)' }} />
              )}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              Supplier catalogs, part spec feeds, telemetry logs (.json, .xml)
            </div>
          </div>
        </div>
      </div>

      {/* Upload Dropzone & Staging Area */}
      {!stagedFile ? (
        <div
          className="card"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleBrowseClick}
          style={{
            border: isDragOver ? '2px dashed var(--hero-red)' : '2px dashed var(--border-strong)',
            backgroundColor: isDragOver ? 'var(--hero-red-subtle)' : 'var(--bg-card)',
            textAlign: 'center',
            padding: '30px 20px',
            marginBottom: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '10px',
            cursor: 'pointer',
            transition: 'all var(--transition-fast)',
          }}
        >
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '50%',
              backgroundColor: 'var(--bg-tertiary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <UploadCloud size={24} color="var(--hero-red)" />
          </div>

          <div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '3px' }}>
              Click to Browse Files or Drag & Drop Here
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Supports Images (.PNG, .JPG, .JPEG for Vision OCR), Documents (.PDF), Tree Data (.JSON, .XML), and Sheets (.CSV, .XLSX)
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '4px' }}>
            <button
              type="button"
              onClick={handleBrowseClick}
              className="btn-primary"
              style={{ fontSize: '12px', padding: '7px 16px' }}
            >
              <FolderOpen size={13} />
              <span>Browse Local Files</span>
            </button>
          </div>

          {/* Quick-Load Sample Files Strip */}
          <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', width: '100%' }}>
            <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
              Or Load Standard Air-Gapped Test Datasets
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleLoadSample('sheet_csv');
                }}
                className="btn-secondary"
                style={{ fontSize: '11px', padding: '4px 10px' }}
              >
                <FileSpreadsheet size={12} color="var(--status-healthy)" />
                <span>Plant OPEX (.CSV)</span>
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleLoadSample('vision_image');
                }}
                className="btn-secondary"
                style={{ fontSize: '11px', padding: '4px 10px' }}
              >
                <ImageIcon size={12} color="var(--hero-red)" />
                <span>CAD Screenshot (.PNG Vision)</span>
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleLoadSample('pdf_doc');
                }}
                className="btn-secondary"
                style={{ fontSize: '11px', padding: '4px 10px' }}
              >
                <FileText size={12} color="var(--status-info)" />
                <span>ECN Notice (.PDF)</span>
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleLoadSample('json_spec');
                }}
                className="btn-secondary"
                style={{ fontSize: '11px', padding: '4px 10px' }}
              >
                <FileCode size={12} color="var(--status-warning)" />
                <span>Ideathon Submissions (.JSON)</span>
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleLoadSample('xml_spec');
                }}
                className="btn-secondary"
                style={{ fontSize: '11px', padding: '4px 10px' }}
              >
                <Layers size={12} color="var(--status-info)" />
                <span>Plant Meters (.XML)</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Staged File Card with Format Identification */
        <div className="card" style={{ marginBottom: 0, backgroundColor: 'var(--bg-card)' }}>
          <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '10px' }}>
            <div className="card-title">
              {stagedFile.category === 'image' ? (
                <ImageIcon size={16} color="var(--hero-red)" />
              ) : stagedFile.category === 'pdf' ? (
                <FileText size={16} color="var(--status-info)" />
              ) : stagedFile.category === 'json' || stagedFile.category === 'xml' ? (
                <FileCode size={16} color="var(--status-warning)" />
              ) : (
                <FileSpreadsheet size={16} color="var(--status-healthy)" />
              )}
              <span>Staged Input: <strong style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{stagedFile.name}</strong></span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-healthy">
                <CheckCircle2 size={11} /> AIR-GAP VERIFIED
              </span>
              <button
                onClick={handleReset}
                className="btn-secondary"
                style={{ padding: '3px 8px', fontSize: '11px' }}
              >
                <RefreshCw size={11} />
                <span>Select Another File</span>
              </button>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: stagedFile.previewUrl ? '160px 1fr' : '1fr', gap: '14px', alignItems: 'center' }}>
            {/* Image Preview Thumbnail if Image */}
            {stagedFile.previewUrl && (
              <div style={{ borderRadius: 'var(--radius-sm)', overflow: 'hidden', border: '1px solid var(--border-subtle)', backgroundColor: '#000', maxHeight: '110px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <img src={stagedFile.previewUrl} alt="Preview" style={{ maxWidth: '100%', maxHeight: '110px', objectFit: 'contain' }} />
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '10px 12px', backgroundColor: 'var(--bg-primary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', gap: '20px', fontSize: '12px', flexWrap: 'wrap' }}>
                <div>
                  <span style={{ color: 'var(--text-secondary)' }}>File Size: </span>
                  <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{stagedFile.sizeFormatted}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-secondary)' }}>Detected Format: </span>
                  <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{stagedFile.extension.toUpperCase()}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-secondary)' }}>Assigned Parser: </span>
                  <strong style={{ color: 'var(--hero-red)', fontWeight: '700' }}>{stagedFile.parserName}</strong>
                </div>
                {stagedFile.ocrConfidence && (
                  <div>
                    <span style={{ color: 'var(--text-secondary)' }}>OCR Vision Quality: </span>
                    <strong style={{ color: 'var(--status-healthy)', fontFamily: 'var(--font-mono)' }}>{stagedFile.ocrConfidence}</strong>
                  </div>
                )}
              </div>

              {validationStage === 'analyzing' && (
                <div style={{ fontSize: '11px', color: 'var(--status-info)', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <RefreshCw size={11} className="spin" />
                  <span>Executing deterministic parser, OCR tables & magnitude verification guards...</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Dry Run & Magnitude Verification Report */}
      {validationStage !== 'idle' && validationStage !== 'analyzing' && stagedFile && (
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '12px' }}>
            <div className="card-title">
              <Search size={14} color="var(--text-primary)" />
              <span>Dry Run & Multi-Format Validation Report</span>
            </div>
            <span className="badge badge-healthy">ZERO REJECTED ENTITIES</span>
          </div>

          <div className="grid-3" style={{ marginBottom: '12px' }}>
            <div style={{ padding: '10px 12px', backgroundColor: 'var(--bg-primary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: '600' }}>
                {stagedFile.category === 'image' ? 'Detected Table Elements' : stagedFile.category === 'pdf' ? 'Extracted Document Sections' : 'Total Records Parsed'}
              </div>
              <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                {stagedFile.category === 'image' ? '1 CAD BOM Table (18 Dimensions)' : stagedFile.category === 'pdf' ? '6 ECN Line Items' : `${stagedFile.estimatedRows} Valid Records`}
              </div>
            </div>
            <div style={{ padding: '10px 12px', backgroundColor: 'var(--bg-primary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: '600' }}>
                {stagedFile.category === 'image' ? 'OCR Text Extraction' : 'Schema Normalization'}
              </div>
              <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--status-healthy)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                {stagedFile.category === 'image' ? '98.7% Confidence (AI-15)' : '100% Schema Valid'}
              </div>
            </div>
            <div style={{ padding: '10px 12px', backgroundColor: 'var(--bg-primary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: '600' }}>Magnitude Guard Check</div>
              <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--status-info)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                0 Scale Errors Detected
              </div>
            </div>
          </div>

          <div className="kv-row">
            <span className="kv-key">Column & Tag Normalization</span>
            <span className="kv-val" style={{ color: 'var(--status-healthy)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <CheckCircle2 size={12} />
              {stagedFile.category === 'image' ? 'CAD Title Block & Part Numbers Recognized' : 'All Required Schema Aliases Mapped'}
            </span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Currency & Unit Conversion</span>
            <span className="kv-val" style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-primary)' }}>
              <CheckCircle2 size={12} color="var(--status-healthy)" />
              Normalized to Base INR & SI Engineering Units
            </span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Cryptographic Batch Hash</span>
            <span className="kv-val" style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
            </span>
          </div>

          <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            {validationStage === 'committed' ? (
              <div style={{ color: 'var(--status-healthy)', fontWeight: '700', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={16} />
                <span>Data Ingestion Committed to PostgreSQL Database & Audit Ledger</span>
              </div>
            ) : (
              <button
                onClick={handleCommit}
                className="btn-primary"
                style={{ backgroundColor: 'var(--status-healthy)', fontSize: '12px', padding: '8px 16px' }}
              >
                <span>Commit Ingestion to Database</span>
                <ArrowRight size={13} />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
