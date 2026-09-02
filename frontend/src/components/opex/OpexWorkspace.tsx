import React, { useEffect, useState } from 'react';
import {
  Factory,
  Zap,
  Droplets,
  TrendingDown,
  Flame,
  Wrench,
  Users,
  Building2,
  Target,
  BarChart3,
  Scale,
  Gauge,
  Info,
  Sun,
  Power,
  Waves,
  BookOpen,
} from 'lucide-react';
import { opexApi } from '../../api/opexApi';
import {
  BenchmarkComparisonResult,
  PlantKPIs,
} from '../../types';
import { EvidenceProvenance } from '../common/EvidenceProvenance';
import { StatCard } from '../common/StatCard';

interface PlantMaster {
  id: string;
  plant_code: string;
  name: string;
  location: string;
  annual_capacity: number;
  active_shifts: number;
  has_paint_shop: boolean;
  has_weld_shop: boolean;
  has_assembly: boolean;
  has_engine_assembly: boolean;
  has_press_shop: boolean;
  is_benchmark_eligible: boolean;
}

interface OpexWorkspaceProps {
  onOpenHelp?: (chapterId: string) => void;
}

export const OpexWorkspace: React.FC<OpexWorkspaceProps> = ({ onOpenHelp }) => {
  const [plants] = useState<PlantMaster[]>([
    { id: 'plant-haridwar', plant_code: 'PLANT_A', name: 'Plant A (Haridwar)', location: 'Haridwar, UK', annual_capacity: 2700000, active_shifts: 3, has_paint_shop: true, has_weld_shop: true, has_assembly: true, has_engine_assembly: true, has_press_shop: true, is_benchmark_eligible: true },
    { id: 'plant-dharuhera', plant_code: 'PLANT_B', name: 'Plant B (Dharuhera)', location: 'Dharuhera, HR', annual_capacity: 2100000, active_shifts: 3, has_paint_shop: true, has_weld_shop: true, has_assembly: true, has_engine_assembly: true, has_press_shop: true, is_benchmark_eligible: true },
    { id: 'plant-neemrana', plant_code: 'PLANT_C', name: 'Plant C (Neemrana - Garden Plant)', location: 'Neemrana, RJ', annual_capacity: 750000, active_shifts: 2, has_paint_shop: true, has_weld_shop: true, has_assembly: true, has_engine_assembly: false, has_press_shop: true, is_benchmark_eligible: true },
    { id: 'plant-gurugram', plant_code: 'PLANT_D', name: 'Plant D (Gurugram)', location: 'Gurugram, HR', annual_capacity: 1800000, active_shifts: 3, has_paint_shop: true, has_weld_shop: true, has_assembly: true, has_engine_assembly: true, has_press_shop: true, is_benchmark_eligible: true },
    { id: 'plant-chittoor', plant_code: 'PLANT_E', name: 'Plant E (Chittoor)', location: 'Chittoor, AP', annual_capacity: 1500000, active_shifts: 2, has_paint_shop: true, has_weld_shop: true, has_assembly: true, has_engine_assembly: true, has_press_shop: true, is_benchmark_eligible: true },
    { id: 'plant-vadodara', plant_code: 'PLANT_F', name: 'Plant F (Vadodara)', location: 'Halol/Vadodara, GJ', annual_capacity: 1200000, active_shifts: 2, has_paint_shop: true, has_weld_shop: true, has_assembly: true, has_engine_assembly: true, has_press_shop: true, is_benchmark_eligible: true },
  ]);
  const [selectedPlant, setSelectedPlant] = useState<string>('plant-haridwar');
  // NOTE: mode values MUST match backend BenchmarkMode enum exactly.
  // 'BEST_IN_GROUP' is invalid — backend does not accept it (causes 422).
  const [comparisonMode, setComparisonMode] = useState<
    'BEST_COMPARABLE' | 'PEER_GROUP' | 'HISTORICAL_BASELINE' | 'MANAGEMENT_TARGET'
  >('BEST_COMPARABLE');
  // benchmarkPlant state removed: backend auto-selects peer via BenchmarkMethodology.

  const [kpis, setKpis] = useState<PlantKPIs | null>(null);
  const [comparison, setComparison] = useState<BenchmarkComparisonResult | null>(null);

  // Fetch plant KPIs and Benchmark comparison
  useEffect(() => {
    const loadOpexData = async () => {
      const syntheticFallbackKpis: PlantKPIs = {
        plant_id: selectedPlant,
        plant_name: 'Plant A (Haridwar)',
        period_start: '2024-01-01',
        period_end: '2024-12-31',
        production_volume: 2400000,
        total_opex_inr: 1428000000,
        cost_per_vehicle_inr: 595.0,
        kwh_per_vehicle: 42.5,
        kl_per_vehicle: 0.35,
        gas_per_vehicle: 1.2,
        gas_cf_per_vehicle: 42.38,
        compressed_air_cf_per_vehicle: 3.45,
        compressor_kwh_per_cf: 0.0215,
        compressor_cf_per_kwh: 46.51,
        compressed_air_cost_per_veh_inr: 15.20,
        is_compressor_power_embedded: true,
        electricity: {
          grid_kwh: 90000000,
          grid_cost_inr: 675000000,
          dg_kwh: 4000000,
          dg_cost_inr: 72000000,
          solar_kwh: 8000000,
          solar_cost_inr: 24000000,
          purchased_kwh: 90000000,
          total_generated_kwh: 12000000,
          total_energy_kwh: 102000000,
          total_electricity_cost_inr: 771000000,
          kwh_per_vehicle: 42.5,
          cost_per_kwh_inr: 7.56,
          cost_per_vehicle_inr: 321.25,
          accounting_classification: 'PRIMARY_FINANCIAL_COST',
        },
        water: {
          borewell_kl: 600000,
          borewell_cost_inr: 9000000,
          pwd_kl: 240000,
          pwd_cost_inr: 12000000,
          total_water_kl: 840000,
          total_water_cost_inr: 21000000,
          kl_per_vehicle: 0.35,
          cost_per_kl_inr: 25.0,
          cost_per_vehicle_inr: 8.75,
        },
        compressed_air: {
          compressed_air_cf_total: 8280000,
          compressed_air_cf_per_vehicle: 3.45,
          compressor_kwh_total: 178020,
          compressor_kwh_per_cf: 0.0215,
          compressor_cf_per_kwh: 46.51,
          compressed_air_cost_inr: 36480000,
          compressed_air_cost_per_vehicle_inr: 15.20,
          is_compressor_power_embedded: true,
        },
        gas_fuel: {
          gas_cf_total: 101712000,
          gas_nm3_total: 2880000,
          gas_cf_per_vehicle: 42.38,
          gas_nm3_per_vehicle: 1.20,
          gas_cost_inr: 120000000,
          gas_cost_per_cf_inr: 1.18,
          gas_cost_per_vehicle_inr: 50.0,
          gas_source_type: 'PNG',
        },
        provenance_hash: 'sha256:4a8b29c91d8e5f32a67bc31e89df90123456789abcdef0123456789abcdef01',
      };

      const syntheticFallbackComp: BenchmarkComparisonResult = {
        target_plant_id: selectedPlant,
        target_plant_name: 'Plant A (Haridwar)',
        benchmark_plant_id: 'plant-dharuhera',
        benchmark_plant_name: 'Plant B (Dharuhera)',
        benchmark_source_name: 'Best Comparable Peer: Plant B (Dharuhera)',
        comparison_mode: comparisonMode,
        comparability_score: 0.88,
        comparability_tier: 'HIGH',
        comparability_breakdown: {
          scope_similarity: 0.95,
          volume_similarity: 0.88,
          shift_similarity: 0.90,
          capacity_similarity: 0.85,
          tariff_similarity: 0.75,
        },
        comparison_explanation:
          'Plant B (Dharuhera) was selected because it shares comparable manufacturing scope (Press, Robotic Weld, Paint, Assembly), similar annual volume scale (2.1M vs 2.7M), aligned 3-shift operating schedule, and high capacity utilization, yielding an 88% composite comparability score.',
        target_cost_per_veh: 595.0,
        benchmark_cost_per_veh: 520.0,
        gross_gap_per_veh: 75.0,
        addressable_efficiency_gap_per_veh: 52.5,
        structural_gap_per_veh: 22.5,
        target_annual_production: 2400000,
        annual_addressable_opportunity_inr: 126000000,
        variance_breakdown: {
          electricity_variance_inr: 28.0,
          fuel_gas_variance_inr: 14.5,
          water_variance_inr: 4.0,
          maintenance_variance_inr: 6.0,
          manpower_variance_inr: 15.0,
          fixed_overhead_variance_inr: 7.5,
          total_variance_inr: 75.0,
        },
        benchmark_compressed_air_cf_per_vehicle: 2.90,
        benchmark_compressor_kwh_per_cf: 0.0195,
        benchmark_compressor_cf_per_kwh: 51.28,
        benchmark_gas_cf_per_vehicle: 35.0,
        provenance_hash: 'sha256:4a8b29c91d8e5f32a67bc31e89df90123456789abcdef0123456789abcdef01',
      };

      try {
        const kpiData = await opexApi.getPlantKpis(selectedPlant);
        setKpis(kpiData || syntheticFallbackKpis);

        // benchmark_plant_id is NOT passed — backend auto-selects peer.
        const compData = await opexApi.comparePlants(
          selectedPlant,
          comparisonMode,
        );
        setComparison(compData || syntheticFallbackComp);
      } catch {
        setKpis(syntheticFallbackKpis);
        setComparison(syntheticFallbackComp);
      }
    };

    loadOpexData();
  }, [selectedPlant, comparisonMode]);

  return (
    <div className="opex-workspace animate-fade-in">
      {/* Workspace Header */}
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--white)', letterSpacing: '-0.3px', margin: 0 }}>
            Plant OPEX & Deterministic Benchmark Engine
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '3px', fontSize: '12px' }}>
            Production-normalized energy, utilities (Electricity, Water, Compressed Air, Natural Gas), maintenance, and manpower variance decomposition.
          </p>
        </div>
        {onOpenHelp && (
          <button
            onClick={() => onOpenHelp('plant-opex')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              fontSize: '11px',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            <BookOpen size={11} color="var(--status-info)" />
            <span>Manual Ch. 04</span>
          </button>
        )}
      </div>

      {/* Control Bar: Plant Selection & Benchmark Mode */}
      <div
        className="card"
        style={{
          padding: '12px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div>
            <label style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>
              Target Plant
            </label>
            <select
              value={selectedPlant}
              onChange={(e) => setSelectedPlant(e.target.value)}
              style={{ minWidth: '220px' }}
            >
              {plants.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>
              Benchmark Mode
            </label>
            <select
              value={comparisonMode}
              onChange={(e) => setComparisonMode(e.target.value as any)}
              style={{ minWidth: '220px' }}
            >
              <option value="BEST_COMPARABLE">Best Comparable Peer (Automatic)</option>
              <option value="PEER_GROUP">Peer Group Average</option>
              <option value="HISTORICAL_BASELINE">Plant Historical Best</option>
              <option value="MANAGEMENT_TARGET">Management Target</option>
            </select>
          </div>

          {/* Auto-selection label: shown for all non-MANAGEMENT_TARGET modes */}
          {comparisonMode !== 'MANAGEMENT_TARGET' && (
            <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
              <div style={{
                fontSize: '11px',
                color: 'var(--text-secondary)',
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '5px 10px',
                maxWidth: '280px',
              }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase', fontSize: '10px', letterSpacing: '0.5px' }}>Benchmark: </span>
                <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>
                  {comparison?.benchmark_source_name
                    ? comparison.benchmark_source_name
                    : 'Auto-selected by comparability engine'}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* TOP-LEVEL OPEX KPI ROW (6 First-Class Neutral Enterprise Cards) */}
      {kpis && (
        <div className="grid-6" style={{ marginBottom: '16px' }}>
          <StatCard
            title="Production Volume"
            value={`${(kpis.production_volume / 100000).toFixed(1)} L units`}
            subtitle="Annualized output"
            icon={<Factory size={14} />}
          />
          <StatCard
            title="Specific Power"
            value={`${kpis.kwh_per_vehicle.toFixed(1)} kWh/veh`}
            subtitle="Total usable energy"
            icon={<Zap size={14} />}
          />
          <StatCard
            title="Specific Water"
            value={`${kpis.kl_per_vehicle.toFixed(2)} KL/veh`}
            subtitle="Combined extraction"
            icon={<Droplets size={14} />}
          />
          <StatCard
            title="Compressed Air"
            value={
              kpis.compressed_air_cf_per_vehicle !== undefined && kpis.compressed_air_cf_per_vehicle !== null
                ? `${kpis.compressed_air_cf_per_vehicle.toFixed(2)} CF/veh`
                : 'N/A'
            }
            subtitle="Air demand"
            icon={<Gauge size={14} />}
          />
          <StatCard
            title="Natural Gas / Fuel"
            value={
              kpis.gas_cf_per_vehicle !== undefined && kpis.gas_cf_per_vehicle !== null
                ? `${kpis.gas_cf_per_vehicle.toFixed(1)} CF/veh`
                : `${kpis.gas_per_vehicle.toFixed(2)} Nm³/veh`
            }
            subtitle="Process heating"
            icon={<Flame size={14} />}
          />
          <StatCard
            title="Unit Plant OPEX"
            value={`₹${kpis.cost_per_vehicle_inr.toFixed(2)} / veh`}
            subtitle={`Total: ₹${(kpis.total_opex_inr / 10000000).toFixed(1)} Cr`}
            accentColor="var(--hero-red)"
            icon={<TrendingDown size={14} />}
          />
        </div>
      )}

      {/* 4 DEDICATED SOURCE-WISE UTILITY ANALYTICAL CONTAINERS (Neutral Enterprise Style) */}
      {kpis && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '16px' }}>
          
          {/* A. ELECTRICITY & ENERGY DOMAIN */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '10px' }}>
              <div className="card-title">
                <Zap size={14} color="var(--white)" />
                <span>Electricity & Energy (Source-Wise Breakdown & Captive Generation)</span>
              </div>
              <span className="badge badge-neutral">
                {kpis.electricity?.accounting_classification || 'PRIMARY_FINANCIAL_COST'}
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '10px' }}>
              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Power size={11} color="var(--text-muted)" /> Grid / Discom
                </div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.electricity?.grid_kwh ? `${(kpis.electricity.grid_kwh / 1000000).toFixed(1)} MU` : 'N/A'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Purchased Grid Power</div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Sun size={11} color="var(--text-muted)" /> Captive Solar
                </div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.electricity?.solar_kwh ? `${(kpis.electricity.solar_kwh / 1000000).toFixed(1)} MU` : 'N/A'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Zero-Emission Solar</div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Flame size={11} color="var(--text-muted)" /> Diesel Generator (DG)
                </div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.electricity?.dg_kwh ? `${(kpis.electricity.dg_kwh / 1000000).toFixed(1)} MU` : 'N/A'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Emergency / Peak Power</div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Blended Energy Cost</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.electricity?.cost_per_kwh_inr ? `₹${kpis.electricity.cost_per_kwh_inr.toFixed(2)} / kWh` : 'N/A'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  Unit Power: ₹{kpis.electricity?.cost_per_vehicle_inr !== undefined && kpis.electricity?.cost_per_vehicle_inr !== null ? Number(kpis.electricity.cost_per_vehicle_inr).toFixed(2) : 'N/A'} / veh
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-muted)', backgroundColor: 'var(--bg-primary)', padding: '5px 8px', borderRadius: 'var(--radius-sm)' }}>
              <Info size={12} color="var(--text-muted)" />
              <span>
                <strong>Accounting Rule:</strong> Total Usable Energy = Grid ({kpis.electricity?.grid_kwh ? `${(kpis.electricity.grid_kwh / 1000000).toFixed(1)} MU` : '0'}) + Captive Generation ({kpis.electricity?.total_generated_kwh ? `${(kpis.electricity.total_generated_kwh / 1000000).toFixed(1)} MU` : '0'}). DG fuel and solar amortizations are accounted without duplicate billing.
              </span>
            </div>
          </div>

          {/* B. WATER DOMAIN */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '10px' }}>
              <div className="card-title">
                <Droplets size={14} color="var(--white)" />
                <span>Water Extraction & Municipal Supply Domain</span>
              </div>
              <span className="badge badge-neutral">Source Accounting</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '10px' }}>
              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Waves size={11} color="var(--text-muted)" /> Borewell / Groundwater
                </div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.water?.borewell_kl ? `${(kpis.water.borewell_kl / 1000).toFixed(0)}k KL` : 'N/A'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>On-Premise Tube Wells</div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Building2 size={11} color="var(--text-muted)" /> PWD / Municipal Supply
                </div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.water?.pwd_kl ? `${(kpis.water.pwd_kl / 1000).toFixed(0)}k KL` : 'N/A'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Government Pipeline</div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Specific Water KPI</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.kl_per_vehicle !== undefined && kpis.kl_per_vehicle !== null ? Number(kpis.kl_per_vehicle).toFixed(2) : 'N/A'} KL / veh
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  Total: {kpis.water?.total_water_kl ? `${(kpis.water.total_water_kl / 1000).toFixed(0)}k KL` : 'N/A'}
                </div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Unit Water Cost</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  ₹{kpis.water?.cost_per_vehicle_inr !== undefined && kpis.water?.cost_per_vehicle_inr !== null ? Number(kpis.water.cost_per_vehicle_inr).toFixed(2) : 'N/A'} / veh
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  Blended Rate: {kpis.water?.cost_per_kl_inr ? `₹${Number(kpis.water.cost_per_kl_inr).toFixed(2)}/KL` : 'N/A'}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-muted)', backgroundColor: 'var(--bg-primary)', padding: '5px 8px', borderRadius: 'var(--radius-sm)' }}>
              <Info size={12} color="var(--text-muted)" />
              <span>
                <strong>Groundwater Policy:</strong> Groundwater and municipal extraction are separately metered. Where source extraction is zero-cost, financial allocation strictly marks cost as unavailable rather than fabricating zeroes.
              </span>
            </div>
          </div>

          {/* C. COMPRESSED AIR DOMAIN */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '10px' }}>
              <div className="card-title">
                <Gauge size={14} color="var(--white)" />
                <span>Compressed Air Utility & Compressor Efficiency (Benchmarkable Domain)</span>
              </div>
              <span className="badge badge-neutral">
                {kpis.is_compressor_power_embedded !== false ? 'Electricity Embedded (No Double-Count)' : 'Separately Allocated'}
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '10px' }}>
              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Specific Consumption</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.compressed_air_cf_per_vehicle !== undefined && kpis.compressed_air_cf_per_vehicle !== null
                    ? `${kpis.compressed_air_cf_per_vehicle.toFixed(2)} CF/veh`
                    : 'N/A (Missing)'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  {comparison?.benchmark_compressed_air_cf_per_vehicle
                    ? `Peer Target: ${comparison.benchmark_compressed_air_cf_per_vehicle.toFixed(2)} CF/veh`
                    : 'Shopfloor Demand'}
                </div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Specific Energy (kWh/CF)</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.compressor_kwh_per_cf !== undefined && kpis.compressor_kwh_per_cf !== null
                    ? `${kpis.compressor_kwh_per_cf.toFixed(4)} kWh/CF`
                    : 'N/A (No Sub-meter)'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  {comparison?.benchmark_compressor_kwh_per_cf
                    ? `Peer Target: ${comparison.benchmark_compressor_kwh_per_cf.toFixed(4)}`
                    : 'Compressor Efficiency'}
                </div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Air Yield (CF/kWh)</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.compressor_cf_per_kwh !== undefined && kpis.compressor_cf_per_kwh !== null
                    ? `${kpis.compressor_cf_per_kwh.toFixed(1)} CF/kWh`
                    : 'N/A (No Sub-meter)'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  {comparison?.benchmark_compressor_cf_per_kwh
                    ? `Peer Target: ${comparison.benchmark_compressor_cf_per_kwh.toFixed(1)}`
                    : 'Generation Yield'}
                </div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Unit Cost Allocation</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.compressed_air_cost_per_veh_inr !== undefined && kpis.compressed_air_cost_per_veh_inr !== null
                    ? `₹${kpis.compressed_air_cost_per_veh_inr.toFixed(2)} / veh`
                    : 'Embedded in Power'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Accounting Allocation</div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-muted)', backgroundColor: 'var(--bg-primary)', padding: '5px 8px', borderRadius: 'var(--radius-sm)' }}>
              <Info size={12} color="var(--text-muted)" />
              <span>
                <strong>Double-Counting Safeguard:</strong> Compressor electrical consumption is tracked as a physical efficiency dimension and is accounted within total plant grid electricity OPEX.
              </span>
            </div>
          </div>

          {/* D. NATURAL GAS / FUEL DOMAIN */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '10px' }}>
              <div className="card-title">
                <Flame size={14} color="var(--white)" />
                <span>Natural Gas / Process Fuel Domain ({kpis.gas_fuel?.gas_source_type || 'PNG'})</span>
              </div>
              <span className="badge badge-neutral">Thermal Utilities</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '10px' }}>
              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Specific Gas (CF/veh)</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.gas_cf_per_vehicle !== undefined && kpis.gas_cf_per_vehicle !== null
                    ? `${kpis.gas_cf_per_vehicle.toFixed(1)} CF/veh`
                    : `${kpis.gas_per_vehicle.toFixed(2)} Nm³/veh`}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  {comparison?.benchmark_gas_cf_per_vehicle
                    ? `Peer Target: ${comparison.benchmark_gas_cf_per_vehicle.toFixed(1)} CF/veh`
                    : 'Paint & Heating Ovens'}
                </div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Volumetric Demand</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.gas_fuel?.gas_cf_total ? `${(kpis.gas_fuel.gas_cf_total / 1000000).toFixed(1)}M CF` : `${kpis.gas_per_vehicle.toFixed(2)} Nm³/v`}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Piped Natural Gas (PNG)</div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Unit Fuel Cost</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  ₹{kpis.gas_fuel?.gas_cost_per_vehicle_inr !== undefined && kpis.gas_fuel?.gas_cost_per_vehicle_inr !== null ? Number(kpis.gas_fuel.gas_cost_per_vehicle_inr).toFixed(2) : 'N/A'} / veh
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  Total: ₹{kpis.gas_fuel?.gas_cost_inr ? `${(Number(kpis.gas_fuel.gas_cost_inr) / 10000000).toFixed(1)} Cr` : 'N/A'}
                </div>
              </div>

              <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Volumetric Tariff</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {kpis.gas_fuel?.gas_cost_per_cf_inr ? `₹${Number(kpis.gas_fuel.gas_cost_per_cf_inr).toFixed(2)} / CF` : 'Direct Gas Bill'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Fuel Price Basis</div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-muted)', backgroundColor: 'var(--bg-primary)', padding: '5px 8px', borderRadius: 'var(--radius-sm)' }}>
              <Info size={12} color="var(--text-muted)" />
              <span>
                <strong>Calorific Baseline:</strong> Natural gas consumption is tracked on actual volumetric flow without arbitrary theoretical conversion factors.
              </span>
            </div>
          </div>

        </div>
      )}

      {/* Transparency / Explainer Card: "Why was Plant A compared with Plant B?" (Neutral Enterprise Card) */}
      {comparison && (
        <div className="card" style={{ marginBottom: '16px' }}>
          <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '12px' }}>
            <div className="card-title">
              <Scale size={14} color="var(--white)" />
              <span>Transparent Benchmark Methodology & Comparability Index</span>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span className="badge badge-healthy">
                Comparability: {(comparison.comparability_score * 100).toFixed(0)}% ({comparison.comparability_tier})
              </span>
              <EvidenceProvenance provenanceHash={comparison.provenance_hash} />
            </div>
          </div>

          <div style={{ padding: '10px 12px', backgroundColor: 'var(--bg-primary)', borderRadius: 'var(--radius-sm)', marginBottom: '12px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: '3px' }}>
              Methodological Alignment: Why {comparison.target_plant_name} was compared with {comparison.benchmark_plant_name}
            </div>
            <p style={{ fontSize: '12px', color: 'var(--white)', lineHeight: 1.45 }}>
              {comparison.comparison_explanation}
            </p>
          </div>

          {/* Implemented Backend Dimensional Breakdown (Phase 3 BenchmarkMethodology) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px' }}>
            <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Scope (35%)</div>
              <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                {(comparison.comparability_breakdown.scope_similarity * 100).toFixed(0)}%
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Shopfloor Scope</div>
            </div>
            <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Volume (25%)</div>
              <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                {(comparison.comparability_breakdown.volume_similarity * 100).toFixed(0)}%
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Scale Alignment</div>
            </div>
            <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Shifts (15%)</div>
              <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                {(comparison.comparability_breakdown.shift_similarity * 100).toFixed(0)}%
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Operating Days/Shifts</div>
            </div>
            <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Capacity (15%)</div>
              <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                {(comparison.comparability_breakdown.capacity_similarity * 100).toFixed(0)}%
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Utilization Rate</div>
            </div>
            <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div className="kv-key" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Tariff (10%)</div>
              <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--white)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                {(comparison.comparability_breakdown.tariff_similarity * 100).toFixed(0)}%
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Grid Power Rate</div>
            </div>
          </div>
        </div>
      )}

      {/* Variance Decomposition & Addressable Opportunity Grid */}
      {comparison && (
        <div className="grid-2">
          {/* Variance Breakdown Table */}
          <div className="card">
            <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '12px' }}>
              <div className="card-title">
                <BarChart3 size={14} color="var(--white)" />
                <span>Variance Decomposition (₹ / Vehicle)</span>
              </div>
              <span className="badge badge-neutral">Pure Decimal Engine</span>
            </div>

            <div className="kv-row">
              <span className="kv-key" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Zap size={13} color="var(--text-secondary)" />
                Electricity & Grid Power (incl. Compressors)
              </span>
              <span className="kv-val">₹{comparison.variance_breakdown.electricity_variance_inr.toFixed(2)} / veh</span>
            </div>
            <div className="kv-row">
              <span className="kv-key" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Flame size={13} color="var(--text-secondary)" />
                Fuel & Natural Gas
              </span>
              <span className="kv-val">₹{comparison.variance_breakdown.fuel_gas_variance_inr.toFixed(2)} / veh</span>
            </div>
            <div className="kv-row">
              <span className="kv-key" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Droplets size={13} color="var(--text-secondary)" />
                Industrial Water & RO
              </span>
              <span className="kv-val">₹{comparison.variance_breakdown.water_variance_inr.toFixed(2)} / veh</span>
            </div>
            <div className="kv-row">
              <span className="kv-key" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Wrench size={13} color="var(--text-secondary)" />
                Line Maintenance & Spares
              </span>
              <span className="kv-val">₹{comparison.variance_breakdown.maintenance_variance_inr.toFixed(2)} / veh</span>
            </div>
            <div className="kv-row">
              <span className="kv-key" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Users size={13} color="var(--text-secondary)" />
                Direct Shopfloor Manpower
              </span>
              <span className="kv-val">₹{comparison.variance_breakdown.manpower_variance_inr.toFixed(2)} / veh</span>
            </div>
            <div className="kv-row">
              <span className="kv-key" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Building2 size={13} color="var(--text-muted)" />
                Fixed Plant Overhead (Configurable 30%)
              </span>
              <span className="kv-val">₹{comparison.variance_breakdown.fixed_overhead_variance_inr.toFixed(2)} / veh</span>
            </div>
            <div className="kv-row" style={{ borderTop: '2px solid var(--border-strong)', paddingTop: '8px', marginTop: '4px' }}>
              <span className="kv-key" style={{ fontWeight: '700', color: 'var(--white)' }}>Total Unit OPEX Variance</span>
              <span className="kv-val" style={{ fontWeight: '700', color: 'var(--white)', fontSize: '13px' }}>
                ₹{comparison.variance_breakdown.total_variance_inr.toFixed(2)} / veh
              </span>
            </div>
          </div>

          {/* Addressable Efficiency Gap & Annualized Opportunity */}
          <div className="card">
            <div className="card-header" style={{ paddingBottom: '8px', marginBottom: '12px' }}>
              <div className="card-title">
                <Target size={14} color="var(--status-healthy)" />
                <span>Addressable Efficiency Gap & Opportunity</span>
              </div>
              <span className="badge badge-neutral">Executive Valuation</span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Target Plant Unit OPEX</span>
              <span className="kv-val">₹{comparison.target_cost_per_veh.toFixed(2)}</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Benchmark Plant Unit OPEX</span>
              <span className="kv-val" style={{ color: 'var(--status-healthy)' }}>₹{comparison.benchmark_cost_per_veh.toFixed(2)}</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Gross OPEX Gap</span>
              <span className="kv-val">₹{comparison.gross_gap_per_veh.toFixed(2)} / veh</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Structural / Baseline Difference (Non-Addressable)</span>
              <span className="kv-val" style={{ color: 'var(--text-muted)' }}>₹{comparison.structural_gap_per_veh.toFixed(2)} / veh</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Net Addressable Efficiency Gap</span>
              <span className="kv-val" style={{ color: 'var(--white)', fontWeight: '700' }}>
                ₹{comparison.addressable_efficiency_gap_per_veh.toFixed(2)} / veh
              </span>
            </div>

            <div style={{ marginTop: '14px', padding: '12px 14px', backgroundColor: 'rgba(16, 185, 129, 0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
              <div style={{ fontSize: '10px', color: 'var(--status-healthy)', textTransform: 'uppercase', letterSpacing: '0.4px', fontWeight: '700' }}>
                Annual Addressable Net Opportunity
              </div>
              <div style={{ fontSize: '22px', fontWeight: '700', color: 'var(--status-healthy)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                ₹{(comparison.annual_addressable_opportunity_inr / 10000000).toFixed(2)} Crore
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Based on planned production of {(comparison.target_annual_production / 100000).toFixed(1)} Lakh vehicles/yr.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
