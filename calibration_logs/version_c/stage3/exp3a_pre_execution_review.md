# Experiment 3A: Pre-Execution Implementation Review & Audit Verification

**Date:** 2026-11-01  
**Status:** Pre-Execution Corrections Applied; 9/9 Unit Tests Passed; Control Reproducibility Verified (100% match with frozen Stage 2 C-76F); **Simulation Runs Paused Pending Approval**  
**Source Code:** `simulator_v3/experiments/stage3/exp3a_type_neutral_reproduction.py`  
**Batch Runner:** `simulator_v3/experiments/stage3/run_exp3a.py`  
**Test Suite:** `simulator_v3/experiments/stage3/tests/test_exp3a_reproduction.py`  

---

## 1. Executive Summary

In accordance with the pre-execution audit instructions, all required corrections have been implemented and verified across unit tests and historical reproducibility checks. The full simulation batch of 20 runs (10 Control + 10 Treatment) **has not been executed** and remains paused.

### Summary of Corrections Applied:
1. **Parent Eligibility Correction:** Retiring agents (`age >= maximum_age`, i.e., age 100) are strictly excluded from `parent_candidates` in both Control and Treatment modes (`parent_candidates = non_retirees.copy()`). An agent due to retire cannot fund a newborn.
2. **Dynamic Strict Energy Recheck:** The strict energy condition (`energy > 10.0`) is evaluated and rechecked dynamically after every energy transfer, ensuring an agent with 18.0 or 20.0 energy can fund at most 1 offspring per replacement step, and an agent with exactly 10.0 cannot reproduce.
3. **Retirement Metric Correction:** `retirement_deaths` in `StepRecord` now records the actual per-step retirement count (`retirement_deaths = step_retirements`), resolving the previous hardcoded `0`. The sum of per-step retirements equals `total_retirement_deaths` exactly across all runs.
4. **True Cross-Type Replacement Accounting:** Implemented rigorous tracking of true cross-type replacements:
   - Q-parent replaces Fixed when living Fixed agents $< 38$ (`cross_type_q_births`).
   - Fixed-parent replaces Q when living Q agents $< 12$ (`cross_type_fixed_births`).
   - Timestamps of first occurrence (`first_cross_type_step`, `first_q_replaces_fixed_step`, `first_fixed_replaces_q_step`).
   - Cumulative cross-type energy transferred (`cumulative_cross_type_energy`).
5. **Expanded Test Suite:** 9 specific diagnostic unit tests created and verified (all 9 PASS).
6. **Control Reproducibility:** 100% bitwise/step-by-step equivalence against frozen Stage 2 `C-76F` across all 10 matched seeds (1,000 steps compared, 0 mismatches, energy discrepancy $< 6.0 \times 10^{-11}$).

---

## 2. Detailed Code Diffs

### A. Parent Eligibility & Retirement Partitioning
Previously, `parent_candidates` was initialized as `self.agents.copy()` before identifying retirees, which theoretically allowed retiring agents to be included in candidate selection. The revised code defines candidates strictly from `non_retirees`:

```python
# --- PREVIOUS (exp3a initial draft) ---
parent_candidates = self.agents.copy()
non_retirees = [a for a in self.agents if a.age < self.parameters.maximum_age]
retirees = [a for a in self.agents if a.age >= self.parameters.maximum_age]

# --- REVISED (Audited Implementation) ---
non_retirees = [a for a in self.agents if a.age < self.parameters.maximum_age]
retirees = [a for a in self.agents if a.age >= self.parameters.maximum_age]
step_retirements = len(retirees)
self.total_retirement_deaths += step_retirements

# Only non-retiring living agents are eligible parent candidates
parent_candidates = non_retirees.copy()
total_vacancies = self.parameters.population_capacity - len(non_retirees)
```

### B. Dynamic Eligibility Recheck and Strict Energy Inequality
In both Control and Treatment, parent eligibility is dynamically filtered on each vacancy iteration:
- Control: `eligible = [a for a in parent_candidates if a.kind == chosen_kind and a.energy > self.parameters.reproduction_cost]`
- Treatment: `eligible = [a for a in parent_candidates if a.energy > self.parameters.reproduction_cost]`

Because `parent.energy -= self.parameters.reproduction_cost` (10.0) mutates the candidate in place:
- An agent with $E = 10.0$: fails strict $> 10.0$, cannot reproduce.
- An agent with $E = 18.0$: after 1 birth, $E = 8.0 < 10.0$, disqualified for subsequent vacancies.
- An agent with $E = 20.0$: after 1 birth, $E = 10.0$, which is not strictly $> 10.0$, disqualified for subsequent vacancies.

### C. StepRecord Retirement Count Correction
Previously, `StepRecord` assigned `retirement_deaths=0`. The revised `step()` method records the exact step count:

