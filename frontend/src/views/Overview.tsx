import {
  Activity,
  ArrowRight,
  GitBranch,
  Layers3,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  Wind,
  Zap,
} from "lucide-react";
import { Badge, fmt, Panel } from "../components/Common";
import { Network } from "../components/Network";
import type { View } from "../data/types";
import { useDashboard } from "../state/context";

import { useStage1Health } from "./DiagnosisUpload";

export function Overview() {
  const { health, checking } = useStage1Health();
  const { data, state, dispatch } = useDashboard();
  const forecast = data.forecasts[state.forecastIndex];
  const scenario = data.catalog.scenarios.find((item) => item.id === state.scenarioId)!;
  const modules: {
    title: string;
    description: string;
    status: string;
    kind: string;
    view: View;
    tab?: string;
    icon: typeof Activity;
  }[] = [
    {
      title: "Forecasting",
      description: "One-hour-ahead demand, solar and wind forecasts",
      status: forecast ? "Replay available" : "Unavailable",
      kind: forecast ? "prediction" : "unavailable",
      view: "Forecasting",
      icon: Activity,
    },
    {
      title: "Event diagnosis",
      description: "Check an uploaded measurement window for a physical disturbance or sensor error",
      status: checking ? "Checking service" : health.ready ? "CSV analysis available" : "Local service unavailable",
      kind: health.ready ? "prediction" : "unavailable",
      view: "Event diagnosis",
      icon: ShieldCheck,
    },
    {
      title: "Telemetry reconstruction",
      description: "Recover missing measurements under different equipment states",
      status: "Interactive simulation",
      kind: "simulated",
      view: "Scenario laboratory",
      tab: "Reconstruction",
      icon: Layers3,
    },
    {
      title: "Cascade assessment",
      description: "Trace propagation after a hypothetical line outage",
      status: "Scripted simulation",
      kind: "simulated",
      view: "Scenario laboratory",
      tab: "Cascade",
      icon: GitBranch,
    },
    {
      title: "Corrective actions",
      description: "Compare redispatch, curtailment and no action",
      status: "Scripted simulation",
      kind: "simulated",
      view: "Scenario laboratory",
      tab: "Corrective actions",
      icon: SlidersHorizontal,
    },
  ];
  const readings = [
    { label: "Demand", value: forecast?.demand_mw, icon: Zap },
    { label: "Solar", value: forecast?.solar_mw, icon: Sun },
    { label: "Wind", value: forecast?.wind_mw, icon: Wind },
  ];

  return (
    <div className="overview">
      <div className="overview-grid">
        <Panel className="topology-panel" title="Grid topology">
          <Network />
        </Panel>
        <Panel
          className="forecast-readout"
          title="Current forecast"
          extra={<Badge kind={forecast ? "prediction" : "unavailable"}>{forecast ? "+1 hour" : "Unavailable"}</Badge>}
        >
          <p className="readout-source">ERCOT aggregate predictions</p>
          <dl className="readout-list">
            {readings.map(({ label, value, icon: Icon }) => (
              <div key={label}>
                <dt><Icon size={16} aria-hidden="true" /> {label}</dt>
                <dd>
                  <span className={value == null ? "missing-value" : undefined}>{fmt(value)}</span>
                  {value != null && <small> MW</small>}
                </dd>
              </div>
            ))}
          </dl>
          <button
            className="primary full"
            onClick={() => dispatch({ type: "view", view: "Forecasting" })}
          >
            Explore forecast replay <ArrowRight size={16} />
          </button>
          <div className="scenario-brief">
            <h3>{scenario.title}</h3>
            <p>{scenario.description}</p>
          </div>
        </Panel>
      </div>

      <section className="module-directory" aria-labelledby="module-heading">
        <div className="directory-heading">
          <h2 id="module-heading">Research modules</h2>
          <button
            className="text-button"
            onClick={() => dispatch({ type: "view", view: "Evaluation & provenance" })}
          >
            Inspect provenance <ArrowRight size={15} />
          </button>
        </div>
        <ul className="module-list">
          {modules.map(({ title, description, status, kind, view, tab, icon: Icon }) => (
            <li key={title}>
              <button
                className="module-link"
                onClick={() => {
                  dispatch({ type: "view", view });
                  if (tab) dispatch({ type: "patch", patch: { labTab: tab } });
                }}
              >
                <span className="module-icon"><Icon size={18} aria-hidden="true" /></span>
                <span className="module-name">{title}</span>
                <span className="module-description">{description}</span>
                <Badge kind={kind}>{status}</Badge>
                <ArrowRight className="module-arrow" size={16} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
