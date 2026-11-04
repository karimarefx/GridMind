import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  Layers3,
  Wind,
  Sun,
  Activity,
} from "lucide-react";
import { useDashboard } from "../state/context";
import { Badge, fmt, Panel } from "../components/Common";
import { Network } from "../components/Network";
import type { View } from "../data/types";
export function Overview() {
  const { data, state, dispatch } = useDashboard();
  const f = data.forecasts[state.forecastIndex];
  const diagnosisReady = data.episodes.some((e) =>
    data.diagnoses.some(
      (p) => p.episode_id === e.episode_id && p.status === "complete",
    ),
  );
  const readyCount = Number(!!f) + Number(diagnosisReady);
  const scenario = data.catalog.scenarios.find(
    (s) => s.id === state.scenarioId,
  )!;
  const cards = [
    {
      title: "Forecasting",
      status: f ? "Replay available" : "Unavailable",
      text: "Demand, solar & wind · +1 hour",
      view: "Forecasting",
      kind: "prediction",
      icon: Activity,
    },
    {
      title: "Event diagnosis",
      status: diagnosisReady ? "Exports available" : "Data readiness blocked",
      text: "Stage 1 · sensor vs physical",
      view: "Event diagnosis",
      kind: diagnosisReady ? "prediction" : "unavailable",
      icon: Clock3,
    },
    {
      title: "Telemetry reconstruction",
      status: "Interactive illustration",
      text: "Separate missingness & equipment status",
      view: "Scenario laboratory",
      kind: "simulated",
      icon: Layers3,
    },
    {
      title: "Cascade assessment",
      status: "Scripted propagation",
      text: "Conditional on a hypothetical outage",
      view: "Scenario laboratory",
      kind: "simulated",
      icon: Wind,
    },
    {
      title: "Corrective actions",
      status: "Scripted comparison",
      text: "No change, redispatch & curtailment",
      view: "Scenario laboratory",
      kind: "simulated",
      icon: Sun,
    },
  ];
  return (
    <>
      <div className="summary-strip">
        <div>
          <span className="eyebrow">Research proof of concept</span>
          <h2>Five capabilities. Transparent evidence.</h2>
          <p>
            Explore genuine forecasting results alongside clearly separated grid
            illustrations.
          </p>
        </div>
        <div className="summary-count">
          <b>02</b>
          <span>
            trained capabilities targeted
            <br />
            <strong>
              {readyCount.toString().padStart(2, "0")} available ·{" "}
              {(2 - readyCount).toString().padStart(2, "0")} blocked
            </strong>
          </span>
        </div>
      </div>
      <div className="capabilities">
        {cards.map((c) => (
          <button
            className={`capability ${c.kind}`}
            key={c.title}
            onClick={() => {
              dispatch({ type: "view", view: c.view as View });
              if (c.title === "Cascade assessment")
                dispatch({ type: "patch", patch: { labTab: "Cascade" } });
              if (c.title === "Corrective actions")
                dispatch({
                  type: "patch",
                  patch: { labTab: "Corrective actions" },
                });
            }}
          >
            <div className="cap-icon">
              <c.icon size={20} />
              <ArrowRight size={16} />
            </div>
            <h3>{c.title}</h3>
            <p>{c.text}</p>
            <span className="cap-status">
              {c.kind === "unavailable" ? (
                <Clock3 size={12} />
              ) : (
                <CheckCircle2 size={12} />
              )}{" "}
              {c.status}
            </span>
            <Badge kind={c.kind}>
              {c.kind === "unavailable" ? "Unavailable" : undefined}
            </Badge>
          </button>
        ))}
      </div>
      <div className="overview-grid">
        <Panel
          title="Network workspace"
          eyebrow="Topology illustration"
          extra={<span className="subtle-tag">ILLUSTRATIVE / 14 BUS</span>}
        >
          <Network />
        </Panel>
        <div className="side-stack">
          <Panel title="Active replay" eyebrow="Scenario brief">
            <span className="scenario-tag">
              SCENARIO / {state.scenarioId.toUpperCase()}
            </span>
            <h3>{scenario.title}</h3>
            <p className="muted">{scenario.description}</p>
            <dl className="brief-list">
              <div>
                <dt>Forecast source</dt>
                <dd>ERCOT aggregate</dd>
              </div>
              <div>
                <dt>Event source</dt>
                <dd>{diagnosisReady ? "Exported episodes" : "Not supplied"}</dd>
              </div>
              <div>
                <dt>Network source</dt>
                <dd>Authored illustration</dd>
              </div>
              <div>
                <dt>Forecast horizon</dt>
                <dd>1 hour</dd>
              </div>
            </dl>
            <button
              className="primary full"
              onClick={() => dispatch({ type: "view", view: "Forecasting" })}
            >
              Explore forecast replay <ArrowRight size={15} />
            </button>
          </Panel>
          <Panel title="Current forecast" eyebrow="Precomputed / MW">
            <div className="quick-value">
              <span>Demand</span>
              <b>{fmt(f?.demand_mw)}</b>
            </div>
            <div className="quick-value">
              <span>Solar</span>
              <b>{fmt(f?.solar_mw)}</b>
            </div>
            <div className="quick-value">
              <span>Wind</span>
              <b>{fmt(f?.wind_mw)}</b>
            </div>
            <Badge />
            <p className="caption">
              Source-domain values are not mapped onto the illustrative network.
            </p>
          </Panel>
        </div>
      </div>
      <div className="scope-note">
        <CheckCircle2 size={18} />
        <p>
          <strong>Evidence first.</strong> No live telemetry, equipment control,
          event localization, or physical validation. Illustrative fixtures
          await model-owner review.
        </p>
        <button
          className="text-button"
          onClick={() =>
            dispatch({ type: "view", view: "Evaluation & provenance" })
          }
        >
          Inspect provenance <ArrowRight size={14} />
        </button>
      </div>
    </>
  );
}
