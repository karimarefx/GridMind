import { useEffect, useReducer, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Database,
  FlaskConical,
  LayoutDashboard,
  Network as NetworkIcon,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import { loadBundle, clearCache } from "../data/load";
import type { Bundle, View } from "../data/types";
import { DashboardContext } from "../state/context";
import { initialState, reducer } from "../state/reducer";
import { Badge, Notice, utc } from "../components/Common";
import { Overview } from "../views/Overview";
import { Forecasting } from "../views/Forecasting";
import { Diagnosis } from "../views/Diagnosis";
import { Laboratory } from "../views/Laboratory";
import { Evaluation } from "../views/Evaluation";
const views: { title: View; icon: typeof Activity; sub: string }[] = [
  { title: "Overview", icon: LayoutDashboard, sub: "Your research workspace" },
  {
    title: "Forecasting",
    icon: Activity,
    sub: "One-hour-ahead power forecasts",
  },
  {
    title: "Event diagnosis",
    icon: ShieldCheck,
    sub: "Normal detection and cause classification",
  },
  {
    title: "Scenario laboratory",
    icon: FlaskConical,
    sub: "Three interactive grid illustrations",
  },
  {
    title: "Evaluation & provenance",
    icon: Database,
    sub: "Results, sources, and limitations",
  },
];
export function App() {
  const [data, setData] = useState<Bundle | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [state, dispatch] = useReducer(reducer, initialState);
  const [resetKey, setResetKey] = useState(0);
  useEffect(() => {
    let current = true;
    setData(null);
    setError("");
    loadBundle()
      .then((d) => {
        if (current) {
          setData(d);
          dispatch({
            type: "scenario",
            scenario: d.catalog.scenarios.find(
              (s) => s.id === d.catalog.default_scenario,
            )!,
          });
        }
      })
      .catch((e) => {
        if (current) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      current = false;
    };
  }, [attempt]);
  const scenario = data?.catalog.scenarios.find(
    (s) => s.id === state.scenarioId,
  );
  const combo = data?.lab?.combinations.find(
    (c) => c.contingency_id === state.contingency && c.stress === state.stress,
  );
  const eventMax = Math.max(0, state.eventCount - 1);
  const labMode = state.view === "Scenario laboratory",
    eventMode = state.view === "Event diagnosis";
  const min = labMode || eventMode ? 0 : (scenario?.forecast_start ?? 0);
  const max = labMode
    ? (combo?.rounds.length ?? 1) - 1
    : eventMode
      ? eventMax
      : (scenario?.forecast_end ?? 0);
  const pos = labMode
    ? state.round
    : eventMode
      ? state.eventIndex
      : state.forecastIndex;
  const timelineEnabled = labMode
    ? !!combo
    : eventMode
      ? state.eventCount > 0
      : !!data?.forecasts[pos];
  useEffect(() => {
    if (!state.playing) return;
    const timer = window.setInterval(() => {
      if (pos >= max) dispatch({ type: "patch", patch: { playing: false } });
      else dispatch({ type: "step", index: pos + 1 });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [state.playing, pos, max]);
  function retry() {
    clearCache();
    setAttempt((a) => a + 1);
  }
  if (!data)
    return (
      <div className="boot">
        <div className="brand-mark">
          <NetworkIcon size={27} />
        </div>
        <h1>GridMind</h1>
        {error ? (
          <>
            <Notice title="Dashboard could not load">{error}</Notice>
            <button onClick={retry}>Retry static asset loading</button>
          </>
        ) : (
          <p role="status">Loading research exports and scenario catalog…</p>
        )}
      </div>
    );
  const f = data.forecasts[state.forecastIndex];
  const view = views.find((v) => v.title === state.view)!;
  return (
    <DashboardContext.Provider value={{ data, state, dispatch }}>
      <div className="app-shell">
        <aside className="sidebar">
          <a
            href="#"
            className="brand"
            onClick={(e) => {
              e.preventDefault();
              dispatch({ type: "view", view: "Overview" });
            }}
          >
            <span className="brand-mark">
              <NetworkIcon size={24} />
            </span>
            <span>
              GridMind<small>RESEARCH CONTROL CENTER</small>
            </span>
          </a>
          <div className="workspace-label">
            WORKSPACE <span>POC / 10%</span>
          </div>
          <nav aria-label="Dashboard views">
            {views.map((v) => (
              <button
                key={v.title}
                className={
                  state.view === v.title ? "nav-item active" : "nav-item"
                }
                onClick={() => dispatch({ type: "view", view: v.title })}
              >
                <v.icon size={18} />
                <span>{v.title}</span>
                {v.title === "Event diagnosis" && <i className="nav-pending" />}
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="offline-card">
              <i className="dot teal" />
              <strong>Local demonstration</strong>
              <p>
                Saved replay and local Python inference.
                <br />
                No live equipment connection.
              </p>
            </div>
            <div className="sidebar-footer">
              <span className="avatar">GM</span>
              <div>
                GridMind team<small>Proposal · 10 Nov 2026</small>
              </div>
              <ArrowUpRight size={15} />
            </div>
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <div className="breadcrumb">
              Workspace <ChevronRight size={13} />
              <b>{state.view}</b>
            </div>
            <div className="topbar-right">
              <span className="offline-label">
                <i className="dot teal" />
                {eventMode ? "Local analysis" : "Offline replay"}
              </span>
              <span className="vertical-divider" />
              <span className="release-tag">PROOF OF CONCEPT</span>
              <span className="avatar light">GM</span>
            </div>
          </header>
          <main>
            {!eventMode && <div className="page-title">
              <div>
                <div className="eyebrow">GRIDMIND / RESEARCH DEMONSTRATION</div>
                <h1>
                  {state.view === "Overview" ? "Control center" : state.view}
                </h1>
                <p>
                  {view.sub}{" "}
                  <span className="title-note">· source timestamps in UTC</span>
                </p>
              </div>
              <span className="scope-pill">
                <i className="dot teal" />
                Local research POC
              </span>
            </div>}
            {!eventMode && <section
              className="replay-toolbar"
              aria-label="Scenario and timeline controls"
            >
              <div className="scenario-selector">
                <SlidersHorizontal size={18} />
                <label>
                  DEMONSTRATION SCENARIO
                  <select
                    aria-label="Demonstration scenario"
                    value={state.scenarioId}
                    onChange={(e) =>
                      dispatch({
                        type: "scenario",
                        scenario: data.catalog.scenarios.find(
                          (s) => s.id === e.target.value,
                        )!,
                      })
                    }
                  >
                    {data.catalog.scenarios.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.title}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="timeline">
                <div className="timeline-label">
                  <span>
                    {labMode
                      ? "SCRIPTED CASCADE ROUND"
                      : eventMode
                        ? "COMPLETE EVENT WINDOW"
                        : "FORECAST ISSUE TIME"}
                  </span>
                  <b>
                    {labMode
                      ? `Round ${pos} / ${max}`
                      : eventMode
                        ? state.eventCount
                          ? "Sample " +
                            (state.eventIndex + 1) +
                            " / " +
                            state.eventCount
                          : "Saved replay unavailable · upload below"
                        : f
                          ? utc(f.issued_at_utc)
                          : "Unavailable"}
                  </b>
                </div>
                <input
                  aria-label="Replay timeline"
                  type="range"
                  min={min}
                  max={Math.max(min, max)}
                  value={Math.min(Math.max(pos, min), max)}
                  disabled={!timelineEnabled}
                  onChange={(e) =>
                    dispatch({ type: "step", index: Number(e.target.value) })
                  }
                />
              </div>
              <div className="playback">
                <button
                  aria-label="Previous replay step"
                  disabled={!timelineEnabled || pos <= min}
                  onClick={() => dispatch({ type: "step", index: pos - 1 })}
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  className="play-button"
                  aria-label={state.playing ? "Pause replay" : "Play replay"}
                  disabled={!timelineEnabled || (pos >= max && !state.playing)}
                  onClick={() =>
                    dispatch({
                      type: "patch",
                      patch: { playing: !state.playing },
                    })
                  }
                >
                  {state.playing ? <Pause size={16} /> : <Play size={16} />}
                </button>
                <button
                  aria-label="Next replay step"
                  disabled={!timelineEnabled || pos >= max}
                  onClick={() => dispatch({ type: "step", index: pos + 1 })}
                >
                  <ChevronRight size={16} />
                </button>
                <button
                  className="reset-button"
                  onClick={() => {
                    dispatch({ type: "reset", scenario: scenario! });
                    setResetKey((k) => k + 1);
                  }}
                >
                  <RotateCcw size={14} />
                  Reset
                </button>
              </div>
            </section>}
            {Object.keys(data.errors).length > 0 && (
              <Notice title="Some artifacts could not load">
                {Object.entries(data.errors).map(([p, e]) => (
                  <p key={p}>
                    {p}: {e}
                  </p>
                ))}
                <button onClick={retry}>Retry loading</button>
              </Notice>
            )}
            <div
              key={`${state.scenarioId}:${resetKey}`}
              className="view-content"
            >
              {state.view === "Overview" ? (
                <Overview />
              ) : state.view === "Forecasting" ? (
                <Forecasting />
              ) : state.view === "Event diagnosis" ? (
                <Diagnosis />
              ) : state.view === "Scenario laboratory" ? (
                <Laboratory />
              ) : (
                <Evaluation />
              )}
            </div>
            <footer className="page-footer">
              <span>
                GRIDMIND <b>RESEARCH POC</b> · No live grid connection
              </span>
              <span>
                <Badge kind="observed">Observed / dataset input</Badge>
                <Badge kind="prediction" />
                <Badge kind="simulated" />
                <Badge kind="calculated" />
              </span>
            </footer>
          </main>
        </div>
      </div>
    </DashboardContext.Provider>
  );
}
