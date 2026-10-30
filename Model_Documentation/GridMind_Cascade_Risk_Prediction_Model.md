# GridMind — Cascade Risk Prediction Model

**Project:** GridMind: A Topology-Aware AI Decision-Support Platform for Resilient Renewable Power Grids  
**Module:** Model 4 — Cascade Risk Prediction  
**Document type:** Project module specification and paper-grounded design reference  
**Research foundation:** Sevak, Jadhav, and Bui, *Physics-Informed Graph Neural Jump ODEs for Cascading Failure Prediction in Power Grids* (PI-GN-JODE), arXiv:2603.20838v1, 21 March 2026.  
**Status:** Planned GridMind functionality, **not** an implemented or validated GridMind model.

> **Source and scope rule:** This document separates (1) GridMind requirements already discussed, (2) what the PI-GN-JODE paper actually does and reports, and (3) proposed implementation choices for GridMind. Published paper results are **not** GridMind results.

---

## 1. Executive summary

The Cascade Risk Prediction module answers:

**“Given the grid's electrical state and an initiating outage, what is likely to become critical next, how might failures propagate, and how severe could the consequences be?”**

Its job is **not** just to detect that the first line has failed. GridMind's simulated SCADA-like telemetry and Event Diagnosis module can already identify an observed first outage. The Cascade Risk module analyzes **what may happen afterward**.

It also supports proactive **what-if contingency screening**: while the grid is still operating, an engineer or automated screening process can *hypothetically* remove a line and ask what subsequent failures and lost load might occur. This allows pre-incident preparation **without claiming to predict when the initial line will fail**.

Expected core outputs:

1. Failure likelihood for each transmission branch after the initiating outage.
2. Likelihood that each bus loses service or becomes isolated/affected.
3. Overall **safe/unsafe** severity classification.
4. **Demand Not Served (DNS)** as a fraction of total demand.
5. Operational ranking of vulnerable next components and an overall **risk indicator**, derived for the GridMind dashboard.
6. Optionally, a round-by-round trajectory of the cascading failure (a more difficult phase).

GridMind remains a **software-only, human-in-the-loop decision-support prototype**. It does not control breakers or physical equipment.

## 2. Position within the complete GridMind system

**Canonical GridMind workflow:**

```text
Simulated grid / operating profiles
    ↓
pandapower AC power flow → SCADA-like telemetry
    ↓
Observe → Reconstruct missing telemetry → Forecast demand / solar / wind
    ↓
Diagnose physical outages vs. bad or manipulated measurements
    ↓
CASCADE RISK PREDICTION  ← current or forecast grid state + initiating outage
    ↓
Highlight vulnerable lines and buses + quantify possible lost load
    ↓
Generate and rank corrective-action candidates
    ↓
pandapower physics-validation of each candidate action
    ↓
Dashboard warning, comparison and evidence → Human operator decision
```

### Inputs received from other GridMind modules

- **Virtual grid/pandapower:** topology, component properties, power-flow solution, loading, voltage and real component status.
- **Telemetry Reconstruction:** estimated values **only for otherwise functioning equipment with missing readings**. Provenance must show measured vs. reconstructed; a truly disconnected line must never be treated as healthy because a sensor value was reconstructed.
- **Forecasting:** anticipated future demand, solar generation and wind generation. These are transformed into a **future electrical operating state** before being used for cascade screening.
- **Event Diagnosis:** physical-outage event type, likely affected component and confidence. Suspicious sensor data must not silently become a real outage.
- **Contingency screening:** a specified hypothetical initiating line/transformer outage, or a small N-k set if computationally feasible.

### Outputs sent to other GridMind modules

- **Dashboard:** warnings, component-level predicted failures, DNS, severity, and clear scenario labels.
- **Corrective-Action Recommendation:** stressed components and expected impacts so candidate generator redispatch, battery discharge, renewable curtailment, topology switching, or last-resort load shedding can be compared.
- **Physics Validation:** each candidate action is applied to a *separate* scenario and tested using pandapower; the resulting operating state can be rescored for cascading consequences. A lower predicted risk is not itself proof of physical feasibility.
- **Scenario history / database:** initiating contingency, model version, input provenance, prediction, and optional validated outcomes.

