import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useDashboard } from "../state/context";
import { Badge, fmt, Notice, Panel } from "../components/Common";
import { Network } from "../components/Network";
import { reconstruct } from "../simulations/reconstruction";
export function Laboratory() {
  const { data, state, dispatch } = useDashboard();
  const [equipment, setEquipment] = useState<
    "in_service" | "out_of_service" | "unknown"
  >("in_service");
  const [filter, setFilter] = useState("all");
  const lab = data.lab;
  const mask = lab?.missingness_presets.find((m) => m.id === state.mask);
  const trace = useMemo(
    () => reconstruct(lab?.traces ?? [], mask?.steps ?? [], equipment),
    [lab, mask, equipment],
  );
  if (!lab || !data.network)
    return (
      <Notice>
        Laboratory fixtures unavailable. No electrical simulator is implemented.
      </Notice>
    );
  const combo = lab.combinations.find(
    (c) => c.contingency_id === state.contingency && c.stress === state.stress,
  );
  const action = lab.actions.find((a) => a.id === state.actionId);
  return (
    <>
      <div className="section-bar">
        <div>
          <Badge kind="simulated" />
          <p className="muted small">
            Separate authored scenario · fixtures await model-owner review
          </p>
        </div>
        <div className="tabs" role="tablist" aria-label="Laboratory capability">
          {["Reconstruction", "Cascade", "Corrective actions"].map((tab) => (
            <button
              role="tab"
              aria-selected={state.labTab === tab}
              key={tab}
              className={state.labTab === tab ? "active" : ""}
              onClick={() =>
                dispatch({
                  type: "patch",
                  patch: { labTab: tab, playing: false },
                })
              }
            >
              {tab}
            </button>
          ))}
        </div>
      </div>
      {state.labTab === "Reconstruction" ? (
        <>
          <Panel
            title="Missing measurement, operating equipment"
            eyebrow="Telemetry reconstruction illustration"
            extra={<Badge kind="simulated" />}
          >
            <div className="toolbar">
              <label>
                Missingness mask{" "}
                <select
                  value={state.mask}
                  onChange={(e) =>
                    dispatch({ type: "patch", patch: { mask: e.target.value } })
                  }
                >
                  {lab.missingness_presets.map((m) => (
                    <option value={m.id} key={m.id}>
                      {m.title}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Equipment status{" "}
                <select
                  value={equipment}
                  onChange={(e) =>
                    setEquipment(e.target.value as typeof equipment)
                  }
                >
                  <option value="in_service">In service</option>
                  <option value="out_of_service">Out of service</option>
                  <option value="unknown">Unknown</option>
                </select>
              </label>
            </div>
            {equipment !== "in_service" && (
              <Notice title="Reconstruction unavailable">
                {equipment === "out_of_service"
                  ? "Do not reconstruct healthy operating voltage for disconnected equipment."
                  : "Unknown equipment status prevents an operating-value estimate."}{" "}
                Reference is an authored comparison trace, not a current
                equipment measurement.
              </Notice>
            )}
            <div className="chart large">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trace}>
                  <CartesianGrid vertical={false} stroke="#e8edf1" />
                  <XAxis
                    dataKey="step"
                    label={{
                      value: "Illustrative sample index",
                      position: "insideBottomRight",
                      offset: -3,
                    }}
                  />
                  <YAxis
                    domain={[0.99, 1.025]}
                    tickFormatter={(v) => Number(v).toFixed(3)}
                    width={65}
                  />
                  <Tooltip
                    formatter={(v, name) => [
                      `${fmt(Number(v), 4)} pu`,
                      String(name),
                    ]}
                  />
                  <Line
                    name="Simulated reference"
                    dataKey="reference"
                    stroke="#aab7c1"
                    strokeDasharray="2 4"
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    name="Simulated displayed readings"
                    dataKey="observed"
                    stroke="#168f84"
                    strokeWidth={2}
                    connectNulls={false}
                    dot={{ r: 3 }}
                    isAnimationActive={false}
                  />
                  <Line
                    name="Simulated demonstration · linear interpolation"
                    dataKey="reconstructed"
                    stroke="#c4882b"
                    strokeDasharray="5 3"
                    dot={{ r: 4 }}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="caption">
              Voltage magnitude · pu · illustrative14:bus:01. Linear
              interpolation is an illustrative rule, not a trained
              reconstruction model. Original/reference values are preserved.
            </p>
          </Panel>
          <Panel
            title="Measurement inspection"
            extra={
              <label>
                Provenance{" "}
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">All samples</option>
                  <option value="missing">Masked samples</option>
                  <option value="present">Present samples</option>
                </select>
              </label>
            }
          >
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Sample</th>
                    <th>Component / channel</th>
                    <th>Reference · pu</th>
                    <th>Displayed · pu</th>
                    <th>Mask</th>
                    <th>Reconstructed · pu</th>
                    <th>Provenance</th>
                  </tr>
                </thead>
                <tbody>
                  {trace
                    .filter(
                      (r) =>
                        filter === "all" ||
                        (filter === "missing" ? r.missing : !r.missing),
                    )
                    .map((r) => (
                      <tr key={r.step}>
                        <td>{r.step}</td>
                        <td>
                          <button
                            className="text-button"
                            onClick={() =>
                              dispatch({
                                type: "patch",
                                patch: { componentId: "illustrative14:bus:01" },
                              })
                            }
                          >
                            Bus 01 / voltage
                          </button>
                        </td>
                        <td>{fmt(r.reference, 4)}</td>
                        <td>{fmt(r.observed, 4)}</td>
                        <td>{r.missing ? "Missing" : "Present"}</td>
                        <td>{fmt(r.reconstructed, 4)}</td>
                        <td>Simulated demonstration</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </Panel>
          <Panel title="Selected illustrative component">
            <Network />
          </Panel>
        </>
      ) : (
        <>
          <div className="toolbar">
            <label>
              Hypothetical outage{" "}
              <select
                value={state.contingency}
                onChange={(e) =>
                  dispatch({ type: "contingency", id: e.target.value })
                }
              >
                {[
                  ...new Set(lab.combinations.map((c) => c.contingency_id)),
                ].map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Stress preset{" "}
              <select
                value={state.stress}
                onChange={(e) =>
                  dispatch({ type: "stress", value: e.target.value })
                }
              >
                <option value="moderate">Moderate</option>
                <option value="elevated">Elevated</option>
              </select>
            </label>
            <span className="caption">
              Chosen by the user; not identified by diagnosis.
            </span>
          </div>
          {!combo ? (
            <Notice>Unsupported outage/stress combination.</Notice>
          ) : state.labTab === "Cascade" ? (
            <>
              <Panel
                title="Scripted propagation"
                extra={<Badge kind="simulated" />}
              >
                <Network cascade />
              </Panel>
              <Panel title="Affected components">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Component</th>
                        <th>Round</th>
                        <th>Interpretation</th>
                        <th>Provenance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {combo.rounds[state.round].affected.map((id) => (
                        <tr key={id}>
                          <td>
                            <button
                              className="text-button"
                              onClick={() =>
                                dispatch({
                                  type: "patch",
                                  patch: { componentId: id },
                                })
                              }
                            >
                              {id}
                            </button>
                          </td>
                          <td>{state.round}</td>
                          <td>
                            Scripted affected component; no failure probability
                          </td>
                          <td>Simulated demonstration</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!combo.rounds[state.round].affected.length && (
                    <p className="caption">
                      No subsequent affected components at this round.
                    </p>
                  )}
                </div>
              </Panel>
            </>
          ) : (
            <>
              <Notice title="Illustrative outcome; physics validation not implemented">
                Candidate values are authored comparisons. No recommendation is
                trained or electrically validated; no action controls equipment.
              </Notice>
              <Panel
                title="Compare corrective-action illustrations"
                eyebrow="Authored state-action outcomes"
                extra={<Badge kind="simulated" />}
              >
                <div className="action-grid">
                  {lab.actions.map((a) => (
                    <div
                      className={`action-card ${state.actionId === a.id ? "chosen" : ""}`}
                      key={a.id}
                    >
                      <span className="eyebrow">
                        {a.id === "no-change" ? "Baseline" : "Candidate"}
                      </span>
                      <h3>{a.title}</h3>
                      <p>{a.outcome}</p>
                      <ul>
                        {a.changes.map((c) => (
                          <li key={c.component_id}>
                            {c.component_id}: {c.delta_mw > 0 ? "+" : ""}
                            {c.delta_mw} MW
                          </li>
                        ))}
                        {!a.changes.length && <li>No setpoint changes</li>}
                      </ul>
                      <button
                        className={state.actionId === a.id ? "primary" : "full"}
                        onClick={() =>
                          dispatch({ type: "patch", patch: { actionId: a.id } })
                        }
                      >
                        Compare illustration
                      </button>
                    </div>
                  ))}
                </div>
                {action ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Scripted quantity</th>
                          <th>Before</th>
                          <th>After</th>
                          <th>Physical validation</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <th>Illustrative maximum loading · % of rating</th>
                          <td>{combo.baseline_loading_pct}%</td>
                          <td>
                            {combo.baseline_loading_pct +
                              action.loading_delta_pct}
                            %
                          </td>
                          <td>Not implemented</td>
                        </tr>
                        <tr>
                          <th>Illustrative minimum voltage · pu</th>
                          <td>{fmt(combo.baseline_voltage_pu, 3)}</td>
                          <td>
                            {fmt(
                              combo.baseline_voltage_pu +
                                action.voltage_delta_pu,
                              3,
                            )}
                          </td>
                          <td>Not implemented</td>
                        </tr>
                      </tbody>
                    </table>
                    <p className="caption">
                      Simulated demonstration · {action.outcome}. No engineering
                      limits, balancing, or feasibility have been verified.
                    </p>
                  </div>
                ) : (
                  <p className="caption">
                    Select a candidate to compare its scripted before/after
                    values.
                  </p>
                )}
              </Panel>
            </>
          )}
        </>
      )}
      <div className="scope-note">
        <p>
          <strong>Simulation assumptions:</strong> {lab.assumptions.join(" ")}
        </p>
      </div>
    </>
  );
}
