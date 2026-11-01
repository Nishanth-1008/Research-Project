# Version B — Stage 1: Stationary Calibration and Baseline Failure Report

**Simulator version:** `sim-2.0.0`  
**Parameter version:** `params-v2.0`  
**Ecological renewal:** Logistic growth: $G(R_t) = g R_t (1 - R_t / K)$  
**Baseline parameters:** $K = 500$, $R_0 = 350$, $g = 0.10$, $c = 0.20$, $E_0 = 10.0$, $E_{\max} = 20.0$, $N = 50$, $T = 2000$, $\beta = 2.0$, $\alpha = 0.10$, $\gamma = 0.95$.  

## 1. Executive Summary

Version B Stage 1 replaces the linear difference renewal model of Version A with standard discrete-time logistic growth ($g=0.10$, maximum sustainable growth $G_{\max} = 12.5$ units/step). Independent group evaluation reveals an **unequivocal calibration failure** for both Q-only and evolving-joint populations. While fixed-only populations maintain ecological stability near $33\%$ capacity ($R \approx 164$), any population containing Q-learning agents rapidly collapses the resource pool to $\le 1$ unit ($< 0.2\%$ capacity) within 15–20 steps. Crucially, the population remains at full capacity (50 agents) across all 2,000 steps due to artificial demographic buffering from initial energy reserves ($E_0 = 10.0$) and scheduled vacancy replenishment, decoupling population survival from ecosystem health.

## 2. Independent Calibration Acceptance Results

| Acceptance Criterion | Fixed-Only | Q-Only | Evolving Joint | Status |
| --- | :---: | :---: | :---: | :---: |
| **1. 2,000-Step Population Retention** ($\ge 80\%$) | 10/10 | 10/10 | 10/10 | PASS (all groups) |
| **2. Resource Band (5%–95% $K$)** ($\ge 20\%$ per group) | 100.0% (PASS) | 0.4% (**FAIL**) | 0.7% (**FAIL**) | **FAIL** (Q & Evolving) |
| **3. Empty Resource Pool Steps** ($\le 10\%$ per group) | 0.0% (PASS) | 99.6% (**FAIL**) | 99.3% (**FAIL**) | **FAIL** (Q & Evolving) |
| **4. Homogeneous Survival $\ge 200$ Steps** | PASS | PASS | N/A | PASS |
| **5. Evolving Mixed Turnover Observed** | N/A | N/A | PASS (1625 repl.) | PASS |
| **6. Non-Floor Operation** ($R > 5\% K$) | PASS | **FAIL** | **FAIL** | **FAIL** |

## 3. Quantitative Trajectory Summary

| Group | Mean Resource (units) | Mean % Capacity | Mean Net Reward | Mean Replacements/Run | Extinctions |
| --- | :---: | :---: | :---: | :---: | :---: |
| `fixed_only` | 163.69 | 32.74% |  0.014 | 1000.0 | 0/10 |
| `q_only` |   0.78 |  0.16% | -0.196 | 1607.6 | 0/10 |
| `evolving_joint` |   1.15 |  0.23% | -0.195 | 1625.1 | 0/10 |

## 4. Q-Learning Action Distribution Analysis

To diagnose whether depletion stems from active aggressive over-harvesting or indiscriminate action choice under uninformative signals, we analyzed the action distribution across 10 seeds:

| Action | Phase 1 (Steps 1–20: Depletion) | Phase 2 (Steps 21–2000: Depleted Floor) |
| --- | :---: | :---: |
| `rest` |   1878 ( 18.8%) |  211652 ( 25.0%) |
| `conservative` |   2803 ( 28.0%) |  211522 ( 25.0%) |
| `moderate` |   2774 ( 27.7%) |  211635 ( 25.0%) |
| `aggressive` |   2545 ( 25.4%) |  211574 ( 25.0%) |

### Diagnostic Interpretations

1. **Phase 1 (Drawdown):** Harvesting actions account for **81.4%** of decisions during the first 20 steps. Because all agents start with zeroed Q-tables, action selection is driven by initial $\varepsilon$-exploration (20%) and weak initial reinforcement. Every harvest attempt returns positive energy while resource exists, quickly draining $R_0 = 350$ to $0$.
2. **Phase 2 (Depleted Floor):** Once $R \le 1$, action distribution flattens to an almost exact uniform distribution (~25.0% across all four actions). In this regime, the Q-table cannot distinguish between actions because all harvesting actions receive zero harvested energy and yield the exact same reward: $-c = -0.20$. Resting also yields $-c = -0.20$. Thus, agents do not persist in aggressive harvesting out of high valuation; rather, the action space collapses into an uninformative, undifferentiated state.

## 5. Starvation, Buffer Energy, and the Replacement Mask

A critical structural discovery in Stage 1 is the decoupling between ecological collapse and demographic extinction:

- **Endowment Buffer:** Newborn agents enter with $E_0 = 10.0$ energy units. At $c = 0.20$ maintenance per step, an agent can survive for up to 50 consecutive steps under absolute zero harvest.
- **Staggered Replacement:** Waves of starvation begin around step 70–80. At step 80 and step 100 (scheduled replacement intervals), vacancies are immediately filled by new agents endowed with another $E_0 = 10.0$ energy units.
- **Demographic Subsidization:** The ecosystem is kept populated not through ecological self-sufficiency, but via the continuous injection of new metabolic energy through demographic turnover. In `static_mixture`, fixed-rule agents refuse to harvest at low resource and starve to death, requiring continuous founder injections ($25$ per mortality cycle).

## 6. Official Decision


**CALIBRATION REJECTED: Model Version B is NOT suitable for main hypothesis testing.**


Proceeding to main batch runs under this configuration would result in degenerate experimental outcomes: sudden shocks at step 1,000 would occur on an already-depleted resource ($R \approx 0$), producing uninformative recovery metrics. Per the research protocol and controlled testing sequence, this calibration failure is logged as formal evidence in `results_v2/` and `calibration_logs/`. No changes to parameters or rewards will be introduced until the research direction is explicitly confirmed.