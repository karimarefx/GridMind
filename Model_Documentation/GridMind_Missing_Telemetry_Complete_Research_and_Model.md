# GridMind --- Missing Telemetry Reconstruction

## Complete model, research, datasets, inputs, outputs, and implementation reference

**Project:** GridMind: A Topology-Aware AI Decision-Support Platform for
Resilient Renewable Power Grids\
**Scope:** Missing Telemetry Reconstruction component only\
**Research basis:** Four-paper review updated 27 October 2026 and the
earlier research comparison/proposed pipeline.

> **Evidence rule:** This document distinguishes (A) facts reported in
> the reviewed papers, (B) the proposed GridMind design, and (C) details
> that still require verification. The four papers study different
> grids, signals, units, and protocols; their raw error values must not
> be ranked against one another.

------------------------------------------------------------------------

# 1. Executive summary

GridMind's Missing Telemetry Reconstruction component estimates
electrical measurements that are unavailable even though the
corresponding grid equipment remains physically in service. It uses
recent measurements, historical context, network topology, line
electrical attributes, explicit missingness masks, and equipment status.

**Latest recommended GridMind model:**

-   One shared **missingness-aware, edge-conditioned graph neural
    network (GNN)**.
-   A **causal GRU** to model temporal history using only the current
    and past observations.
-   Two output heads:
    -   **Line head:** active/reactive power at both ends of a line.
    -   **Bus head:** voltage magnitude and, secondarily, voltage angle.
-   Physics and quality checks after reconstruction.
-   Derive line current and loading from coherent electrical quantities
    and known ratings where possible.
-   Return observed/estimated/uncertain status and quality information
    with every value.

**Recommended data:** SimBench HV/EHV for primary training/validation,
with NREL-118 as an independent benchmark/domain-transfer evaluation.
Complete electrical measurements must be generated or verified using AC
power flow. Profile files alone are not necessarily model-ready
telemetry.

This is a software-only research prototype. It is not connected to the
Egyptian grid or confidential SCADA data, and it does not control real
equipment.

# 2. Problem definition and boundaries

## 2.1 What is being reconstructed?

A transmission-grid measurement can become unavailable because of sensor
failure, communication interruption, or data-acquisition problems. The
model estimates the unavailable value using:

-   Other measurements that remain available.
-   Recent historical measurements.
-   Bus-line connectivity and network topology.
-   Static electrical properties such as resistance and reactance.
-   Feature-level missingness masks.
-   Physical equipment status.

## 2.2 Missing telemetry is not a physical outage

  -----------------------------------------------------------------------
  State                   Meaning                 Required behaviour
  ----------------------- ----------------------- -----------------------
  Measurement missing;    Reading unavailable,    Estimate may be
  equipment in service    equipment still         produced
                          operating               

  Measurement observed;   Trusted reading         Preserve it unchanged
  equipment in service    available               

  Equipment out of        Physical line/equipment Do not reconstruct a
  service                 disconnected            healthy operating flow

  Equipment status        Physical state          Flag uncertainty; do
  unknown                 uncertain               not return
                                                  high-confidence
                                                  estimate
  -----------------------------------------------------------------------

Keep separate: `measurement_missing_mask`, `equipment_in_service`,
`edge_validity_mask`, and optional `measurement_quality_mask`.

## 2.3 What this module does not do

-   It does not control or switch the real grid.
-   It does not classify a physical fault merely because a reading is
    missing.
-   It does not replace GridMind's diagnosis, cascade-risk, forecasting,
    or recommendation modules.
-   It does not claim access to real Egyptian SCADA data.
-   It cannot measure reconstruction error for truly missing real-world
    values unless independent ground truth exists.
-   It must not present simulated or reconstructed values as observed
    sensor readings.

## 2.4 Place in GridMind

`Benchmark/profile data → AC power-flow truth → simulated telemetry/masks → reconstruction model → physics/quality checks → reconstructed state with flags → downstream diagnosis and cascade-risk modules`

# 3. Four research papers

## Comparison

  ------------------------------------------------------------------------------------
  ID             Paper          Task/data           Main method       GridMind
                                                                      relevance
  -------------- -------------- ------------------- ----------------- ----------------
  P1             STGNI, Ping Li Transmission line   Spatio-temporal   Closest match to
                 et al. (2026)  P/Q; NREL-118       dynamic GNN       primary line
                                hourly + private                      target
                                provincial grid                       

  P2             Auxiliary Task Missing PMU         PMU-subgraph      Graph learning
                 Learning GNN,  bus-voltage         GNN + auxiliary   and voltage
                 Bo Li et       signals; simulated  low-rank GNN +    reconstruction
                 al. (2025      IEEE 145-bus, 50 Hz ST-Net + GRU-R    
                 preprint)                                            

  P3             GSP-WLS,       Voltage-state       Graph             Physics-aware
                 Dabush,        estimation in       smoothness +      non-neural
                 Kroizer &      partially observed  weighted least    voltage baseline
                 Routtenberg    IEEE 118-bus        squares           
                 (2023)                                               

  P4             PSTG-ODF, Wei  Heterogeneous       Graph             Multi-signal and
                 et al. (2026)  distribution-grid   convolution +     physics-guided
                                measurements; IEEE  LSTM + physics +  design reference
                                33 + OpenDSS        online data       
                                                    fusion            
  ------------------------------------------------------------------------------------

