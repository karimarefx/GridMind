"""Sampled, rolling one-hour ERCOT forecasting. No target measurements in inputs."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

TARGETS = {'demand': 'total_load', 'solar': 'solar_generation', 'wind': 'wind_generation'}
SAMPLE_START = '2023-01-01 06:00:00+00:00'
SAMPLE_END = '2025-01-01 06:00:00+00:00'
HISTORY = 168  # Common eligibility for every model and weekly baseline.


def validate(frame: pd.DataFrame) -> None:
    required = ['wind_generation', 'wind_installed', 'total_load', 'solar_generation',
                'solar_installed', 'net_load', 'clear_sky_proxy']
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError('Expected timezone-aware UTC hourly timestamps')
    if len(frame) < 2 or not frame.index.is_monotonic_increasing or frame.index.has_duplicates:
        raise ValueError('History must be ordered and unique')
    if not np.all(np.diff(frame.index.as_unit('ns').asi8) == 3_600_000_000_000):
        raise ValueError('Hourly gaps are unsupported; no interpolation is performed')
    values = frame[required].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Missing, nonfinite, or negative data')
    for kind in ['solar', 'wind']:
        if (frame[f'{kind}_installed'] <= 0).any():
            raise ValueError('Capacity must be positive')
        if (frame[f'{kind}_generation'] > 1.05 * frame[f'{kind}_installed']).any():
            raise ValueError('Generation exceeds capacity allowance')
    if not np.allclose(frame.net_load, frame.total_load-frame.solar_generation-frame.wind_generation, atol=1e-5):
        raise ValueError('Inconsistent net-load arithmetic')
    local = frame.index.tz_convert('America/Chicago')
    proxy = np.maximum(np.sin(np.pi * (local.hour.to_numpy()-6)/12), 0)
    if not np.allclose(frame.clear_sky_proxy, proxy, atol=1e-6):
        raise ValueError('Proxy differs from the documented local-hour formula')


def load_sample(path: Path) -> pd.DataFrame:
    # Read only the selected contiguous sample into the experiment frame.
    chunks = []
    for chunk in pd.read_csv(path, chunksize=2048):
        chunk['time'] = pd.to_datetime(chunk.time, utc=True, errors='raise')
        chunks.append(chunk.loc[(chunk.time >= pd.Timestamp(SAMPLE_START)) &
                                (chunk.time < pd.Timestamp(SAMPLE_END))])
    frame = pd.concat(chunks).set_index('time')
    validate(frame)
    if len(frame) != 17544:
        raise ValueError(f'Expected 17,544 sampled hourly rows; found {len(frame)}')
    return frame


def calendar(index: pd.DatetimeIndex) -> pd.DataFrame:
    local = index.tz_convert('America/Chicago')
    # Fixed calendar vocabulary, not fitted on held-out observations.
    out = {}
    for name, values, vocabulary in [('hour', local.hour, range(24)),
                                     ('day', local.day, range(1, 32)),
                                     ('month', local.month, range(1, 13)),
                                     ('year', local.year, range(2021, 2025))]:
        for value in vocabulary:
            out[f'{name}_{value}'] = (values == value).astype('float32')
    return pd.DataFrame(out, index=index)


def features(frame: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Rows indexed by target time; every measured input is at target-1 or older.

    Also accepts a final placeholder target row for inference. The placeholder's
    observations are never consumed by that row's feature vector.
    """
    cal = calendar(frame.index)
    if kind == 'solar':
        cf = frame.solar_generation / frame.solar_installed
        base = pd.DataFrame({'cf': cf, 'proxy': frame.clear_sky_proxy}, index=frame.index)
        for lag in [1, 2, 24, 48]:
            base[f'cf_lag{lag}'] = cf.shift(lag)
            base[f'proxy_lag{lag}'] = frame.clear_sky_proxy.shift(lag)
        local = frame.index.tz_convert('America/Chicago')
        base['hour_sin'] = np.sin(2*np.pi*local.hour/24)
        base['hour_cos'] = np.cos(2*np.pi*local.hour/24)
        base['doy_sin'] = np.sin(2*np.pi*local.dayofyear/366)
        base['doy_cos'] = np.cos(2*np.pi*local.dayofyear/366)
        base['daylight'] = (frame.clear_sky_proxy > 1e-6).astype(float)
    else:
        cols = [TARGETS[kind]] + (['wind_installed'] if kind == 'wind' else [])
        base = pd.concat([frame[cols], cal], axis=1)
    return pd.concat([base.shift(lag).add_suffix(f'_tminus{lag}')
                      for lag in range(24, 0, -1)], axis=1).astype('float32')


