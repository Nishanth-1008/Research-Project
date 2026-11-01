# Version D: Stage 0 Pre-Execution Audit Report

**Date:** 2026-11-01  
**Simulator Target:** `simulator_v4/` (`sim-4.0.0`, `params-v4.0`)  
**Status:** Verification Complete — Ready for Review Prior to Simulation Execution  

---

## 1. Executive Summary

In accordance with scientific audit standards, `simulator_v4` has been implemented and verified. All Version C files, results, and historical baselines remain strictly frozen and untouched. 

This audit documents:
1. Reconciled mathematical specifications and code implementations.
2. Complete elimination of artificial population caps ($N_{t+1} = N_t + B_t - D_t$).
3. Explicit separation of $Q_{\text{parent}}$, $Q_{\text{own}}$, and $Q_{\text{active}}$ with 12-step linear scaffolding.
4. Birth-step refractory and aging timing rules.
5. Thermodynamic energy balance verification ($|E_{\text{ledger\_error}}| \le 1.34 \times 10^{-10}$).
6. Passing status across all 37 test suites.

**No simulation runs or experimental batches have been executed.**

---

## 2. Parameter Specification Sheet (`params-v4.0`)

| Parameter | Value | Biological / Computational Meaning |
| :--- | :---: | :--- |
| `initial_population` ($N_0$) | $50$ | 38 Fixed, 12 Q-learning founders |
| `population_capacity` ($N_{\max}$) | **None** | Removed; population emerges from vital rates |
| `initial_founder_age` | $0$ | Synchronized founder cohort to isolate mechanism causality |
| `maximum_age` ($a_{\max}$) | $100$ | Senescent maximum lifespan (retires at 100) |
| `initial_founder_energy` ($E_0$) | $10.0$ | Founder starting somatic energy |
| `maximum_energy` ($E_{\max}$) | $25.0$ | Somatic storage ceiling |
| `maintenance_cost` ($m$) | $0.20$ | Somatic metabolic deduction per step |
| `reproduction_min_energy` | $15.0$ | Threshold below which reproduction probability is 0 |
| `reproduction_target_energy` | $20.0$ | Threshold at which reproduction probability plateaus |
| `reproduction_max_prob` ($P_{\max}$) | $0.10$ | Maximum reproduction probability per eligible step |
| `reproduction_age_full` | $45$ | Upper age limit for 100% reproductive ability ($A_i = 1.0$) |
| `reproduction_age_max` | $60$ | Senescent reproductive cutoff ($A_i = 0.0$ for $a \ge 60$) |
| `reproduction_cooldown` | $20$ | Minimum interval between births |
| `reproduction_cost` | $10.0$ | Energy deducted from parent |
| `newborn_energy` | $10.0$ | Energy endowed to newborn ($\Delta E_{\text{birth}} = 0.000$) |
| `inheritance_duration` | $12$ | Steps over which parental scaffolding linearly decays |
| `harvest_request` (50% quota) | $\{0.0, 0.25, 0.5, 1.0\}$ | Treatment B action space (`rest`, `cons`, `mod`, `aggr`) |
| `resource_capacity` ($K$) | $500.0$ | Ecological carrying capacity |
| `initial_resource` ($R_0$) | $350.0$ | Ecosystem initial endowment |
| `baseline_regeneration` ($g$) | $0.10$ | Logistic growth rate parameter |

---

## 3. Implementation Verification & Diffs

### A. Dynamic Population Without Artificial Cap
- In `simulator_v4/simulator.py`, the rigid capacity ceiling $N_{\max} = 50$ is eliminated.
- Any living agent meeting physiological criteria evaluates reproduction independently.
- Population expands and contracts naturally:
  $$N_{t+1} = N_t + B_t - D_{\text{starve}} - D_{\text{retire}}$$

### B. Birth-Step Refractory & Aging Immunity
To prevent newborns and parents from losing a cooldown step or aging on their birth step:
- **Parent:** Upon birth, `reproduction_cooldown = 20` and `skip_cooldown_decrement = True`.
- **Newborn:** Upon birth, `reproduction_cooldown = 20`, `skip_cooldown_decrement = True`, and `skip_age_increment = True`.
- **Stage 7 execution:** Agents with `skip_cooldown_decrement` or `skip_age_increment` clear their flags and do not decrement/increment on the birth step. On step $t+1$, standard decrements and aging resume.

### C. Explicit Tri-Table Q-Learning Architecture
- **$Q_{\text{parent}}$:** An immutable, deep-copied snapshot of the parent's active Q-table at birth. Never modified after birth.
- **$Q_{\text{own}}$:** The offspring's autonomous table, initialized empty/neutral. Updated via experience:
  $$Q_{\text{own}}(s, a) \gets Q_{\text{own}}(s, a) + \alpha \left[ r + \gamma \max_{a'} Q_{\text{active}}(s', a') - Q_{\text{own}}(s, a) \right]$$
- **$Q_{\text{active}}$:** The blended table used for action selection:
  $$Q_{\text{active}}(s, a) = (1 - \lambda_t) Q_{\text{own}}(s, a) + \lambda_t Q_{\text{parent}}(s, a)$$
  $$\lambda_t = 1 - \frac{\min(\text{age}, 12)}{12}$$

### D. Full Thermodynamic Ledger
The energy ledger tracks:
$$E_{\text{living}} = E_{\text{initial}} + \sum H - \sum m - E_{\text{cap\_losses}} - E_{\text{retirement\_losses}} - E_{\text{starvation\_losses}}$$
- Internal reproduction transfers: $\Delta E_{\text{parent}} (-10.0) + \Delta E_{\text{newborn}} (+10.0) = 0.00000000$.
- Verified across 100 simulation steps: maximum observed discrepancy is $1.34 \times 10^{-10}$, well within floating-point epsilon.

---

## 4. Test Suite Execution Results

All 37 unit tests across the entire repository pass with zero errors:

```text
======================================================================
1. simulator/test_simulator.py (Version A):
   Ran 6 tests in 0.022s -> OK
2. simulator_v3/tests/test_stage0_validation.py (Version C):
   Ran 7 tests in 0.008s -> OK
3. simulator_v3/experiments/stage3/tests (Stage 3A & 3B):
   Ran 15 tests in 0.006s -> OK
4. simulator_v4/tests/test_version_d.py (Version D):
   - test_probability_energy_boundaries -> OK
   - test_probability_age_boundaries -> OK
   - test_birth_step_cooldown_and_age_immunity -> OK
   - test_energy_conservation_on_birth -> OK
   - test_lambda_decay -> OK
   - test_q_blending_and_immutability -> OK
   - test_energy_ledger_conservation_full_run -> OK
   - test_unconstrained_population_growth -> OK
   - test_deterministic_seed_reproducibility -> OK
   Ran 9 tests in 0.012s -> OK
======================================================================
TOTAL: 37 tests, 0 failures, 0 errors, 0 regressions.
```

---

## 5. Compliance Checklist

- [x] Version C files, results, and reports strictly preserved and frozen.
- [x] Population capacity $N_{\max} = 50$ completely removed.
- [x] 50% harvest-quota action values implemented (`rest`: 0.0, `conservative`: 0.25, `moderate`: 0.5, `aggressive`: 1.0).
- [x] All 50 founders initialized at age 0.
- [x] $P_i(E_i, a_i)$ continuous probability and senescent decline implemented and tested.
- [x] 20-step cooldown and birth-step immunity verified.
- [x] Tri-table Q-inheritance with 12-step linear decay verified.
- [x] Thermodynamic conservation ($|E_{\text{error}}| < 10^{-8}$) verified.
- [x] Zero experimental runs launched.

