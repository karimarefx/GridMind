"""Package existing, locally measured research outputs. No training or inference.

Run from any directory. Source CSV precision is preserved; net load is explicitly
recalculated from the packaged component predictions to avoid rounding conflicts.
Future Colab runs must provide the same contracts and accurate origin metadata.
"""
import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'frontend/public/data'
REPORTS = ROOT / 'reports/forecasting'

def stamp(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).isoformat()

def write(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))

def main():
    run = json.loads((REPORTS / 'run_manifest.json').read_text(encoding='utf-8'))
    source = ROOT / 'data/raw/ercot_2021_2024_hourly.csv'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == run['source_sha256'], 'Source checksum mismatch'
    selected = [r for r in rows(REPORTS / 'predictions.csv') if r['split'] == 'test'][:168]
    assert len(selected) == 168
    version = json.loads((REPORTS / 'example_forecast.json').read_text())['model_version']
    forecasts, baselines = [], []
    for i, row in enumerate(selected):
        target = datetime.fromisoformat(row['target_time_utc'])
        issue = target - timedelta(hours=1)
        values = {f'{k}_mw': float(row[f'{k}_xgboost']) for k in ['demand', 'solar', 'wind']}
        values['net_load_mw'] = values['demand_mw'] - values['solar_mw'] - values['wind_mw']
        forecasts.append(dict(forecast_id=f'forecast-{i:03}', issued_at_utc=issue.isoformat(), target_time_utc=target.isoformat(), horizon_hours=1, region_id='ERCOT', history_start_utc=(issue-timedelta(hours=167)).isoformat(), history_end_utc=issue.isoformat(), history_rows=168, split='test', model_version=version, run_id='local-sampled-run', data_quality_status='complete', capacity_policy='Last-observed installed capacity at issue time', provenance_kind='precomputed_prediction', **values))
        for kind in ['demand', 'solar', 'wind', 'net_load']:
            for method in ['persistence', 'daily', 'weekly', 'daily_cf']:
                key = f'{kind}_{method}'
                if key in row:
                    baselines.append(dict(forecast_id=f'forecast-{i:03}', target_time_utc=target.isoformat(), target=kind, method=method, value_mw=float(row[key]), status='available'))
    start = datetime.fromisoformat(forecasts[0]['history_start_utc'])
    end = datetime.fromisoformat(forecasts[-1]['target_time_utc'])
    observations = []
    for row in rows(source):
        instant = datetime.fromisoformat(stamp(row['time']))
        if start <= instant <= end:
            observations.append(dict(time=instant.isoformat(), **{k: float(v) for k, v in row.items() if k != 'time'}))
    assert len(observations) == 336
    metrics = [{k: (int(v) if k == 'n' else float(v) if k in ['mae_mw', 'rmse_mw', 'r2', 'mae_skill_vs_persistence'] and v else None if not v else v) for k, v in row.items()} for row in rows(REPORTS / 'metrics.csv')]
    write('forecasting/forecast_predictions.json', forecasts)
    write('forecasting/forecast_observations.json', observations)
    with (OUT / 'forecasting/forecast_observations.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(observations[0]))
        writer.writeheader()
        writer.writerows(observations)
    write('forecasting/forecast_baselines.json', baselines)
    write('evaluation/forecast_metrics.json', metrics)
    write('evaluation/run_manifest.json', run)
    for name in ['metrics.csv', 'split_manifest.csv', 'summary.md']:
        target = OUT / 'evaluation' / name
        target.write_bytes((REPORTS / name).read_bytes())
    write('diagnosis/event_episodes.json', [])
    write('diagnosis/diagnosis_predictions.json', [])
    write('diagnosis/diagnosis_evaluation.json', {'status': 'unavailable', 'reason': 'No inspected diagnosis dataset, trained classifier, or held-out export has been supplied. Channels, cadence, defensible labels, and parent-family splits remain unresolved.'})
    write('catalog.json', {'schema_version': '1', 'bundle_id': 'gridmind-local-v1', 'default_scenario': 'first-week', 'scenarios': [
        {'id': 'first-week', 'title': 'First held-out week', 'description': '168 genuine hourly forecasts from the first test week. The laboratory is a separate authored illustration.', 'forecast_start': 0, 'forecast_end': 167, 'laboratory_id': 'illustrative14-v1'},
        {'id': 'day-two', 'title': 'Day two · replay focus', 'description': 'A 24-hour subset of the same held-out export. No additional training or inference.', 'forecast_start': 24, 'forecast_end': 47, 'laboratory_id': 'illustrative14-v1'}]})
    manifest = {'schema_version': '1', 'bundle_id': 'gridmind-local-v1', 'artifact_version': '1', 'run_id': 'local-sampled-run', 'model_version': version, 'exported_at_utc': datetime.now(timezone.utc).isoformat(), 'dataset_id': 'ercot-2021-2024-sampled', 'source_id': 'supplied-ercot-csv', 'source_sha256': run['source_sha256'], 'origin': 'Existing locally executed XGBoost run; not a Colab execution', 'units': {'power': 'MW', 'capacity': 'MW', 'proxy': 'dimensionless'}, 'limitations': run['limitations'] + ['CSV component precision retained; packaged net load calculated from those components.', 'Illustrative fixtures await model-owner review.'], 'capabilities': {'forecasting': 'available', 'diagnosis': 'blocked', 'reconstruction': 'simulated', 'cascade': 'simulated', 'actions': 'simulated'}, 'files': []}
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.name != 'bundle_manifest.json':
            manifest['files'].append({'path': path.relative_to(OUT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'artifact_version': '1'})
    write('bundle_manifest.json', manifest)
    print(f'Packaged {len(forecasts)} genuine predictions, {len(observations)} observations; diagnosis blocked.')

if __name__ == '__main__':
    main()
