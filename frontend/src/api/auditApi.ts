/**
 * Audit Trail, User Activity, and Multi-Format Export API Client
 */

const API_BASE = '/api/v1';

export interface AuditLogItem {
  id: string;
  sequence_number?: number;
  timestamp: string;
  username: string;
  role: string;
  department?: string;
  scope?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  status: string;
  session_id?: string;
  client_ip?: string;
  previous_event_hash: string;
  event_hash: string;
  payload: Record<string, any>;
}

export interface AuditLogListResponse {
  total_count: number;
  page: number;
  page_size: number;
  events: AuditLogItem[];
}

export interface IntegrityVerificationResult {
  is_valid: boolean;
  total_events_checked: number;
  chain_status: 'INTACT' | 'TAMPERED' | 'EMPTY';
  message: string;
  head_hash?: string;
  corrupted_at_sequence?: number;
}

export interface TimelineEvent {
  id: string;
  type: 'USER_ACTIVITY' | 'AUDIT_EVENT';
  timestamp: string;
  activity_type: string;
  page: string;
  plant_id?: string;
  entity_type?: string;
  entity_id?: string;
  status?: string;
  sequence_number?: number;
  event_hash?: string;
  details: Record<string, any>;
}

export interface SessionTimelineResponse {
  session_id: string;
  user_id: string;
  username: string;
  event_count: number;
  start_time?: string;
  end_time?: string;
  timeline: TimelineEvent[];
}

export interface SessionNarrationResponse {
  narration_id: string;
  session_id: string;
  status: string;
  generated_at: string;
  model_id: string;
  model_hash: string;
  source_event_count: number;
  summary: string;
  highlights: string[];
}

export async function fetchAuditLogs(
  token: string,
  params: {
    page?: number;
    pageSize?: number;
    action?: string;
    username?: string;
    entityType?: string;
    search?: string;
  } = {}
): Promise<AuditLogListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.set('page', String(params.page));
  if (params.pageSize) query.set('page_size', String(params.pageSize));
  if (params.action) query.set('action', params.action);
  if (params.username) query.set('username', params.username);
  if (params.entityType) query.set('entity_type', params.entityType);
  if (params.search) query.set('search', params.search);

  const res = await fetch(`${API_BASE}/audit/logs?${query.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch audit logs');
  return res.json();
}

export async function verifyAuditIntegrity(token: string): Promise<IntegrityVerificationResult> {
  const res = await fetch(`${API_BASE}/audit/verify-integrity`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to verify audit trail integrity');
  return res.json();
}

export async function logUserActivity(
  token: string,
  payload: {
    activity_type: string;
    page: string;
    plant_id?: string;
    entity_type?: string;
    entity_id?: string;
    details?: Record<string, any>;
  }
): Promise<void> {
  try {
    await fetch(`${API_BASE}/activity/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    // Non-blocking telemetry
    console.warn('Activity event recording failed:', err);
  }
}

export async function fetchSessionTimeline(
  token: string,
  sessionId: string
): Promise<SessionTimelineResponse> {
  const res = await fetch(`${API_BASE}/activity/sessions/${sessionId}/timeline`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch session timeline');
  return res.json();
}

export async function generateSessionNarration(
  token: string,
  sessionId: string
): Promise<SessionNarrationResponse> {
  const res = await fetch(`${API_BASE}/activity/sessions/${sessionId}/narrate`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to generate session narration');
  return res.json();
}

export function getExportUrl(format: 'csv' | 'xlsx' | 'pdf' | 'html', token: string): string {
  return `${API_BASE}/audit/export/${format}?token=${encodeURIComponent(token)}`;
}