------------------------------------------------------------------------

## P1 --- STGNI: Spatio-temporal Dynamic Graph Neural Network

**Reference:** Ping Li et al., *Applied Energy* 411 (2026), 127604.\
https://doi.org/10.1016/j.apenergy.2026.127604

### Problem

Reconstruct missing transmission-line active/reactive power under random
and continuous missingness, including severe 10--90% missing rates. The
grid is a time-varying graph: buses are nodes and existing lines are
edges.

### Inputs

-   Node context: examples include bus voltage magnitude, voltage angle,
    active injection, and reactive injection. The supplied manuscript
    does not provide an exhaustive raw node-column list.
-   Edge telemetry: `P_from`, `P_to`, `Q_from`, `Q_to`.
-   Graph: bus-line connectivity, active edge set, edge attributes,
    time-varying adjacency/validity.
-   Feature-level missingness mask; paper convention `1 = missing`,
    `0 = observed`.
-   Temporal sequences of node/edge readings.
-   Validity information distinguishing missing readings from physically
    absent/disconnected edges.

### Outputs

The main output is reconstructed missing line-power features: `P_from`,
`P_to`, `Q_from`, `Q_to`. Bus voltages are context, not the primary
output of this paper's line-imputation head.

### Internal architecture --- cooperating components

1.  Missing-aware gating.
2.  Mask-enhanced dual-channel attention.
3.  Spatial processing: heat-kernel GCN + edge-guided GAT + gated
    fusion.
4.  Short-term temporal processing: IncepTCN + bidirectional Neural ODE.
5.  Long-term temporal processing: Informer.
6.  Temporal fusion + residual MLP output.

**Comparison baselines, not components:** BRITS, SAITS, MTC-GNN,
CC-GAIN, G-LSTM.

### Data and preprocessing

-   NREL-118: modified IEEE 118-bus transmission grid, one year of
    hourly operation (8,760 positions); public renewable/load profiles,
    but solved per-hour electrical measurements must be verified or
    recomputed.
-   Private provincial grid: about 1,200 nodes, 4,450 branches, 1,613
    generators, six months of five-minute readings (about 51,840
    positions); confidential and not reproducible by GridMind.
-   Random masking: 10%--90% in 10-point increments.
-   Continuous gaps: NREL 6/12/18 hours; private grid 30/60/90 minutes;
    mixed scenarios add 10% random loss.
-   Missing values use zero placeholders plus explicit masks.
-   Inputs/outputs normalized; loss is MAE plus regularization.
-   Train/validation/test used, but exact proportions and
    normalization-fit details are not stated in the supplied manuscript.
-   Up to 300 epochs, early stopping, and tuning of learning rate,
    weight decay, and hidden size.

### Results reported by STGNI on NREL-118

    Random missingness    MAE ↓   RMSE ↓   SMAPE     R² ↑
  -------------------- -------- -------- ------- --------
                   30%   0.0059   0.0400   3.28%   0.9985
                   60%   0.0077   0.0508   3.47%   0.9980
                   90%   0.0087   0.0600   4.25%   0.9970

    Continuous gap    MAE ↓   RMSE ↓     R² ↑
  ---------------- -------- -------- --------
               6 h   0.0077   0.0417   0.9984
              12 h   0.0082   0.0478   0.9978
              18 h   0.0116   0.0972   0.9909

Important counterexample: for the 18-hour NREL gap, BRITS RMSE is 0.0623
and SAITS RMSE is 0.0719, both better than STGNI's 0.0972, although
STGNI has lower MAE. Do not claim STGNI wins every metric.

At 90% random missingness, STGNI MAE/RMSE are 0.0087/0.0600; BRITS
0.0224/0.0749; SAITS 0.0271/0.0780; MTC-GNN 0.0889/0.3649; CC-GAIN
0.0289/0.0812; G-LSTM 0.0508/0.1183.

### Limitations and GridMind lesson

-   Large architecture and expensive attention/ODE/Informer components.
-   Bidirectional temporal processing can use future data, unsuitable
    for strict live inference.
-   Private real-grid data and exact prepared tensors are unavailable.
-   Exact feature preparation is not fully documented.
-   High global R² can hide critical-line or tail errors.
-   Cross-grid topology generalization is not established.

**GridMind use:** closest foundation for line P/Q reconstruction. Adopt
graph + masks + temporal context, but begin with a smaller causal GNN +
GRU.

------------------------------------------------------------------------

## P2 --- Auxiliary Task Learning GNN (ATL-GNN)

**Reference:** Bo Li et al., *A Graph Neural Network with Auxiliary Task
Learning for Missing PMU Data Reconstruction*, arXiv manuscript.\
https://arxiv.org/abs/2512.24542

### Problem, inputs, outputs

Reconstruct missing PMU voltage measurements when PMUs cover only some
buses and readings can disappear. Inputs are PMU-equipped bus voltage
time series (two feature dimensions in ST-Net), PMU subgraph
connections, missingness mask, and an eight-step temporal window. The
paper lists 27 PMU buses. Output is reconstructed missing PMU voltage
values on equipped buses.

