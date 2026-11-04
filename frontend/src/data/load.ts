import type { Bundle, Forecast, Catalog } from "./types";

export function validateForecasts(value: unknown): Forecast[] {
  if (!Array.isArray(value) || !value.length)
    throw new Error("No forecast records supplied.");
  const ids = new Set<string>();
  for (const r of value) {
    if (!r || typeof r.forecast_id !== "string" || ids.has(r.forecast_id))
      throw new Error("Missing or duplicate forecast ID.");
    ids.add(r.forecast_id);
    for (const key of ["demand_mw", "solar_mw", "wind_mw", "net_load_mw"])
      if (typeof r[key] !== "number" || !Number.isFinite(r[key]))
        throw new Error(`Invalid ${key}.`);
    const issue = Date.parse(r.issued_at_utc),
      target = Date.parse(r.target_time_utc);
    if (
      !Number.isFinite(issue) ||
      !Number.isFinite(target) ||
      target - issue !== 3600000 ||
      r.horizon_hours !== 1
    )
      throw new Error("Forecast is not exactly one hour ahead.");
    if (
      r.split !== "test" ||
      r.history_rows < 168 ||
      Date.parse(r.history_end_utc) > issue
    )
      throw new Error("Invalid replay split or historical context.");
    if (
      Math.abs(r.net_load_mw - r.demand_mw + r.solar_mw + r.wind_mw) > 0.00001
    )
      throw new Error("Net-load arithmetic mismatch.");
    if (!r.model_version || !r.capacity_policy || !r.data_quality_status)
      throw new Error("Prediction metadata missing.");
  }
  return value;
}
export function validateCatalog(value: unknown): Catalog {
  const c = value as Catalog;
  if (
    c?.schema_version !== "1" ||
    !c.bundle_id ||
    !Array.isArray(c.scenarios) ||
    !c.scenarios.length ||
    !c.scenarios.some((s) => s.id === c.default_scenario)
  )
    throw new Error("Unsupported or empty scenario catalog.");
  for (const s of c.scenarios)
    if (
      !s.id ||
      !s.title ||
      !Number.isInteger(s.forecast_start) ||
      !Number.isInteger(s.forecast_end) ||
      s.forecast_start < 0 ||
      s.forecast_end < s.forecast_start
    )
      throw new Error("Invalid scenario bounds.");
  return c;
}
export function validateEpisodes(value: unknown): boolean {
  if (!Array.isArray(value)) return false;
  return value.every(
    (r) =>
      r &&
      typeof r.episode_id === "string" &&
      r.parent_family_id &&
      r.trace_path &&
      r.split === "test" &&
      ["physical", "sensor", "unsupported"].includes(r.ground_truth_class) &&
      typeof r.input_origin === "string" &&
      r.observation_window?.start &&
      r.observation_window?.end &&
      typeof r.time_basis === "string" &&
      r.sample_count > 0 &&
      Number.isFinite(r.sample_interval) &&
      r.sample_interval > 0 &&
      Array.isArray(r.channel_definitions) &&
      r.channel_definitions.length > 0 &&
      r.channel_definitions.every(
        (c: any) =>
          c.channel_id && c.source_component_id && c.unit && c.quantity,
      ),
  );
}
export function validateDiagnoses(value: unknown): boolean {
  if (!Array.isArray(value)) return false;
  return value.every(
    (r) =>
      r &&
      r.prediction_id &&
      r.episode_id &&
      r.status &&
      r.physical_location === null &&
      (r.predicted_category === null ||
        ["sensor", "physical", "uncertain"].includes(r.predicted_category)) &&
      (r.raw_score === null ||
        (Number.isFinite(r.raw_score) &&
          r.raw_score >= 0 &&
          r.raw_score <= 1)) &&
      (r.decision_threshold === null ||
        (Number.isFinite(r.decision_threshold) &&
          r.decision_threshold >= 0 &&
          r.decision_threshold <= 1)) &&
      (r.predicted_category === null ||
        (r.model_version && r.class_mapping && r.score_class)),
  );
}
export function assetUrl(path: string) {
  return `${import.meta.env.BASE_URL}data/${path}`;
}
const cache = new Map<string, unknown>();
async function get(path: string) {
  if (cache.has(path)) return cache.get(path);
  const response = await fetch(assetUrl(path));
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  const data: unknown = await response.json();
  cache.set(path, data);
  return data;
}
export async function loadBundle(): Promise<Bundle> {
  const catalog = validateCatalog(await get("catalog.json"));
  const manifest = (await get("bundle_manifest.json")) as Bundle["manifest"];
  if (
    manifest?.schema_version !== "1" ||
    manifest.bundle_id !== catalog.bundle_id
  )
    throw new Error("Catalog and manifest bundle/version mismatch.");
  const errors: Record<string, string> = {};
  async function optional<T>(
    path: string,
    fallback: T,
    validate: (v: any) => boolean = () => true,
  ): Promise<T> {
    try {
      const data = await get(path);
      if (!validate(data)) throw new Error("Invalid schema or references.");
      return data as T;
    } catch (e) {
      errors[path] = e instanceof Error ? e.message : "Load failed";
      return fallback;
    }
  }
  const forecasts = await optional<Forecast[]>(
    "forecasting/forecast_predictions.json",
    [],
    (v) => {
      validateForecasts(v);
      return true;
    },
  );
  const [
    observations,
    baselines,
    metrics,
    run,
    network,
    lab,
    episodes,
    diagnoses,
    diagnosisEvaluation,
  ] = await Promise.all([
    optional<Bundle["observations"]>(
      "forecasting/forecast_observations.json",
      [],
      (v) =>
        Array.isArray(v) &&
        v.every(
          (r) =>
            Number.isFinite(Date.parse(r.time)) &&
            [
              "total_load",
              "solar_generation",
              "wind_generation",
              "net_load",
            ].every((k) => Number.isFinite(r[k])),
        ),
    ),
    optional<Bundle["baselines"]>(
      "forecasting/forecast_baselines.json",
      [],
      (v) =>
        Array.isArray(v) &&
        v.every(
          (r) =>
            Number.isFinite(r.value_mw) &&
            forecasts.some(
              (f) =>
                f.forecast_id === r.forecast_id &&
                f.target_time_utc === r.target_time_utc,
            ),
        ),
    ),
    optional<Bundle["metrics"]>(
      "evaluation/forecast_metrics.json",
      [],
      (v) =>
        Array.isArray(v) &&
        v.every(
          (r) =>
            Number.isFinite(r.mae_mw) &&
            Number.isFinite(r.rmse_mw) &&
            Number.isFinite(r.n),
        ),
    ),
    optional<Bundle["run"]>(
      "evaluation/run_manifest.json",
      null,
      (v) => v && v.splits && Number.isFinite(v.total_seconds),
    ),
    optional<Bundle["network"]>(
      "scenarios/network.json",
      null,
      (v) =>
        v?.buses?.length === 14 &&
        Array.isArray(v.lines) &&
        v.lines.every(
          (l: any) =>
            v.buses.some((b: any) => b.id === l.source) &&
            v.buses.some((b: any) => b.id === l.target),
        ),
    ),
    optional<Bundle["lab"]>(
      "scenarios/laboratory.json",
      null,
      (v) =>
        Array.isArray(v?.combinations) &&
        Array.isArray(v?.traces) &&
        Array.isArray(v?.actions) &&
        v.defaults,
    ),
    optional<Bundle["episodes"]>(
      "diagnosis/event_episodes.json",
      [],
      validateEpisodes,
    ),
    optional<Bundle["diagnoses"]>(
      "diagnosis/diagnosis_predictions.json",
      [],
      validateDiagnoses,
    ),
    optional<Bundle["diagnosisEvaluation"]>(
      "diagnosis/diagnosis_evaluation.json",
      {
        status: "unavailable",
        reason: "Diagnosis evaluation file unavailable.",
      },
      (v) => v?.status,
    ),
  ]);
  if (forecasts.some((f) => f.model_version !== manifest.model_version)) {
    errors.forecasting =
      "Forecast model version differs from the bundle manifest.";
    forecasts.length = 0;
  }
  if (
    forecasts.length &&
    catalog.scenarios.some((s) => s.forecast_end >= forecasts.length)
  )
    throw new Error(
      "Scenario refers to a forecast record outside the packaged window.",
    );
  if (
    network &&
    lab &&
    (network.id !== lab.id ||
      catalog.scenarios.some((s) => s.laboratory_id !== lab.id))
  ) {
    errors.laboratory = "Scenario/network fixture version mismatch.";
    return {
      catalog,
      manifest,
      forecasts,
      observations,
      baselines,
      metrics,
      run,
      network: null,
      lab: null,
      episodes,
      diagnoses,
      diagnosisEvaluation,
      errors,
    };
  }
  return {
    catalog,
    manifest,
    forecasts,
    observations,
    baselines,
    metrics,
    run,
    network,
    lab,
    episodes,
    diagnoses,
    diagnosisEvaluation,
    errors,
  };
}
export async function loadTrace(path: string) {
  const data = await get(path);
  if (
    !Array.isArray(data) ||
    !data.every(
      (r) =>
        r && (Number.isFinite(r.elapsed_seconds) || typeof r.time === "string"),
    )
  )
    throw new Error("Trace needs time or elapsed_seconds for every row.");
  return data as Record<string, string | number | null>[];
}
export function clearCache() {
  cache.clear();
}