def partition(index: pd.DatetimeIndex) -> pd.Series:
    n = len(index)
    labels = np.full(n, 'test', dtype=object)
    labels[:int(n*.8)] = 'train'
    labels[int(n*.8):int(n*.9)] = 'validation'
    return pd.Series(labels, index=index, name='split')


def postprocess(raw, frame: pd.DataFrame, kind: str):
    if kind == 'demand':
        return np.maximum(raw, 0)
    cap = frame[f'{kind}_installed'].shift(1).to_numpy()
    if kind == 'solar':
        daily_cf = (frame.solar_generation/frame.solar_installed).shift(24).to_numpy()
        return np.clip(daily_cf + raw, 0, 1.05) * cap
    return np.clip(raw, 0, 1.05*cap)


def scores(actual, predicted):
    return {'mae_mw': float(mean_absolute_error(actual, predicted)),
            'rmse_mw': float(np.sqrt(mean_squared_error(actual, predicted))),
            'r2': float(r2_score(actual, predicted)) if len(actual) > 1 else None,
            'n': len(actual)}


def predict_next(history: pd.DataFrame, bundle: Path) -> dict:
    """Forecast from observed history only, using the exported ordered schema."""
    validate(history)
    if len(history) < 72:
        raise ValueError('At least 72 consecutive hourly observations are required')
    manifest = json.loads((bundle/'manifest.json').read_text())
    target = history.index[-1] + pd.Timedelta(hours=1)
    extended = history.reindex(history.index.append(pd.DatetimeIndex([target])))
    result = {'issued_at_utc': history.index[-1].isoformat(), 'target_time_utc': target.isoformat(),
              'horizon_hours': 1, 'region_id': 'ERCOT', 'provenance': 'Model prediction',
              'model_version': 'xgboost-sample-v1', 'data_quality_status': 'complete'}
    for kind in TARGETS:
        model = XGBRegressor()
        model.load_model(bundle/f'{kind}.json')
        x = features(extended, kind).iloc[[-1]]
        if list(x.columns) != manifest['features'][kind] or x.isna().any().any():
            raise ValueError('Invalid feature schema/history')
        raw = float(model.predict(x)[0])
        if kind == 'solar':
            cf = history.solar_generation.iloc[-24]/history.solar_installed.iloc[-24]
            value = np.clip(cf+raw, 0, 1.05)*history.solar_installed.iloc[-1]
        elif kind == 'wind':
            value = np.clip(raw, 0, 1.05*history.wind_installed.iloc[-1])
        else:
            value = max(raw, 0)
        result[f'{kind}_mw'] = float(value)
    result['net_load_mw'] = result['demand_mw']-result['solar_mw']-result['wind_mw']
    return result


