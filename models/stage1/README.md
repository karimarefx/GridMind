# Experimental Stage 1 model

This is the locally trained detector plus the frozen v3 cause model. It accepts
1,800 original 30 Hz measurements with the five required measurement channels.
The model is executable joblib serialization; load only this pinned trusted file.
The service verifies its checksum and scikit-learn version before loading it.

The included evaluation is grouped development, not independent final validation.
The complete confidence policy returned only eight normal decisions from 62
inputs and no physical/timing diagnoses. This is an experimental software PoC.
See `reports/diagnosis/stage1_summary.md` for data provenance, outcomes and limits.
The deployment manifest intentionally records `generalization_validated: false`.

No source archives, original measurement CSVs or user uploads are included here.
