import { useEffect, useState } from 'react';
import { fmt, Notice, Panel } from '../components/Common';
type Evaluation = { records: number; normal_records: number; abnormal_records: number; evidence_role: string;
  detector: { abnormal_recall_after_policy: number; normal_false_alarm_rate: number; uncertain_count: number; forced_confusion_matrix: number[][] };
  pipeline: { coverage: number; confusion_matrix: number[][] }; limitations: string[] };
export function Stage1Evaluation() {
  const [data, setData] = useState<Evaluation | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/data/diagnosis/stage1_evaluation.json', { signal: controller.signal }).then(r => r.ok ? r.json() : null)
      .then(value => { if (value?.pipeline && !controller.signal.aborted) setData(value); }).catch(() => {});
    return () => controller.abort();
  }, []);
  const returnedCauses = data?.pipeline.confusion_matrix.reduce((count, row) => count + row[1] + row[2], 0);
  return <Panel title="Complete Stage 1 evaluation" eyebrow="Grouped development — both models">
    {!data ? <Notice>Combined detection/diagnosis evaluation unavailable.</Notice> : <>
      <Notice title="Experimental — not independently validated">{data.evidence_role}. Low coverage means many inputs receive no diagnosis.</Notice>
      <p>{data.records} inputs: {data.normal_records} source-labeled ambient and {data.abnormal_records} abnormal.</p>
      <p>Detector abnormal recall after uncertainty: {fmt(data.detector.abnormal_recall_after_policy * 100, 2)}% · normal false alarms: {fmt(data.detector.normal_false_alarm_rate * 100, 2)}% · detector uncertain: {data.detector.uncertain_count}</p>
      <p>Complete-pipeline coverage was {fmt(data.pipeline.coverage * 100, 2)}%. The pipeline returned {returnedCauses} physical or sensor error diagnoses in this evaluation.</p>
      <div className="table-scroll"><table><caption>Complete pipeline: rows actual; uncertainty included</caption>
        <thead><tr><th>Actual</th><th>Normal</th><th>Physical</th><th>Timing</th><th>Uncertain</th></tr></thead>
        <tbody>{data.pipeline.confusion_matrix.map((row, i) => <tr key={i}><th>{['Normal', 'Physical', 'Timing'][i]}</th>{row.map((value, j) => <td key={j}>{value}</td>)}</tr>)}</tbody>
      </table></div>
      <details><summary>Data and validation limits</summary><ul>{data.limitations.map(text => <li key={text}>{text}</li>)}</ul></details>
    </>}
  </Panel>;
}
