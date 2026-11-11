import { useDashboard } from "../state/context";
import { Badge, fmt } from "./Common";
export function Network({ cascade = false }: { cascade?: boolean }) {
  const { data, state, dispatch } = useDashboard();
  const network = data.network;
  if (!network) return <p>Illustrative network unavailable.</p>;
  const combo = data.lab?.combinations.find(
    (c) => c.contingency_id === state.contingency && c.stress === state.stress,
  );
  const affected = cascade ? (combo?.rounds[state.round]?.affected ?? []) : [];
  const active = state.componentId;
  const bus = network.buses.find((b) => b.id === active);
  const line = network.lines.find((l) => l.id === active);
  function select(id: string) {
    dispatch({ type: "patch", patch: { componentId: id } });
  }
  return (
    <>
      <div className="network-wrap">
        <div className="network-meta">
          <span>
            <i className="dot teal" />
            14 buses <span className="muted">/</span> 20 illustrative lines
          </span>
          <Badge kind="simulated" />
        </div>
        <div className="network-plot">
          <svg
            className="network"
            viewBox="0 0 900 495"
            role="group"
            aria-label="Interactive illustrative 14-bus network"
          >
            <defs>
              <pattern
                id="grid"
                width="25"
                height="25"
                patternUnits="userSpaceOnUse"
              >
                <circle className="network-grid-dot" cx="1" cy="1" r="0.9" />
              </pattern>
            </defs>
            <rect width="900" height="495" fill="url(#grid)" />
            {network.lines.map((l) => {
              const a = network.buses.find((b) => b.id === l.source)!,
                b = network.buses.find((b) => b.id === l.target)!;
              const outage = cascade && l.id === state.contingency;
              return (
                <g
                  key={l.id}
                  role="button"
                  tabIndex={0}
                  aria-label={`Inspect ${l.label}${outage ? ", hypothetical outage" : ""}`}
                  aria-pressed={active === l.id}
                  onClick={() => select(l.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      select(l.id);
                    }
                  }}
                  className={`network-line ${outage ? "outage" : affected.includes(l.id) ? "affected" : ""} ${active === l.id ? "selected" : ""}`}
                >
                  <title>
                    {l.id} ·{" "}
                    {outage ? "Hypothetical outage" : "Simulated demonstration"}
                  </title>
                  <line
                    className="line-hit"
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                  />
                  <line
                    className="line-visible"
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                  />
                  <text x={(a.x + b.x) / 2 + 6} y={(a.y + b.y) / 2 - 7}>
                    {l.label}
                  </text>
                </g>
              );
            })}
            {network.buses.map((b) => (
              <g
                key={b.id}
                role="button"
                tabIndex={0}
                aria-label={`Inspect bus ${b.label}`}
                aria-pressed={active === b.id}
                onClick={() => select(b.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    select(b.id);
                  }
                }}
                className={`network-bus ${active === b.id ? "selected" : ""}`}
              >
                <circle cx={b.x} cy={b.y} r="19" />
                <circle className="bus-core" cx={b.x} cy={b.y} r="5" />
                <text x={b.x} y={b.y + 36}>
                  BUS {b.label}
                </text>
              </g>
            ))}
            <g className="generator-label">
              <text x="50" y="85">
                G1 / GENERATION
              </text>
              <text x="690" y="85">
                G2 / RENEWABLE
              </text>
              <text x="200" y="470">
                ILLUSTRATIVE LOAD
              </text>
            </g>
          </svg>
        </div>
        {cascade ? (
          <div className="network-legend">
            <span>
              <i className="legend-line" />
              Illustrative connection
            </span>
            <span>
              <i className="legend-line amber" />
              Scripted propagation
            </span>
            <span>
              <i className="legend-line red" />
              Hypothetical outage
            </span>
          </div>
        ) : (
          <p className="network-legend">
            Select a bus or line to inspect it.
            <span className="network-scroll-hint">Scroll sideways to see the full grid.</span>
          </p>
        )}
      </div>
      <p className="caption">
        The schematic uses an authored topology. Forecast and event data come from separate sources.
      </p>
      {(bus || line) && (
        <div className="inspector" aria-live="polite">
          <div>
            <div className="eyebrow">Component inspector</div>
            <strong>{active}</strong>
          </div>
          <div>
            Type <b>{bus ? "Bus" : "Line"}</b>
          </div>
          <div>
            Equipment{" "}
            <b>
              {cascade && active === state.contingency
                ? "Hypothetically out of service"
                : "Illustratively in service"}
            </b>
          </div>
          <div>
            Measurements{" "}
            <b>
              {bus?.id === network.buses[0].id
                ? "Laboratory voltage trace"
                : "Unavailable"}
            </b>
          </div>
          <div>
            Risk{" "}
            <b>
              {affected.includes(active!)
                ? "Scripted affected component"
                : "No calibrated assessment"}
            </b>
          </div>
          <button className="text-button" onClick={() => select("")}>
            Close
          </button>
        </div>
      )}
      {cascade && combo && (
        <div className="network-readout">
          <div>
            <span>Propagation round</span>
            <strong>
              {state.round} / {combo.rounds.length - 1}
            </strong>
          </div>
          <div>
            <span>Severity · simulated</span>
            <strong>{combo.rounds[state.round]?.severity}</strong>
          </div>
          <div>
            <span>Scripted DNS fraction</span>
            <strong>
              {fmt((combo.rounds[state.round]?.dns_fraction ?? 0) * 100)}%{" "}
              <small>of illustrative demand</small>
            </strong>
          </div>
        </div>
      )}
    </>
  );
}
