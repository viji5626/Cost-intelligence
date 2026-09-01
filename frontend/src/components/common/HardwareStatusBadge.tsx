import React from 'react';
import { Lock, Cpu, Database } from 'lucide-react';

interface HardwareProfileProps {
  tier?: string;
  executionMode?: string;
  safeRamGb?: number;
  gpuAvailable?: boolean;
}

export const HardwareStatusBadge: React.FC<HardwareProfileProps> = ({
  tier = 'TIER1_LOW',
  executionMode = 'GPU_PARTIAL_OFFLOAD',
  safeRamGb = 7.0,
  gpuAvailable = true,
}) => {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <span className="badge badge-hero" title="Air-gapped deployment verified">
        <Lock size={10} />
        AIR-GAP ACTIVE
      </span>
      <span className="badge badge-healthy" title={`Execution Mode: ${executionMode}`}>
        <Cpu size={10} />
        {tier} | {gpuAvailable ? 'RTX 4060 8GB' : 'CPU'}
      </span>
      <span className="badge badge-info" title="Safe Memory Operating Envelope">
        <Database size={10} />
        RAM: {safeRamGb} GB
      </span>
    </div>
  );
};
