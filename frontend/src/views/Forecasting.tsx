import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Eye, EyeOff } from "lucide-react";
import { useDashboard } from "../state/context";
import { targets, labels, type Target, type Observation } from "../data/types";
import {
  Badge,
  fmt,
  MetricCard,
  Notice,
  Panel,
  utc,
} from "../components/Common";
const colors: Record<Target, string> = {
  demand: "#3581be",
  solar: "#c88b20",
  wind: "#159981",
  net_load: "#8060b4",
};
export function observedValue(o: Observation, t: Target) {
  return t === "demand"
    ? o.total_load
    : t === "solar"
      ? o.solar_generation
      : t === "wind"
        ? o.wind_generation
        : o.net_load;
}
export function Forecasting() {
  const { data, state, dispatch } = useDashboard();
  const [table, setTable] = useState(false);
  const f = data.forecasts[state.forecastIndex];
  if (!f)
    return (
      <Notice>
        {data.errors["forecasting/forecast_predictions.json"] ??
          data.errors.forecasting ??
          "Genuine forecasting artifacts unavailable. No simulation is substituted."}
      </Notice>
    );
  const actual = data.observations.find((o) => o.time === f.target_time_utc);
  const history = data.observations
    .filter((o) => o.time <= f.issued_at_utc)
    .slice(-24);
  return (
    <>
      <div className="section-bar">
        <div>
          <Badge />
          <p className="muted small">
            Frozen XGBoost outputs · {f.region_id} · one hour ahead
          </p>
        </div>
        <button
          className="primary"
          onClick={() =>
            dispatch({ type: "patch", patch: { revealed: !state.revealed } })
          }
        >
          {state.revealed ? <EyeOff size={16} /> : <Eye size={16} />}{" "}
          {state.revealed ? "Hide actual" : "Reveal actual"}
        </button>
      </div>
      <div className="metrics-grid">
        {targets.map((t) => (
          <MetricCard
            key={t}
            label={labels[t]}
            value={fmt(f[`${t}_mw`])}
            kind={t === "net_load" ? "calculated" : "prediction"}
            detail={
              t === "net_load"
                ? "Calculated from precomputed model predictions"
                : state.revealed && actual
                  ? `Observed ${fmt(observedValue(actual, t))} MW · absolute error ${fmt(Math.abs(f[`${t}_mw`] - observedValue(actual, t)), 2)} MW`
                  : undefined
            }
          />
        ))}
      </div>
      <div className="toolbar">
        <div className="chips">
          {targets.map((t) => (
            <button
              key={t}
              aria-pressed={state.series.includes(t)}
              className={state.series.includes(t) ? "chip active" : "chip"}
              onClick={() =>
                dispatch({
                  type: "patch",
                  patch: {
                    series: state.series.includes(t)
                      ? state.series.filter((x) => x !== t)
                      : [...state.series, t],
                  },
                })
              }
            >
              <i style={{ background: colors[t] }} />
              {labels[t]}
            </button>
          ))}
        </div>
        <label>
          Baseline{" "}
          <select
            value={state.baseline}
            onChange={(e) =>
              dispatch({ type: "patch", patch: { baseline: e.target.value } })
            }
          >
            <option value="persistence">Last observation</option>
            <option value="daily">Daily persistence</option>
            <option value="weekly">Weekly persistence</option>
            <option value="daily_cf">Solar daily capacity factor</option>
          </select>
        </label>
      </div>
      <div className="chart-grid">
        {state.series.map((t) => {
          const baseline = data.baselines.find(
            (b) =>
              b.forecast_id === f.forecast_id &&
              b.target === t &&
              b.method === state.baseline,
          );
          const chart = [
            ...history.map((o) => ({
              time: Date.parse(o.time),
              observed: observedValue(o, t),
              prediction: null as number | null,
              baseline: null as number | null,
            })),
            {
              time: Date.parse(f.target_time_utc),
              observed:
                state.revealed && actual
                  ? observedValue(actual, t)
                  : (null as unknown as number),
              prediction: f[`${t}_mw`],
              baseline: baseline?.value_mw ?? null,
            },
          ];
          return (
            <Panel
              key={t}
              title={`${labels[t]} · MW`}
              extra={
                <Badge kind={t === "net_load" ? "calculated" : "prediction"} />
              }
            >
              <div
                className="chart"
                aria-label={`${labels[t]} observations and precomputed forecast`}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={chart}
                    margin={{ top: 15, right: 20, bottom: 5, left: 5 }}
                  >
                    <CartesianGrid vertical={false} stroke="#e8edf1" />
                    <XAxis
                      ticks={chart.filter((_, i) => i % 6 === 0).map(p => p.time)}
                      dataKey="time"
                      type="number"
                      domain={["dataMin", "dataMax"]}
                      tickFormatter={(v) =>
                        new Date(v).toISOString().slice(11, 16)
                      }
                      tick={{ fontSize: 11 }}
                      minTickGap={35}
                    />
                    <YAxis
                      tickFormatter={(v) => fmt(v / 1000, 1) + "k"}
                      tick={{ fontSize: 11 }}
                      width={55}
                    />
                    <Tooltip
                      labelFormatter={(v) =>
                        utc(new Date(Number(v)).toISOString())
                      }
                      formatter={(v, name) => [
                        `${fmt(Number(v), 2)} MW`,
                        String(name),
                      ]}
                    />
                    <ReferenceLine
                      x={Date.parse(f.issued_at_utc)}
                      stroke="#90a5b3"
                      strokeDasharray="3 3"
                      label={{
                        value: "Issue",
                        fontSize: 10,
                        position: "insideTopLeft",
                      }}
                    />
                    <Line
                      name={t === 'net_load' ? 'Calculated from observed dataset values' : 'Observed — ERCOT dataset'}
                      type="linear"
                      dataKey="observed"
                      stroke={colors[t]}
                      strokeWidth={2}
                      dot={false}
                      connectNulls={false}
                      isAnimationActive={false}
                    />
                    <Line
                      name={
                        t === "net_load"
                          ? "Calculated from precomputed model predictions"
                          : "Precomputed model predictions"
                      }
                      dataKey="prediction"
                      stroke={colors[t]}
                      strokeDasharray="4 3"
                      dot={{ r: 5, fill: colors[t] }}
                      isAnimationActive={false}
                    />
                    <Line
                      name={`Calculated baseline · ${state.baseline}`}
                      dataKey="baseline"
                      stroke="#8b9daa"
                      dot={{ r: 4 }}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="chart-key">
                <span>
                  <i style={{ background: colors[t] }} />
                  {t === 'net_load' ? 'Calculated actual' : 'Observed'}
                </span>
                <span>◆ Precomputed target</span>
                <span>○ Calculated baseline</span>
              </div>
              {!baseline && (
                <p className="caption">
                  Selected baseline unavailable for {labels[t].toLowerCase()}.
                </p>
              )}
            </Panel>
          );
        })}
      </div>
      {!state.series.length && (
        <Notice title="No series selected">
          Select a series to show its forecast chart.
        </Notice>
      )}
      <Panel
        title="Forecast record"
        eyebrow="Alignment & provenance"
        extra={
          <button onClick={() => setTable(!table)}>
            {table ? "Hide" : "Show"} value table
          </button>
        }
      >
        <div className="details-grid">
          <div>
            <span>Issue time</span>
            <strong>{utc(f.issued_at_utc)}</strong>
          </div>
          <div>
            <span>Target time · hour ending</span>
            <strong>{utc(f.target_time_utc)}</strong>
          </div>
          <div>
            <span>Bundle</span>
            <strong>{f.model_version}</strong>
          </div>
          <div>
            <span>Quality</span>
            <strong>
              {f.data_quality_status} · {f.history_rows} history rows
            </strong>
          </div>
        </div>
        <p className="caption">
          Demand/wind: 24-hour history · Solar: 72-hour history · Weekly
          baseline: 168-hour context. {f.capacity_policy}. Replay reveals saved
          values; no inference runs in the browser.
        </p>
        {table && (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Series</th>
                  <th>Prediction · MW</th>
                  <th>Observed · MW</th>
                  <th>Absolute error · MW</th>
                  <th>Provenance</th>
                </tr>
              </thead>
              <tbody>
                {targets.map((t) => (
                  <tr key={t}>
                    <th>{labels[t]}</th>
                    <td>{fmt(f[`${t}_mw`], 2)}</td>
                    <td>
                      {state.revealed && actual
                        ? fmt(observedValue(actual, t), 2)
                        : "Hidden until reveal"}
                    </td>
                    <td>
                      {state.revealed && actual
                        ? fmt(
                            Math.abs(f[`${t}_mw`] - observedValue(actual, t)),
                            2,
                          )
                        : "Unavailable until reveal"}
                    </td>
                    <td>
                      {t === "net_load"
                        ? "Calculated from precomputed model predictions"
                        : "Precomputed model predictions"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  );
}