## 3. Exactly what “cascade risk” means

A **cascading failure** occurs when an initial component failure changes the grid's flows and operating conditions, causing additional components to fail.

Example:

```text
Line 37 trips (observed or hypothetical initial event).
    ↓
Power redistributes to other lines.
    ↓
Line 42 goes from 70% to 96% loading.
    ↓
Line 48 becomes stressed.
    ↓
The model estimates which lines/buses may fail and how much load may be lost.
```

The values above illustrate the **GridMind scenario previously discussed**, not a verified research experiment.

### Important distinction: conditional consequences vs. probability of the first fault

The PI-GN-JODE paper predicts consequences **conditioned on a specified initiating contingency**:

`P(Line 42 trips later | current grid state, initial Line 37 outage)`

It does **not** directly estimate:

`P(Line 37 fails in the next hour | current grid state)`

And it does not by itself predict the calendar time of the initial outage. These are different tasks.

GridMind may still warn **before any fault has occurred** by running **what-if analysis** for plausible initiating outages. The warning should say, for example, **“If Line 37 trips under the forecast operating state, Line 42 appears vulnerable”**, not **“Line 37 is 80% likely to fail tomorrow”**.

A full probabilistic risk estimate would additionally require initiating-outage likelihood information (for example, a separate reliability/hazard model or justified failure-rate data). That is **not** provided by PI-GN-JODE and is **not** a committed GridMind model in the current scope.

### Risk vs. consequence

- **Conditional cascade probability:** likelihood of additional failures following the specified initial outage.
- **Consequence:** estimated number of affected branches/buses, severe-event classification, and DNS.
- **Expected risk:** in a fuller formulation, initiating-event probability multiplied by conditional consequence, or a scenario-weighted expectation. This would require separately estimated event probabilities.
- **GridMind risk tier:** a dashboard-oriented HIGH/MEDIUM/LOW warning derived from model outputs and operating thresholds. The exact formula, decision thresholds and probability calibration are **proposed design choices**, not quantities or thresholds established by the paper.

## 4. Dataset versus model inputs: a critical distinction

**The dataset is a collection of labeled scenarios. Inputs are what the model receives for *one* scenario. Labels are the reference outcomes used to train it.**

### Dataset used in the PI-GN-JODE paper

- **Reference networks:** IEEE 24-bus and IEEE 118-bus.
- **Simulations:** 20,000 scenarios on each network, **40,000 total**.
- **Simulation tool:** `pandapower` with **AC power flow**; the authors implement additional relay-based cascading logic.
- **Load variation:** base-load scaling to generate different operating points.
- **Initial failures:** sampled and screened, with bias toward heavily loaded branches and some low-degree load-bus connections.
- **Labels:** simulated downstream failed branches, affected buses, safe/unsafe severity, and DNS; in the multi-round setting, round-specific labels.
- **Published split:** 70% train / 15% validation / 15% test, grouped by operating point to reduce leakage.
- **Data provenance:** simulation-generated cascading outcomes, **not a database of recorded real-world cascading incidents**.
- **Availability:** the paper does not identify a directly downloadable release of its exact 40,000 training scenarios. Public IEEE test grids are not equivalent to the finished labeled cascade dataset.

### GridMind's agreed dataset strategy

GridMind will use a **hybrid data strategy**, not a single ready-made file:

1. **Benchmark network models** (IEEE/PGLib/SimBench, as suitable) for topology and physical properties.
2. **Public real-world load and renewable profiles** where available, to create more plausible variations in operating conditions.
3. **Automated GridMind scenario generation with pandapower**, producing operating-state features and **simulated** cascading-failure labels.
4. **Historical outage statistics (when available)** for plausibility/sanity checks, **not** as supervised training records that magically contain voltages, flow, dispatch and ground-truth cascade sequences.

The project is **not** connected to the Egyptian national grid, does not require confidential SCADA data, and does not claim to predict real Egyptian blackouts.

### One training example

```text
SCENARIO 0001
Input X:
  Grid topology: IEEE 118-bus network
  Bus conditions: voltages, loads, generation, net injections, etc.
  Line conditions: power flow, loading, resistance, limits, status, etc.
  Initial failure: line 37 selected as the initiating contingency

Label Y (generated by the cascade simulator):
  Which additional lines failed
  Which buses lost service / became isolated
  Final DNS fraction
  Final safe/unsafe severity
  Failure rounds (if modeling sequences)
```

