# GridMind — Corrective-Action Recommendation Model

**Owner:** Seif Eleslam Yasser  
**Updated:** 30 October 2026  
**Status:** Proposed design and implementation roadmap; no completed training or prototype results are established by the handover document.  
**Research focus:** The first paper, *Imitation Learning for Intra-Day Power Grid Operation through Topology Actions*.

## 1. My model in simple English

My component helps an engineer decide **what action to take when the electricity grid is stressed**.

Other GridMind components may estimate the grid state, forecast demand, diagnose an event, or predict cascade risk. My component takes the available information and asks:

> Which available corrective actions could improve this situation, and which of them pass our simulation checks?

The proposed system generates possible actions, uses a learned model to rank them, and simulates a shortlist before presenting recommendations. The engineer makes the operational decision.

For example, when a line is overloaded, the system might consider reducing one generator's output and increasing another generator's output. Whether this helps depends on where those generators are connected and how power flows through the network. Reducing total demand or generation in the abstract is not enough; the location and electrical effect of the change matter.

## 2. What the first paper actually contributes

**Reference:** Matthijs de Jong, Jan Viebahn and Yuliya Shapovalova (2024), arXiv:2407.19865v2. [1]

- **Task:** Grid2Op IEEE 14-bus topology control through busbar reconfiguration, rather than generator redispatch.
- **Experts:** Greedy search minimizes maximum line loading; an N-1 expert considers selected single-line outages.
- **Data:** Normalized electrical features and topology accompany expert actions. Scenario splits are 70/10/20%; processed training/validation/test sets contain 196,477/26,228/59,150 points. Explicit do-nothing points and failed-day data are excluded.
- **Model:** A fully connected neural network predicts binary object-switch decisions; postprocessing maps predictions to valid actions. It is not a GNN.
- **Evaluation:** Test accuracy is 76.4% ± 0.6%. Class imbalance and overlap limit accuracy. Hybrid agents combine predictions with simulation and expert fallback, achieving favorable operational performance and speed in the tested setting.
- **Boundary:** These results establish neither redispatch performance nor general grid safety. GNNs appear as a future research direction.

**Implementation notes from the official repository:** It separates simulation, preprocessing and training. Entry scripts include `simulate.py`, `preprocess_data.py` and `train_network.py`. The README warns that the project is unmaintained, its original environment is deprecated, saved observation vectors can break across Grid2Op versions, and its day-splitting implementation needs improvement. Treat the code as a reference, not a ready-made GridMind package. [2]

## 3. What we take from it for GridMind

Our proposed adaptation is **expert-guided supervised learning with simulation at recommendation time**.

Here, an “expert” means a computational teacher: a search procedure or optimizer that evaluates actions using a simulator. It does not require an engineer to manually label every training example.

During development, this teacher can evaluate many actions and produce expensive training labels. After training, the learned model should help identify promising actions with fewer online evaluations. We still need experiments to establish whether this saves time without losing useful recommendations.

The proposed mapping is:

| GridMind design choice | How we will implement it |
| --- | --- |
| Teacher-generated examples | Simulate legal redispatch and curtailment candidates and store their outcomes |
| Simple learned baseline | Train an MLP or tree model before assessing the GNN |
| Graph-based extension | Test whether connectivity improves candidate scoring |
| Simulation before recommendation | Validate shortlisted actions in pandapower |
| Recovery when the shortlist fails | Expand the search within a defined budget, then abstain if necessary |
| Operational evaluation | Measure constraint satisfaction, improvement, runtime and simulator calls |

**Attribution:** Candidate ranking, the GNN/GAT architecture, redispatch controls and the pandapower validation workflow below are GridMind design proposals carried forward from our project plan. They are not implementations or findings demonstrated by the first paper.

## 4. The first implementation's action space

An action is a specific change to one or more controllable resources.

| Action | Meaning | Conditions to represent |
| --- | --- | --- |
| Generator redispatch | Change a controllable generator's active-power setpoint | Minimum/maximum output, availability, ramping over the response interval |
| Renewable curtailment | Reduce renewable output below the available amount | Available production, permitted reduction, replacement supply |
| No change | Keep current setpoints | Useful as a comparison and as an outcome when intervention is unnecessary |

