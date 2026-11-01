# Experiment B2-C: Demographic Rules and Metabolic Subsidies — Formal Report

**Date:** 2026-11-01  
**Experiment:** B2-C  
**Objective:** Test whether exogenous newborn energy endowments ($E_0$) and automatic vacancy replacement artificially maintain population size and harvesting pressure during resource collapse, masking ecological failure.

---

## 1. Experimental Design & Variants

All variants were tested across the identical **10 calibration seeds (1–10)** and **3 population groups** (`fixed_only`, `q_only`, `evolving_joint`) using the Version B logistic resource model ($K=500, R_0=350, g=0.10$) and baseline net-energy reward ($r_t = \Delta E_t$).

- **C0 (Baseline Control):** $E_0 = 10.0$ units exogenous endowment; scheduled replacement every 20 steps.
- **C1 (Reduced Endowment, $E_0 = 2.0$):** Newborns receive only $2.0$ energy units (10 steps of metabolic maintenance without food).
- **C2 (Zero Endowment, $E_0 = 0.0$):** Newborns enter with $0.0$ energy. Must harvest $> c = 0.20$ on their first active step or perish immediately.
- **C3 (Parent-Funded Endowment):** Offspring energy ($10.0$ units) must be funded by the reproducing parent (`parent.energy >= 10.0`, deducted upon birth). If no living candidate has $\ge 10.0$ energy, vacancies remain unfilled.
- **C4 (Delayed Replacement Interval):** Vacancy replacement occurs every 40 steps instead of 20 steps; $E_0 = 10.0$.

---

## 2. Quantitative Summary Across Variants (10 Seeds $\times$ 3 Groups)

| Variant | Group | Extinction Rate | Mean Steps Completed | Mean Resource (units) | Mean Births / Run | Mean Deaths / Run | Unfunded Vacancies |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **C0** | `fixed_only` | **0/10** | 2000.0 | **163.69** | 1,000.0 | 1,000.0 | 0.0 |
| (Baseline) | `q_only` | **0/10** | 2000.0 | **0.78** | 1,607.6 | 1,607.6 | 0.0 |
| | `evolving_joint` | **0/10** | 2000.0 | **1.15** | 1,625.1 | 1,625.1 | 0.0 |
| **C1** | `fixed_only` | **0/10** | 2000.0 | **163.69** | 1,000.0 | 1,000.0 | 0.0 |
| ($E_0=2$) | `q_only` | **10/10** | 111.0 | **14.02** | 57.6 | 107.6 | 0.0 |
| | `evolving_joint` | **10/10** | 111.0 | **20.80** | 75.1 | 125.1 | 0.0 |
| **C2** | `fixed_only` | **10/10** | 201.0 | **167.81** | 100.0 | 150.0 | 0.0 |
| ($E_0=0$) | `q_only` | **10/10** | 101.0 | **15.41** | 57.6 | 107.6 | 0.0 |
| | `evolving_joint` | **10/10** | 101.0 | **22.86** | 75.1 | 125.1 | 0.0 |
| **C3** | `fixed_only` | **0/10** | 2000.0 | **163.69** | 1,000.0 | 1,000.0 | 0.0 |
| (Parent Funded) | `q_only` | **10/10** | 100.0 | **15.56** | 0.0 | 50.0 | 57.6 |
| | `evolving_joint` | **10/10** | 100.0 | **23.09** | 0.0 | 50.0 | 75.1 |
| **C4** | `fixed_only` | **0/10** | 2000.0 | **163.69** | 800.0 | 800.0 | 0.0 |
| (Interval 40) | `q_only` | **0/10** | 2000.0 | **0.78** | 1,207.6 | 1,207.6 | 0.0 |
| | `evolving_joint` | **0/10** | 2000.0 | **1.15** | 1,225.1 | 1,225.1 | 0.0 |

---

## 3. Seed-Level Variation Analysis