### Cooperating model components

1.  **PEK-GCN:** creates K-hop connectivity among buses that actually
    have PMUs.
2.  **ST-Net:** main spatio-temporal reconstruction network.
3.  **Auxiliary low-rank GNN:** unsupervised structural
    prior/complementary prediction; pretrained, with online adaptation
    studied.
4.  **GRU-R:** fuses spatial, temporal, and low-rank information.

**Comparison-only methods:** GAN, GRU, LSTM, self-attention, non-local,
convex optimization.

### Data generation

-   IEEE 145-bus, 50-generator case; public base case:
    https://matpower.org/docs/ref/matpower6.0/case145.html
-   10,000 feasible load conditions using Latin Hypercube Sampling;
    loads 85--115% nominal; non-converging power flows rejected.
-   Power System Toolbox transient simulations after
    three-phase-to-ground faults, cleared within 0.2 s.
-   PMU-style voltage sampled at 50 Hz; eight consecutive steps per
    example.
-   The generated transient training matrix is not established as a
    simple public download. Pandapower steady-state AC power flow alone
    cannot reproduce these 50 Hz transients.

### Split/missingness/results

-   70% train / 10% validation / 20% test.
-   30% random missingness; additional consecutive multi-PMU loss,
    reaching about 60% in designated tests.
-   Paper reports 30 events across 10,000 time steps, each 300 steps
    long.

  Method             MSPE (%) ↓    RMSE ↓
  ---------------- ------------ ---------
  ATL-GNN                 1.056   0.01883
  GAN                     1.587   0.02632
  GRU                     2.374   0.02954
  LSTM                    2.302   0.05508
  Self-attention          2.715   0.07139
  Non-local               2.588   0.02838
  Optimization            54.13   0.67449

MSPE is not classification accuracy. Do not compare its RMSE directly
with another paper.

### Limitations and GridMind lesson

This is 50 Hz transient PMU voltage data, not slower SCADA-like
snapshots. It assumes partial PMU deployment and includes complex
low-rank/online-update mechanisms. Use it to motivate graph-based
bus-voltage reconstruction and partial-observation handling; do not
reproduce its transient simulator in the first GridMind version.

------------------------------------------------------------------------

## P3 --- GSP-WLS: Graph Signal Processing + Weighted Least Squares

**Reference:** L. Dabush, A. Kroizer, T. Routtenberg (2023), "State
Estimation in Partially Observable Power Systems via Graph Signal
Processing Tools," *Sensors* 23(3), 1387.\
https://doi.org/10.3390/s23031387

### Problem and task distinction

Estimate bus-voltage states when only some buses are observed, using
network physics and graph smoothness. This is **not a neural time-series
imputer**.

### Inputs and outputs

Inputs: IEEE network topology, branch electrical information,
admittance/Laplacian, noisy measurements at selected buses, sensor
locations, and noise assumptions.

Outputs: bus voltage phase angles for DC power flow; phases and
magnitudes for nonlinear AC extension. It also studies bad-data
detection and sensor placement. It does not directly reconstruct
multi-timestep line P/Q, current, or loading.

### Algorithms

-   Graph-signal smoothness regularization + WLS for DC estimation.
-   Gauss--Newton extension for nonlinear AC estimation.
-   Graph-based sensor placement using a Cramér--Rao-bound criterion.
-   Comparison methods include pseudo-measurement WLS, matrix
    completion, and alternative sensor placement.

### Data/protocol

-   IEEE 118-bus case and MATPOWER AC/DC simulation.
-   Simulated measurements at selected sensor locations.
-   Some experiments use a 24-hour load curve:
    http://motor.ece.iit.edu/Data/
-   MATPOWER computes reference states.
-   Tests vary observed-bus count (including 48 and 70), noise, and
    placement; 1,000 Monte Carlo trials are reported for relevant
    experiments.
-   No train/validation/test split: this is an
    optimization/state-estimation method, not a neural network trained
    on a dataset.

### Reported result

DC, 48 observed buses, noise variance 0.01:

  Placement                                    Average MSE ↓      Std. MSE
  ------------------------------------------ --------------- -------------
  Authors' Algorithm 1 optimized placement            0.0116   9.45 × 10⁻⁶
  Random placement                                    0.2479        0.0116
  E-design placement                                  0.7929        0.0701

The abstract's up-to-100-fold reduction and up-to-30-percentage-point
bad-data-detection improvement refer to other specified experiments, not
this table.

### GridMind use

Use as a non-neural graph/physics voltage-state baseline and diagnostic
cross-check, not as the primary temporal line-telemetry model.

------------------------------------------------------------------------

## P4 --- PSTG-ODF: Physics-guided Spatio-temporal GNN + Online Data Fusion

**Reference:** W. Wei et al. (2026), "Measurement data recovery for
power distribution systems based on physics-guided spatio-temporal graph
neural network and online data fusion," *Energy and AI* 24, 100754.\
https://doi.org/10.1016/j.egyai.2026.100754

### Problem, inputs, outputs

