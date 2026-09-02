import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { SystemReadinessProvider, useSystemReadiness } from './context/SystemReadinessContext';
import { FirstBootAdminSetupModal } from './components/auth/FirstBootAdminSetupModal';
import { LoginModal } from './components/auth/LoginModal';
import { UserManagementWorkspace } from './components/users/UserManagementWorkspace';
import { UserActivityWorkspace } from './components/activity/UserActivityWorkspace';
import { AIStudioWorkspace } from './components/aistudio/AIStudioWorkspace';
import { AuditLogWorkspace } from './components/audit/AuditLogWorkspace';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Header } from './components/common/Header';
import { Sidebar } from './components/common/Sidebar';
import { Footer } from './components/common/Footer';
import { FloatingExecutiveAssistant } from './components/common/FloatingExecutiveAssistant';
import { ExecutiveDashboard } from './components/dashboard/ExecutiveDashboard';
import { ExecutiveCopilotWorkspace } from './components/executive/ExecutiveCopilotWorkspace';
import { ReviewQueueWorkspace } from './components/governance/ReviewQueueWorkspace';
import { HardwareMonitor } from './components/hardware/HardwareMonitor';
import { IdeaDetailView } from './components/ideathon/IdeaDetailView';
import { IdeathonWorkspace } from './components/ideathon/IdeathonWorkspace';
import { IngestionWorkspace } from './components/ingestion/IngestionWorkspace';
import { OpexWorkspace } from './components/opex/OpexWorkspace';
import { OpportunityWorkspace } from './components/opportunity/OpportunityWorkspace';
import { HelpManualWorkspace } from './components/help/HelpManualWorkspace';
import { logUserActivity } from './api/auditApi';

const MainApplication: React.FC = () => {
  const { isAuthenticated, isLoading: authLoading, token } = useAuth();
  const { requiresSetup, isLoading: readyLoading } = useSystemReadiness();

  const [activeTab, setActiveTab] = useState('overview');
  const [selectedIdeaId, setSelectedIdeaId] = useState<string | null>(null);
  const [targetHelpChapterId, setTargetHelpChapterId] = useState<string | undefined>(undefined);

  // Track page change activity
  useEffect(() => {
    if (token && isAuthenticated) {
      logUserActivity(token, {
        activity_type: 'PAGE_OPENED',
        page: activeTab,
      });
    }
  }, [activeTab, token, isAuthenticated]);

  const handleSelectIdea = (ideaId: string) => {
    setSelectedIdeaId(ideaId);
    setActiveTab('idea-detail');
  };

  const handleBackToIdeathon = () => {
    setSelectedIdeaId(null);
    setActiveTab('ideathon');
  };

  const handleOpenHelp = (chapterId?: string) => {
    setTargetHelpChapterId(chapterId || 'getting-started');
    setActiveTab('help');
  };

  if (authLoading || readyLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-slate-950 text-slate-400 text-xs font-mono">
        Initializing Hero Cost Intelligence Security Subsystem...
      </div>
    );
  }

  // First-boot Admin Setup Gate
  if (requiresSetup) {
    return <FirstBootAdminSetupModal />;
  }

  // Authentication Gate
  if (!isAuthenticated) {
    return <LoginModal />;
  }

  return (
    <div className="app-container">
      <Sidebar
        activeTab={activeTab === 'idea-detail' ? 'ideathon' : activeTab}
        setActiveTab={(tab) => {
          setSelectedIdeaId(null);
          setActiveTab(tab);
        }}
        pendingReviewsCount={14}
      />
      <div className="main-content">
        <Header activeTab={activeTab} />
        <main className="content-body">
          {activeTab === 'overview' && (
            <ExecutiveDashboard
              onNavigate={(tab) => {
                setSelectedIdeaId(null);
                setActiveTab(tab);
              }}
              onSelectIdea={handleSelectIdea}
            />
          )}

          {activeTab === 'executive_copilot' && (
            <ExecutiveCopilotWorkspace onOpenHelp={handleOpenHelp} />
          )}

          {activeTab === 'aistudio' && (
            <AIStudioWorkspace onOpenHelp={handleOpenHelp} />
          )}

          {activeTab === 'ideathon' && (
            <IdeathonWorkspace
              onSelectIdea={handleSelectIdea}
              onOpenHelp={handleOpenHelp}
            />
          )}

          {activeTab === 'idea-detail' && selectedIdeaId && (
            <IdeaDetailView
              ideaId={selectedIdeaId}
              onBack={handleBackToIdeathon}
            />
          )}

          {activeTab === 'opex' && (
            <OpexWorkspace onOpenHelp={handleOpenHelp} />
          )}

          {activeTab === 'governance' && (
            <ReviewQueueWorkspace
              onSelectIdea={handleSelectIdea}
              onOpenHelp={handleOpenHelp}
            />
          )}

          {activeTab === 'opportunity' && (
            <OpportunityWorkspace onOpenHelp={handleOpenHelp} />
          )}

          {activeTab === 'ingestion' && (
            <IngestionWorkspace onOpenHelp={handleOpenHelp} />
          )}

          {activeTab === 'users' && (
            <UserManagementWorkspace />
          )}

          {activeTab === 'activity' && (
            <UserActivityWorkspace />
          )}

          {activeTab === 'hardware' && (
            <HardwareMonitor onOpenHelp={handleOpenHelp} />
          )}

          {activeTab === 'audit' && (
            <AuditLogWorkspace onOpenHelp={handleOpenHelp} />
          )}

          {activeTab === 'help' && (
            <HelpManualWorkspace
              initialChapterId={targetHelpChapterId}
              onNavigateWorkspace={(tab) => {
                setSelectedIdeaId(null);
                setActiveTab(tab);
              }}
            />
          )}
        </main>
        <Footer />
      </div>

      {/* Global Floating Executive Assistant across all pages except full-screen copilot */}
      {activeTab !== 'executive_copilot' && (
        <FloatingExecutiveAssistant
          currentPage={activeTab}
          onNavigateToCopilotWorkspace={() => {
            setSelectedIdeaId(null);
            setActiveTab('executive_copilot');
          }}
        />
      )}
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <SystemReadinessProvider>
          <MainApplication />
        </SystemReadinessProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
};

export default App;
