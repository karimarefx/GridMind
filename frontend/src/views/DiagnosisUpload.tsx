import { useEffect, useRef, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, fmt, Notice, Panel } from "../components/Common";

type Result = {
  prediction: { status: string; category: string | null; reason: string | null; model_version: string;
    detection: { decision: string; abnormal_score: number; thresholds: { normal_max: number | null; abnormal_min: number | null } };
    diagnosis: { decision: string; raw_score: number; threshold: number | null } | null };
  trace: Record<string, number>[];
  angle_unit: string;
};
type Health = { ready: boolean; reason?: string; model_version?: string };
export function useStage1Health() {
  const [health, setHealth] = useState<Health>({ ready: false, reason: "Checking local Python service…" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/health', { signal: controller.signal }).then(async response => {
      const body = await response.json();
      if (typeof body.ready !== 'boolean') throw new Error('Unsupported health response');
      if (!controller.signal.aborted) setHealth(body);
    }).catch(() => {
      if (!controller.signal.aborted) setHealth({ ready: false, reason: 'Start the local Python service to upload and diagnose measurements.' });
    });
    return () => controller.abort();
  }, [attempt]);
  return { health, retry: () => setAttempt(value => value + 1) };
}

export function DiagnosisUpload() {
  const { health, retry } = useStage1Health();
  const [file, setFile] = useState<File | null>(null);
  const [unit, setUnit] = useState('degree');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<Result | null>(null);
  const [channel, setChannel] = useState('angle');
  const [cursor, setCursor] = useState(0);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  const clear = () => { setResult(null); setError(''); setCursor(0); };
  const labels: Record<string, string> = { normal: 'No abnormality detected', physical: 'Physical disturbance detected', sensor: 'PMU timing anomaly detected' };
  async function run() {
    if (!file) return;
    clear();
    if (file.size > 2 * 1024 * 1024) { setError('Upload exceeds the 2 MiB file limit.'); return; }
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    try {
      const body = new FormData(); body.append('file', file); body.append('angle_unit', unit);
      const response = await fetch('/api/diagnosis', { method: 'POST', body, signal: controller.signal });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The file could not be validated.');
      if (!Array.isArray(data.trace) || data.trace.length !== 1800 || !data.prediction?.detection) throw new Error('Unsupported diagnosis response.');
      if (!controller.signal.aborted) setResult(data);
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'Diagnosis service unavailable.');
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  const p = result?.prediction;
  return <>
    <Panel title="Upload and diagnose" eyebrow="Normal → abnormal → cause">
      <Badge>Experimental local model</Badge>
      <p>Upload a complete 60-second, 30 Hz window from one PMU. The detector checks for abnormality before classifying its cause. Normal means no abnormality detected under this model.</p>
      <p className="caption">Requires 1,800 original samples: elapsed_seconds, angle, reconstructed, frequency, voltage_magnitude, current_magnitude, current_angle. Both angles must use the selected unit; frequency is in Hz. Magnitudes retain consistent source units. All reconstruction flags must be zero. Maximum 2 MiB.</p>
      <a download="gridmind-window-header.csv" href={'data:text/csv;charset=utf-8,' + encodeURIComponent('elapsed_seconds,angle,reconstructed,frequency,voltage_magnitude,current_magnitude,current_angle\n')}>Download CSV header template</a>
      {!health.ready && <Notice title="Detection service unavailable">{health.reason} <button onClick={retry}>Check service again</button></Notice>}
      <div className="toolbar">
        <label>Measurement CSV <input aria-label="Measurement CSV" type="file" accept=".csv,text/csv" disabled={busy} onChange={e => { clear(); setFile(e.target.files?.[0] ?? null); }} /></label>
        <label>Angle unit <select aria-label="Angle unit" value={unit} disabled={busy} onChange={e => { clear(); setUnit(e.target.value); }}><option value="degree">Degrees</option><option value="radian">Radians</option></select></label>
        <button disabled={!file || busy || !health.ready} onClick={run}>{busy ? 'Diagnosing…' : 'Run diagnosis'}</button>
      </div>
      {busy && <p role="status">Validating measurements and running both stages…</p>}
      {error && <div role="alert"><Notice title="Input unavailable">{error}</Notice></div>}
      {p && <div aria-live="polite">
        <h3>{p.category ? labels[p.category] : p.detection.decision === 'abnormal' ? 'Abnormal — cause uncertain' : 'Abnormality decision uncertain'}</h3>
        <p>Ground truth not supplied · {p.model_version}</p>
        <p>Detector: {p.detection.decision} · uncalibrated abnormal score: {fmt(p.detection.abnormal_score, 4)}</p>
        <p>Normal cutoff ≤ {fmt(p.detection.thresholds.normal_max, 4)} · abnormal cutoff ≥ {fmt(p.detection.thresholds.abnormal_min, 4)}</p>
        {p.diagnosis && <p>Cause score: {fmt(p.diagnosis.raw_score, 4)} · validation threshold: {fmt(p.diagnosis.threshold, 4)}</p>}
        {p.reason && <Notice>{p.reason}</Notice>}
        <p className="caption">Scores are not calibrated probabilities. Small grouped development samples do not establish reliable real-world performance. Physical location is unavailable.</p>
      </div>}
    </Panel>
    {result && <Panel title="Uploaded original measurements">
      <div className="toolbar"><label>Measurement channel <select value={channel} onChange={e => setChannel(e.target.value)}>
        {['angle', 'frequency', 'voltage_magnitude', 'current_magnitude', 'current_angle'].map(c => <option key={c} value={c}>{c}</option>)}
      </select></label></div>
      <p>{channel === 'frequency' ? 'Hz' : channel.includes('angle') ? result.angle_unit : 'Original source magnitude units'} · 1,800 samples · cursor inspection does not rerun diagnosis</p>
      <div className="chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={result.trace}>
        <CartesianGrid vertical={false} /><XAxis dataKey="elapsed_seconds" type="number" domain={[0, 60]} tickCount={7} tickFormatter={value => fmt(Number(value), 0)} /><YAxis domain={['auto', 'auto']} /><Tooltip />
        <ReferenceLine x={result.trace[cursor]?.elapsed_seconds} stroke="#a47c37" />
        <Line dataKey={channel} dot={false} isAnimationActive={false} stroke="#168f84" />
      </LineChart></ResponsiveContainer></div>
      <label>Uploaded sample <input aria-label="Uploaded sample" type="range" min={0} max={1799} value={cursor} onChange={e => setCursor(Number(e.target.value))} /></label>
      <p>Sample {cursor + 1} / 1800 · {fmt(result.trace[cursor].elapsed_seconds, 3)} seconds</p>
      <div className="table-scroll"><table><thead><tr><th>Measurement</th><th>Original value</th></tr></thead><tbody>
        {['angle', 'frequency', 'voltage_magnitude', 'current_magnitude', 'current_angle'].map(c => <tr key={c}><td>{c}</td><td>{fmt(result.trace[cursor][c], 6)}</td></tr>)}
      </tbody></table></div>
    </Panel>}
  </>;
}