**The model is never given the downstream failure labels as inputs at inference time.**

The **same base grid topology** can be reused across many different load, renewable, generation and outage scenarios; we do not need to duplicate an entire physical network definition for every record.

## 5. Model inputs, with paper-exact feature definitions

GridMind would construct an attributed graph from the known network and the electrical state **after specifying/applying the initiating outage, before the subsequent cascade is propagated**.

- **Nodes** represent electrical buses.
- **Edges** represent transmission lines and transformers.
- The paper represents each physical branch with **two directed edges** for message passing. For example, 186 physical branches on IEEE 118-bus correspond to 372 directed graph edges.
- Initial-failure masks and service status identify the components that were part of the triggering event.

### 5.1 Eleven node (bus) features from Table II

| Feature(s) | Meaning |
| --- | --- |
| 1. Bus type | PQ, PV or slack-bus category |
| 2–3. Voltage magnitude and angle | AC power-flow electrical state |
| 4–5. Net active and reactive injection | Net P and Q at the bus |
| 6–7. Active and reactive demand | Pd and Qd |
| 8. Generator active output | Pg |
| 9. Generator status | Active/in-service flag |
| 10. Graph degree | Number of incident connections |
| 11. Initial contingency mask | Whether the node is affected in the initiating event |

### 5.2 Twelve directed-edge (branch) features from Table III

| Feature(s) | Meaning |
| --- | --- |
| 1. Loading percentage | Relative to branch rating |
| 2–5. P/Q at from/to ends | Active and reactive power at both ends |
| 6. Resistance | r |
| 7. Reactance | x |
| 8. Thermal current rating | Imax |
| 9. In-service status | Whether the branch is connected |
| 10. Parallel circuit count | Number of parallel circuits |
| 11. Initial contingency mask | Whether the line/transformer is in the initiating outage |
| 12. Branch type | Transmission line or transformer |

**Note:** these are the paper's reported feature counts and types. GridMind may need a consistent feature encoder/normalizer and explicit handling of optional solar/wind/storage context before training. Such feature changes would be a **GridMind extension** and must be evaluated, not represented as results from the paper.

### Source of each input

- Benchmark network and equipment tables → topology, bus type, branch type, r/x, ratings.
- Operating profiles / dispatch → demand, generator output and renewable generation.
- `pandapower` AC power flow → bus voltage magnitude/angle, active/reactive flows, line loading.
- Scenario/event definition → which initial components are out of service; contingency masks.
- Telemetry reconstruction → explicitly marked estimates when readings are missing **but assets are still functioning**.

## 6. The four predictive outputs

The original PI-GN-JODE architecture simultaneously predicts:

### Output A — Edge failure probabilities

A probability-like score for whether each **branch** will trip **during the cascade following the specified initial event**.

Example (illustrative only): `Line 42 = 0.84`, `Line 48 = 0.51`.

Use this for highlighting **vulnerable next branches**. Do not mislabel it as the probability that the initial incident occurs by itself. If a physical branch uses two directed message-passing edges, GridMind must map the prediction back to its **one physical branch ID** consistently.

### Output B — Node failure probabilities

A probability-like score for whether each **bus** is affected by **load shedding or isolation**. This does **not** necessarily mean the bus hardware is physically destroyed.

Example: `Bus 12 = 0.70` (illustrative).

### Output C — Severity classification

A system-level **Safe / Unsafe** classification based on DNS near the paper's **5% threshold**.

**Boundary caution:** the methodology describes *exceeding* 5% (`DNS > 5%`), while the results section also uses `DNS ≥ 5%`. GridMind should pick and document **one** exact boundary rule and apply it consistently in label generation, evaluation and the UI. The proposal in this specification is `Unsafe if DNS >= 0.05`, matching the results section and our previous discussion. This is a project implementation decision, not a claim that the paper is perfectly consistent on equality.

### Output D — Demand Not Served (DNS)

The fraction of electricity demand not supplied after the simulated cascade:

`DNS = 1 - (served demand after cascade / total demand before cascade)`

