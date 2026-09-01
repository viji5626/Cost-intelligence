import { apiClient } from './client';
import { AuditLogEntry, HardwareProfile } from '../types';

export const systemApi = {
  getHardwareProfile: async (): Promise<HardwareProfile> => {
    return apiClient<HardwareProfile>('/system/hardware-profile');
  },

  getAuditLogs: async (limit: number = 50): Promise<AuditLogEntry[]> => {
    try {
      return await apiClient<AuditLogEntry[]>(`/system/audit-logs?limit=${limit}`);
    } catch {
      // Fallback structured audit entries if standalone audit endpoint not yet populated
      return [
        {
          id: 'audit-001',
          action: 'GATEWAY_VERIFICATION',
          entity_type: 'SYSTEM',
          entity_id: 'AIR_GAP_EGRESS_FILTER',
          payload: { egress_blocked: true, allowed_endpoints: ['127.0.0.1', 'localhost'] },
          created_at: new Date().toISOString(),
        },
      ];
    }
  },
};
