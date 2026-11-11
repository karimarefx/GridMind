import { useEffect, useRef, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmt, Panel } from "../components/Common";
import { Stage1Evaluation } from "./Stage1Evaluation";
import "../styles/diagnosis.css";

const channels = {
  angle: "Voltage angle",
  frequency: "Frequency",
  voltage_magnitude: "Voltage magnitude",
  current_magnitude: "Current magnitude",
  current_angle: "Current angle",
};
type Channel = keyof typeof channels;
const channelKeys = Object.keys(channels) as Channel[];
const header = "elapsed_seconds,angle,reconstructed,frequency,voltage_magnitude,current_magnitude,current_angle";
const outcomes = {
  normal: ["No abnormality detected", "The detector accepted this window as normal."],
  physical: ["Physical disturbance detected", "The cause model identified a pattern consistent with a grid disturbance."],
  sensor: ["Sensor error detected", "The cause model identified a pattern consistent with a timing issue in the measurement."],
};

type Result = {
  prediction: {
    category: keyof typeof outcomes | null;
    reason: string | null;
    model_version: string;
    detection: { decision: "normal" | "abnormal" | "uncertain"; abnormal_score: number; thresholds: { normal_max: number | null; abnormal_min: number | null } };
    diagnosis: { decision: "physical" | "sensor" | "uncertain"; raw_score: number; threshold: number | null } | null;
  };
  trace: (Record<Channel, number> & { elapsed_seconds: number })[];
  angle_unit: "degree" | "radian";
};
type Health = { ready: boolean; reason?: string; model_version?: string };

export function useStage1Health() {
  const [health, setHealth] = useState<Health>({ ready: false });
  const [checking, setChecking] = useState(true);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/health", { signal: controller.signal }).then(async response => {
      const body = await response.json();
      if (typeof body.ready !== "boolean") throw new Error("Unsupported health response");
      if (!controller.signal.aborted) setHealth(body);
    }).catch(() => {
      if (!controller.signal.aborted) setHealth({ ready: false, reason: "Start the local Python service, then check the connection again." });
    }).finally(() => {
      if (!controller.signal.aborted) setChecking(false);
    });
    return () => controller.abort();
  }, [attempt]);
  return { health, checking, retry: () => {
    setChecking(true);
    setAttempt(value => value + 1);
  } };
}