A candidate may combine several changes. For example, increasing generator A by 5 MW and decreasing generator B by 5 MW is one redispatch plan. The numbers are illustrative; generator limits and the network determine legal values.

Equal opposite changes do not guarantee exact AC balance because losses may change. Slack/external-grid behavior and limits must be checked. Curtailment also requires a credible balancing response; an unlimited external source must not silently make an otherwise infeasible plan look acceptable.

Battery control and topology switching remain later extensions. Batteries require time-dependent energy accounting; switching requires a separately defined set of permitted operations.

## 5. Inputs, learned model and outputs

### Inputs

| Input group | Examples | Purpose |
| --- | --- | --- |
| Grid structure | Bus IDs, connections, in-service equipment | Identify where resources and constraints are located |
| Operating state | Voltage, power injections, branch loading, generator output | Describe the current condition |
| Operating limits | Voltage bounds, equipment ratings, generator/external-grid limits | Define what must pass |
| Available controls | Controllable generators, renewable availability, response interval | Generate realistic candidates |
| Optional GridMind context | Forecasts, event diagnosis, cascade-risk estimates, confidence flags | Add context as other components become available |
| Candidate action | Affected assets and proposed changes in MW | Tell the scorer which plan it is assessing |

All interfaces need consistent units, component IDs, timestamps and topology versions. The core prototype can start with simulated operating states without waiting for every upstream model.

### Proposed learned model

The main research option remains a **GNN/GAT candidate scorer**. Represent buses as graph nodes and lines/transformers as edges, with equipment information attached consistently to the connected buses or represented explicitly if needed.

The model combines information from connected components with the candidate's resource changes and produces a score for that state-action pair. Evaluate the scorer for every candidate, then sort the results. A shared scorer avoids tying the output to a fixed catalogue of action IDs, but does not by itself prove generalization to other grids.

Use an MLP or tree-based scorer as a baseline. Adopting the first paper as the main reference does not mean we must replace the proposed GNN with its architecture; it means the graph model needs its own justification and comparison.

### Outputs

For each recommended candidate, show:

- Affected resources and exact setpoint changes.
- Expected post-action loading and voltage results.
- Constraint-check results and remaining violations.
- Redispatch amount, curtailment and cost if a cost model is defined.
- Scenario timestamp, topology version and validation scope.

If no candidate passes, return **“No validated corrective action found for this scenario.”** This means none was found within the tested candidate set and budget; it is not proof that no physically feasible action exists.

## 6. Complete workflow

### A. Generate training evidence offline

1. Load a small benchmark network and verify the base AC power flow.
2. Create reproducible stressed scenarios by varying loads, generation or selected outages.
3. Generate legal candidate actions, including no change.
4. Apply each candidate to an independent copy of the scenario.
5. Simulate and check explicit constraints.
6. Store the state, candidate, outcomes and failure reason.
7. Train a baseline scorer, then the graph scorer.

The training record should include `scenario_id`, `topology_version`, candidate changes, convergence status, constraint results, violation amounts and intervention size. Preserve solver failures as a separate status rather than treating every failure as confirmed physical infeasibility.

Split complete scenarios or trajectories before producing candidate rows. Every candidate belonging to the same state must remain in the same split. Fit normalization using training data only.

### B. Produce a recommendation online

1. Receive a credible operating state and its uncertainty indicators.
2. Generate actions allowed by the current resources and limits.
3. Score and rank the candidates with the trained model.
4. AC-validate a small top-K shortlist.
5. Order the passing candidates using their simulated outcomes and intervention cost.
6. If none passes, use a bounded wider search or return no validated action.
7. Present the results for engineer review.

The initial prototype performs the simulation steps directly. The learned scorer is added after the candidate generator and labels work.

## 7. What the training target should mean

The scorer should learn usefulness from simulated outcomes, rather than merely memorize which action was selected once.

A practical starting design is to store separate targets for:

- Whether the candidate passes configured constraints.
- How much overload or voltage violation remains.
- Redispatch and curtailment amounts.

These can support a feasibility predictor plus a utility scorer, or a single scorer with a carefully defined target. Architecture and loss selection remain implementation decisions.

For final recommendation ordering, use this priority:

1. Require action legality and all configured validation checks to pass.
2. Compare the operational benefit of passing candidates.
3. Prefer lower intervention cost when outcomes are otherwise comparable.

