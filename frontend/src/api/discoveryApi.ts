import { apiClient } from './client';
import { IdeaEvidenceEvaluation } from '../types';

export const discoveryApi = {
  evaluateIdeaEvidence: async (ideaId: string): Promise<IdeaEvidenceEvaluation> => {
    return apiClient<IdeaEvidenceEvaluation>(`/discovery/evaluate-idea/${ideaId}`, {
      method: 'POST',
    });
  },

  getCrossModelSummary: async (partId: string): Promise<any> => {
    return apiClient(`/discovery/cross-model-summary/${partId}`);
  },
};
