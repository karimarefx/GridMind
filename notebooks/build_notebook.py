"""Regenerate the portable tutorial notebook using the standard JSON format."""
import json
from pathlib import Path


def md(text):
    return {'cell_type':'markdown', 'metadata':{}, 'source':text.splitlines(True)}


def code(text):
    return {'cell_type':'code', 'metadata':{}, 'source':text.splitlines(True),
            'execution_count':None, 'outputs':[]}


cells = [
md('''# GridMind: sampled XGBoost forecasting baseline

Train three separate one-hour predictors for demand, solar and wind; derive net load.
**17,544 continuous sampled hours from 2023–2024**, with 168 warmup hours and chronological
**13,900 / 1,738 / 1,738** train/validation/test examples. Raw data stays unchanged.

This is an adapted PoC, not a reproduction of the paper's neural experiments.
The held-out periods cover about 72 days each and cannot establish year-round performance.
'''),
code('''# Colab only: clone the repository on first use and install dependencies.
# Local VS Code: select your prepared Python environment instead.
import sys
import subprocess
from pathlib import Path

IN_COLAB = 'google.colab' in sys.modules
if IN_COLAB:
    if not Path('/content/GridMind').exists():
        subprocess.run(['git', 'clone', 'https://github.com/karimarefx/GridMind.git', '/content/GridMind'], check=True)
    ROOT = Path('/content/GridMind')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', str(ROOT/'requirements-forecasting.txt')], check=True)
else:
    ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p/'src/gridmind/forecasting.py').exists())
sys.path.insert(0, str(ROOT/'src'))
print('Repository:', ROOT)
'''),
md('''## 1. Inspect the selected sample and freeze the split

Only the fixed sample is retained in memory. Validation rejects missing/nonfinite values,
duplicates, gaps, inconsistent net load and a proxy inconsistent with the documented local-hour formula.
UTC/hour-ending interpretation follows the repository; independent workbook provenance remains unresolved.
'''),
code('''import pandas as pd
import numpy as np
from gridmind.forecasting import load_sample, partition, run, predict_next, HISTORY

sample = load_sample(ROOT/'data/raw/ercot_2021_2024_hourly.csv')
split = partition(sample.index[HISTORY:])
display(sample.head())
display(sample.describe())
display(pd.DataFrame([{'split': s, 'examples': int((split == s).sum()),
                      'first_target_utc': split[split == s].index.min(),
                      'last_target_utc': split[split == s].index.max()} for s in split.unique()]))
'''),
md('''## 2. Fit the fixed baseline configuration

Each model uses only historical measurements. Demand/wind use 24-hour flattened windows;
solar uses 15 historical channels and a daily capacity-factor residual target, requiring 72 raw hours.
No weather, random row splitting or future capacities. Last-known capacity is used at inference.

CPU histogram trees; depth 4; learning rate 0.05; at most 500 trees; 30-round validation early stopping.
Test targets never control fitting. Rerun only for reproducibility, not to tune against test results.
This cell exports models and reports and checks model reload plus batch/request equivalence.
'''),
code('''metrics = run(ROOT)
display(metrics.query("group == 'all'").round(3))
'''),
md('''## 3. Compare held-out errors

MAE and RMSE are in MW. R² is not accuracy. Positive MAE skill means lower error than
last-observation persistence. Inspect component scores independently: net-load errors can cancel.
Solar daily capacity-factor persistence is an additional baseline.
'''),
code('''test = metrics.query("split == 'test' and group == 'all'")
display(test.pivot(index='target', columns='method', values='mae_mw').round(2))
display(metrics.query("split == 'test' and method == 'xgboost'").round(3))
'''),
code('''import matplotlib.pyplot as plt

predictions = pd.read_csv(ROOT/'reports/forecasting/predictions.csv', index_col=0, parse_dates=True)
week = predictions.loc[predictions['split'] == 'test'].iloc[:168]
fig, axes = plt.subplots(4, 1, figsize=(13, 12), sharex=True, layout='constrained')
for ax, kind in zip(axes, ['demand', 'solar', 'wind', 'net_load']):
    ax.plot(week.index, week[f'{kind}_actual'], label='Observed', linewidth=1.5)
    ax.plot(week.index, week[f'{kind}_xgboost'], label='Model prediction', linewidth=1)
    ax.plot(week.index, week[f'{kind}_persistence'], label='Persistence', alpha=.5)
    ax.set_ylabel(f'{kind} (MW)')
    ax.legend(loc='upper right')
axes[-1].set_xlabel('Target hour-ending label (UTC)')
fig.suptitle('First held-out test week — selected by time, not prediction quality')
fig.savefig(ROOT/'reports/forecasting/test_week.png', dpi=140)
plt.show()
'''),
md('''## 4. Forecast from history with the exported bundle

This is a replay of the first held-out hour. Only completed observations before its target label are passed.
The interface returns issue/target UTC timestamps, MW predictions and calculated net load.
Insufficient, missing or incompatible history raises a clear error rather than inventing values.
'''),
code('''target = split[split == 'test'].index[0]
history = sample.loc[sample.index < target].iloc[-168:]
forecast = predict_next(history, ROOT/'artifacts/forecasting')
display(pd.Series(forecast))
'''),
md('''## 5. Save results

The exported manifest records feature order, source checksum, sample boundaries, split counts,
versions, model sizes, clipping rates, runtimes and limitations. Model binaries are versioned with this PoC.
Colab requires the notebook and new source files to be pushed/uploaded before its clone step can use them.
Downloading this archive preserves artifacts when a Colab session ends.
'''),
code('''import json
manifest = json.loads((ROOT/'artifacts/forecasting/manifest.json').read_text())
display(pd.DataFrame(manifest['models']).T)
print('Total measured seconds:', round(manifest['total_seconds'], 2))
print('Limitations:')
print('\\n'.join('- '+s for s in manifest['limitations']))
if IN_COLAB:
    import shutil
    from google.colab import files
    export = ROOT/'forecasting_export'
    export.mkdir(exist_ok=True)
    for folder in ['artifacts/forecasting', 'reports/forecasting', 'src/gridmind']:
        shutil.copytree(ROOT/folder, export/folder, dirs_exist_ok=True)
    archive = shutil.make_archive(str(ROOT/'forecasting_export'), 'zip', export)
    files.download(archive)
''')]

notebook = {'nbformat':4, 'nbformat_minor':5,
            'metadata': {'kernelspec': {'display_name':'Python 3', 'language':'python', 'name':'python3'},
                         'language_info': {'name':'python', 'version':'3.12'}}, 'cells':cells}
for i, cell in enumerate(cells):
    cell['id'] = f'forecasting-{i:02d}'
Path(__file__).with_name('01_xgboost_forecasting.ipynb').write_text(json.dumps(notebook, indent=1), encoding='utf-8')
