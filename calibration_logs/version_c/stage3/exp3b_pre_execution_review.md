# Experiment 3B: Pre-Execution Implementation Review & Audit Verification

**Date:** 2026-11-01  
**Status:** Implementation Complete; 6/6 Unit Tests Passed; Control Reproducibility Verified (100% match with frozen Stage 2 C-76F); **Simulation Runs Paused Pending Approval**  
**Source Code:** `simulator_v3/experiments/stage3/exp3b_harvest_quotas.py`  
**Batch Runner:** `simulator_v3/experiments/stage3/run_exp3b.py`  
**Test Suite:** `simulator_v3/experiments/stage3/tests/test_exp3b_harvest_quotas.py`  
**Experimental Plan:** `calibration_logs/version_c/stage3/stage3b_experimental_plan.md`  

---

## 1. Executive Summary & Audit Verification

In accordance with the conditionally approved Stage 3B plan, the graded harvest quota simulator and diagnostic test suite have been implemented and verified. The full batch of 40 simulation runs (10 Control + 30 Treatments across 2,000 steps) **has not been executed** and remains paused.

### Summary of Implementations & Verifications:
1. **Four-Level Graded Quota Matrix Implemented:**
   - Universal proportional scaling across all four actions (`aggressive`, `moderate`, `conservative`, `rest`), applying equally to Fixed and Q-learning agents.
   - Preserves policy neutrality and action-space cardinality.
2. **Strict Version C Demographic Baseline Preserved:**
   - Reproduction remains strictly parent-funded and **type-restricted** matching frozen `C-76F`.
   - Retiring agents (`age >= 100`) are strictly excluded from parent eligibility.
   - Strict energy condition $E > 10.0$ rechecked dynamically inside the vacancy loop.
3. **Comprehensive Demand and Metabolic Telemetry Added:**
   - Tracks requested vs. allocated harvest separately for Fixed, Q, and Total population.
   - Tracks reproduction eligibility percentages by type at every 20-step interval.
   - Tracks actual harvest-to-regeneration ratio $\frac{H_{\text{total}}}{G(R)}$.
4. **Unit Test Suite (6/6 PASS):**
   - Verified action scaling across all 4 groups.
   - Verified requested vs. allocated harvest accounting.
   - Verified reproduction eligibility percentage calculation.
   - Verified type-restricted vacancy blocking.
   - Verified retiring agent exclusion.
   - Verified energy conservation ($\Delta E < 10^{-10}$) across all 4 quota levels.
5. **Control Reproducibility Audit:**
   - Control mode executed against seeds 1001–1010 and compared against frozen `C-76F` results.
   - **Total step mismatches across all 1,000 step-records:** **0**.
   - Energy conservation verified to machine precision ($\Delta E < 6.0 \times 10^{-11}$).

---

## 2. Detailed Implementation Description & Code Architecture

### A. Canonical Action Space & Quota Scaling Matrix
`simulator_v3/agents.py` canonically defines four actions: `ACTIONS = ("rest", "conservative", "moderate", "aggressive")`.
Fixed agents evaluate: `{"low": "rest", "medium": "conservative", "high": "moderate"}[resource_band]`.
Q-learning agents explore across all 4 actions, maintaining 4 Q-values per state tuple.

The lookup dictionary `QUOTA_HARVEST_REQUESTS` in `exp3b_harvest_quotas.py` applies proportional scaling across all four canonical actions:

```python
QUOTA_HARVEST_REQUESTS: dict[QuotaGroup, dict[str, float]] = {
    "control":     {"rest": 0.0, "conservative": 0.500, "moderate": 1.000, "aggressive": 2.000},
    "treatment_a": {"rest": 0.0, "conservative": 0.375, "moderate": 0.750, "aggressive": 1.500},
    "treatment_b": {"rest": 0.0, "conservative": 0.250, "moderate": 0.500, "aggressive": 1.000},
    "treatment_c": {"rest": 0.0, "conservative": 0.1875, "moderate": 0.375, "aggressive": 0.750},
}
```

### B. Action Execution & Requested vs. Allocated Harvest Accounting
In `step()`, agents choose actions using their unchanged policy/Q-table. Harvest requests are evaluated using the group's quota dictionary, and requested harvest is logged before allocation:

```python
# Track requested harvest by type
fixed_requested = sum(
    self.harvest_requests[decisions[a.identifier][1]]
    for a in self.agents
    if a.kind == "fixed"
)
q_requested = sum(
    self.harvest_requests[decisions[a.identifier][1]]
    for a in self.agents
    if a.kind == "q_learning"
)
total_requested = fixed_requested + q_requested

# Allocation in randomized order against available resource
allocation_order = self.agents.copy()
self.stream_env.shuffle(allocation_order)
remaining_resource = self.resource
harvested: dict[int, float] = {}

for agent in allocation_order:
    requested = self.harvest_requests[decisions[agent.identifier][1]]
    allocated = min(requested, remaining_resource)
    harvested[agent.identifier] = allocated
    remaining_resource -= allocated
```

