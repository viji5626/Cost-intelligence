import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserSessionData, fetchSession, loginUser, logoutUser } from '../api/authApi';

interface AuthContextType {
  currentUser: UserSessionData | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (role: string) => boolean;
  hasPlantAccess: (plantId: string) => boolean;
  setAuthSession: (token: string, user: UserSessionData) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('hero_auth_token'));
  const [currentUser, setCurrentUser] = useState<UserSessionData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadUser() {
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const user = await fetchSession(token);
        setCurrentUser(user);
      } catch (err) {
        console.warn('Session expired or invalid:', err);
        localStorage.removeItem('hero_auth_token');
        setToken(null);
        setCurrentUser(null);
      } finally {
        setIsLoading(false);
      }
    }
    loadUser();
  }, [token]);

  const login = async (username: string, password: string) => {
    const res = await loginUser({ username, password });
    localStorage.setItem('hero_auth_token', res.access_token);
    setToken(res.access_token);
    setCurrentUser({
      user_id: res.user_id,
      username: res.username,
      display_name: res.display_name,
      roles: res.roles,
      plant_scope: res.plant_scope,
      department: res.department,
      session_id: res.session_id,
      is_active: true,
      is_superuser: res.roles.includes('ADMINISTRATOR'),
    });
  };

  const logout = async () => {
    if (token) {
      try {
        await logoutUser(token);
      } catch (e) {
        // ignore
      }
    }
    localStorage.removeItem('hero_auth_token');
    setToken(null);
    setCurrentUser(null);
  };

  const setAuthSession = (newToken: string, user: UserSessionData) => {
    localStorage.setItem('hero_auth_token', newToken);
    setToken(newToken);
    setCurrentUser(user);
  };

  const hasRole = (role: string) => {
    if (!currentUser) return false;
    if (currentUser.roles.includes('ADMINISTRATOR') || currentUser.roles.includes('ADMIN')) return true;
    return currentUser.roles.includes(role);
  };

  const hasPlantAccess = (plantId: string) => {
    if (!currentUser) return false;
    if (currentUser.roles.includes('ADMINISTRATOR') || currentUser.roles.includes('CENTRAL_OPERATIONS')) return true;
    if (currentUser.plant_scope.includes('ALL')) return true;
    return currentUser.plant_scope.map(p => p.toUpperCase()).includes(plantId.toUpperCase());
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        token,
        isAuthenticated: !!currentUser,
        isLoading,
        login,
        logout,
        hasRole,
        hasPlantAccess,
        setAuthSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