```python
# --- PREVIOUS (exp3a initial draft) ---
rec = StepRecord(
    ...,
    births=step_births,
    starvation_deaths=step_starvations,
    retirement_deaths=0,
    unfunded_vacancies=step_unfunded,
    ...
)

# --- REVISED (Audited Implementation) ---
rec = StepRecord(
    ...,
    births=step_births,
    starvation_deaths=step_starvations,
    retirement_deaths=step_retirements,
    unfunded_vacancies=step_unfunded,
    ...
)
```

### D. True Cross-Type Replacement Tracking
In `_replace_vacancies_treatment()`:

```python
# Track true cross-type replacement
if parent.kind == "q_learning" and current_fixed < self.fixed_target:
    step_cross_type_q += 1
    self.cross_type_q_births += 1
    step_cross_type_energy += self.parameters.reproduction_cost
    self.cumulative_cross_type_energy += self.parameters.reproduction_cost
    if self.first_cross_type_step is None:
        self.first_cross_type_step = step_number
    if self.first_q_replaces_fixed_step is None:
        self.first_q_replaces_fixed_step = step_number
elif parent.kind == "fixed" and current_q < self.q_target:
    step_cross_type_fixed += 1
    self.cross_type_fixed_births += 1
    step_cross_type_energy += self.parameters.reproduction_cost
    self.cumulative_cross_type_energy += self.parameters.reproduction_cost
    if self.first_cross_type_step is None:
        self.first_cross_type_step = step_number
    if self.first_fixed_replaces_q_step is None:
        self.first_fixed_replaces_q_step = step_number
```

---

## 3. Unit Test Suite Results (9/9 PASS)

The test suite in `simulator_v3/experiments/stage3/tests/test_exp3a_reproduction.py` covers all 9 required edge cases and mechanisms:

```text
Ran 9 tests in 0.001s

OK
```

### Verification Matrix:

| # | Test Name | Purpose / Assertion | Result |
| :--- | :--- | :--- | :--- |
| 1 | `test_1_exact_10_energy_cannot_reproduce` | Agent with $E = 10.0$ cannot reproduce under strict $> 10.0$. Verifies 0 births, 49 unfunded vacancies. | **PASS** |
| 2 | `test_2_eighteen_energy_funds_only_one_birth` | Agent with $E = 18.0$ funds exactly 1 birth; remaining $E = 8.0$ disqualifies 2nd birth; total energy conserved ($8.0 + 10.0 = 18.0$). | **PASS** |
| 3 | `test_3_twenty_energy_funds_only_one_birth_under_strict_inequality` | Agent with $E = 20.0$ funds exactly 1 birth; remaining $E = 10.0$ fails strict $> 10.0$; cannot fund 2nd birth. | **PASS** |
| 4 | `test_4_q_parent_fills_fixed_deficit_in_treatment` | 5 Q-agents ($E = 15.0$, 0 Fixed) fund 5 births in Treatment; verifies `cross_type_q_births = 5`, `cumulative_cross_type_energy = 50.0`. | **PASS** |
| 5 | `test_5_fixed_parent_fills_q_deficit_in_treatment` | 38 Fixed agents ($E = 15.0$, 0 Q) fund 12 births in Treatment; verifies `cross_type_fixed_births = 12`, `cumulative_cross_type_energy = 120.0`. | **PASS** |
| 6 | `test_6_retiring_agents_cannot_reproduce` | Agent with `age = 100` and $E = 20.0$ cannot reproduce; produces 0 births, 1 retirement, 50 unfunded vacancies; unspent 20.0 energy logged to retirement losses. | **PASS** |
| 7 | `test_7_newborns_do_not_act_or_pay_maintenance_on_birth_step` | Agent created at step 20 has `age = 0`, `energy = 10.0` at end of step 20 (no actions chosen, no harvest, no maintenance deducted on birth step). | **PASS** |
| 8 | `test_8_q_newborn_receives_empty_q_table` | Q-parent with populated Q-table funds newborn; newborn has `q_table == {}` (separate instance). | **PASS** |
| 9 | `test_9_population_capacity_never_exceeded` | 45 living agents ($E = 20.0$) in Treatment fund exactly 5 births to reach $N = 50$; population never exceeds capacity. | **PASS** |

---

## 4. Control Reproducibility Verification against Frozen Stage 2 `C-76F`

To ensure that the corrections did not introduce regression or alter the control baseline, `Experiment3ASimulator(mode="control")` was executed against all 10 matched seeds (1001–1010) and compared directly against `results_v3/stage2_mechanism/c2c_mixtures/C-76F_summary.csv` and `C-76F_timeseries.csv`.

### Step-by-Step Trajectory Comparison:
- **Total step-records evaluated:** 1,000 steps (10 runs $\times$ 100 steps).
- **Resource trajectory discrepancies ($|R_{\text{control}} - R_{\text{frozen}}|$):** $0.0$ ($< 10^{-9}$ across all steps).
- **Harvest discrepancies ($|H_{\text{control}} - H_{\text{frozen}}|$):** $0.0$ ($< 10^{-9}$ across all steps).
- **Living population discrepancies:** $0$ across all steps.
- **Total step mismatches:** **0**.