export function DiagnosisUpload() {
  const { health, checking, retry } = useStage1Health();
  const [file, setFile] = useState<File | null>(null);
  const [unit, setUnit] = useState("degree");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ text: string; invalid: boolean } | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [channel, setChannel] = useState<Channel>("angle");
  const [cursor, setCursor] = useState(0);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  const clear = () => { setResult(null); setError(null); setCursor(0); };

  async function analyze() {
    if (!file || busy || checking || !health.ready) return;
    clear();
    if (file.size > 2 * 1024 * 1024) {
      setError({ text: "Choose a CSV no larger than 2 MiB.", invalid: true });
      return;
    }

    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    try {
      const body = new FormData();
      body.append("file", file);
      body.append("angle_unit", unit);
      const response = await fetch("/api/diagnosis", { method: "POST", body, signal: controller.signal });
      const data = await response.json();
      if (!response.ok) {
        const invalid = [413, 422].includes(response.status);
        setError({ text: typeof data.detail === "string" ? data.detail : "Check the input format and try again.", invalid });
        if (!invalid) retry();
        return;
      }
      if (!Array.isArray(data.trace) || data.trace.length !== 1800 || !data.prediction?.detection) {
        throw new Error("Unsupported diagnosis response");
      }
      if (!controller.signal.aborted) setResult(data);
    } catch {
      if (!controller.signal.aborted) {
        setError({ text: "Analysis could not be completed. Check the local service and try again.", invalid: false });
        retry();
      }
    } finally {
      if (!controller.signal.aborted) {
        pending.current = null;
        setBusy(false);
      }
    }
  }

  const prediction = result?.prediction;
  const detection = prediction?.detection.decision;
  const cause = prediction?.diagnosis?.decision;
  const detectionLabel = detection === "abnormal" ? "Abnormality detected" : detection === "normal" ? "No abnormality detected" : "Uncertain";
  const causeLabel = cause === "physical" ? "Physical disturbance" : cause === "sensor" ? "Sensor error" : "Uncertain";
  const [title, explanation] = prediction?.category ? outcomes[prediction.category]
    : detection === "abnormal" ? ["Abnormality detected, cause uncertain", "The cause score did not meet the decision threshold."]
    : ["Abnormality decision uncertain", "The detector could not decide whether this window was abnormal."];
  const status = checking ? "Checking service" : health.ready ? "Service ready" : "Service unavailable";
  const sample = result?.trace[cursor];
  const measurementUnit = channel === "frequency" ? "Hz"
    : channel === "angle" || channel === "current_angle" ? result?.angle_unit === "degree" ? "°" : "rad" : "Source units";

  return <section className="diagnosis-workspace" aria-label="Event diagnosis workspace">
    <header className="diagnosis-heading">
      <h1>Event diagnosis</h1>
      <span role="status" className={`diagnosis-status ${checking ? "" : health.ready ? "diagnosis-ready" : "diagnosis-error"}`}>{status}</span>
    </header>

    <Panel title="Upload measurements">
      <div className="diagnosis-controls">
        <label>Measurement CSV <input type="file" accept=".csv,text/csv" disabled={busy} onChange={event => {
          clear();
          setFile(event.target.files?.[0] ?? null);
        }} /></label>
        <label>Angle unit <select aria-label="Angle unit" value={unit} disabled={busy} onChange={event => {
          clear();
          setUnit(event.target.value);
        }}><option value="degree">Degrees</option><option value="radian">Radians</option></select></label>
        <button disabled={!file || busy || checking || !health.ready} onClick={analyze}>Analyze</button>
      </div>
      <details className="diagnosis-format">
        <summary>Input format</summary>
        <p>Upload a 60-second window from one phasor measurement unit (PMU), with 1,800 original samples at 30 Hz and a maximum file size of 2 MiB.</p>
        <p>Use the template columns. Both angles must match the selected unit, frequency must be in Hz, and every reconstruction flag must be zero.</p>
        <a download="gridmind-window-header.csv" href={"data:text/csv;charset=utf-8," + encodeURIComponent(header + "\n")}>Download CSV header template</a>
      </details>
      {!checking && !health.ready && <p role="alert" className="diagnosis-error">
        {health.reason ?? "Start the local Python service."} <button onClick={retry}>Check service again</button>
      </p>}
      {busy && <p role="status">Analyzing…</p>}
      {error && <p role="alert" className="diagnosis-error">{error.text}{error.invalid && " See Input format and try again."}</p>}
    </Panel>

    <ol className="diagnosis-flow" aria-label="Analysis steps">
      <li><strong>Validation</strong><span>{prediction ? "Valid" : error?.invalid ? "Invalid" : "Pending"}</span></li>
      <li><strong>Detection</strong><span>{prediction ? detectionLabel : error?.invalid ? "Skipped" : "Pending"}</span></li>
      <li><strong>Cause</strong><span>{cause ? causeLabel : prediction || error?.invalid ? "Skipped" : "Pending"}</span></li>
    </ol>

    <div className="diagnosis-results">
      <Panel title="Measurement chart" extra={result ? <span>60 s at 30 Hz</span> : undefined}>
        {result && sample ? <>
          <div className="diagnosis-chart-heading">
            <label>Measurement channel <select aria-label="Measurement channel" value={channel} onChange={event => setChannel(event.target.value as Channel)}>
              {channelKeys.map(key => <option key={key} value={key}>{channels[key]}</option>)}
            </select></label>
            <span>{measurementUnit}</span>
          </div>
          <div className="diagnosis-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={result.trace}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="elapsed_seconds" type="number" domain={[0, 60]} ticks={[0, 10, 20, 30, 40, 50, 60]} unit=" s" />
                <YAxis domain={["auto", "auto"]} width={62} tickFormatter={value => fmt(Number(value), 3)} />
                <Tooltip labelFormatter={value => `${fmt(Number(value), 3)} s`} />
                <ReferenceLine x={sample.elapsed_seconds} stroke="#946200" />
                <Line dataKey={channel} name={channels[channel]} unit={` ${measurementUnit}`} stroke="#14897e" dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <label className="diagnosis-sample">Uploaded sample <input type="range" min={0} max={result.trace.length - 1}
            value={cursor} onChange={event => setCursor(Number(event.target.value))} /></label>
          <p>Sample {cursor + 1} / {result.trace.length} at {fmt(sample.elapsed_seconds, 3)} s</p>
          <p>{channels[channel]} <strong>{fmt(sample[channel], 6)} {measurementUnit}</strong></p>
        </> : <p className="diagnosis-placeholder">Analyze a CSV to view its measurement trace.</p>}
      </Panel>

      <div className="diagnosis-result" aria-live="polite">
        <Panel title="Diagnosis result" extra={<span className="diagnosis-status">Experimental model</span>}>
          {prediction ? <>
            <h3 className={prediction.category === "normal" ? "diagnosis-normal" : prediction.category ? "" : "diagnosis-uncertain"}>{title}</h3>
            <p>{explanation}</p>
            {file && <p className="caption diagnosis-file">{file.name}</p>}
          </> : <p>{busy ? "Waiting for analysis." : "Results appear here after analysis."}</p>}
        </Panel>
      </div>
    </div>

    <div className="diagnosis-disclosures">
      <details className="diagnosis-disclosure">
        <summary>Model details</summary>
        {prediction ? <>
          <p>Model version {prediction.model_version}. Ground truth was not supplied.</p>
          <p>Detector score {fmt(prediction.detection.abnormal_score, 4)}. Normal cutoff ≤ {fmt(prediction.detection.thresholds.normal_max, 4)}. Abnormal cutoff ≥ {fmt(prediction.detection.thresholds.abnormal_min, 4)}.</p>
          {prediction.diagnosis && <p>Cause score {fmt(prediction.diagnosis.raw_score, 4)}. Decision threshold {fmt(prediction.diagnosis.threshold, 4)}.</p>}
          <p>Scores are uncalibrated.</p>
        </> : <p>Analyze a CSV to see its scores and thresholds.</p>}
      </details>
      <details className="diagnosis-disclosure">
        <summary>Validation results</summary>
        <Stage1Evaluation />
      </details>
    </div>
  </section>;
}