Across all 10 independent seeds (1–10):
- **C0 & C4:** Variance across seeds was essentially zero. In every single seed, `fixed_only` maintained $R \approx 163.7$ with 0 extinctions, while `q_only` and `evolving_joint` depleted the resource to $R \approx 0$ by step 10–12 and maintained a trapped 50-agent population through constant subsidized turnover (1,600+ replacements).
- **C1 ($E_0 = 2.0$):** In every single seed (10/10), `q_only` and `evolving_joint` went completely extinct between steps 111 and 112. The founder generation depleted the pool to 0, starvation killed ~32 agents before step 100, and at step 100 all surviving founders retired ($A_{\max}=100$). The 50 replacement newborns entered with only $E_0 = 2.0$. With zero harvest available, they exhausted their 2 units of energy in exactly 10 steps ($10 \times 0.20 = 2.0$) and died simultaneously at step 110–111.
- **C3 (Parent-Funded):** In every single seed (10/10), `q_only` and `evolving_joint` went extinct at exactly step 100. Because the resource collapsed to 0 by step 10, no agent ever accumulated $\ge 10.0$ energy by maturity (mean energy was ~1.7). At step 100, zero parents could fund offspring (`unfunded_vacancies = 50`), founders retired, and the population ceased to exist.
- **Fixed-Only Robustness:** Fixed-only agents survived indefinitely (0 extinctions across 2,000 steps) in C0, C1, C3, and C4 because their conservative harvesting maintained healthy individual energy ($E \approx 14.5$) and sustainable resource stock ($R \approx 164$). Only in C2 ($E_0=0$) did fixed-only fail, because newborns with zero energy taking `rest` (as dictated by the fixed rule at low/medium stock) pay maintenance $0.20$ without harvest and immediately die.

---

## 4. Implementation Validation & Integrity Checks

1. **Rule Isolation:** Each demographic variant modified strictly its intended parameter/function. Learning rates, Q-table updates, action allocations, and logistic equations were unchanged.
2. **Negative Parent Energy Check:** In C3, parent energy was protected by requiring `parent.energy >= 10.0` before reproduction; parents never dropped into negative energy.
3. **Zero-Endowment Sequencing:** In C2, newborns entering with $E_0=0$ were allowed to act in their first step; only if their net energy remained $\le 0$ after harvesting were they removed during the energy check.
4. **Ecological Distinction:** As required by validation guideline #4, **population extinction in C1, C2, and C3 is NOT classified as ecological resilience**. When the population collapses at step 100–111, the simulation halts because no living agents remain; the resource at termination remains severely degraded ($R < 25$).

---

## 5. Key Scientific Findings & Verdict

1. **The Demographic Subsidy Hypothesis is Confirmed:**
   In C0, the survival of Q-only and evolving-joint populations for 2,000 steps was **100% an artifact of exogenous energy endowments ($E_0 = 10.0$) and automatic vacancy filling**. Each newborn introduced 10 units of free external energy into the simulation, acting as an artificial life-support pump that masked total ecological exhaustion.
2. **Without Subsidies, Q-Learning Over-Exploitation Leads Directly to Demographic Extinction:**
   When newborns must survive on their own harvesting (C1) or parents must physically pay for offspring from accumulated surplus (C3), Q-learning populations **collapse and go extinct within 100–111 steps**.
3. **Fixed-Rule Agents are Demographically Self-Sustaining:**
   Fixed-rule harvesters easily pass the parent-funding gate (C3) because their conservative restraint allows them to build surplus energy and preserve the resource stock.

---

## 6. Synthesis of Stage 2 Investigations (B2-A, B2-B, B2-C)

We now have the complete, rigorously verified diagnostic picture:
1. **Perception (B2-A):** Finer state resolution does not change behavior because individual extractive actions weakly/strictly dominate resting.
2. **Incentives (B2-B):** Standard individual reward signals cannot overcome the tragedy of the commons without collective coordination.
3. **Demographics (B2-C):** Free newborn endowments artificially prop up unsustainable populations; removing this subsidy converts ecological collapse into demographic extinction.

All diagnostic raw records are archived in `results_v2/` and `calibration_logs/`.

