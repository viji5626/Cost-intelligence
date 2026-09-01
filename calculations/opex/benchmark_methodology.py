"""
Benchmark Methodology Domain Engine
Implements 4 distinct benchmark modes with configurable multi-factor comparability scoring.
Never defines 'best' as simply lowest absolute OPEX; evaluates comparability rigorously.
Includes multi-utility benchmarking (Electricity, Water, Compressed Air, Gas/Fuel).
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
import uuid

from calculations.opex.engine import OpexCalculationEngine
from calculations.opex.models import (
    BenchmarkMode,
    BenchmarkOpportunityResult,
    ComparabilityWeights,
    PlantComparabilityScore,
    PlantKpiMetrics,
)


class BenchmarkMethodology:
    """Domain service for multi-factor plant benchmarking and opportunity quantification."""

    @staticmethod
    def _round(value: Decimal, places: int = 4) -> Decimal:
        return value.quantize(Decimal("10") ** -places, rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_comparability_score(
        cls,
        target_scope: str,
        target_volume: int,
        target_shifts: int,
        target_capacity: int,
        target_tariff: Optional[Decimal],
        peer_scope: str,
        peer_volume: int,
        peer_shifts: int,
        peer_capacity: int,
        peer_tariff: Optional[Decimal],
        peer_total_opex_per_veh: Decimal,
        candidate_plant_id: str,
        candidate_plant_code: str,
        candidate_plant_name: str,
        weights: Optional[ComparabilityWeights] = None,
    ) -> PlantComparabilityScore:
        """
        Calculates multi-factor comparability score (0.0 to 1.0) between target plant and candidate peer.
        Uses configurable weights.
        """
        w = weights or ComparabilityWeights()

        # 1. Manufacturing Scope Similarity
        if target_scope.upper() == peer_scope.upper():
            scope_sim = Decimal("1.00")
        elif "FULL" in target_scope.upper() and "ASSEMBLY" in peer_scope.upper():
            scope_sim = Decimal("0.70")
        else:
            scope_sim = Decimal("0.30")

        # 2. Volume Scale Similarity
        max_vol = max(target_volume, peer_volume, 1)
        min_vol = min(target_volume, peer_volume)
        vol_sim = cls._round(Decimal(str(min_vol)) / Decimal(str(max_vol)), 4)

        # 3. Shift & Operational Schedule Similarity
        max_shifts = max(target_shifts, peer_shifts, 1)
        min_shifts = min(target_shifts, peer_shifts)
        shift_sim = cls._round(Decimal(str(min_shifts)) / Decimal(str(max_shifts)), 4)

        # 4. Capacity Utilization Similarity
        target_util = Decimal(str(target_volume)) / Decimal(str(max(target_capacity, 1)))
        peer_util = Decimal(str(peer_volume)) / Decimal(str(max(peer_capacity, 1)))
        util_diff = abs(target_util - peer_util)
        cap_sim = cls._round(max(Decimal("0.0"), Decimal("1.0") - util_diff), 4)

        # 5. Grid Tariff Comparability
        tariff_sim = Decimal("1.00")
        if target_tariff and peer_tariff and max(target_tariff, peer_tariff) > 0:
            diff_tariff = abs(target_tariff - peer_tariff)
            tariff_sim = cls._round(max(Decimal("0.0"), Decimal("1.0") - (diff_tariff / max(target_tariff, peer_tariff))), 4)

        # Weighted Aggregation
        total_index = cls._round(
            (scope_sim * w.scope_weight)
            + (vol_sim * w.volume_weight)
            + (shift_sim * w.shift_weight)
            + (cap_sim * w.capacity_weight)
            + (tariff_sim * w.tariff_weight),
            4,
        )

        return PlantComparabilityScore(
            candidate_plant_id=candidate_plant_id,
            candidate_plant_code=candidate_plant_code,
            candidate_plant_name=candidate_plant_name,
            comparability_index=total_index,
            scope_similarity=scope_sim,
            volume_similarity=vol_sim,
            shift_similarity=shift_sim,
            capacity_similarity=cap_sim,
            tariff_similarity=tariff_sim,
            total_opex_per_vehicle=peer_total_opex_per_veh,
        )

    @classmethod
    def evaluate_benchmark_opportunity(
        cls,
        target_plant_id: str,
        target_plant_name: str,
        target_kpi: PlantKpiMetrics,
        target_scope: str,
        target_capacity: int,
        target_shifts: int,
        target_tariff: Optional[Decimal],
        peer_kpis: List[PlantKpiMetrics],
        peer_metadata_map: Dict[str, Dict[str, Any]],
        mode: BenchmarkMode = BenchmarkMode.BEST_COMPARABLE,
        manual_target_opex_per_veh: Optional[Decimal] = None,
        manual_target_kwh_per_veh: Optional[Decimal] = None,
        manual_target_water_kl_per_veh: Optional[Decimal] = None,
        manual_target_air_cf_per_veh: Optional[Decimal] = None,
        manual_target_gas_cf_per_veh: Optional[Decimal] = None,
        weights: Optional[ComparabilityWeights] = None,
        fixed_overhead_ratio: Optional[Decimal] = None,
    ) -> BenchmarkOpportunityResult:
        """
        Executes full benchmark evaluation across the selected benchmark mode with multi-utility dimensions.
        """
        calc_id = f"calc-{uuid.uuid4().hex[:12]}"
        target_period = target_kpi.period
        target_vol = target_kpi.production_quantity
        target_util = Decimal(str(target_vol)) / Decimal(str(max(target_capacity, 1)))

        benchmark_source_name = ""
        comparability_idx = Decimal("1.00")
        bench_total_opex = Decimal("0.0")
        bench_kwh = Decimal("0.0")
        bench_water_kl = Decimal("0.0")
        bench_gas_cf: Optional[Decimal] = None
        bench_air_cf: Optional[Decimal] = None
        bench_kwh_per_cf: Optional[Decimal] = None
        bench_cf_per_kwh: Optional[Decimal] = None
        bench_air_cost_per_veh: Optional[Decimal] = None
        bench_tariff = target_tariff
        bench_util = target_util
        
        bench_elec_snapshot = None
        bench_water_snapshot = None
        bench_air_snapshot = None
        bench_gas_snapshot = None

        if mode == BenchmarkMode.BEST_COMPARABLE:
            candidates: List[PlantComparabilityScore] = []
            for peer in peer_kpis:
                if peer.plant_id == target_plant_id:
                    continue
                meta = peer_metadata_map.get(peer.plant_id, {})
                score = cls.calculate_comparability_score(
                    target_scope=target_scope,
                    target_volume=target_vol,
                    target_shifts=target_shifts,
                    target_capacity=target_capacity,
                    target_tariff=target_tariff,
                    peer_scope=meta.get("scope", "FULL_VEHICLE_ASSEMBLY"),
                    peer_volume=peer.production_quantity,
                    peer_shifts=meta.get("shifts", 3),
                    peer_capacity=meta.get("capacity", 1000000),
                    peer_tariff=meta.get("tariff", target_tariff),
                    peer_total_opex_per_veh=peer.total_opex_per_vehicle,
                    candidate_plant_id=peer.plant_id,
                    candidate_plant_code=peer.plant_code,
                    candidate_plant_name=peer.plant_name,
                    weights=weights,
                )
                candidates.append(score)

            superior_candidates = [c for c in candidates if c.total_opex_per_vehicle < target_kpi.total_opex_per_vehicle]

            if superior_candidates:
                best_candidate = max(superior_candidates, key=lambda c: c.comparability_index)
                matching_peer = next(p for p in peer_kpis if p.plant_id == best_candidate.candidate_plant_id)
                benchmark_source_name = f"Best Comparable Peer: {matching_peer.plant_name} ({best_candidate.candidate_plant_code})"
                comparability_idx = best_candidate.comparability_index
                bench_total_opex = matching_peer.total_opex_per_vehicle
                bench_kwh = matching_peer.kwh_per_vehicle
                bench_water_kl = matching_peer.water_kl_per_vehicle
                bench_gas_cf = matching_peer.gas_cf_per_vehicle
                bench_air_cf = matching_peer.compressed_air_cf_per_vehicle
                if matching_peer.compressed_air:
                    bench_kwh_per_cf = matching_peer.compressed_air.compressor_kwh_per_cf
                    bench_cf_per_kwh = matching_peer.compressed_air.compressor_cf_per_kwh
                    bench_air_cost_per_veh = matching_peer.compressed_air.compressed_air_cost_per_vehicle_inr
                bench_elec_snapshot = matching_peer.electricity
                bench_water_snapshot = matching_peer.water
                bench_air_snapshot = matching_peer.compressed_air
                bench_gas_snapshot = matching_peer.gas_fuel
                bench_meta = peer_metadata_map.get(matching_peer.plant_id, {})
                bench_tariff = bench_meta.get("tariff", target_tariff)
                bench_util = Decimal(str(matching_peer.production_quantity)) / Decimal(str(max(bench_meta.get("capacity", 1), 1)))
            else:
                benchmark_source_name = f"Target Plant is Efficiency Leader among peers ({target_plant_name})"
                bench_total_opex = target_kpi.total_opex_per_vehicle
                bench_kwh = target_kpi.kwh_per_vehicle
                bench_water_kl = target_kpi.water_kl_per_vehicle
                bench_gas_cf = target_kpi.gas_cf_per_vehicle
                bench_air_cf = target_kpi.compressed_air_cf_per_vehicle
                if target_kpi.compressed_air:
                    bench_kwh_per_cf = target_kpi.compressed_air.compressor_kwh_per_cf
                    bench_cf_per_kwh = target_kpi.compressed_air.compressor_cf_per_kwh
                    bench_air_cost_per_veh = target_kpi.compressed_air.compressed_air_cost_per_vehicle_inr
                bench_elec_snapshot = target_kpi.electricity
                bench_water_snapshot = target_kpi.water
                bench_air_snapshot = target_kpi.compressed_air
                bench_gas_snapshot = target_kpi.gas_fuel

        elif mode == BenchmarkMode.PEER_GROUP:
            valid_peers = [p for p in peer_kpis if p.total_opex_per_vehicle > Decimal("0.0")]
            if valid_peers:
                sorted_peers = sorted(valid_peers, key=lambda p: p.total_opex_per_vehicle)
                top_quartile_count = max(1, len(sorted_peers) // 4 or 1)
                top_peers = sorted_peers[:top_quartile_count]
                bench_total_opex = cls._round(sum(p.total_opex_per_vehicle for p in top_peers) / Decimal(str(len(top_peers))), 4)
                bench_kwh = cls._round(sum(p.kwh_per_vehicle for p in top_peers) / Decimal(str(len(top_peers))), 4)
                bench_water_kl = cls._round(sum(p.water_kl_per_vehicle for p in top_peers) / Decimal(str(len(top_peers))), 4)
                valid_air = [p.compressed_air_cf_per_vehicle for p in top_peers if p.compressed_air_cf_per_vehicle is not None]
                if valid_air:
                    bench_air_cf = cls._round(sum(valid_air) / Decimal(str(len(valid_air))), 4)
                valid_gas = [p.gas_cf_per_vehicle for p in top_peers if p.gas_cf_per_vehicle is not None]
                if valid_gas:
                    bench_gas_cf = cls._round(sum(valid_gas) / Decimal(str(len(valid_gas))), 4)
                benchmark_source_name = f"Peer Group Top-Quartile Benchmark ({len(top_peers)} peers)"
            else:
                bench_total_opex = target_kpi.total_opex_per_vehicle
                benchmark_source_name = "Peer Group (No valid peers)"

        elif mode == BenchmarkMode.HISTORICAL_BASELINE:
            historical_records = [p for p in peer_kpis if p.plant_id == target_plant_id]
            if historical_records:
                best_hist = min(historical_records, key=lambda p: p.total_opex_per_vehicle)
                benchmark_source_name = f"Historical Best: {target_plant_name} ({best_hist.period})"
                bench_total_opex = best_hist.total_opex_per_vehicle
                bench_kwh = best_hist.kwh_per_vehicle
                bench_water_kl = best_hist.water_kl_per_vehicle
                bench_gas_cf = best_hist.gas_cf_per_vehicle
                bench_air_cf = best_hist.compressed_air_cf_per_vehicle
                if best_hist.compressed_air:
                    bench_kwh_per_cf = best_hist.compressed_air.compressor_kwh_per_cf
                    bench_cf_per_kwh = best_hist.compressed_air.compressor_cf_per_kwh
                    bench_air_cost_per_veh = best_hist.compressed_air.compressed_air_cost_per_vehicle_inr
                bench_elec_snapshot = best_hist.electricity
                bench_water_snapshot = best_hist.water
                bench_air_snapshot = best_hist.compressed_air
                bench_gas_snapshot = best_hist.gas_fuel
            else:
                bench_total_opex = target_kpi.total_opex_per_vehicle
                benchmark_source_name = f"Historical Baseline ({target_plant_name})"

        elif mode == BenchmarkMode.MANAGEMENT_TARGET:
            bench_total_opex = manual_target_opex_per_veh or Decimal("1200.00")
            bench_kwh = manual_target_kwh_per_veh or Decimal("20.00")
            bench_water_kl = manual_target_water_kl_per_veh or Decimal("0.20")
            bench_air_cf = manual_target_air_cf_per_veh or Decimal("3.00")
            bench_gas_cf = manual_target_gas_cf_per_veh or Decimal("1.20")
            benchmark_source_name = "Corporate Strategic Management Target"

        # 2. Decompose Variance
        overhead_ratio = fixed_overhead_ratio or Decimal("0.30")
        variance = OpexCalculationEngine.decompose_variance(
            actual_total_opex_per_veh=target_kpi.total_opex_per_vehicle,
            benchmark_total_opex_per_veh=bench_total_opex,
            actual_grid_tariff=target_tariff,
            benchmark_grid_tariff=bench_tariff,
            benchmark_kwh_per_veh=bench_kwh,
            actual_capacity_util=target_util,
            benchmark_capacity_util=bench_util,
            fixed_overhead_ratio=overhead_ratio,
        )

        # 3. Calculate Annualized Financial Opportunity
        annual_vol = target_vol * 12
        opp_inr, opp_cr = OpexCalculationEngine.calculate_annual_opportunity(
            addressable_gap_per_vehicle=variance.addressable_gap_per_vehicle,
            annual_production_volume=annual_vol,
        )

        # 4. Generate Cryptographic Provenance Hash
        provenance_inputs = {
            "target_plant_id": target_plant_id,
            "target_period": target_period,
            "actual_total_opex_per_veh": str(target_kpi.total_opex_per_vehicle),
            "benchmark_mode": mode.value,
            "benchmark_total_opex_per_veh": str(bench_total_opex),
            "annual_production_volume": str(annual_vol),
        }
        provenance_outputs = {
            "addressable_gap_per_veh": str(variance.addressable_gap_per_vehicle),
            "gross_annual_opportunity_inr": str(opp_inr),
            "gross_annual_opportunity_crores": str(opp_cr),
        }
        ts, calc_hash = OpexCalculationEngine.generate_calculation_provenance(calc_id, provenance_inputs, provenance_outputs)

        return BenchmarkOpportunityResult(
            target_plant_id=target_plant_id,
            target_plant_name=target_plant_name,
            target_period=target_period,
            target_actual_kpi=target_kpi,
            benchmark_mode=mode,
            benchmark_source_name=benchmark_source_name,
            benchmark_comparability_index=comparability_idx,
            benchmark_kwh_per_vehicle=bench_kwh,
            benchmark_water_kl_per_vehicle=bench_water_kl,
            benchmark_gas_cf_per_vehicle=bench_gas_cf,
            benchmark_total_opex_per_vehicle=bench_total_opex,
            benchmark_compressed_air_cf_per_vehicle=bench_air_cf,
            benchmark_compressor_kwh_per_cf=bench_kwh_per_cf,
            benchmark_compressor_cf_per_kwh=bench_cf_per_kwh,
            benchmark_compressed_air_cost_per_vehicle=bench_air_cost_per_veh,
            benchmark_electricity=bench_elec_snapshot,
            benchmark_water=bench_water_snapshot,
            benchmark_compressed_air=bench_air_snapshot,
            benchmark_gas_fuel=bench_gas_snapshot,
            variance=variance,
            annual_production_volume=annual_vol,
            gross_annual_opportunity_inr=opp_inr,
            gross_annual_opportunity_crores=opp_cr,
            calculation_id=calc_id,
            calculation_timestamp=ts,
            calculation_hash=calc_hash,
            provenance_details={
                "inputs": provenance_inputs,
                "outputs": provenance_outputs,
                "weights_used": w.model_dump() if weights else ComparabilityWeights().model_dump(),
            },
        )
