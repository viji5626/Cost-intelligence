import { apiClient } from './client';
import { BenchmarkComparisonResult, PlantKPIs } from '../types';

/**
 * BenchmarkMode enum values — must exactly match backend BenchmarkMode enum.
 * 'BEST_IN_GROUP' is NOT valid — use 'BEST_COMPARABLE'.
 */
export type BenchmarkMode =
  | 'BEST_COMPARABLE'       // Automatic multi-factor comparability selection (default)
  | 'PEER_GROUP'            // Peer group average
  | 'HISTORICAL_BASELINE'   // Plant's own historical best
  | 'MANAGEMENT_TARGET';    // Management-defined target

export const opexApi = {
  getPlantKpis: async (plantId: string, startDate?: string, endDate?: string): Promise<PlantKPIs> => {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    const query = params.toString() ? `?${params.toString()}` : '';
    return apiClient<PlantKPIs>(`/opex/kpis/${plantId}${query}`);
  },

  /**
   * Runs benchmark gap analysis for a target plant.
   *
   * ARCHITECTURE NOTE: benchmark peer selection is ALWAYS automatic.
   * The backend BenchmarkMethodology engine selects the best comparable peer
   * using multi-factor comparability scoring (scope, volume, shifts, capacity, tariff).
   * benchmark_plant_id is NOT accepted as a request parameter — do not pass it.
   */
  comparePlants: async (
    targetPlantId: string,
    mode: BenchmarkMode = 'BEST_COMPARABLE',
    period?: string,
  ): Promise<BenchmarkComparisonResult> => {
    return apiClient<BenchmarkComparisonResult>('/opex/benchmark/compare', {
      method: 'POST',
      body: JSON.stringify({
        target_plant_id: targetPlantId,
        mode,
        period,
        // benchmark_plant_id is intentionally omitted:
        // backend auto-selects the best peer via BenchmarkMethodology
      }),
    });
  },

  getOpexSummary: async (): Promise<any> => {
    return apiClient('/opex/summary');
  },
};

