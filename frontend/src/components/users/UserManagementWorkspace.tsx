import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';

export interface UserRow {
  id: string;
  username: string;
  email: string;
  display_name: string;
  department: string;
  plant_scope: string[];
  role: string;
  is_active: boolean;
  is_locked: boolean;
  last_login_at?: string;
  created_at: string;
}

export const UserManagementWorkspace: React.FC = () => {
  const { token, hasRole } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Form states
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newDisplayName, setNewDisplayName] = useState('');
  const [newDepartment, setNewDepartment] = useState('ENGINEERING');
  const [newRole, setNewRole] = useState('PLANT_HEAD');
  const [newPlantScope, setNewPlantScope] = useState('HARIDWAR');
  const [newPassword, setNewPassword] = useState('');

  const loadUsers = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/users?page=1&page_size=50', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load user accounts');
      const data = await res.json();
      setUsers(data.users || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, [token]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    try {
      const res = await fetch('/api/v1/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          username: newUsername,
          email: newEmail,
          display_name: newDisplayName,
          department: newDepartment,
          plant_scope: [newPlantScope],
          role: newRole,
          password: newPassword,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error?.message || err.detail || 'User creation failed');
      }
      setShowCreateModal(false);
      setNewUsername('');
      setNewEmail('');
      setNewDisplayName('');
      setNewPassword('');
      await loadUsers();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleUnlock = async (userId: string) => {
    if (!token) return;
    try {
      const res = await fetch(`/api/v1/users/${userId}/unlock`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to unlock user');
      await loadUsers();
    } catch (err: any) {
      alert(err.message);
    }
  };

  if (!hasRole('ADMINISTRATOR')) {
    return (
      <div className="p-8 text-center text-slate-400">
        <h2 className="text-lg font-bold text-red-400 mb-2">Access Denied</h2>
        <p className="text-sm">User Management is restricted to Administrators.</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center border-b border-slate-700/60 pb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100">User & Access Management</h1>
          <p className="text-xs text-slate-400 mt-0.5">Role-Based Access Control and Plant Data Scope Governance</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg shadow transition-all"
        >
          + Add New User
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-xs text-red-200">
          {error}
        </div>
      )}

      {/* Users Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950 text-slate-400 uppercase font-semibold text-[11px] border-b border-slate-800">
            <tr>
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Department</th>
              <th className="px-4 py-3">Plant Scope</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Last Login</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">Loading user directory...</td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">No user accounts found.</td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-semibold text-slate-100">{u.display_name}</div>
                    <div className="text-[11px] text-slate-400">@{u.username} • {u.email}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[11px] text-slate-200">
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{u.department}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded bg-blue-950/60 text-blue-300 border border-blue-800/50 text-[11px]">
                      {u.plant_scope?.join(', ') || 'ALL'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {u.is_locked ? (
                      <span className="px-2 py-0.5 rounded bg-red-950/80 text-red-300 border border-red-800 text-[11px] font-semibold">
                        LOCKED
                      </span>
                    ) : u.is_active ? (
                      <span className="px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800 text-[11px]">
                        ACTIVE
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[11px]">
                        INACTIVE
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {u.last_login_at ? u.last_login_at.replace('T', ' ').substring(0, 16) : 'Never'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {u.is_locked && (
                      <button
                        onClick={() => handleUnlock(u.id)}
                        className="px-2 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-[11px]"
                      >
                        Unlock
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-xl p-6 shadow-2xl text-slate-100">
            <h3 className="text-base font-bold mb-4">Provision New User Account</h3>
            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block mb-1 text-slate-300">Username</label>
                  <input
                    type="text"
                    required
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-100"
                  />
                </div>
                <div>
                  <label className="block mb-1 text-slate-300">Display Name</label>
                  <input
                    type="text"
                    required
                    value={newDisplayName}
                    onChange={(e) => setNewDisplayName(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-100"
                  />
                </div>
              </div>

              <div>
                <label className="block mb-1 text-slate-300">Email Address</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-100"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block mb-1 text-slate-300">Department</label>
                  <select
                    value={newDepartment}
                    onChange={(e) => setNewDepartment(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-100"
                  >
                    <option value="ENGINEERING">Engineering</option>
                    <option value="OPERATIONS">Operations</option>
                    <option value="VAVE">VAVE</option>
                    <option value="PURCHASE">Purchase</option>
                    <option value="COMMERCIAL">Commercial</option>
                    <option value="EXECUTIVE">Executive</option>
                  </select>
                </div>
                <div>
                  <label className="block mb-1 text-slate-300">Role</label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-100"
                  >
                    <option value="PLANT_HEAD">Plant Head</option>
                    <option value="CENTRAL_OPERATIONS">Central Operations</option>
                    <option value="COMMERCIAL_VAVE">Commercial VAVE</option>
                    <option value="PURCHASE">Purchase & Sourcing</option>
                    <option value="ENGINEERING">Engineering</option>
                    <option value="VIEWER">Viewer</option>
                    <option value="ADMINISTRATOR">Administrator</option>
                  </select>
                </div>
                <div>
                  <label className="block mb-1 text-slate-300">Plant Scope</label>
                  <select
                    value={newPlantScope}
                    onChange={(e) => setNewPlantScope(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-100"
                  >
                    <option value="HARIDWAR">Haridwar</option>
                    <option value="DHARUHERA">Dharuhera</option>
                    <option value="NEEMRANA">Neemrana</option>
                    <option value="GURGAON">Gurgaon</option>
                    <option value="ALL">ALL (Universal)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block mb-1 text-slate-300">Initial Password (min 8 chars)</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-100"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-red-600 hover:bg-red-700 text-white font-semibold rounded shadow"
                >
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