Reconstruct heterogeneous distribution-grid measurements. Inputs
include: - `IL`: line current magnitude. - `PL`, `QL`: line
active/reactive power. - `PN`, `QN`: node active/reactive injection. -
`UN`: node voltage magnitude. - Measurement-specific weighted graphs. -
Transparency/availability masks. - Twelve-step histories and remaining
trusted online readings.

Outputs: reconstructed line current, active/reactive power, node
voltage, and node active/reactive injection.

### Cooperating architecture

1.  Separate graph channels per measurement type.
2.  Graph convolution for spatial dependency.
3.  LSTM for temporal patterns.
4.  Physics-guided optimization using Ohm's/Kirchhoff's laws.
5.  Online data fusion using transparency masks to merge trusted
    observations with predictions.

**Comparison-only baselines:** DCRNN, AGCRN, STGCN, STSGCN, BSVT,
SoftWalk, SAITS, CSDI.

### Data/preprocessing

-   IEEE 33-node distribution network.
-   15-minute profiles from 32 European countries, 1 June--30 August
    2018 (8,736 steps), from Open Power System Data:
    https://data.open-power-system-data.org/time_series/
-   OpenDSS power-flow simulation; Gaussian noise standard deviation
    0.01.
-   Normalize; 60% train / 20% validation / 20% test.
-   History `P=12`.
-   Random, continuous, correlated gaps; missing rates 10%, 25%, 50%,
    75%; durations 1, 4, 12 steps.
-   Confidential real 10-kV feeders XI46 and WAN48. The exact real
    measurements are unavailable.
-   Some original missing values are spline-imputed to construct
    references; these should not be treated as pristine ground truth.

### Selected reported results: IEEE 33, one-step, 25% missing

  Target   Scenario            RMSE           MAE      MAPE
  -------- ---------- ------------- ------------- ---------
  IL       1               0.5900 A      0.3614 A   1.4331%
  PL       2              0.0059 MW     0.0038 MW   1.1752%
  QL       2            0.0040 Mvar   0.0026 Mvar   1.2481%
  PN       3              0.0035 MW     0.0016 MW   1.7375%
  QN       3            0.0056 Mvar   0.0019 Mvar   1.7177%
  UN       3              0.0047 kV      0.0029\*   0.0255%

`*` The source table appears to label the second UN numeric row as RMSE
again. Do not silently relabel it as MAE; verify before quoting it as
MAE. Abstract MAPE improvements of 1.04--3.41 percentage points vary by
variable/scenario.

### Limitations and GridMind use

Distribution, not transmission; real feeder data are confidential;
physics/online optimization can be costly; some references use imputed
values; cross-grid transfer is not guaranteed. Use as a design reference
for multiple measurement types, physical checks, and preserving trusted
observations. Begin with lightweight checks rather than the full online
optimization system.

------------------------------------------------------------------------

# 4. Synthesis and GridMind design implications

  -----------------------------------------------------------------------
  Evidence                            GridMind decision
  ----------------------------------- -----------------------------------
  STGNI uses graph structure and      Explicit node/edge feature masks
  masks                               and graph encoder

  STGNI uses bidirectional temporal   Causal GRU for live inference
  processing                          

  ATL-GNN handles partially observed  Support partial observations and
  PMU subgraphs                       graph relationships

  GSP-WLS uses graph physics          Include non-neural voltage-state
                                      baseline

  PSTG-ODF links measurement types    Separate output heads and
  physically                          post-reconstruction checks

  PSTG-ODF preserves trusted readings Never overwrite observed values
  through masks                       

  STGNI has a long-gap RMSE           Report tail and critical-line
  counterexample                      errors, not only mean error

  Papers use different grids and      No direct cross-paper metric
  units                               ranking
  -----------------------------------------------------------------------

# 5. Dataset plan

## 5.1 Recommended combination

  ---------------------------------------------------------------------------------
  Dataset           Public material         Work still        GridMind role
                                            required          
  ----------------- ----------------------- ----------------- ---------------------
  **SimBench        Transmission-relevant   Verify selected   Primary
  HV/EHV**          network, branches,      profile;          training/validation
                    electrical data,        run/verify AC     
                    load/generator          power flow for    
                    profiles; often         voltage and line  
                    15-minute annual        measurements      
                    profiles (35,040                          
                    positions)                                

  **NREL modified   118-bus system and one  Verify or         Independent
  IEEE-118**        year hourly             recompute solved  benchmark/domain
                    demand/wind/solar       per-hour          transfer
                    profiles (8,760         electrical        
                    positions)              measurements      

  IEEE 118 / PGLib  Static cases/operating  Generate          Controlled stress,
                    points                  operating         topology, N-1 tests
                                            scenarios and AC  
                                            solves            

  IEEE 145 / Power  Public base case        Paper's 10,000    Optional PMU
  System Toolbox                            transient 50 Hz   extension, not main
                                            trajectories are  training
                                            custom            

  IEEE 33           Public standard         P4 real feeder    Method reference only
  distribution      distribution case       data confidential 
  ---------------------------------------------------------------------------------

### SimBench