Example: `DNS = 0.20` means **20% of the requested demand remains unserved**, not that generation itself has decreased by exactly 20%.

GridMind should display both **fraction/percentage**, and **MW** only when calculated against a documented baseline total demand (for example, `0.20 × 1,000 MW = 200 MW unserved`).

### Optional fifth operational view — propagation by round

The paper's **multi-round** mode updates the graph and predicts per-round failures; GridMind could show a timeline like:

```text
Initial contingency: Line 37 (known)
Round 1 prediction: Line 42 may trip
Round 2 prediction: Line 48 may trip
Final predicted impact: DNS / severity
```

This is **an optional advanced extension**, not necessary for a first working prototype. It is less accurate than the paper's one-shot mode on some metrics and can compound errors.

## 7. How PI-GN-JODE produces these predictions

One **integrated architecture**, not four independent competing models:

```text
Graph + node/edge features + initiating contingency
                         ↓
1) Edge-conditioned GNN encoder
   Learns which buses/lines interact through network connectivity
   and equipment characteristics.
                         ↓
2) Neural ODE
   Learns the evolution of hidden grid representations between
   abrupt outage events. This does not solve the full AC equations.
                         ↓
3) Jump handler
   Represents sudden changes in latent states when the model
   considers a branch to trip.
                         ↓
4) Prediction heads
   Edge failures | Bus effects | Severity | DNS

During TRAINING: an additional soft Kirchhoff-balance loss
regularizes internal learned power injection/flow representations.
```

### What the physics-informed loss really does

The model has additional learned functions that estimate bus net injections and edge active/reactive flows from hidden states. A **soft Kirchhoff power-balance penalty** discourages a mismatch between estimated injection and estimated incoming/outgoing branch flows at a bus.

- The penalty is part of **training**, not a separate required prediction input.
- It is gradually introduced using a **warm-up weight** to avoid destabilizing early training.
- It **encourages** physical consistency; it does **not** guarantee exact AC power-flow feasibility.
- The GNN, ODE, jump handler and decoder heads still learn from supervised simulator labels.

### Why physics is still required elsewhere in GridMind

**Physics-informed training ≠ physics validation of corrective actions.**

GridMind should still use `pandapower` to test candidate operational actions and verify post-action power flows and constraints. The AI prediction must not be presented as a certified safe operational plan.

## 8. GridMind Cascade Risk: offline data-generation pipeline

**Proposed implementation following the paper while respecting the agreed project scope:**

1. **Choose grid(s):** start with one small/medium benchmark network, then test larger/different topologies.
2. **Define realistic operating profiles:** active/reactive load, solar, wind, controllable generation and optional storage schedules, using benchmark data and public profiles where appropriate.
3. **Run AC power flow:** `pandapower` computes electrical state and loading. Record or reject cases with non-converged/inconsistent solutions according to a transparent policy.
4. **Select initiating contingencies:** line/transformer outages; start with N-1 and only expand to N-2/N-k when supported by the simulator and data budget.
5. **Apply outage and represent the new state:** update service status and initiating-contingency masks. Ensure labels refer to **subsequent** failures, not just the known first failure.
6. **Simulate cascade progression:** repeatedly solve power flow on the surviving network, check branch loading/voltage/protection rules, disconnect newly failed branches and account for islands/unserved load where the simulator supports it.
7. **Record ground-truth targets:** tripped branches, affected buses, cascade rounds, severity, DNS; also keep scenario IDs, initial component IDs and solver status.
8. **Build model-ready graphs:** node matrix, edge matrix, connectivity and labels. Keep consistent indexing for physical and directed edges.
9. **Split and train:** use separate operating points and, for realistic generalization claims, separated scenarios and topology tests. Do not leak nearly identical operating states between train and test.
10. **Evaluate:** compare predictions to held-out simulated outcomes and a simple GNN baseline.

**Important:** `pandapower` is an AC network modeling and power-flow library; it is **not** automatically a fully validated cascading-failure simulator. GridMind must implement and test the cascade progression, relay rules, treatment of islands, and DNS labels. The PI-GN-JODE paper uses a specific simplified relay-based simulator; copying a published architecture does not establish correctness of a new GridMind simulator.

