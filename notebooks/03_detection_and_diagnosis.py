# %% [markdown]
# # Complete Stage 1: normal detection followed by cause diagnosis
# This notebook explains the new two-stage upload prototype. It reads the frozen
# measured result; it does not retrain by default. The current complete policy
# returned only eight normal decisions from 62 inputs and no cause diagnoses.
# The software is implemented; useful independent diagnostic performance is pending.

# %%
from pathlib import Path
import sys
import json
import joblib
import pandas as pd
from IPython.display import display
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p/'src/gridmind/stage1.py').exists())
sys.path.insert(0, str(ROOT/'src'))
from gridmind import stage1
from gridmind.api import load_model
MODEL_DIRECTORY = ROOT/'models/stage1'
bundle = load_model(MODEL_DIRECTORY)
print('Trusted packaged model:', bundle['version'])

# %% [markdown]
# ## 1. Data used
# Thirty source-labeled ambient examples from GESL Providers 9/10 join the existing
# 24 physical and eight timing recordings. Compatible source tags and complete
# measurements support the labels; they do not independently prove healthy sensors.
# Same-provider/month normal and physical records share a family. Three timing
# families remain a research limitation. Measurement CSVs are kept outside Git.

# %%
evaluation = json.loads((MODEL_DIRECTORY/'evaluation.json').read_text())
display(pd.Series({k: evaluation[k] for k in ['records','normal_records','abnormal_records','families','evidence_role']}))

# %% [markdown]
# ## 2. Training and evaluation
# Model A is a 300-tree Random Forest using the same 23 features explained in
# notebook 02. Normal labels form one class; physical and timing form abnormal.
# Inner grouped validation chooses leaf size and separate normal/abnormal score
# cutoffs. Scores between usable cutoffs return uncertain. Weights balance class
# and then source family. Model B is trained without the outer test families when
# evaluating; deployment retains the frozen v3 cause classifier.
# New training requires local source manifests and creates a fresh run directory.
# Keep the protocol fixed and preserve failed results.

# %%
RUN_TRAINING = False
if RUN_TRAINING:
    from datetime import datetime, timezone
    output = ROOT/'artifacts/diagnosis'/('stage1-notebook-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    stage1.train(ROOT/'data/diagnosis/stage1/normal_manifest.json', ROOT/'data/diagnosis/context/manifest.json',
                 ROOT/'artifacts/diagnosis/gesl-measurement-context-rf-003',
                 ROOT/'reports/diagnosis/stage1_protocol.json', output)
    print('New experimental run:', output)
else:
    print('No retraining; reading the packaged measured evaluation.')

# %% [markdown]
# ## 3. Detector performance and complete pipeline performance differ
# Forced detection got 60/62 right. With uncertainty, only 10/32 abnormal inputs
# were flagged, eight normal inputs were accepted, and 44 remained uncertain at
# detection. After the cause classifier, the full system returned only the eight
# normal decisions, with 54 uncertain. The matrix below includes those abstentions.
# This did not meet the declared development sensitivity target.

# %%
display(pd.Series(evaluation['detector'], dtype=object))
display(pd.DataFrame(evaluation['pipeline']['confusion_matrix'],
                     index=['actual normal','actual physical','actual timing'],
                     columns=['normal','physical','timing','uncertain']))
display(pd.Series({k:v for k,v in evaluation['pipeline'].items() if k not in ['confusion_matrix','row_order','column_order']}))

# %% [markdown]
# ## 4. Predict your own prepared window
# Set INPUT_CSV to a local seven-column CSV with 1800 original 30 Hz samples.
# Both angle columns must use ANGLE_UNIT. The function validates data before
# calculating features. It calls the cause classifier only if Model A returns
# abnormal. Your upload has no supplied ground-truth class.
# Trying a training recording demonstrates software behavior, not held-out accuracy.

# %%
INPUT_CSV = None  # Example: Path(r'D:\my_measurements\prepared_window.csv')
ANGLE_UNIT = 'degree'
if INPUT_CSV is not None:
    prediction, original_trace = stage1.predict(bundle, Path(INPUT_CSV), ANGLE_UNIT)
    display(pd.Series(prediction))
else:
    print('Set INPUT_CSV to run a prediction; no data file has been opened.')

# %% [markdown]
# ## 5. Interface connection
# From the repository root, install requirements-api-lock.txt, build frontend,
# set PYTHONPATH to src, and run `python -m gridmind.api`.
# Open http://127.0.0.1:8000 and select Event diagnosis. The API loads this trusted
# bundle once. Uploaded files are validated and processed in temporary storage,
# then deleted. The interface displays original measurements, both-stage scores
# and uncertainty. It does not train on upload or assume a correct answer.
# See reports/diagnosis/stage1_summary.md for the remaining research work.
