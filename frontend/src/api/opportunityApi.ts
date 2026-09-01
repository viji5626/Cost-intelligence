import { apiClient } from './client';
import { OpportunityEvaluation } from '../types';

export const opportunityApi = {
  evaluateOpportunity: async (
    ideaId: string,
    options?: {
      target_calendar_year?: number;
      tooling_investment_inr?: number;
      validation_investment_inr?: number;
      target_model_ids?: string[];
    }
  ): Promise<OpportunityEvaluation> => {
    return apiClient<OpportunityEvaluation>(`/opportunity/evaluate-idea/${ideaId}`, {
      method: 'POST',
      body: JSON.stringify(options || {}),
    });
  },

  getIdeaOpportunity: async (ideaId: string): Promise<OpportunityEvaluation> => {
    return apiClient<OpportunityEvaluation>(`/opportunity/idea/${ideaId}`);
  },

  /**
   * What-if simulation (no DB write).
   * Field names MUST match OpportunitySimulateRequest on the backend:
   *   current_piece_cost    (not current_cost)
   *   proposed_piece_cost   (not proposed_cost)
   *   volumes_by_model      { model_code: annual_volume }
   *   applicable_models     string[]
   */
  simulate: async (data: {
    current_piece_cost: number;
    proposed_piece_cost: number;
    volumes_by_model: Record<string, number>;
    applicable_models: string[];
    tooling_investment?: number;
    validation_investment?: number;
    effective_calendar_year?: number;
  }): Promise<{
    saving_per_vehicle_inr: number;
    gross_annual_opportunity_inr: number;
    net_opportunity_inr: number;
    payback_period_months: number | null;
    payback_period_years: number | null;
    provenance_hash: string;
  }> => {
    return apiClient('/opportunity/simulate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

