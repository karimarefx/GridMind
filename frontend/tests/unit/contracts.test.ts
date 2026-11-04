import { describe, it, expect } from "vitest";
import {
  validateForecasts,
  validateCatalog,
  validateEpisodes,
  validateDiagnoses,
} from "../../src/data/load";
import forecasts from "../../public/data/forecasting/forecast_predictions.json";
import observations from "../../public/data/forecasting/forecast_observations.json";
import baselines from "../../public/data/forecasting/forecast_baselines.json";
import metrics from "../../public/data/evaluation/forecast_metrics.json";
import catalog from "../../public/data/catalog.json";
import manifest from "../../public/data/bundle_manifest.json";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { initialState, reducer } from "../../src/state/reducer";
import { reconstruct } from "../../src/simulations/reconstruction";
describe("Genuine export integrity", () => {
  it("matches every packaged asset to the bundle's checksum manifest", () => {
    for (const file of manifest.files) {
      const contents = readFileSync(new URL(`../../public/data/${file.path}`, import.meta.url));
      expect(createHash("sha256").update(contents).digest("hex")).toBe(file.sha256);
    }
  });
  it("contains one continuous test week with 168-hour context and one-hour targets", () => {
    expect(validateForecasts(forecasts)).toHaveLength(168);
    expect(observations).toHaveLength(336);
    expect(validateCatalog(catalog).bundle_id).toBe(manifest.bundle_id);
    for (let i = 0; i < forecasts.length; i++) {
      const f = forecasts[i];
      expect(observations.some((o) => o.time === f.target_time_utc)).toBe(true);
      expect(
        observations.filter(
          (o) => o.time >= f.history_start_utc && o.time <= f.history_end_utc,
        ),
      ).toHaveLength(168);
      if (i)
        expect(
          Date.parse(f.target_time_utc) -
            Date.parse(forecasts[i - 1].target_time_utc),
        ).toBe(3600000);
    }
    for (const b of baselines)
      expect(
        forecasts.some(
          (f) =>
            f.forecast_id === b.forecast_id &&
            f.target_time_utc === b.target_time_utc,
        ),
      ).toBe(true);
    expect(
      metrics
        .filter(
          (m) =>
            m.split === "test" && m.group === "all" && m.method === "xgboost",
        )
        .every((m) => m.n === 1738),
    ).toBe(true);
  });
  it.each([
    { horizon_hours: 2 },
    { demand_mw: NaN },
    { net_load_mw: 0 },
    { split: "train" },
    { history_rows: 24 },
    { target_time_utc: forecasts[0].issued_at_utc },
  ])("rejects unsupported prediction %j", (patch) =>
    expect(() => validateForecasts([{ ...forecasts[0], ...patch }])).toThrow(),
  );
  it("rejects duplicate record IDs", () =>
    expect(() => validateForecasts([forecasts[0], forecasts[0]])).toThrow());
});
describe("Diagnosis readiness gates", () => {
  it("rejects missing units and family identities rather than making up a trace", () =>
    expect(
      validateEpisodes([
        {
          episode_id: "test",
          split: "test",
          channel_definitions: [{ channel_id: "voltage" }],
        },
      ]),
    ).toBe(false));
  it("rejects fabricated location and invalid raw scores", () => {
    expect(
      validateDiagnoses([
        {
          prediction_id: "test",
          episode_id: "test",
          status: "complete",
          physical_location: "bus:01",
          raw_score: 4,
        },
      ]),
    ).toBe(false);
  });
});
describe("Scenario state isolation", () => {
  it("changing hour hides revealed actuals", () => {
    const s = reducer(
      { ...initialState, revealed: true },
      { type: "step", index: 5 },
    );
    expect(s.forecastIndex).toBe(5);
    expect(s.revealed).toBe(false);
  });
  it("changing scenario resets all results and uses the scenario bounds", () => {
    const s = reducer(
      {
        ...initialState,
        playing: true,
        revealed: true,
        round: 2,
        actionId: "redispatch",
        componentId: "bus",
      },
      { type: "scenario", scenario: catalog.scenarios[1] },
    );
    expect(s.forecastIndex).toBe(24);
    expect(s.round).toBe(0);
    expect(s.actionId).toBe(null);
    expect(s.playing).toBe(false);
    expect(s.componentId).toBe(null);
  });
  it("outage changes clear action and propagation while leaving forecasts intact", () => {
    const s = reducer(
      { ...initialState, round: 2, actionId: "redispatch" },
      { type: "contingency", id: "line" },
    );
    expect(s.round).toBe(0);
    expect(s.actionId).toBe(null);
    expect(s.forecastIndex).toBe(0);
  });
});
describe("Illustrative reconstruction safeguards", () => {
  const trace = [
    { step: 0, reference: 1 },
    { step: 1, reference: 1.1 },
    { step: 2, reference: 1.2 },
  ];
  it("preserves reference, missingness and unmasked readings", () => {
    const result = reconstruct(trace, [1], "in_service");
    expect(result[1].observed).toBe(null);
    expect(result[1].reference).toBe(1.1);
    expect(result[1].reconstructed).toBeCloseTo(1.1);
    expect(result[0].observed).toBe(1);
    expect(trace[1].reference).toBe(1.1);
  });
  it.each(["out_of_service", "unknown"] as const)(
    "does not reconstruct %s equipment",
    (status) =>
      expect(reconstruct(trace, [1], status)[1].reconstructed).toBe(null),
  );
});
