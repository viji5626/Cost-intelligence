import { apiClient } from './client';
import { IdeaSubmission } from '../types';

export interface IdeaListParams {
  skip?: number;
  limit?: number;
  decision_state?: string;
  evidence_state?: string;
  vehicle_model?: string;
  subsystem?: string;
  query?: string;
}

export const ideathonApi = {
  listIdeas: async (params: IdeaListParams = {}): Promise<IdeaSubmission[]> => {
    const searchParams = new URLSearchParams();
    if (params.skip !== undefined) searchParams.append('skip', params.skip.toString());
    if (params.limit !== undefined) searchParams.append('limit', params.limit.toString());
    if (params.decision_state) searchParams.append('decision_state', params.decision_state);
    if (params.evidence_state) searchParams.append('evidence_state', params.evidence_state);
    if (params.vehicle_model) searchParams.append('vehicle_model', params.vehicle_model);
    if (params.subsystem) searchParams.append('subsystem', params.subsystem);
    if (params.query) searchParams.append('query', params.query);
    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return apiClient<IdeaSubmission[]>(`/ideathon/ideas${query}`);
  },

  getIdea: async (ideaId: string): Promise<IdeaSubmission> => {
    return apiClient<IdeaSubmission>(`/ideathon/ideas/${ideaId}`);
  },

  submitIdea: async (data: {
    raw_title: string;
    raw_description: string;
    raw_claimed_saving_per_veh?: number;
    target_vehicle_id?: string;
  }): Promise<IdeaSubmission> => {
    return apiClient<IdeaSubmission>('/ideathon/submit', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};