**Example generation ranges already discussed** (project examples, not final parameters): load multiplier `0.7–1.3`, variable renewable penetration `10–60%`, and randomized valid initiating outages. Avoid indiscriminately applying the paper's exact sampling bias without testing dataset representativeness.

## 9. Three supported inference modes in GridMind

### Mode A — Reactive: an incident has already happened

Trigger: virtual SCADA/event diagnosis confirms **Line 37 is OUT**.

1. Receive current trusted/estimated electrical state.
2. Receive initiating-outage component ID.
3. Construct the post-initiating, pre-cascade graph.
4. Run cascade model.
5. Show next vulnerable lines/buses, DNS and severity.
6. Send at-risk components to Corrective-Action Recommendation.
7. Validate candidate actions in pandapower before marking any as simulation-verified.

**This is the closest use to the paper's basic prediction problem.**

### Mode B — Proactive: what-if contingency screening before any incident

Trigger: operating grid is still intact; engineer asks **“What if Line 37 trips?”**

1. Copy the current operating state into a scenario workspace.
2. Specify **hypothetical** Line 37 outage; do not modify the live virtual grid.
3. Derive the scenario's electrical state and contingency masks.
4. Run cascade model on that scenario.
5. Rank **conditional consequences** across tested initiating outages.
6. Optionally compare candidate pre-emptive actions through simulation.

**Supported claim:** screening consequences of possible outages **before they occur**.  
**Unsupported claim:** predicting the actual date, probability or cause of the initiating outage using PI-GN-JODE alone.

### Mode C — Forecast-driven contingency screening

Trigger: Forecasting predicts **higher demand or lower solar/wind** in 15, 30 or 60 minutes.

1. Forecast demand, solar and wind.
2. Map forecasts to buses/generators for the chosen network.
3. Derive forecast operating state with a consistent dispatch/AC power-flow calculation.
4. Test selected hypothetical contingencies on that **future** state.
5. Present warnings such as: **“Under the 15:00 forecast state, a Line 37 outage would put Line 42 at risk.”**

This combines GridMind's modules and is **a proposed GridMind integration**, not a capability measured in the PI-GN-JODE paper.

## 10. Operational warnings and risk ranking

The paper's four outputs can drive a GridMind warning view. An operational aggregation layer should be kept **separate from the trained base model** so its criteria are inspectable.

**Proposed fields to show:**

- Known or hypothetical initiating outage.
- Current vs. forecast operating conditions.
- Top 3–5 vulnerable subsequent branches and their scores.
- Top affected buses and whether they face isolation/load shedding.
- Expected DNS and estimated lost demand (if baseline load is known).
- Severity label and risk tier (e.g., LOW / MEDIUM / HIGH).
- Uncertainty/qualification, model version, source of telemetry, and simulator-validation status.

**Do not invent a supposedly scientific probability from an arbitrary risk tier.** If scores must be called **probabilities**, evaluate their calibration, reliability diagrams and Brier score first; otherwise label them as *model scores*.

### Illustrative dashboard message

> **Cascade screening warning — scenario based**  
> Initial event: Line 37 is OUT.  
> Vulnerable components: Line 42 (HIGH), Line 48 (MEDIUM).  
> Predicted DNS and safe/unsafe label: shown from the model.  
> Recommended next step: compare corrective-action candidates and validate them in the simulator.  
> Status: AI estimate; no real equipment action executed.

Any numerical examples such as `Line 42 score = 84%` are demonstrations of intended UX, **not measured GridMind accuracy**.

## 11. Integration with corrective actions and physics validation

GridMind's action module may consider:

- Generator redispatch.
- Battery charge/discharge.
- Renewable curtailment.
- Eligible topology switching.
- Controlled load shedding as a last resort.

For each candidate:

1. Apply it to a **copy** of the stressed or forecast grid state.
2. Run pandapower AC power-flow/constraint checks.
3. Re-evaluate operating violations and, when supported, conditional cascading impact.
4. Compare branch loading, voltage, unserved demand, risk score and practical action constraints.
5. Label **“Candidate Action Verified in Simulation”** only if the specified checks pass, and report which checks were actually performed.
6. Present evidence for the engineer's decision; do **not** operate real-world breakers, storage or generators automatically.