-   https://simbench.de/
-   https://simbench.de/en/download/datasets/
-   https://github.com/e2nIEE/simbench

### NREL-118

-   https://github.com/Sienna-Platform/PowerSystemsTestData
-   https://research-hub.nlr.gov/en/publications/an-extended-ieee-118-bus-test-system-with-high-renewable-penetrat-4/

### Other dataset/tool references

-   PGLib-OPF: https://github.com/power-grid-lib/pglib-opf
-   MATPOWER: https://matpower.org
-   IEEE-118 case:
    https://matpower.org/docs/ref/matpower6.0/case118.html
-   IEEE-145 case:
    https://matpower.org/docs/ref/matpower6.0/case145.html
-   pandapower: https://pandapower.readthedocs.io/
-   IEEE-33 pandapower cases:
    https://pandapower.readthedocs.io/en/v2.10.0/networks/power_system_test_cases.html
-   Open Power System Data:
    https://data.open-power-system-data.org/time_series/
-   GSP-WLS load profile: http://motor.ece.iit.edu/Data/

### Earlier candidate repository --- verify before use

https://github.com/evgenytsydenov/ieee118_power_flow_data

A previously inspected sample reportedly contained 118 buses, 177 lines,
9 transformers, 91 loads, and 321 generators. Observed result fields
included bus `vm_pu`, `va_degree`, `p_mw`, `q_mvar`; line `p_from_mw`,
`q_from_mvar`, `p_to_mw`, `q_to_mvar`, `pl_mw`, `ql_mvar`, `i_from_ka`,
`i_to_ka`, `i_ka`, `vm_from_pu`, `va_from_degree`, `vm_to_pu`,
`va_to_degree`, and `loading_percent`. These counts/fields came from a
sample and must be checked across the full repository. Its license was
previously reported as CC BY-NC-SA 4.0; verify current terms. This is
not the latest recommended primary source.

### Dataset arithmetic

SimBench's 35,040 and NREL's 8,760 potential time positions sum to
43,800 positions across **two distinct grids**, not one homogeneous
dataset. Preserve `grid_id` and separate topologies. Multiple
masks/windows from one base state are not additional independent
physical states.

Practical targets, not guarantees: - First: 1,000 validated AC states on
one network. - Then: 10,000--20,000 validated snapshots with 3--5
masking variants where justified. - Expand toward 30,000--40,000 only if
data diversity, convergence, learning curves, and held-out tests justify
it.

# 6. Complete input specification

## 6.1 Input fields and provenance

  -------------------------------------------------------------------------------------
  Field                  Meaning             Source                 Provenance
  ---------------------- ------------------- ---------------------- -------------------
  `grid_id`, `timestamp` Grid and operating  Dataset                Direct
                         time                metadata/profile       

  `bus_id`, `line_id`    Stable equipment    Network metadata       Direct
                         identifiers                                

  `from_bus`, `to_bus`   Line endpoints      Branch table           Direct

  `in_service`           Physical equipment  Network/contingency    Direct or simulated
                         status              log                    

  `r`, `x`, `b`          Electrical line     Branch data            Direct; verify
                         parameters                                 units/base

  `rating`               Thermal/equipment   Network data           Direct if supplied
                         rating                                     

  `load_p_mw`,           Demand              Profiles/assumptions   Direct or defined
  `load_q_mvar`                                                     assumption

  `gen_p_mw`,            Generator output    Dispatch/generator     Often requires
  `gen_q_mvar`                               tables                 assumptions and AC
                                                                    solution

  `vm_pu`, `va_degree`   Bus voltage         AC power flow          Computed/verified
                         magnitude/angle                            

  `p_from_mw`, `p_to_mw` Line active flow at AC power flow          Computed
                         both ends                                  

  `q_from_mvar`,         Line reactive flow  AC power flow          Computed
  `q_to_mvar`            at both ends                               

  `node_observed_mask`   Bus feature         Mask generator         Generated
                         availability                               

  `edge_observed_mask`   Line feature        Mask generator         Generated
                         availability                               

  `edge_validity_mask`   Physical line       Equipment              Generated from
                         validity            status/topology        status

  Quality/noise flags    Sensor              Noise simulator        Generated
                         quality/noise state                        

  History window         Current and past    Chronological states   Constructed
                         sequence                                   
  -------------------------------------------------------------------------------------

## 6.2 Proposed node features

-   `vm_pu`
-   `va_degree`
-   Active injection (`p_mw` or explicitly defined `p_injection_mw`)
-   Reactive injection (`q_mvar` or explicitly defined
    `q_injection_mvar`)
-   Per-feature observation masks
-   Optional quality/noise flags
-   Static bus features only if consistently available and justified

## 6.3 Proposed edge features

-   `p_from_mw`
-   `p_to_mw`
-   `q_from_mvar`
-   `q_to_mvar`
-   Line `r`, `x`, and optionally `b`
-   Rating/thermal limit if available
-   `in_service` / edge validity
-   Per-feature observation masks
-   Optional quality/noise flags

## 6.4 Graph and tensor representation

