import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  CartesianGrid,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useDashboard } from "../state/context";
import { loadTrace } from "../data/load";
import { Badge, fmt, Notice, Panel } from "../components/Common";
export function Diagnosis() {
  const { data, state, dispatch } = useDashboard();
  const [filter, setFilter] = useState("all");
  const [id, setId] = useState(data.episodes[0]?.episode_id ?? "");
  const [channels, setChannels] = useState<string[]>([]);
  const [trace, setTrace] = useState<Record<string, string | number | null>[]>(
    [],
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPolicy, setShowPolicy] = useState(false);
  const episode = data.episodes.find((e) => e.episode_id === id);
  const prediction = data.diagnoses.find((p) => p.episode_id === id);
  useEffect(() => {
    let current = true;
    setTrace([]);
    setError("");
    setChannels(episode?.channel_definitions.map((c) => c.channel_id) ?? []);
    dispatch({
      type: "patch",
      patch: { eventIndex: 0, eventCount: 0, playing: false },
    });
    if (episode) {
      setLoading(true);
      loadTrace(episode.trace_path)
        .then((t) => {
          if (current) {
            setTrace(t);
            dispatch({ type: "patch", patch: { eventCount: t.length } });
          }
        })
        .catch((e) => {
          if (current) setError(String(e));
        })
        .finally(() => {
          if (current) setLoading(false);
        });
    }
    return () => {
      current = false;
    };
  }, [episode, dispatch]);
  return (
    <>
      <div className="section-bar">
        <div>
          <span className="eyebrow">XGBoost / stage 1</span>
          <h2>Sensor problem or physical event?</h2>
        </div>
        <Badge kind={prediction ? "prediction" : "unavailable"}>
          {prediction
            ? "Precomputed model predictions"
            : "Unavailable · dataset gate"}
        </Badge>
      </div>
      <Notice title="Physical location unavailable — stage 2 excluded">
        This capability classifies complete abnormal windows. It does not detect
        normal operation, locate faulty sensors, or identify an initiating grid
        outage.
      </Notice>
      <div className="toolbar">
        <button onClick={() => setShowPolicy(!showPolicy)}>
          {showPolicy ? "Hide" : "Show"} insufficient-input example
        </button>
      </div>
      {showPolicy && (
        <Notice title="Unavailable — insufficient observation window">
          Policy demonstration: an empty or incomplete observation window is
          rejected. No classifier inference or raw score is produced. This is
          input validation, not a third trained event class.
        </Notice>
      )}
      {!data.episodes.length ? (
        <>
          <Panel
            title="Diagnosis is not ready for integration"
            eyebrow="Readiness blocker"
          >
            <div className="empty-illustration">⌁</div>
            <h3 className="center">No genuine diagnosis exports supplied</h3>
            <p className="center muted">{data.diagnosisEvaluation.reason}</p>
            <div className="readiness-grid">
              {[
                "Defensible physical/sensor labels",
                "Channels, units & sampling cadence",
                "Independent parent-family splits",
                "Trained classifier & held-out predictions",
                "Raw score, class mapping & threshold",
                "Evaluation & confusion matrix",
              ].map((s) => (
                <div key={s}>
                  <span className="pending-dot" />
                  {s}
                  <strong>Required</strong>
                </div>
              ))}
            </div>
            <p className="caption">
              No electrical traces, confidence scores, or classification results
              have been invented. Controlled sensor corruptions require
              compatible clean source episodes and documented recipes.
            </p>
          </Panel>
          <Panel title="Colab handoff">
            <p>
              Supply event_episodes.json, referenced original trace files,
              diagnosis_predictions.json, diagnosis_evaluation.json, and
              group/feature manifests. See the frontend README for the trace
              contract.
            </p>
          </Panel>
        </>
      ) : (
        <>
          <div className="toolbar">
            <label>
              Example class{" "}
              <select
                value={filter}
                onChange={(e) => {
                  setFilter(e.target.value);
                  setId(
                    data.episodes.find(
                      (x) =>
                        e.target.value === "all" ||
                        x.ground_truth_class === e.target.value,
                    )?.episode_id ?? "",
                  );
                }}
              >
                <option value="all">All examples</option>
                <option value="physical">Physical</option>
                <option value="sensor">Sensor</option>
                <option value="unsupported">Unsupported input</option>
              </select>
            </label>
            <label>
              Episode{" "}
              <select value={id} onChange={(e) => setId(e.target.value)}>
                {data.episodes
                  .filter(
                    (e) => filter === "all" || e.ground_truth_class === filter,
                  )
                  .map((e) => (
                    <option key={e.episode_id}>{e.episode_id}</option>
                  ))}
              </select>
            </label>
          </div>
          {!episode ? (
            <Notice title="No matching episodes">
              Change the example filter.
            </Notice>
          ) : (
            <>
              <Panel
                title={episode.episode_id}
                extra={
                  <Badge kind="observed">
                    Dataset input · {episode.input_origin}
                  </Badge>
                }
              >
                <p>
                  Window: {episode.observation_window.start} →{" "}
                  {episode.observation_window.end} · {episode.time_basis}
                </p>
                <p className="caption">
                  Classification uses the complete exported abnormal window.
                  Inspecting trace samples does not rerun classification.
                </p>
                <div className="chips">
                  {episode.channel_definitions.map((c) => (
                    <button
                      key={c.channel_id}
                      className={
                        channels.includes(c.channel_id) ? "chip active" : "chip"
                      }
                      aria-pressed={channels.includes(c.channel_id)}
                      onClick={() =>
                        setChannels(
                          channels.includes(c.channel_id)
                            ? channels.filter((x) => x !== c.channel_id)
                            : [...channels, c.channel_id],
                        )
                      }
                    >
                      {c.channel_id} · {c.unit}
                    </button>
                  ))}
                </div>
                {loading ? (
                  <p role="status">Loading original trace…</p>
                ) : error ? (
                  <Notice>{error}</Notice>
                ) : (
                  [
                    ...new Set(
                      episode.channel_definitions
                        .filter((c) => channels.includes(c.channel_id))
                        .map((c) => c.unit),
                    ),
                  ].map((unit) => (
                    <div className="chart" key={unit}>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trace}>
                          <CartesianGrid vertical={false} />
                          <XAxis
                            dataKey={
                              episode.time_basis === "elapsed_seconds"
                                ? "elapsed_seconds"
                                : "time"
                            }
                          />
                          <YAxis label={{ value: unit, angle: -90 }} />
                          <Tooltip />
                          <ReferenceLine
                            x={
                              trace[state.eventIndex]?.[
                                episode.time_basis === "elapsed_seconds"
                                  ? "elapsed_seconds"
                                  : "time"
                              ] ?? undefined
                            }
                            stroke="#a47c37"
                            strokeDasharray="3 3"
                          />
                          {episode.channel_definitions
                            .filter(
                              (c) =>
                                c.unit === unit &&
                                channels.includes(c.channel_id),
                            )
                            .map((c, i) => (
                              <Line
                                key={c.channel_id}
                                dataKey={c.channel_id}
                                name={`Dataset input · ${c.channel_id} · ${unit}`}
                                stroke={
                                  ["#168f84", "#3581be", "#b58938"][i % 3]
                                }
                                dot={false}
                                isAnimationActive={false}
                              />
                            ))}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  ))
                )}
              </Panel>
              <Panel title="Stage-1 result">
                {prediction ? (
                  <>
                    <Badge />
                    <h3>
                      {prediction.predicted_category ??
                        "Uncertain / unavailable"}
                    </h3>
                    <p>
                      Uncalibrated raw score: {fmt(prediction.raw_score, 4)} ·
                      score class: {prediction.score_class} · validation
                      threshold: {fmt(prediction.decision_threshold, 4)}
                    </p>
                    <p>
                      Ground truth: {episode.ground_truth_class} · Result:{" "}
                      {prediction.predicted_category ===
                      episode.ground_truth_class
                        ? "Correct for this example"
                        : "Mismatch / unavailable"}
                    </p>
                    <p>
                      Computed at: {prediction.diagnosed_at_utc} · Model:{" "}
                      {prediction.model_version}
                    </p>
                    {prediction.reason && <Notice>{prediction.reason}</Notice>}
                  </>
                ) : (
                  <Notice>No prediction matches this episode.</Notice>
                )}
              </Panel>
              <Panel title="Original measurement table">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Channel</th>
                        <th>Source component</th>
                        <th>Unit</th>
                        <th>Selected original value</th>
                        <th>Quality / provenance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {episode.channel_definitions
                        .filter((c) => channels.includes(c.channel_id))
                        .map((c) => (
                          <tr key={c.channel_id}>
                            <td>{c.channel_id}</td>
                            <td>{c.source_component_id}</td>
                            <td>{c.unit}</td>
                            <td>
                              {String(
                                trace[state.eventIndex]?.[c.channel_id] ??
                                  "Unavailable",
                              )}
                            </td>
                            <td>Dataset input · {episode.input_origin}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            </>
          )}
        </>
      )}
    </>
  );
}
