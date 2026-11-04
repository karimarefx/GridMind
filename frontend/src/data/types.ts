export type View =
  | "Overview"
  | "Forecasting"
  | "Event diagnosis"
  | "Scenario laboratory"
  | "Evaluation & provenance";
export type Target = "demand" | "solar" | "wind" | "net_load";
export const targets: Target[] = ["demand", "solar", "wind", "net_load"];
export const labels: Record<Target, string> = {
  demand: "Demand",
  solar: "Solar",
  wind: "Wind",
  net_load: "Net load",
};
export interface Forecast {
  forecast_id: string;
  issued_at_utc: string;
  target_time_utc: string;
  horizon_hours: number;
  region_id: string;
  history_start_utc: string;
  history_end_utc: string;
  history_rows: number;
  split: string;
  demand_mw: number;
  solar_mw: number;
  wind_mw: number;
  net_load_mw: number;
  model_version: string;
  data_quality_status: string;
  capacity_policy: string;
}
export interface Observation {
  time: string;
  total_load: number;
  solar_generation: number;
  wind_generation: number;
  net_load: number;
  solar_installed: number;
  wind_installed: number;
}
export interface Baseline {
  forecast_id: string;
  target_time_utc: string;
  target: Target;
  method: string;
  value_mw: number;
}
export interface Metric {
  target: Target;
  split: string;
  group: string;
  method: string;
  mae_mw: number;
  rmse_mw: number;
  r2: number | null;
  n: number;
  mae_skill_vs_persistence: number | null;
}
export interface Scenario {
  id: string;
  title: string;
  description: string;
  forecast_start: number;
  forecast_end: number;
  laboratory_id: string;
}
export interface Catalog {
  schema_version: string;
  bundle_id: string;
  default_scenario: string;
  scenarios: Scenario[];
}
export interface Manifest {
  schema_version: string;
  bundle_id: string;
  model_version: string;
  source_sha256: string;
  origin: string;
  exported_at_utc: string;
  limitations: string[];
  files: { path: string; sha256: string }[];
}
export interface Run {
  splits: Record<
    string,
    { n: number; first_target: string; last_target: string }
  >;
  sample_rows: number;
  eligible_examples: number;
  warmup_rows: number;
  total_seconds: number;
  python: string;
  versions: Record<string, string>;
  models: Record<
    string,
    { training_seconds: number; best_iteration: number; features: number }
  >;
}
export interface Bus {
  id: string;
  label: string;
  x: number;
  y: number;
  type: string;
  in_service: boolean;
}
export interface Line {
  id: string;
  label: string;
  source: string;
  target: string;
  type: string;
  in_service: boolean;
}
export interface Network {
  id: string;
  review_status: string;
  buses: Bus[];
  lines: Line[];
  resources: { id: string; bus_id: string; type: string }[];
}
export interface Round {
  round: number;
  affected: string[];
  severity: string;
  dns_fraction: number;
}
export interface Combination {
  contingency_id: string;
  stress: string;
  rounds: Round[];
  baseline_loading_pct: number;
  baseline_voltage_pu: number;
}
export interface Action {
  id: string;
  title: string;
  changes: { component_id: string; delta_mw: number }[];
  loading_delta_pct: number;
  voltage_delta_pu: number;
  outcome: string;
}
export interface Lab {
  id: string;
  review_status: string;
  assumptions: string[];
  defaults: { contingency_id: string; stress: string; mask: string };
  traces: { step: number; reference: number }[];
  missingness_presets: { id: string; title: string; steps: number[] }[];
  combinations: Combination[];
  actions: Action[];
}
export interface Episode {
  episode_id: string;
  parent_family_id: string;
  split: string;
  ground_truth_class: string;
  input_origin: string;
  trace_path: string;
  observation_window: { start: string; end: string };
  time_basis: string;
  sample_interval: number;
  channel_definitions: {
    channel_id: string;
    source_component_id: string;
    quantity: string;
    unit: string;
  }[];
  limitations: string[];
}
export interface Diagnosis {
  prediction_id: string;
  episode_id: string;
  predicted_category: string | null;
  status: string;
  raw_score: number | null;
  score_class: string;
  decision_threshold: number | null;
  model_version: string;
  diagnosed_at_utc: string;
  reason: string | null;
  physical_location: null;
}
export interface DiagnosisEvaluation {
  status: string;
  reason?: string;
  metrics?: Record<string, number>;
  confusion_matrix?: number[][];
  class_order?: string[];
  counts?: Record<string, number>;
}
export interface Bundle {
  catalog: Catalog;
  manifest: Manifest;
  forecasts: Forecast[];
  observations: Observation[];
  baselines: Baseline[];
  metrics: Metric[];
  run: Run | null;
  network: Network | null;
  lab: Lab | null;
  episodes: Episode[];
  diagnoses: Diagnosis[];
  diagnosisEvaluation: DiagnosisEvaluation;
  errors: Record<string, string>;
}