``` text
node_tensor:             [T, N_bus, F_node]
edge_tensor:             [T, N_line, F_edge]
edge_index:              [2, N_line]
node_observed_mask:      same feature shape as node_tensor
edge_observed_mask:      same feature shape as edge_tensor
line_status:             [T, N_line]
edge_validity_mask:      [T, N_line]
node_targets_clean:      complete clean node values before masking
edge_targets_clean:      complete clean edge values before masking
grid_id:                 grid identifier
timestamps:              [T]
```

For graph batching, preserve node/edge offsets, valid-edge masks, and
`grid_id`. Padded edges must not participate in message passing.

## 6.5 Mask convention

Adopt one consistent convention; the reviewed STGNI paper uses
`1 = missing`, `0 = observed`.

``` text
observed: value=0.42, missing_mask=0
missing:  placeholder=0.00, missing_mask=1
```

A zero placeholder is not a measurement. The mask carries availability
information.

# 7. Output specification

## 7.1 Direct model predictions

  -----------------------------------------------------------------------
  Output            Unit              Head              Priority
  ----------------- ----------------- ----------------- -----------------
  `p_from_mw`,      MW                Line head         Primary
  `p_to_mw`                                             

  `q_from_mvar`,    Mvar              Line head         Primary
  `q_to_mvar`                                           

  `vm_pu`           p.u.              Bus head          Secondary

  `va_degree`       degrees           Bus head          Secondary;
                                                        reference
                                                        alignment
                                                        required
  -----------------------------------------------------------------------

## 7.2 Derived outputs

-   `i_from_ka`, `i_to_ka`: derive from coherent voltage/complex-power
    quantities or validated AC solution; validate separately.
-   `loading_percent`: derive using current and a known thermal rating;
    omit if rating/status is unavailable.
-   Physics-validation flags.
-   Quality/uncertainty metadata only after meaningful calibration.

Bus active/reactive injections are initially contextual inputs or
optional later targets. Do not expand the first target set without a
requirement and evidence.

## 7.3 Suggested output record

``` json
{
  "grid_id": "simbench_grid_id",
  "timestamp": "simulation_timestamp",
  "component_id": "line_or_bus_id",
  "feature": "p_from_mw",
  "value": 12.34,
  "unit": "MW",
  "measurement_status": "estimated",
  "equipment_status": "in_service",
  "missingness_reason": "simulated_telemetry_loss",
  "quality_score": null,
  "physics_validation": "passed",
  "model_version": "reconstruction_model_version"
}
```

Use `observed`, `estimated`, and `unavailable/abstained` statuses.
`quality_score` remains null until a calibrated method exists. Preserve
original observed values.

# 8. Proposed GridMind architecture

``` text
Node measurements + node masks ─────┐
Line measurements + edge masks ─────┼─> Missingness-aware input encoder
Topology + electrical attributes ───┤
Equipment status + quality flags ───┘
                   |
                   v
       Edge-conditioned graph GNN
          (GCN/GAT/message passing)
                   |
                   v
             Causal GRU
       (current and past only)
                   |
          Shared representation
                   |
          ┌────────┴────────┐
          v                 v
     Line head           Bus head
 P_from/P_to/Q_from/   vm_pu; optional
       Q_to              va_degree
          └────────┬────────┘
                   v
       Restore trusted observations
                   |
                   v
        Physics/quality validation
                   |
                   v
    Derive current/loading where valid
                   |
                   v
    Values + units + status + quality
```

### 8.1 Missingness-aware encoder

Fuse normalized readings with feature-level masks. Missing placeholders
must not be interpreted as real measurements. Keep equipment status and
edge validity as separate inputs.

### 8.2 Edge-conditioned graph encoder

Learn relationships between buses and connected lines, using electrical
line attributes. Candidate implementations are GCN, GAT/edge-aware GAT,
or edge-conditioned message passing. Start with a manageable encoder and
compare alternatives in ablations.

### 8.3 Causal GRU

Use only the current and past values:

`[t-L+1, ..., t-2, t-1, t]`

Do not use `t+1` or later observations in live inference. A
bidirectional/offline backfill mode can be studied separately and
labelled clearly.

### 8.4 Two heads

-   Line head: four line-end P/Q channels.
-   Bus head: voltage magnitude; angle only after reference alignment is
    handled.

A shared encoder with separate heads avoids a separate large model for
every signal while allowing target-specific decoding and loss weights.

### 8.5 Physics/post-processing

Start with status checks, numerical bounds, electrical residuals, and
pandapower validation where feasible. Preserve observations. Derive
current/loading only with coherent inputs and known ratings. Add
physics-guided correction only after the baseline is stable and the
constraint is formulated correctly.

**This GNN + causal GRU + two-head design is GridMind's proposed
implementation, not the exact architecture of any of the four papers.**

# 9. Data preparation and training protocol

1.  Pin one SimBench HV/EHV grid and its profile/version.
2.  Load buses, branches, endpoints, impedances, ratings,
    load/generation profiles, and status.
3.  Define dispatch/reactive assumptions where profiles are incomplete.
4.  Run pandapower AC power flow at selected timestamps.
5.  Log solver settings and convergence; reject failed solves from clean
    targets.
6.  Save clean voltage, angle, line P/Q, current, loading, and equipment
    status before masking.