### C. Reproduction Eligibility Telemetry
At each replacement step (`step_number % 20 == 0`), reproduction eligibility percentages among living, non-retiring agents are recorded prior to executing reproduction:

```python
if step_number % self.parameters.replacement_interval == 0 and self.agents:
    non_ret = [a for a in self.agents if a.age < self.parameters.maximum_age]
    living_f = [a for a in non_ret if a.kind == "fixed"]
    living_q = [a for a in non_ret if a.kind == "q_learning"]
    elig_f = [a for a in living_f if a.energy > self.parameters.reproduction_cost]
    elig_q = [a for a in living_q if a.energy > self.parameters.reproduction_cost]

    pct_fixed_eligible = (len(elig_f) / len(living_f) * 100.0) if living_f else 0.0
    pct_q_eligible = (len(elig_q) / len(living_q) * 100.0) if living_q else 0.0
```

---

## 3. Unit Test Suite Results (6/6 PASS)

The test suite in `simulator_v3/experiments/stage3/tests/test_exp3b_harvest_quotas.py` passed with zero errors:

```text
Ran 6 tests in 0.006s

OK
```

### Verification Matrix:

| # | Test Name | Purpose / Assertion | Result |
| :--- | :--- | :--- | :--- |
| 1 | `test_1_action_space_scaling_matrix` | Verifies correct numeric values for all 4 actions across all 4 quota groups. | **PASS** |
| 2 | `test_2_requested_vs_allocated_harvest_accounting` | Verifies disaggregated requested vs allocated harvest tracking under abundant resource. | **PASS** |
| 3 | `test_3_type_restricted_reproduction_enforced` | Confirms Q agents cannot fund Fixed vacancies when Fixed agents die (0 births, 38 unfunded). | **PASS** |
| 4 | `test_4_retiring_agents_cannot_reproduce` | Confirms agents at age 100 cannot reproduce; produces 0 births, 1 retirement, 50 unfunded vacancies. | **PASS** |
| 5 | `test_5_reproduction_eligibility_tracking` | Confirms exact percentage calculation of eligible parents ($E > 10.0, \text{age} < 100$) by type. | **PASS** |
| 6 | `test_6_energy_conservation_across_all_quotas` | Executes 25 steps across all 4 quota groups; confirms $\Delta E < 10^{-10}$ in every group. | **PASS** |

---

## 4. Control Reproducibility Verification against Frozen Stage 2 `C-76F`

To ensure that the quota simulator does not alter baseline Version C dynamics, `Experiment3BSimulator(quota_group="control")` was run across all 10 matched seeds (1001–1010) and compared step-by-step against `results_v3/stage2_mechanism/c2c_mixtures/C-76F_summary.csv` and `C-76F_timeseries.csv`:

- **Total step-records evaluated:** 1,000 steps (10 runs $\times$ 100 steps).
- **Resource trajectory discrepancies ($|R_{\text{control}} - R_{\text{frozen}}|$):** $0.0$ ($< 10^{-9}$ across all steps).
- **Harvest discrepancies ($|H_{\text{control}} - H_{\text{frozen}}|$):** $0.0$ ($< 10^{-9}$ across all steps).
- **Population count discrepancies:** $0$ across all steps.
- **Total step mismatches:** **0**.
- **Energy conservation:** PASS across all 10 seeds (maximum discrepancy $= 5.98 \times 10^{-11}$).

---

## 5. Mechanism Isolation & Verification of Unchanged Behavior

Treatment alters **strictly one variable**: the harvest request amounts returned by the action lookup table.
- **What Remains 100% Identical to Version C Baseline:**
  - Initial population composition: Exactly 38 Fixed / 12 Q-learning ($N = 50$).
  - Action selection algorithm: Fixed policy logic and Q-learning $\varepsilon$-greedy action selection are unchanged.
  - State space representation: 3-tuple $(R_{\text{band}}, E_{\text{band}}, \Delta R_{\text{trend}})$ identical.
  - Reward function: Net energy change $r_t = \Delta E_t = H_i - m$.
  - Environment: Logistic regrowth parameters ($g = 0.10, K = 500, R_0 = 350$), maintenance cost ($m = 0.20$), maximum energy ($E_{\max} = 20.0$).
  - Reproduction: Strict type-restricted parent-funded reproduction (parent must have $E > 10.0$ and $\text{age} < 100$).
  - PRNG Streams: Independent streams for environmental allocation (`stream_env`) and agent decisions (`stream_agents`) using matched seeds 1001–1010.

---

## 6. Execution Gate

All pre-execution implementation steps, unit tests, and baseline reproducibility audits are complete.  
The batch execution of the 40 simulation runs (10 Control + 10 Treatment A + 10 Treatment B + 10 Treatment C $\times$ 2,000 steps) in `run_exp3b.py` **remains paused and will not be launched until you review and grant formal approval.**

