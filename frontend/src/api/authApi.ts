/**
 * Authentication and System Readiness API Client
 */

const API_BASE = '/api/v1';

export interface BootstrapStatusResponse {
  is_bootstrapped: boolean;
  requires_setup: boolean;
  active_admins: number;
}

export interface UserSessionData {
  user_id: string;
  username: string;
  display_name: string;
  roles: string[];
  plant_scope: string[];
  department: string;
  session_id?: string;
  is_active: boolean;
  is_superuser?: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  display_name: string;
  roles: string[];
  plant_scope: string[];
  department: string;
  session_id: string;
  expires_at: string;
}

export interface SystemReadinessResponse {
  status: 'NEEDS_BOOTSTRAP' | 'NEEDS_RUNTIME_INIT' | 'READY_TO_RESTORE' | 'READY' | 'RECOVERY_REQUIRED' | 'UNINITIALIZED';
  is_ready: boolean;
  is_admin_configured: boolean;
  has_saved_config: boolean;
  saved_model_id?: string;
  saved_provider?: string;
  active_model_id?: string;
  active_provider?: string;
  recovery_mode: boolean;
  recovery_reason?: string;
  message: string;
}

export interface AvailableUserItem {
  username: string;
  display_name: string;
  role: string;
  department: string;
  plant_scope: string[];
}

export async function fetchBootstrapStatus(): Promise<BootstrapStatusResponse> {
  const res = await fetch(`${API_BASE}/auth/bootstrap-status`);
  if (!res.ok) throw new Error('Failed to fetch bootstrap status');
  return res.json();
}

export async function fetchAvailableUsers(): Promise<AvailableUserItem[]> {
  const res = await fetch(`${API_BASE}/auth/available-users`);
  if (!res.ok) throw new Error('Failed to fetch available users');
  return res.json();
}

export async function bootstrapAdmin(payload: {
  username: string;
  email: string;
  display_name: string;
  password: string;
  confirm_password: string;
}): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/bootstrap-admin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error?.message || err.detail || 'Bootstrap failed');
  }
  return res.json();
}

export async function loginUser(payload: { username: string; password: string }): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error?.message || err.detail || 'Login failed');
  }
  return res.json();
}

export async function fetchSession(token: string): Promise<UserSessionData> {
  const res = await fetch(`${API_BASE}/auth/session`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Invalid or expired session');
  return res.json();
}

export async function logoutUser(token: string): Promise<void> {
  await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function fetchSystemReadiness(): Promise<SystemReadinessResponse> {
  const res = await fetch(`${API_BASE}/system/readiness`);
  if (!res.ok) throw new Error('Failed to fetch readiness status');
  return res.json();
}

export async function initializeRuntime(
  token: string,
  payload: {
    provider: string;
    model_id: string;
    runtime_profile: string;
    context_length?: number;
    gpu_layers?: number;
  }
): Promise<any> {
  const res = await fetch(`${API_BASE}/system/runtime/initialize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error?.message || err.detail || 'Runtime initialization failed');
  }
  return res.json();
}

export async function restoreSavedRuntime(token: string): Promise<any> {
  const res = await fetch(`${API_BASE}/system/runtime/restore`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to restore saved runtime');
  return res.json();
}