7.  Generate noisy observations separately from clean targets.
8.  Create random, channel, continuous, spatially correlated, and mixed
    missingness.
9.  Split chronological blocks/scenarios before windows and masks.
10. Proposed GridMind split: 70% train / 15% validation / 15% test. This
    is a proposal, not a split reported by all papers.
11. Add a purge boundary at least as long as the history lookback.
12. Fit normalization only on training data; save scalers and
    denormalize for physical-unit metrics.
13. Build causal windows; do not cross split boundaries.
14. Batch graphs while preserving valid-edge masks and grid IDs.
15. Save an experiment manifest: dataset version, grid/profile ID,
    solver/software versions, assumptions, time range, split boundaries,
    seeds, masks, noise, feature schema, scaler, and failed solves.

# 10. Missingness scenarios

  -----------------------------------------------------------------------
  Scenario                            Description
  ----------------------------------- -----------------------------------
  Random point loss                   Individual feature values hidden

  Rate sweep                          10%, 30%, 50%, 70%, 90% missing

  Continuous gap                      Same channel missing for
                                      consecutive time steps

  Whole-line channel loss             Multiple readings for one line
                                      disappear

  Spatially correlated loss           Neighboring buses/lines lose
                                      telemetry together

  Mixed loss                          Random + continuous/spatial
                                      patterns

  Topology change                     Physical line status changes; not a
                                      missing measurement

  Noise/bias                          Reading remains present but is
                                      degraded
  -----------------------------------------------------------------------

Match gap duration to sampling cadence. A step is 15 minutes in one
dataset and one hour in another unless explicitly resampled.

# 11. Loss, baselines, and ablations

## Proposed loss

A masked multi-target reconstruction loss computed only on deliberately
hidden values:

``` text
L = weighted_error(hidden line P/Q)
  + weighted_error(hidden bus voltage)
  + optional regularization
  + optional physics penalty (later, after validation)
```

Use per-feature scaling/weights because MW, Mvar, p.u., and degrees
differ. MAE is a practical starting point; compare alternatives. Never
leak clean hidden targets through derived inputs or future readings.

## Essential baselines

1.  Persistence / last observation.
2.  Interpolation (offline reference; not causal if it uses future
    values).
3.  Temporal-only GRU.
4.  Graph-only GCN/GAT.
5.  Combined GNN + causal GRU.
6.  GSP-WLS for the compatible voltage-state estimation task.

Literature baselines to consider, not all mandatory: BRITS, SAITS,
MTC-GNN, CC-GAIN, G-LSTM, GRU, LSTM, GAN, DCRNN, AGCRN, STGCN, STSGCN,
BSVT, SoftWalk, CSDI, and matrix completion.

## Ablations

-   No graph vs graph encoder.
-   No temporal layer vs GRU.
-   No mask vs explicit masks.
-   Shared model vs separate heads.
-   No physics checks vs physics checks.
-   Different lookback lengths.
-   GCN vs GAT/edge-conditioned GNN.
-   Causal vs offline bidirectional mode, if offline mode is built.

# 12. Evaluation

Report results separately by feature, missingness rate, pattern, gap
duration, and grid.

**Reconstruction metrics** - MAE. - RMSE. - NRMSE (state normalization
definition). - SMAPE only with near-zero handling. - R² (coefficient of
determination, not classification accuracy). - P95/P99 absolute error. -
Errors on heavily loaded/critical lines. - Inference latency.

Report physical units after denormalization. For voltage angles, align
reference conventions and use angle-aware errors.

**Physical checks** - Fraction outside valid bounds. -
Electrical/power-flow residuals. - Nodal consistency. - Line status vs
reconstructed flow consistency. - Validity of derived current/loading. -
Number of flagged/abstained predictions.

**Downstream utility** - Does reconstruction improve or harm overload
diagnosis? - Does it improve cascade-risk input quality? - Does it
destabilize downstream decisions? - Can the dashboard clearly show
estimated vs observed values?

Do not invent an "accuracy percentage." This is continuous-value
reconstruction, not classification. Do not compare paper RMSEs across
incompatible signals/grids/units.

# 13. Reliability and operational behaviour

-   Preserve trusted observed readings unchanged.
-   Mark every reconstructed value as estimated.
-   Keep telemetry status separate from physical equipment status.
-   If `in_service=false`, do not reconstruct a normal flow.
-   If equipment status is unknown, flag and avoid high-confidence
    output.
-   If too many sensors are missing, return low quality or abstain.
-   If physical checks fail, flag the result and provide a
    fallback/abstention state.
-   Do not expose an uncalibrated confidence probability.
-   Never feed unflagged estimates downstream.
-   Dashboard states should distinguish observed, estimated,
    unavailable, and out-of-service.

In real operation, truly missing values often have no ground truth.
Quantitative accuracy is therefore measured in simulation by hiding
values whose clean originals are retained.

# 14. Implementation milestones

**M1 --- Data correctness:** one SimBench network; 1,000 validated AC
states; clean bus voltage and line P/Q; unit/status/convergence checks.

**M2 --- Masks and baselines:** reproducible random/block masks, clean
truth separated from observations, chronological split,
persistence/interpolation baselines.