**Example from earlier GridMind discussions (illustrative):** after Line 37 trips, Line 42 rises toward overload; a proposed battery discharge or generator redispatch might lower Line 42's loading. The result must be calculated by GridMind's own pandapower run, not assumed from the AI recommendation.

## 12. Implementation boundaries and interfaces

### Proposed training representation

| Entity | Suggested fields |
| --- | --- |
| `scenario` | ID, network ID, operating-point ID, timestamps, input source, simulator version, random seed |
| `bus` | bus ID, node features, measurement provenance and quality masks |
| `branch` | physical branch ID, from/to bus ID, directed-edge mapping, electrical parameters, status |
| `contingency` | initially out-of-service branch/bus IDs, observed vs. hypothetical |
| `labels` | later failed branches, affected buses, per-round failures if present, severity, DNS fraction |
| `prediction` | per-branch/per-bus scores, severity, DNS, model version, confidence metadata |
| `action_evaluation` | candidate action, pre/post electrical state, constraint violations, physics-check status |

### Suggested model request schema (illustrative contract)

```json
{
  "network_id": "IEEE118",
  "scenario_id": "demo-001",
  "scenario_type": "confirmed_incident",
  "operating_time": "simulated-timestamp",
  "bus_features": "[num_buses, 11] array",
  "edge_index": "[2, num_directed_edges] integer array",
  "edge_features": "[num_directed_edges, 12] array",
  "initial_outage_branch_ids": [37],
  "data_quality": {
    "estimated_measurements": [],
    "verified_component_outages": [37]
  }
}
```

The arrays above are placeholders documenting expected *shapes*, not a working endpoint. For IEEE 118-bus in the paper, `num_buses=118` and `num_directed_edges=372` under the full physical topology mapping; the chosen model representation must define handling of initially disconnected branches consistently.

### Suggested prediction response schema (illustrative contract)

```json
{
  "scenario_id": "demo-001",
  "conditional_on_initial_outage": true,
  "initiating_outage_probability_predicted": false,
  "branch_failure_scores": [{"branch_id": 42, "score": 0.84}],
  "affected_bus_scores": [{"bus_id": 12, "score": 0.70}],
  "severity_label": "UNSAFE",
  "dns_fraction": 0.20,
  "overall_risk_tier": "HIGH",
  "risk_tier_policy_version": "to_be_defined",
  "physics_action_validation": "NOT_RUN",
  "model_version": "to_be_defined"
}
```

**All numbers in this JSON are illustrative, not real predictions.** The interface and tier policy are **proposals**, not features already implemented or provided verbatim in the paper.

### Storage and tools

- **Planned/proposed:** Python, `pandapower`, PyTorch and a graph framework such as PyTorch Geometric.
- **Possible storage:** PostgreSQL for grid/scenario/prediction records, and TimescaleDB for telemetry/time series.
- A dedicated Neo4j instance is **not** required simply because the ML data is a graph; relational network tables can be transformed into GNN graph objects in code.
- A shared graph encoder for Reconstruction, Diagnosis and Cascade Prediction is **possible**, but joint training is an **architectural option**, not a validated GridMind decision.

## 13. Testing and evaluation plan

### Core prediction metrics

- **Branch failures:** PR-AUC and F1, ideally also precision/recall at operational thresholds.
- **Affected buses:** PR-AUC and F1.
- **Severity:** F1 and confusion matrix; scrutinize **false negatives** for unsafe states.
- **DNS regression:** R², MAE and/or RMSE; report DNS in consistent units.
- **Probabilistic reliability:** calibration/Brier score if interpreting per-component scores as likelihoods.
- **Multi-round (if included):** per-round failure errors, final-set agreement and degradation through successive rounds.
- **Inference speed:** measured on GridMind's actual hardware, including feature preprocessing.

### Testing conditions

- Compare a simple GCN-only baseline with the proposed richer model.
- Keep operating-point groups separated in train/validation/test.
- Test under different load and renewable levels; include non-cascade as well as severe cases.
- Test different initiating lines and N-1 contingencies, not just the most overloaded lines.
- Check whether model quality changes across network sizes and topologies. Results on a new topology require dedicated evaluation and may require retraining.
- Include **missing but recoverable** telemetry, erroneous readings and real physical outages as distinct cases.
- Test whether inaccurate forecast states degrade conditional cascade predictions.
- Evaluate downstream corrective-action rankings against actual pandapower simulation results.
- Measure dataset label quality and consistency of the cascade simulator before trusting ML evaluation.