### Seed-Level Summary Comparison:

| Seed | Frozen C-76F Steps | Control Steps | Frozen Mean Resource | Control Mean Resource | Frozen Extinction | Control Extinction | Energy Conserved | Energy Discrepancy |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1001 | 100 | 100 | 52.5379 | 52.5379 | True | True | True | $5.20 \times 10^{-11}$ |
| 1002 | 100 | 100 | 40.2714 | 40.2714 | True | True | True | $5.43 \times 10^{-11}$ |
| 1003 | 100 | 100 | 46.5871 | 46.5871 | True | True | True | $5.98 \times 10^{-11}$ |
| 1004 | 100 | 100 | 34.1870 | 34.1870 | True | True | True | $5.38 \times 10^{-11}$ |
| 1005 | 100 | 100 | 33.9618 | 33.9618 | True | True | True | $5.05 \times 10^{-11}$ |
| 1006 | 100 | 100 | 41.6222 | 41.6222 | True | True | True | $5.44 \times 10^{-11}$ |
| 1007 | 100 | 100 | 36.7971 | 36.7971 | True | True | True | $5.07 \times 10^{-11}$ |
| 1008 | 100 | 100 | 40.3721 | 40.3721 | True | True | True | $5.44 \times 10^{-11}$ |
| 1009 | 100 | 100 | 67.2573 | 67.2573 | True | True | True | $5.60 \times 10^{-11}$ |
| 1010 | 100 | 100 | 43.8992 | 43.8992 | True | True | True | $5.11 \times 10^{-11}$ |

### Retirement Accounting Verification:
- For every run, `res.total_retirement_deaths == 12` (or 50 if all reached age 100).
- Sum of per-step `rec.retirement_deaths` equals `res.total_retirement_deaths` exactly.
- **Why excluding retiring agents did not alter C-76F:** In Stage 2 C-76F, all fixed agents starved to death at step 75. At step 80, the 12 living Q-agents were age 80 (not retiring). At step 100, the 12 Q-agents reached age 100 with energy $E \approx 8.10 < 10.0$. Because their energy was already below the reproduction threshold, they could not reproduce regardless of whether retiring agents were included or excluded. Thus, the trajectory is identical.

---

## 5. Mechanism Isolation Confirmation

Treatment alters **strictly one mechanism**:
- **Parent Eligibility:** Removes the type-quota restriction. Any living non-retiring parent with $E > 10.0$ may fund an offspring into an available vacancy.
- **What Remains Identical:**
  - Initial population composition (38 Fixed / 12 Q).
  - Seed set (1001–1010) with identical pseudo-random number generator architecture.
  - Parent reproduction cost ($10.0$ units deducted from parent).
  - Newborn energy ($10.0$ units received from parent; $\Delta E = 0.0$; no exogenous subsidy).
  - Logistic resource growth ($g = 0.10, K = 500, R_0 = 350$).
  - Agent decision models, action requests, and maintenance ($0.20$/step).
  - Q-learning parameters ($\alpha = 0.10, \gamma = 0.95, \varepsilon = 0.20 \to 0.02$).
  - Maximum age ($100$) and replacement interval ($20$).

---

## 6. Identified Limitations & Scientific Hypotheses

### What Experiment 3A Will Test:
- In Stage 2 `C-76F`, at step 80 (after all 38 Fixed agents starved at step 75), the 12 living Q-agents had energy $E \approx 11.90 > 10.0$ in several seeds (e.g., Seed 1001, 1009, 1010). Under Control, 38 vacancies were left unfunded because they were reserved for Fixed agents.
- Under Treatment, Q-agents with $E > 10.0$ will fund Q-offspring at step 80, filling up to 12 vacancies.
- **Hypothesis 1 (Resource Depletion):** If Q-agents reproduce at step 80, population will increase (e.g., from 12 to 24). However, higher Q population will dramatically increase harvest pressure on an already depleted resource ($R < 15$), accelerating resource collapse and driving the newly expanded population to extinction by starvation or at step 100.
- **Hypothesis 2 (Demographic Rescue):** Can Q-agents maintain sufficient reproduction to survive beyond step 100? If the resource cannot regenerate faster than $G_{\max} = 12.5$, 24 Q-agents demanding 48 units/step will rapidly drive $R \to 0$.

### Known Implementation Boundaries:
- `Experiment3ASimulator` does not alter Q-learning exploration, rewards, or memory structures.
- It tests demographic neutrality alone, isolating the institutional rule from agent cognitive capabilities.

---

## 7. Execution Gate

All pre-execution corrections, diagnostic tests, and control reproducibility checks are complete.  
The batch execution of the 20 simulation runs (10 Control + 10 Treatment $\times$ 2,000 steps) in `run_exp3a.py` **remains paused and will not be launched until you review and grant formal approval.**
