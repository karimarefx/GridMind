import { useState } from "react";
import { useDashboard } from "../state/context";
import { assetUrl } from "../data/load";
import { Badge, fmt, Notice, Panel, utc } from "../components/Common";
import { Stage1Evaluation } from "./Stage1Evaluation";
export function Evaluation() {
  const { data } = useDashboard();
  const [split, setSplit] = useState("test");
  const [group, setGroup] = useState("all");
  const [target, setTarget] = useState("all");
  const run = data.run;
  const rows = data.metrics.filter(
    (m) =>
      m.split === split &&
      m.group === group &&
      (target === "all" || m.target === target),
  );
  return (
    <>
      <div className="section-bar">
        <div>
          <span className="eyebrow">Frozen research evidence</span>
          <h2>Performance with context.</h2>
        </div>
        <Badge kind="calculated">Calculated · held-out evaluation</Badge>
      </div>
      <div className="toolbar">
        <label>
          Partition{" "}
          <select value={split} onChange={(e) => setSplit(e.target.value)}>
            <option value="test">Test</option>
            <option value="validation">Validation</option>
          </select>
        </label>
        <label>
          Subset{" "}
          <select value={group} onChange={(e) => setGroup(e.target.value)}>
            {[...new Set(data.metrics.map((m) => m.group))].map((g) => (
              <option key={g}>{g}</option>
            ))}
          </select>
        </label>
        <label>
          Target{" "}
          <select value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="all">All targets</option>
            {["demand", "solar", "wind", "net_load"].map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
      </div>
      <Panel
        title="Forecast error & baseline comparison"
        extra={
          <a
            className="text-button"
            href={assetUrl("evaluation/metrics.csv")}
            download
          >
            Download source metrics CSV ↗
          </a>
        }
      >
        <p className="caption">
          Metrics cover the complete selected held-out partition/subset, not
          just the replay window. Skill = 1 − model MAE / persistence MAE; it is
          not percentage accuracy.
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Target</th>
                <th>Method</th>
                <th>MAE · MW</th>
                <th>RMSE · MW</th>
                <th>R²</th>
                <th>MAE skill</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((m, i) => (
                <tr
                  key={i}
                  className={m.method === "xgboost" ? "highlight-row" : ""}
                >
                  <th>{m.target}</th>
                  <td>
                    {m.method === "xgboost" ? (
                      <span className="method">XGBoost</span>
                    ) : (
                      m.method
                    )}
                  </td>
                  <td>{fmt(m.mae_mw, 2)}</td>
                  <td>{fmt(m.rmse_mw, 2)}</td>
                  <td>{fmt(m.r2, 3)}</td>
                  <td>
                    {m.mae_skill_vs_persistence == null
                      ? "Unavailable"
                      : fmt(m.mae_skill_vs_persistence * 100, 1) + "%"}
                  </td>
                  <td>{fmt(m.n)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && (
            <Notice title="No reported subset">
              No metrics were exported for this selection. Missing coverage is
              not a successful result.
            </Notice>
          )}
        </div>
      </Panel>
      <div className="chart-grid">
        <Panel
          title="Chronological forecasting split"
          eyebrow="Sampled 2023–2024 experiment"
        >
          {run ? (
            <>
              <div className="split-bar">
                <span style={{ flex: 8 }}>TRAIN · 80%</span>
                <span style={{ flex: 1 }}>VAL</span>
                <span style={{ flex: 1 }}>TEST</span>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Split</th>
                      <th>Count</th>
                      <th>First / last target · UTC</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(run.splits).map(([key, s]) => (
                      <tr key={key}>
                        <th>{key}</th>
                        <td>{fmt(s.n)}</td>
                        <td>
                          {utc(s.first_target)}
                          <br />
                          {utc(s.last_target)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="caption">
                {fmt(run.sample_rows)} sampled rows · {run.warmup_rows} warmup
                hours · {fmt(run.eligible_examples)} targets. Short held-out
                periods do not establish full-season generalization.
              </p>
            </>
          ) : (
            <Notice>Split manifest unavailable.</Notice>
          )}
        </Panel>
        <Stage1Evaluation />
        <Panel title="Cause classifier replay evaluation" eyebrow="Grouped development">
          {data.diagnosisEvaluation.status === "unavailable" ? (
            <Notice title="Saved cause-replay evaluation unavailable">
              {data.diagnosisEvaluation.reason} No confusion matrix or family
              counts are invented.
            </Notice>
          ) : (
            <>
              <dl className="brief-list">
                {Object.entries(data.diagnosisEvaluation.metrics ?? {}).map(
                  ([k, v]) => (
                    <div key={k}>
                      <dt>{k}</dt>
                      <dd>{fmt(v, 3)}</dd>
                    </div>
                  ),
                )}
                {Object.entries(data.diagnosisEvaluation.counts ?? {}).map(
                  ([k, v]) => (
                    <div key={k}>
                      <dt>{k}</dt>
                      <dd>{fmt(v)}</dd>
                    </div>
                  ),
                )}
              </dl>
              <div className="table-scroll">
                <table>
                  <caption>
                    Forced cause choices before abstention · rows actual, columns predicted ·{" "}
                    {(data.diagnosisEvaluation.class_order ?? []).join(", ")}
                  </caption>
                  <tbody>
                    {data.diagnosisEvaluation.confusion_matrix?.map((r, i) => (
                      <tr key={i}>
                        {r.map((v, j) => (
                          <td key={j}>{v}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Panel>
      </div>
      <Panel title="Run provenance" eyebrow="Source of truth">
        <div className="details-grid">
          <div>
            <span>Origin</span>
            <strong>{data.manifest.origin}</strong>
          </div>
          <div>
            <span>Model bundle</span>
            <strong>{data.manifest.model_version}</strong>
          </div>
          <div>
            <span>Measured training pipeline</span>
            <strong>
              {run ? fmt(run.total_seconds, 2) + " seconds" : "Unavailable"}
            </strong>
          </div>
          <div>
            <span>Exported</span>
            <strong>{utc(data.manifest.exported_at_utc)}</strong>
          </div>
        </div>
        <p className="hash">Source SHA256: {data.manifest.source_sha256}</p>
        <p className="caption">
          Runtime excludes environment setup. Browser replay latency is not
          model inference latency.
        </p>
        {run && (
          <p className="small">
            Python {run.python} ·{" "}
            {Object.entries(run.versions)
              .map(([k, v]) => `${k} ${v}`)
              .join(" · ")}
          </p>
        )}
        <div className="file-links">
          <a href={assetUrl("bundle_manifest.json")} download>
            Bundle manifest ↗
          </a>
          <a href={assetUrl("evaluation/run_manifest.json")} download>
            Run & ordered feature manifest ↗
          </a>
          <a href={assetUrl("evaluation/split_manifest.csv")} download>
            Split assignments ↗
          </a>
        </div>
      </Panel>
      <Panel title="Limitations & exclusions">
        <ul className="limitations">
          {data.manifest.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
        <p className="caption">
          No prediction intervals or calibrated confidence were supplied.
          Simulations are not scored as trained capabilities. Paper-reported
          results are not GridMind results.
        </p>
      </Panel>
    </>
  );
}