Avoid allowing a low cost to compensate for a failed engineering limit in the displayed recommendation list. Keep invalid and unsuccessful examples in the dataset so the model sees difficult cases.

## 8. What pandapower validates

Pandapower supplies electrical simulations; our surrounding code must configure and inspect the relevant checks.

| Check | Required interpretation |
| --- | --- |
| AC convergence | A numerical solution was obtained; other checks still apply |
| Line/transformer loading | Compare against explicitly configured ratings |
| Bus voltage | Compare against configured lower/upper bounds |
| Generator output | Check active/reactive limits and any response restrictions represented |
| External-grid/slack output | Verify balancing supply remains within defined limits |
| Connectivity and supply | Detect disconnected or unsupplied areas explicitly |
| Selected contingencies | State exactly which additional outage cases were tested |

Our planned claim is **steady-state AC validation under stated constraints and tested scenarios**. It does not establish transient stability, frequency response or universal blackout prevention. A normal power-flow run does not automatically enforce every resource restriction.

## 9. First 10% prototype

The immediate deliverable is a small simulation and candidate-evaluation pipeline:

1. Start with one IEEE 14-bus or 30-bus benchmark in pandapower.
2. Run and inspect its base case.
3. Construct one reproducible stressed condition.
4. Generate 3–5 legal redispatch/curtailment candidates where the represented resources permit them.
5. Simulate each candidate and the no-change case.
6. Produce a table with convergence, maximum loading, voltage range, resource-limit checks and intervention amount.
7. Explain which candidates pass, which improve the situation, and which fail.

This proves that we can create the labels needed for learning. It does not yet prove that an AI model recommends actions, that the system is fast, or that the proposed controls can solve every stress case.

If the benchmark has no renewable resource, introduce and document one explicitly before demonstrating curtailment, or begin the prototype with redispatch alone.

## 10. How we will evaluate the learned model

Compare no action, a simple heuristic, full candidate search/optimization, an MLP or tree scorer, and the GNN/GAT scorer on the same held-out scenarios.

| Metric | Question it answers |
| --- | --- |
| Validated effective-action rate | How often does the pipeline find a passing action that improves a stressed case? |
| Top-K useful-action recall | Does the shortlist contain at least one passing useful candidate when the evaluated pool contains one? |
| Remaining violations | How much stress remains after the selected action? |
| Redispatch and curtailment | How much intervention is required? |
| Simulator calls and total runtime | Does ranking reduce online work, including validation and fallback? |
| Abstention and missed-action rate | Does the system decline appropriately, and how often does it miss an available solution? |
| Held-out outages/topologies | How well does it handle operating conditions excluded from training? |

Report candidate-pool coverage separately from ranker quality. If no generated candidate works, even perfect ranking cannot solve that case. Speed claims require end-to-end measurements, not neural-network inference timing alone.

## 11. Explanation I can use in the project review

> My model is the corrective-action recommendation component of GridMind. It uses the grid state, topology and available control resources to generate possible generator-redispatch and renewable-curtailment plans. We will generate training examples using simulation-based search, then compare a simple scorer with a GNN/GAT candidate ranker. At recommendation time, pandapower checks the shortlisted actions against explicit operating limits before an engineer sees the results. The first implementation is the simulation and dataset foundation; the learned ranker follows once that foundation works.

## Sources and attribution

1. de Jong, M., Viebahn, J. and Shapovalova, Y. (2024). *Imitation Learning for Intra-Day Power Grid Operation through Topology Actions*. Version 2, 18 August 2024. [Paper](https://arxiv.org/abs/2407.19865v2) · [Full text](https://arxiv.org/html/2407.19865v2). See Sections 3–5 and 7 for the paper facts summarized above.
2. [Official accompanying repository](https://github.com/MatthijsdeJ/Imitation_Learning_Topology_Control), README, accessed 30 October 2026. Repository observations are limited to the inspected documentation; dataset/weight availability and successful reproduction were not established.
3. User-provided handover: *GridMind — Project Review Readiness: Corrective-Action Recommendation Model*, prepared 30 October 2026. Basis for the GridMind scope, proposed architecture, validation requirements and development stages in this document.

The GridMind design sections describe planned work and proposed adaptations. Paper metrics describe that paper's experiments and are not GridMind results.