**M3 --- Graph-only line reconstruction:** graph tensors, GCN/GAT, line
P/Q reconstruction and evaluation.

**M4 --- Temporal model and bus head:** causal GRU, bus voltage
magnitude, angle only after reference handling; compare graph-only,
temporal-only, combined.

**M5 --- Physics and uncertainty:** status-aware checks, derive
current/loading, quality/abstention, out-of-service tests.

**M6 --- Integration:** API/service contract, dashboard,
observed/estimated flags downstream, held-out time/regime and NREL-118
tests.

# 15. Risks and open decisions

  -----------------------------------------------------------------------
  Risk                                Mitigation
  ----------------------------------- -----------------------------------
  Cross-grid topology/feature         Stable physical schema; separate
  differences                         grid IDs; honest held-out tests

  NREL dispatch/reactive setpoints    Document assumptions; solve AC
  incomplete                          feasibility; reject infeasible
                                      cases

  Only 8,760 NREL hourly positions    Use SimBench diversity and
                                      controlled perturbations; do not
                                      count masks as new states

  Bidirectional leakage               Causal GRU for live mode

  PMU/SCADA cadence mismatch          Keep 50 Hz ATL-GNN experiment
                                      optional

  Rare large errors                   P95/P99 and critical-line metrics

  Missing equipment ratings           Only report loading where rating
                                      exists

  Power-flow failures                 Log and reject invalid target
                                      states

  No labels for truly lost real       Evaluate on deliberately hidden
  readings                            simulated ground truth

  Unrealistic perfect simulation      Add noise, bias, quantization,
                                      delay stress tests

  Confidential paper datasets         Do not claim reproduction

  Uncalibrated confidence             Calibrate before showing a
                                      probability
  -----------------------------------------------------------------------

# 16. Current recommended specification

  -----------------------------------------------------------------------
  Element                             Decision
  ----------------------------------- -----------------------------------
  Main task                           Reconstruct missing readings for
                                      in-service equipment

  Primary dataset                     SimBench HV/EHV with AC
                                      power-flow-generated measurements

  Independent evaluation              NREL-118, with solved measurements
                                      verified/generated

  Primary targets                     Line P/Q at both ends

  Secondary targets                   Bus `vm_pu`, then `va_degree` if
                                      aligned

  Inputs                              Recent node/edge values, topology,
                                      line electrical attributes, masks,
                                      equipment status, quality flags

  Model                               Missingness-aware edge-conditioned
                                      GNN + causal GRU

  Heads                               Shared encoder; separate line and
                                      bus heads

  Current/loading                     Derived, not initial independent
                                      prediction heads

  Physics                             Validate first; physics-guided
                                      correction later

  Split                               Proposed chronological 70/15/15
                                      before windows/masks

  Tests                               Random, channel, continuous,
                                      spatially correlated, mixed

  Metrics                             MAE, RMSE, NRMSE, careful SMAPE,
                                      R², P95/P99, critical-line error,
                                      latency

  Safety                              Preserve observations; separate
                                      equipment and measurement masks;
                                      flag/abstain when invalid
  -----------------------------------------------------------------------

# 17. Research references

1.  **STGNI --- Ping Li et al. (2026).** *Applied Energy* 411, 127604.
    https://doi.org/10.1016/j.apenergy.2026.127604
2.  **ATL-GNN --- Bo Li et al. (2025 preprint).** *A Graph Neural
    Network with Auxiliary Task Learning for Missing PMU Data
    Reconstruction.* https://arxiv.org/abs/2512.24542
3.  **GSP-WLS --- L. Dabush, A. Kroizer, T. Routtenberg (2023).** *State
    Estimation in Partially Observable Power Systems via Graph Signal
    Processing Tools.* *Sensors* 23(3), 1387.
    https://doi.org/10.3390/s23031387
4.  **PSTG-ODF --- W. Wei et al. (2026).** *Measurement data recovery
    for power distribution systems based on physics-guided
    spatio-temporal graph neural network and online data fusion.*
    *Energy and AI* 24, 100754.
    https://doi.org/10.1016/j.egyai.2026.100754

# 18. Evidence rules for future use

-   Separate paper-reported facts from GridMind proposals.
-   Do not claim the proposed GNN + GRU + dual-head model is the exact
    architecture of any paper.
-   Do not claim public SimBench/NREL profiles already contain every
    solved telemetry channel.
-   Do not claim access to confidential provincial-grid or feeder
    measurements.
-   Do not equate R² or `1 − MSPE` with classification accuracy.
-   Do not rank raw metrics across incompatible datasets, signals, and
    units.
-   Do not claim cross-grid generalization until it is tested.
-   Do not present estimates as observed measurements.
-   Treat proposed split ratios, volume targets, architecture, and
    milestones as engineering recommendations.

**Bottom line:** The component is a topology-aware, mask-aware, causal
spatio-temporal reconstruction service. It first recovers line
active/reactive power on in-service transmission equipment, then adds
bus-voltage reconstruction. The recommended practical model is a shared
edge-conditioned GNN + causal GRU with separate line and bus heads,
followed by physics validation, derived quantities, and explicit
status/quality flags.
