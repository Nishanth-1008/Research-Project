# Stage 3B Experimental Plan: Graded Harvest Quotas

**Document:** `calibration_logs/version_c/stage3/stage3b_experimental_plan.md`  
**Date:** 2026-11-01  
**Status:** Approved Plan; Implementation Pending Pre-Execution Audit  
**Baseline Model:** Version C Architecture (`sim-3.0.0`, `params-v3.0`, `C-76F` Demographic Rules)  
**Target Simulator:** `simulator_v3/experiments/stage3/exp3b_harvest_quotas.py`  
**Target Runner:** `simulator_v3/experiments/stage3/run_exp3b.py`  
**Target Tests:** `simulator_v3/experiments/stage3/tests/test_exp3b_harvest_quotas.py`  
**Target Output Directory:** `results_v3/stage3_mechanism_isolation/exp3b/`  

---

## 1. Central Research Question & Conceptual Distinction

> **Primary Question:** Is ecological collapse caused by the harvesting behavior itself, or by the fact that the environment cannot support the aggregate harvesting demand permitted by the unconstrained action space?

Experiment 3A established that changing reproduction rules does not prevent ecological collapse when resource replenishment cannot match extraction. Stage 3B isolates the ecological mechanism by directly testing how systematic reductions in per-capita harvesting limits affect resource stability and population viability.

---

## 2. Theoretical Carrying Capacity & Regeneration Analysis

The logistic regeneration equation with baseline parameters ($g = 0.10, K = 500$) is:
$$G(R) = 0.10 R \left(1 - \frac{R}{500}\right)$$
Maximum regeneration occurs strictly at $R = 250$, yielding $G_{\max} = 12.50\text{ units/step}$.

For a given constant aggregate extraction rate $D$, the system can maintain a non-declining resource level ($\Delta R = G(R) - D \ge 0$) only when $R$ lies between the roots of $0.10 R (1 - R/500) = D$:
$$R^2 - 500R + 5000D \le 0 \implies R \in \left[250 - \sqrt{62500 - 5000D},\; 250 + \sqrt{62500 - 5000D}\right]$$

### Exact Sustainable Resource Ranges by Demand Level

| Constant Demand Rate ($D$) | Feasible Range for $G(R) \ge D$ | Theoretical Notes |
| :---: | :---: | :--- |
| **$24.0$ units/step** | **None** ($D > G_{\max} = 12.5$) | Unconstrained 12 Q aggressive demand guarantees collapse from any starting $R$. |
| **$18.0$ units/step** | **None** ($D > G_{\max} = 12.5$) | Treatment A 12 Q aggressive demand guarantees collapse from any starting $R$. |
| **$12.0$ units/step** | **$200.0 \le R \le 300.0$** | Treatment B 12 Q aggressive demand requires resource to stay in a narrow 100-unit band. |
| **$9.0$ units/step** | **$138.2 \le R \le 361.8$** | Treatment C 12 Q aggressive demand sustainable across a 223.6-unit band. |
| **$6.0$ units/step** | **$77.5 \le R \le 422.5$** | Sustainable across a wide 345.0-unit band. |

*Important Caveat:* These calculations represent static benchmarks under hypothetical Q-only demand. In reality, actual resource trajectories depend on dynamic action choices, full population demand (including Fixed agents), and PRNG exploration.

---

## 3. Experimental Design & Treatment Groups

### A. Action Space Matrix Across Groups

Harvest quotas are scaled universally across both Fixed and Q-learning agents to preserve policy neutrality across all four canonical actions (`rest`, `conservative`, `moderate`, `aggressive`):

| Group | Treatment Label | Scaling Factor | `aggressive` (Idx 3) | `moderate` (Idx 2) | `conservative` (Idx 1) | `rest` (Idx 0) | 12 Q Max Demand | Full Pop ($N=50$) Max Demand |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Control** | Baseline (`C-76F`) | $\times 1.000$ | **2.000** | **1.000** | **0.500** | **0.000** | $24.0$ units/step | $100.0$ units/step |
| **Treatment A** | $-25\%$ Quota | $\times 0.750$ | **1.500** | **0.750** | **0.375** | **0.000** | $18.0$ units/step | $75.0$ units/step |
| **Treatment B** | $-50\%$ Quota | $\times 0.500$ | **1.000** | **0.500** | **0.250** | **0.000** | $12.0$ units/step | $50.0$ units/step |
| **Treatment C** | $-62.5\%$ Quota | $\times 0.375$ | **0.750** | **0.375** | **0.1875** | **0.000** | $9.0$ units/step | $37.5$ units/step |