### Paper performance: reference values, NOT GridMind targets already achieved

| Paper benchmark | Reported value |
| --- | ---: |
| IEEE118 one-shot edge PR-AUC | 0.991 |
| IEEE118 one-shot node PR-AUC | 0.973 |
| IEEE118 one-shot severity F1 | 0.974 |
| IEEE118 one-shot DNS R² | 0.951 |
| IEEE118 one-shot DNS R² **without physics loss** | 0.858 |
| IEEE118 multi-round DNS R² | 0.728 |
| PowerGraph IEEE24 binary balanced accuracy, retrained PI-GN-JODE | 0.996 ± 0.002 |

These values depend on that paper's simulator, operating-point sampling, data splits, training setup and task definitions. They **cannot** be claimed as evidence of GridMind accuracy or performance on field data.

## 14. Limitations, safety and honest claims

1. **Simulation-to-reality gap:** training labels are based on synthetic cascade simulations. Real operating-state/cascade labels are generally not publicly available together in the required form.
2. **Simplified protection modeling:** AC power flow plus threshold-based relay rules omits many real dynamics, operator interventions and hidden relay failures.
3. **Soft physics penalty:** trained predictions may still violate real power-flow constraints; the paper does not guarantee exact physics.
4. **Initiating outage is specified:** prediction of initial equipment failure likelihood or timing is a separate unimplemented task.
5. **Sampling bias:** choosing more risky initiating outages for training can cause poor calibration or generalization to routine/unseen conditions.
6. **Class imbalance:** few branches fail in many scenarios; plain accuracy is not sufficient to evaluate the model.
7. **Multi-round uncertainty:** autoregressive predictions can compound mistakes. Start with one-shot predictions for a defensible MVP.
8. **Uncertain topology generalization:** strong results on IEEE 24/118 do not demonstrate zero-shot operation on arbitrary transmission networks.
9. **Bad telemetry vs. equipment failure:** don't insert reconstructed ‘normal’ values for physically failed components; require diagnosis/provenance checks.
10. **No silent control:** GridMind offers recommendations and simulated validation; final decision belongs to a trained human operator.
11. **Validation language:** the PowerGraph project's Cascades simulator has historical-statistics validation in prior research. **This does not validate GridMind's separate pandapower-based cascade simulator.** GridMind must perform its own checks and cannot advertise “validated on real events” without direct evidence.
12. **No national-grid claims:** this is a research prototype, not a deployed EMS/SCADA replacement or a real Egyptian outage predictor.

## 15. Proposed incremental delivery plan

These phases are **implementation recommendations**, not an agreed schedule or a claim of completed work.

### Phase 1 — Minimal useful cascade model

- Load one benchmark network in pandapower.
- Generate normal and post-N-1 electrical states.
- Implement a transparent, tested simplified cascade simulator.
- Produce labeled graphs, edge/bus outcomes, DNS and severity.
- Train a baseline GNN and implement **one-shot** predictions.
- Show a ranked component list and risk warning for a specified initial outage.

### Phase 2 — GridMind integration

- Connect trusted/estimated telemetry and Event Diagnosis.
- Add proactive what-if contingency screening.
- Connect demand/solar/wind forecasts to **future operating-state scenarios**.
- Feed results into candidate corrective-action ranking.
- Validate candidate actions through pandapower before any “verified” label.

### Phase 3 — Advanced research extensions

- Add PI-GN-JODE's edge-conditioned encoder, ODE, jump handler and soft physics loss, ideally with ablation studies.
- Investigate round-by-round propagation, with appropriate uncertainty and error monitoring.
- Test other network sizes/topologies and sampling strategies.
- Calibrate failure scores and evaluate operational risk tiers.
- Investigate real outage-statistics sanity checks while explicitly acknowledging limited validation.

### Definition of a credible prototype result

A GridMind demo should be able to show:

