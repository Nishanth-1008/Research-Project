# Version C Stage 0 Implementation & Validation Report

**Date:** 2026-11-01  
**Simulator Version:** `sim-3.0.0`  
**Parameter Version:** `params-v3.0`  
**Architecture:** Closed Parent-Funded Reproduction with Strict Energy Conservation and Logistic Ecology.

---

## 1. Architectural Design & Step Sequencing

Version C establishes a strictly energy-accountable ecosystem:
- **Reproduction Cost:** 10.0 energy units, transferred dollar-for-dollar from parent to newborn.
- **Strict Parent Eligibility:** `parent.energy > 10.0` (parent must retain positive energy after birth).
- **No Recurring Subsidies:** The 50 founder agents receive $E_0 = 10.0$ units at step 0 ($500.0$ total units recorded as an explicit initial endowment). After step 0, zero external energy enters the population; all new agents must be funded by living parents out of harvested surplus.
- **Unfunded Vacancies:** If no living candidate has energy $> 10.0$, vacancies remain unfilled.

### Unambiguous 13-Stage Step Order:
1. **Observation:** Agents observe current shared resource $R_t$, prior resource $R_{t-1}$, and private energy $E_i$.
2. **Action Selection:** Living agents choose actions according to policy.
3. **Randomized Allocation:** Living agents are randomly permuted and allocated harvest up to available stock.
4. **Energy Update & Cap Losses:** $E_i \leftarrow E_i + H_i - M_i$. Any excess over $E_{\max}=20.0$ is logged as an energy-cap loss.
5. **Maintenance:** Applied exactly once per living agent ($0.20$/step).
6. **Age & Q-value Records:** Age incremented, net energy added to lifetime reward.
7. **Starvation Deaths:** Agents with $E_i \le 0$ die and are removed. Deficits are logged.
8. **Vacancy Identification & Parent Eligibility:** At scheduled intervals (`step % 20 == 0`), living agents reaching `maximum_age` remain eligible as parents for this event, then retire. Vacancies $= N - \text{survivors}$.
9. **Eligible Parent Selection:** Candidates filtered dynamically by $E_{\text{parent}} > 10.0$.
10. **Energy Transfer & Offspring Creation:** $E_{\text{parent}} \leftarrow E_{\text{parent}} - 10.0$; $E_{\text{newborn}} = 10.0$; age $= 0$.
11. **Retirement Execution:** Maximum-age agents retire, and any unspent energy is logged.
12. **Resource Regeneration:** Logistic renewal $G(R) = g R (1 - R/K)$ prepares the resource for step $t+1$.
13. **Metric Recording:** Comprehensive telemetry recorded for the step.

---

## 2. Stage 0 Verification & Unit Test Results

The Stage 0 test suite in `simulator_v3/tests/test_stage0_validation.py` passed with **7/7 checks OK**:

1. **Energy Conservation During Reproduction (`test_energy_conservation_during_reproduction`):**
   - Verified that parent deduction exactly matches newborn starting energy: $\Delta E_{\text{reproduction}} = -10.0 + 10.0 = 0.0$.
2. **Strict Eligibility (`test_parent_eligibility_strict_greater_than_cost`):**
   - An agent with exactly $10.0$ energy is disqualified from reproducing, preventing immediate post-birth starvation.
3. **Multiple Offspring Rechecking (`test_multiple_offspring_rechecking`):**
   - A parent with $18.0$ energy funds 1 offspring (dropping to $8.0$), after which rechecking correctly disqualifies it from funding a second vacancy.
4. **Newborn Timing (`test_newborn_timing_does_not_act_on_birth_step`):**
   - Verified that newborns born at step 20 do not act or pay maintenance until step 21.
5. **Population Capacity (`test_population_capacity_limit`):**
   - Population strictly constrained to $\le 50$ agents.
6. **Resource Bounds (`test_resource_bounds`):**
   - Resource strictly contained in $[0, 500]$.
7. **Type Parity (`test_parity_across_agent_types`):**
   - Identical reproduction accounting applies to fixed-rule and Q-learning agents.

---

## 3. Full-Run Energy Conservation Verification

Running a complete simulation run for each group under Seed 1 confirms absolute energy conservation to machine precision ($\Delta < 10^{-7}$):

- **`fixed_only` (2,000 steps completed):**
  - Conserved: **True** ($\text{discrepancy} = 0.000000037762$)
  - Living agents: 50, living energy: $500.00$
  - Births: 1,000, Starvations: 0, Retirements: 1,000, Unfunded: 0
- **`q_only` (100 steps to extinction):**
  - Conserved: **True** ($\text{discrepancy} = 0.000000000068$)
  - Living agents: 0, living energy: $0.00$
  - Births: 0, Starvations: 33, Retirements: 17, Unfunded: 61
- **`evolving_joint` (100 steps to extinction):**
  - Conserved: **True** ($\text{discrepancy} = 0.000000000057$)
  - Living agents: 0, living energy: $0.00$
  - Births: 0, Starvations: 30, Retirements: 20, Unfunded: 76

---

## 4. Stage 0 Status & Next Milestone

- **Status:** **STAGE 0 PASS**.
- Version C is fully implemented, verified, and completely decoupled from Version A and Version B.
- Ready for Stage 1 basic calibration (10 seeds $\times$ 3 groups $\times$ 2,000 steps).