def run(root: Path, n_estimators: int = 500) -> pd.DataFrame:
    started = time.perf_counter()
    source = root/'data/raw/ercot_2021_2024_hourly.csv'
    frame = load_sample(source)
    eligible = frame.index[HISTORY:]
    splits = partition(eligible)
    bundle = root/'artifacts/forecasting'
    reports = root/'reports/forecasting'
    bundle.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    splits.to_csv(reports/'split_manifest.csv', index_label='target_time_utc')
    predictions = pd.DataFrame(index=eligible)
    predictions['split'] = splits
    records, schemas, models_info = [], {}, {}
    params = dict(n_estimators=n_estimators, max_depth=4, learning_rate=.05,
                  subsample=.8, colsample_bytree=.8, objective='reg:squarederror',
                  tree_method='hist', n_jobs=4, random_state=42,
                  eval_metric='rmse', early_stopping_rounds=30)
    for kind, column in TARGETS.items():
        x = features(frame, kind).loc[eligible]
        y = frame[column].copy()
        if kind == 'solar':
            cf = frame.solar_generation/frame.solar_installed
            y = cf-cf.shift(24)
        y = y.loc[eligible]
        if not np.isfinite(x.to_numpy()).all() or not np.isfinite(y).all():
            raise ValueError('Nonfinite supervised examples')
        train, val = splits.eq('train'), splits.eq('validation')
        model = XGBRegressor(**params)
        tick = time.perf_counter()
        model.fit(x.loc[train], y.loc[train], eval_set=[(x.loc[val], y.loc[val])], verbose=False)
        elapsed = time.perf_counter()-tick
        # Final test is evaluated once after this fixed configuration is fitted.
        raw = model.predict(x)
        raw_full = pd.Series(raw, index=eligible).reindex(frame.index).to_numpy()
        predicted = pd.Series(postprocess(raw_full, frame, kind), index=frame.index).loc[eligible]
        model.save_model(bundle/f'{kind}.json')
        reloaded = XGBRegressor()
        reloaded.load_model(bundle/f'{kind}.json')
        np.testing.assert_allclose(raw, reloaded.predict(x), rtol=0, atol=0)
        schemas[kind] = list(x.columns)
        predictions[f'{kind}_actual'] = frame.loc[eligible, column]
        predictions[f'{kind}_xgboost'] = predicted
        for label, lag in [('persistence', 1), ('daily', 24), ('weekly', 168)]:
            predictions[f'{kind}_{label}'] = frame[column].shift(lag).loc[eligible]
        if kind == 'solar':
            predictions['solar_daily_cf'] = (cf.shift(24).clip(0, 1.05)*frame.solar_installed.shift(1)).loc[eligible]
        if kind == 'solar':
            unclipped = (cf.shift(24).loc[eligible].to_numpy()+raw)*frame.solar_installed.shift(1).loc[eligible].to_numpy()
        else:
            unclipped = raw
        models_info[kind] = {'best_iteration': model.best_iteration, 'training_seconds': elapsed,
                             'features': len(x.columns), 'model_bytes': (bundle/f'{kind}.json').stat().st_size,
                             'clipping_fraction': float(np.mean(~np.isclose(unclipped, predicted)))}
        print(kind, models_info[kind], flush=True)
        del x
    methods = ['xgboost', 'persistence', 'daily', 'weekly']
    predictions['net_load_actual'] = frame.loc[eligible, 'net_load']
    for method in methods:
        predictions[f'net_load_{method}'] = predictions[f'demand_{method}']-predictions[f'solar_{method}']-predictions[f'wind_{method}']
    thresholds = {}
    for kind, col in {**TARGETS, 'net_load': 'net_load'}.items():
        actual = predictions[f'{kind}_actual']
        train_actual = actual.loc[splits.eq('train')]
        peak = float(train_actual.quantile(.95))
        ramp_series = frame[col].diff().abs().loc[eligible]
        ramp = float(ramp_series.loc[splits.eq('train')].quantile(.95))
        thresholds[kind] = {'peak_mw': peak, 'absolute_ramp_mw': ramp}
        kind_methods = methods + (['daily_cf'] if kind == 'solar' else [])
        for split in ['validation', 'test']:
            groups = {'all': splits.eq(split),
                      'peak': splits.eq(split)&actual.ge(peak),
                      'ramp': splits.eq(split)&ramp_series.ge(ramp)}
            local = eligible.tz_convert('America/Chicago')
            for season, months in {'winter':[12,1,2], 'spring':[3,4,5], 'summer':[6,7,8], 'autumn':[9,10,11]}.items():
                groups[season] = splits.eq(split)&np.isin(local.month, months)
            if kind == 'solar':
                groups['daylight'] = splits.eq(split)&frame.loc[eligible, 'clear_sky_proxy'].gt(1e-6)
            for group, mask in groups.items():
                if not mask.any():
                    continue
                baseline_mae = mean_absolute_error(actual[mask], predictions.loc[mask, f'{kind}_persistence'])
                for method in kind_methods:
                    row = scores(actual[mask], predictions.loc[mask, f'{kind}_{method}'])
                    row['mae_skill_vs_persistence'] = 1-row['mae_mw']/baseline_mae if baseline_mae else None
                    records.append(dict(target=kind, split=split, group=group, method=method, **row))
    metrics = pd.DataFrame(records)
    metrics.to_csv(reports/'metrics.csv', index=False)
    predictions.to_csv(reports/'predictions.csv', index_label='target_time_utc')
    manifest = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'sample_start_inclusive': SAMPLE_START, 'sample_end_exclusive': SAMPLE_END,
                'sample_rows': len(frame), 'warmup_rows': HISTORY, 'eligible_examples': len(eligible),
                'split_policy': 'chronological 80/10/10 of common eligible targets, floor boundaries',
                'splits': {s: {'n': int((splits == s).sum()), 'first_target': str(eligible[splits == s][0]),
                               'last_target': str(eligible[splits == s][-1])} for s in splits.unique()},
                'features': schemas, 'models': models_info, 'parameters': params,
                'thresholds_from_training': thresholds, 'python': platform.python_version(),
                'versions': {p: importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','xgboost']},
                'total_seconds': time.perf_counter()-started,
                'limitations': ['UTC hour-ending semantics follow supplied documentation, not an independent workbook audit.',
                    'Assumes completed source hour is available immediately at issue time.',
                    'Last-observed installed capacity used for clipping/reconstruction; historical publication timing unverified.',
                    'Uniform solar weights; no weather; no neural-model reproduction.',
                    'Held-out windows do not cover all seasons; no full-year generalization claim.']}
    (bundle/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    # A real held-out replay also verifies exported inference against batch features.
    target = eligible[splits.eq('test')][0]
    fixture = predict_next(frame.loc[frame.index < target].iloc[-168:], bundle)
    for kind in TARGETS:
        np.testing.assert_allclose(fixture[f'{kind}_mw'], predictions.loc[target, f'{kind}_xgboost'], rtol=1e-6)
    (reports/'example_forecast.json').write_text(json.dumps(fixture, indent=2), encoding='utf-8')
    (reports/'run_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    lines = ['# Sampled XGBoost baseline results', '',
             f'Sampled rows: {len(frame):,}; common eligible target hours: {len(eligible):,}.', '',
             '| Split | Examples | First target (UTC) | Last target (UTC) |',
             '|---|---:|---|---|']
    for name, item in manifest['splits'].items():
        lines.append(f"| {name} | {item['n']:,} | {item['first_target']} | {item['last_target']} |")
    lines += ['', '## Final test (all hours)', '',
              '| Target | Model MAE (MW) | Persistence MAE (MW) | Daily MAE (MW) | Weekly MAE (MW) | Model RMSE (MW) | MAE skill vs persistence |',
              '|---|---:|---:|---:|---:|---:|---:|']
    final = metrics.query("split == 'test' and group == 'all'")
    for kind in [*TARGETS, 'net_load']:
        rows = final.loc[final.target.eq(kind)].set_index('method')
        learned = rows.loc['xgboost']
        lines.append(f"| {kind} | {learned.mae_mw:.2f} | {rows.loc['persistence','mae_mw']:.2f} | {rows.loc['daily','mae_mw']:.2f} | {rows.loc['weekly','mae_mw']:.2f} | {learned.rmse_mw:.2f} | {learned.mae_skill_vs_persistence:.1%} |")
    lines += ['', 'Positive skill means lower MAE than persistence. These are measured held-out errors, not percentage accuracy.',
              '', '## Validation and reproducibility', '',
              'Validation alone controls early stopping. The single fixed configuration was frozen before test evaluation. '
              'Native model reload predictions matched exactly; the exported one-hour interface matched the first test prediction. '
              'Complete per-model results, daylight/season/peak/ramp subsets and baseline scores are in metrics.csv.', '',
              f"Measured pipeline runtime: {manifest['total_seconds']:.2f} seconds (excludes environment setup).", '',
              '## Limitations', '']
    lines += ['- '+item for item in manifest['limitations']]
    (reports/'summary.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    print(run(args.root).query("split == 'test' and group == 'all'").to_string(index=False))