1. A *known or hypothetical* initiating outage on the virtual grid.
2. The pre-cascade graph and trusted/estimated measurements.
3. The model's ranked next at-risk branches/buses and DNS/severity estimate.
4. A set of corrective-action candidates.
5. AC simulation results **before vs. after each candidate action**.
6. A clear human decision-support dashboard with no physical control execution.

## 16. Example end-to-end demo: Line 37 incident

The following is an **illustrative GridMind scenario from the previously discussed project definition**, not a published paper result:

1. GridMind forecasts rising demand and/or falling solar output; the dashboard shows a future Line 42 loading warning.
2. **Line 37** trips in the virtual grid (or the operator chooses a hypothetical Line 37 outage).
3. `pandapower` and the event/telemetry pipeline update the state; Line 42 loading rises (e.g., **70% → 96%**) and Line 48 becomes stressed.
4. Cascade Prediction estimates **Line 42: HIGH** and **Line 48: MEDIUM** next-component risk; it also estimates system DNS and severity.
5. Corrective-Action Recommendation proposes generator redispatch, battery discharge and/or limited demand reduction.
6. GridMind simulates candidates and shows their effect on line loading, voltages, and possible cascade consequences.
7. A candidate is displayed as **verified in simulation** only after explicit checks pass.
8. The control-center engineer reviews the evidence and makes the final decision.

## 17. What is agreed vs. what is from the paper vs. what is proposed

| Item | Status |
| --- | --- |
| GridMind software-only decision support; human remains in control | **Previously agreed project scope** |
| Detect the initiating incident through separate diagnosis, then predict consequences | **Previously agreed GridMind role** |
| Forecast demand, solar and wind; convert forecasts into operational risk | **Previously agreed GridMind integration goal** |
| Use pandapower AC power flow and simulated cascading-outage training labels | **Previously agreed GridMind data strategy** |
| Four paper targets: branch failures, bus effects, severity, DNS | **Supported by PI-GN-JODE** |
| Paper uses 11 node and 12 directed-edge input features | **Supported by PI-GN-JODE** |
| GNN + Neural ODE + Jump Handler + Physics Loss | **Supported by PI-GN-JODE** |
| Paper's specific scores (e.g., DNS R² = 0.951 on IEEE118) | **Published paper results only** |
| Before-incident screening of hypothetical first outages | **GridMind intended application; conditional on chosen outage** |
| Model for probability/timing of the initiating line failure | **Not provided by PI-GN-JODE / not committed** |
| UI risk-tier formula, score calibration policy, model APIs | **Proposed details; must be designed and tested** |
| Shared multi-task GNN encoder across other GridMind modules | **Optional architecture; not finalized** |
| Exact GridMind dataset size, accuracy, latency and real-event validation | **Not yet established** |

## 18. References and evidence

### Primary research paper

Birva Sevak, Shrenik Jadhav and Van-Hai Bui. **“Physics-Informed Graph Neural Jump ODEs for Cascading Failure Prediction in Power Grids.”** arXiv:2603.20838v1, 21 March 2026.  
- [Paper abstract and PDF access](https://arxiv.org/abs/2603.20838)
- **§II.A–C and Tables I–III:** problem, simulator data, inputs and labels.
- **§II.D–E and Figure 1:** GNN–ODE–jump architecture and Kirchhoff-based training penalty.
- **Tables V–VI:** one-shot metrics and ablations.
- **Tables VIII–IX:** PowerGraph benchmark and multi-round performance.
- **§III.E / §IV:** limitations and future work.

### GridMind project baseline

**GridMind canonical project definition** (`Pasted text.txt`, shared in previous project work). Particularly: Model 4 Cascade Risk Prediction; Model 5 Corrective-Action Recommendation; the full runtime pipeline; hybrid dataset strategy; physics-based action validation; in-scope/out-of-scope definitions; and the human-in-the-loop principle.

### Related public dataset (separate from PI-GN-JODE's original 40,000 scenarios)

- [PowerGraph benchmark dataset](https://figshare.com/articles/dataset/PowerGraph/22820534)
- [PowerGraph example code and repositories](https://github.com/PowerGraph-Datasets)

**Do not confuse PowerGraph's downloadable scenarios with the unpublished/unspecified exact PI-GN-JODE training dataset.**
