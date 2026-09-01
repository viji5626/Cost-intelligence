import { apiClient } from './client';
import { ReviewCaseDetail, ReviewPriority, ReviewRecord, ReviewStatus } from '../types';

export interface ReviewQueueParams {
  priority?: ReviewPriority;
  status?: ReviewStatus;
  safety_only?: boolean;
}

export const governanceApi = {
  getReviewQueue: async (params: ReviewQueueParams = {}): Promise<ReviewRecord[]> => {
    const searchParams = new URLSearchParams();
    if (params.priority) searchParams.append('priority', params.priority);
    if (params.status) searchParams.append('status', params.status);
    if (params.safety_only) searchParams.append('safety_only', 'true');
    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return apiClient<ReviewRecord[]>(`/governance/queue${query}`);
  },

  syncIdeaReview: async (ideaId: string): Promise<ReviewRecord> => {
    return apiClient<ReviewRecord>(`/governance/sync/${ideaId}`, {
      method: 'POST',
    });
  },

  assignReviewer: async (ideaId: string, reviewerId: string): Promise<ReviewRecord> => {
    return apiClient<ReviewRecord>(`/governance/assign/${ideaId}`, {
      method: 'POST',
      body: JSON.stringify({ reviewer_id: reviewerId }),
    });
  },

  performAction: async (
    ideaId: string,
    action: {
      action_type: string;
      comments?: string;
      override_rationale?: string;
      target_decision_state?: string;
    }
  ): Promise<ReviewRecord> => {
    return apiClient<ReviewRecord>(`/governance/action/${ideaId}`, {
      method: 'POST',
      body: JSON.stringify(action),
    });
  },

  getReviewCaseDetail: async (ideaId: string): Promise<ReviewCaseDetail> => {
    return apiClient<ReviewCaseDetail>(`/governance/review-case/${ideaId}`);
  },
};