*Fixed-Agent Policy Mapping:* Fixed agents deterministically choose `{"low": "rest", "medium": "conservative", "high": "moderate"}` based on $R_{\text{band}}$. `aggressive` is strictly an exploratory or learned choice for Q-learning agents. All four actions are available to Q-learning agents.

### B. Unchanged Version C Parameters (Strict Isolation)
- **Initial Population:** Exactly 38 Fixed / 12 Q-learning ($N_0 = 50$, $76\%$ Fixed).
- **Environment:** $K = 500$, $g = 0.10$, $R_0 = 350$, scenario = `"stationary"`.
- **Maintenance & Energy:** $m = 0.20$/step, $E_{\max} = 20.0$, initial founder energy $E_0 = 10.0$.
- **Demographics:** Maximum age $= 100$, replacement interval $= 20$.
- **Reproduction Rules:** Strictly parent-funded and **type-restricted**, matching `C-76F` (vacancies target deficit type; candidate must have $E > 10.0$; candidate loses $10.0$ and newborn receives $10.0$; retiring agents at `age >= 100` are strictly excluded).
- **Q-Learning Algorithm:** $\alpha = 0.10, \gamma = 0.95, \varepsilon = 0.20 \to 0.02$ age-decay, state representation $(R_{\text{band}}, E_{\text{band}}, \Delta R_{\text{trend}})$, reward $r_t = \Delta E_t$. Action-selection logic, exploration schedules, and reward functions remain untouched.
- **Seeds:** 10 matched seeds (`1001`–`1010`), totaling 40 runs across 2,000 steps.

---

## 4. Comprehensive Metric & Telemetry Plan

The simulator will record disaggregated demand, allocation, and metabolic telemetry:

### A. Ecological Telemetry (Per Step):
- Current resource $R_t$ and post-harvest remaining resource.
- Actual regeneration $G(R_t)$.
- Resource extraction ratio: $\text{Ratio}_t = \frac{\text{Total Actual Harvest}_t}{G(R_t)}$ (measures ecological pressure).
- Resource state stability: Steps spent in $[100, 350]$, time to first $R < 25$, time to first $R < 1$.
- First resource recovery: Detection of any step where $R$ rebounds by $> 10$ units after falling below $25.0$.

### B. Behavioral & Foraging Demand Telemetry (Per Step):
- **Fixed Requested Harvest** vs. **Fixed Allocated Harvest**.
- **Q Requested Harvest** vs. **Q Allocated Harvest**.
- **Total Requested Harvest** vs. **Total Allocated Harvest** (quantifies unmet demand).
- Action distributions (`rest`, `conservative`, `aggressive`) tracked separately by agent type.

### C. Demographic & Reproductive Telemetry (Per Step & Per Interval):
- Living population count by type (Fixed vs. Q).
- Mean and minimum energy by agent type ($E_{\text{fixed}}, E_{\text{q}}$).
- **Reproduction Eligibility Percentage:** At each replacement step ($20, 40, \dots$), record the exact percentage of living Fixed and Q agents satisfying $E > 10.0$ and $\text{age} < 100$.
- Funded births and unfunded vacancies by type.
- Starvation deaths and retirement deaths by type.

### D. Summary & Evaluation Metrics:
- Mean resource over the first 100 steps (fair comparison against baseline).
- Mean resource over full run duration (reported alongside steps completed).
- Linear resource trend slope over the active lifetime.
- Extinction incidence ($10/\text{group}$) and mean survival steps.
- Numerical energy audit: Machine-precision verification ($\Delta E < 10^{-10}$) using the untouched Version C `EnergyLedger`.

---

## 5. Execution Sequence & Governance Gates

1. **Plan Freezing:** Save this document to `calibration_logs/version_c/stage3/stage3b_experimental_plan.md`.
2. **Implementation:** Create `simulator_v3/experiments/stage3/exp3b_harvest_quotas.py` subclassing `EcosystemSimulator` while altering only the action space lookup table and adding the required telemetry.
3. **Unit Test Suite:** Implement `simulator_v3/experiments/stage3/tests/test_exp3b_harvest_quotas.py` testing:
   - Action scaling for all 4 groups.
   - Energy conservation across quota levels.
   - Strict parent eligibility and retirement exclusion.
   - Requested vs. allocated harvest accounting.
4. **Control Reproducibility Audit:** Execute Control mode against seeds 1001–1010 and verify bitwise/numerical identity against frozen `C-76F` results.
5. **Pre-Execution Report:** Generate `calibration_logs/version_c/stage3/exp3b_pre_execution_review.md` and halt for user review.
6. **Simulation Execution:** Execute the 40 runs only upon explicit approval.
