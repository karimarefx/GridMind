# GridMind - Event Diagnosis Model

**Owner:** Karim  
**Last updated:** 30 October 2026  
**Status:** Proposed design following instructor feedback; training and evaluation are pending.

## Purpose

The event-diagnosis component identifies whether detected abnormal behavior comes from a **sensor problem** or a **physical grid event**. When the event is physical, it predicts the likely affected location from a sequence of electrical measurements.

Its main outputs are:

1. **Broad event category:** sensor problem or physical event.
2. **Physical-event location:** likely affected bus or line, depending on the selected training labels.
3. **Uncertainty:** an uncertain or unavailable result when the evidence is insufficient.

## Model design

The component has two stages:

```text
Electrical measurement sequence
             |
     Check and prepare data
             |
Stage 1: Random Forest or XGBoost
             |
    +--------+---------+
    |        |         |
 Sensor   Physical  Uncertain
 problem   event       |
    |        |     Report insufficient
 Report   Stage 2:     evidence
 category   LSTM
             |
     Likely bus or line
             |
     Diagnosis for GridMind
```

### Stage 1 - Sensor or physical classification

Random Forest and XGBoost are the proposed candidates. Both learn relationships between numerical features and the event category. They will be compared using the same held-out event episodes; the final classifier has not been selected.

The input features may describe measurement levels, recent changes, and statistics over a time window. For example, they may capture a sudden voltage drop and whether related signals also changed. The exact feature set depends on the available measurements.

This stage answers **sensor or physical**, rather than naming a specific physical event such as a generator trip or line fault.

### Stage 2 - Physical-event localization

If Stage 1 predicts a physical event, an LSTM processes the measurement sequence. It learns how signals change over time and uses those patterns to predict the event location.

The location output must match the available labels. A model trained with bus labels predicts a bus; a model trained with line labels predicts a line. Whether the prototype supports buses, lines, or both remains to be decided.

Sensor-classified events do not enter this stage. The current design does not locate faulty sensors.

An LSTM does not automatically understand grid connections. The use of topology as model input or additional context remains a design decision.

### Uncertain results

When measurements are missing, conflicting, or insufficient, the component should be able to return an uncertain category or location. The decision thresholds still require development and validation. A model score should not be presented as a reliable confidence percentage without checking its calibration.

## Inputs

| Input | Description |
|---|---|
| Electrical measurement sequence | Readings across a defined time window; possible signals include voltage, current, and active/reactive power, subject to data availability |
| Timestamps | Align the readings and identify the observation window |
| Component IDs | Map measurements and predicted locations to the correct buses or lines |
| Original observations | Preserve the readings received before reconstruction |
| Reconstructed values and flags | Supply estimates for missing entries while identifying which values were estimated |
| Available topology and equipment status | Provide network context and location mapping; their exact use is not finalized |

The measurement channels, units, sampling rate, window length, component ordering, and missing-value treatment must be agreed before training and integration.

## Outputs

| Output | Description |
|---|---|
| Event category | Sensor problem, physical event, or uncertain |
| Physical-event location | Likely bus/line ID when applicable; otherwise unavailable or uncertain |
| Observation window | Start and end timestamps of the measurements used |
| Diagnosis time | When the result was produced; this is different from estimating the exact event start time |
| Reliability information | Data limitations and uncertainty; validated confidence if implemented |

## Relation to GridMind

```text
Grid measurements + available network context
                    |
    Reconstruction outputs and estimate flags
                    |
           Event diagnosis component
                    |
        Event category + physical location
                    |
     Downstream analysis and operator dashboard
```

The component uses available measurements and flagged reconstruction outputs to describe the current abnormal behavior. Original observations remain available so reconstruction does not silently replace the evidence used for diagnosis.

The diagnosis can be passed to risk assessment, corrective-action modules, and the dashboard. Those components perform their own tasks; event diagnosis does not predict propagation, choose actions, or operate equipment.

The normal-operation boundary is still unresolved. Either an earlier detector supplies abnormal windows, or classification must include a normal class. A sensor-versus-physical classifier alone should not be treated as a complete detector for every incoming window.

## Dataset requirements

The final dataset has not been selected. The two stages require:

- Labeled sensor-problem and physical-event examples for Stage 1.
- Physical-event measurement sequences with location labels for Stage 2.
- Suitable normal examples to evaluate false alarms if event detection is included.

PSML is a candidate for physical-event sequences and location labels. The previously inspected physical-event loader does not supply the full sensor-versus-physical classification task. Compatible sensor-problem examples would still be needed. Controlled sensor corruptions are a possible approach, but their realism and labels must be checked.

Reconstruction and diagnosis should be evaluated using the same event episodes for integration. Independent episodes and related variants must be separated before creating overlapping windows or fitting preprocessing, to avoid information leaking between training and testing.

## Example behavior

| Scenario | Intended result |
|---|---|
| An isolated abnormal reading while related measurements remain consistent | Sensor problem; physical localization is skipped |
| A physical disturbance changes several measurements over time | Physical event; the LSTM predicts a supported bus or line location |
| Missing or conflicting readings prevent a reliable decision | Uncertain category or location, with the data limitation reported |

These are illustrative scenarios, not measured results or fixed rules. A single unusual reading does not always mean a sensor fault, and changes across several signals do not by themselves prove a physical event.

## Evaluation

- **Stage 1:** per-class precision and recall, macro-F1, and a confusion matrix.
- **Stage 2:** location accuracy on physical events, using the agreed bus/line targets.
- **Complete pipeline:** whether a physical event is both routed correctly and located correctly. A physical event misclassified as sensor must count as a pipeline failure.
- **Reconstruction effect:** compare complete observations, missing observations with a defined simple treatment, and reconstructed observations with flags on the same held-out episodes.
- **Practical behavior:** runtime, uncertainty handling, and performance under relevant noise and missingness. Evaluate false alarms when normal-operation detection is included.

## Current boundaries and pending decisions

The current scope covers broad category classification and physical-event localization. Specific physical subtypes, faulty-sensor localization, cyberattack diagnosis, and exact event-onset estimation are outside this design.

The remaining decisions are the main dataset, supported scenarios, normal-operation handling, feature schema, sequence settings, location labels, and uncertainty thresholds.

No final classifier selection, completed GridMind training, or achieved performance is claimed yet.
