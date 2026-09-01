import React, { useState } from 'react';
import { AIStudioWorkspace } from './components/aistudio/AIStudioWorkspace';
import { AuditLogWorkspace } from './components/audit/AuditLogWorkspace';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Header } from './components/common/Header';
import { Sidebar } from './components/common/Sidebar';
import { ExecutiveDashboard } from './components/dashboard/ExecutiveDashboard';
import { ReviewQueueWorkspace } from './components/governance/ReviewQueueWorkspace';
import { HardwareMonitor } from './components/hardware/HardwareMonitor';
import { IdeaDetailView } from './components/ideathon/IdeaDetailView';
import { IdeathonWorkspace } from './components/ideathon/IdeathonWorkspace';
import { IngestionWorkspace } from './components/ingestion/IngestionWorkspace';
import { OpexWorkspace } from './components/opex/OpexWorkspace';
import { OpportunityWorkspace } from './components/opportunity/OpportunityWorkspace';
import { HelpManualWorkspace } from './components/help/HelpManualWorkspace';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedIdeaId, setSelectedIdeaId] = useState<string | null>(null);
  const [targetHelpChapterId, setTargetHelpChapterId] = useState<string | undefined>(undefined);

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

  return (
    <ErrorBoundary>
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
          <Header
            activeTab={activeTab}
            onOpenHelp={handleOpenHelp}
          />
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
        </div>
      </div>
    </ErrorBoundary>
  );
};

export default App;
