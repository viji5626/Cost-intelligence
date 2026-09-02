import React, { createContext, useContext, useState, useEffect } from 'react';
import { SystemReadinessResponse, fetchSystemReadiness, fetchBootstrapStatus } from '../api/authApi';

interface SystemReadinessContextType {
  readiness: SystemReadinessResponse | null;
  isBootstrapped: boolean;
  requiresSetup: boolean;
  isLoading: boolean;
  refreshReadiness: () => Promise<void>;
}

const SystemReadinessContext = createContext<SystemReadinessContextType | undefined>(undefined);

export const SystemReadinessProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [readiness, setReadiness] = useState<SystemReadinessResponse | null>(null);
  const [isBootstrapped, setIsBootstrapped] = useState<boolean>(true);
  const [requiresSetup, setRequiresSetup] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshReadiness = async () => {
    try {
      const bootStatus = await fetchBootstrapStatus();
      setIsBootstrapped(bootStatus.is_bootstrapped);
      setRequiresSetup(bootStatus.requires_setup);

      const readyData = await fetchSystemReadiness();
      setReadiness(readyData);
    } catch (err) {
      console.warn('Failed to refresh system readiness:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshReadiness();
  }, []);

  return (
    <SystemReadinessContext.Provider
      value={{
        readiness,
        isBootstrapped,
        requiresSetup,
        isLoading,
        refreshReadiness,
      }}
    >
      {children}
    </SystemReadinessContext.Provider>
  );
};

export function useSystemReadiness(): SystemReadinessContextType {
  const ctx = useContext(SystemReadinessContext);
  if (!ctx) throw new Error('useSystemReadiness must be used within a SystemReadinessProvider');
  return ctx;
}
