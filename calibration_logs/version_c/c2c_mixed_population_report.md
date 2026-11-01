# Experiment C2-C: Mixed-Population Mechanism — Formal Report

**Date:** 2026-11-01  
**Experiment:** C2-C (Mixed Static Compositions)  
**Sample:** 30 new runs (10 matched seeds `1001`–`1010` $\times$ 3 mixture treatments)  
**Baseline Controls Reused:** Frozen Stage 1 `fixed_only` (`C-100F`, 10 runs) & `q_only` (`C-0F`, 10 runs)  
**Status:** **BATCH EXECUTION & VALIDATION COMPLETE**

---

## 1. Experimental Overview & Treatments Tested

Experiment C2-C investigated whether introducing conservative fixed-rule harvesters into a population can buffer a common renewable resource against Q-learning extraction and avert extinction under closed metabolic reproduction ($E_{\text{cost}} = 10.0$).

### Compositions Evaluated ($N = 50$ total capacity):
1. **`C-100F` (Frozen Control):** 50 Fixed (100.0%) / 0 Q (0.0%)
2. **`C-76F`:** 38 Fixed (76.0%) / 12 Q (24.0%)
3. **`C-50F`:** 25 Fixed (50.0%) / 25 Q (50.0%)
4. **`C-24F`:** 12 Fixed (24.0%) / 38 Q (76.0%)
5. **`C-0F` (Frozen Control):** 0 Fixed (0.0%) / 50 Q (100.0%)

### Static Replacement & Closed Energy Rules:
- When vacancies open, the replacement mechanism targets the deficit type relative to the intended quota.
- Replacement requires an eligible parent ($E > 10.0$) of the deficit type to transfer $10.0$ energy units to the newborn.
- **Unfunded Vacancy Rule:** If no parent of the deficit type has $E > 10.0$, the vacancy remains unfilled (no external energy injection).

---

## 2. Quantitative Results Across the Composition Gradient

| Metric | C-100F (100% Fixed) | C-76F (76% Fixed) | C-50F (50% Fixed) | C-24F (24% Fixed) | C-0F (100% Q) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Extinction Rate** | **0/10 (0.0%)** | <span style="color:red">**10/10 (100.0%)**</span> | <span style="color:red">**10/10 (100.0%)**</span> | <span style="color:red">**10/10 (100.0%)**</span> | <span style="color:red">**10/10 (100.0%)**</span> |
| **Mean Extinction Step** | **2,000.0** (Surviving) | **100.0** | **100.0** | **100.0** | **100.0** |
| **Mean Resource Level (units)** | **163.69** (32.7% $K$) | **43.75** (8.8% $K$) | **22.35** (4.5% $K$) | **17.59** (3.5% $K$) | **15.56** (3.1% $K$) |
| **Time to $R < 25$ (Depletion)** | **Never** | **Step 30.2** | **Step 13.7** | **Step 10.5** | **Step 8.9** |
| **Total Funded Births / Run** | **1,000.0** | **0.0** | **0.0** | **0.0** | **0.0** |
| **Total Unfunded Vacancies** | **0.0** | **84.2** | **75.0** | **64.2** | **57.6** |
| **Energy Conserved across runs?** | **YES** | **YES** | **YES** | **YES** | **YES** |
| **Max Energy Discrepancy** | **$3.78 \times 10^{-8}$** | **$5.98 \times 10^{-11}$** | **$6.12 \times 10^{-11}$** | **$6.99 \times 10^{-11}$** | **$7.17 \times 10^{-11}$** |

---

## 3. Seed-Level Breakdown (New Treatment Runs)

| Seed | Treatment | Completed Steps | Extinct? | Mean Resource | Time to $R < 25$ | Starvations | Retirements | Unfunded | Energy Discrepancy | Conserved? |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1001** | C-76F | 100 | True | 52.54 | 33 | 38 | 12 | 88 | $5.20 \times 10^{-11}$ | **PASS** |
| **1002** | C-76F | 100 | True | 40.27 | 28 | 38 | 12 | 88 | $5.43 \times 10^{-11}$ | **PASS** |
| **1003** | C-76F | 100 | True | 46.59 | 30 | 38 | 12 | 88 | $5.98 \times 10^{-11}$ | **PASS** |
| **1004** | C-76F | 100 | True | 34.19 | 24 | 38 | 12 | 88 | $5.38 \times 10^{-11}$ | **PASS** |
| **1005** | C-76F | 100 | True | 33.96 | 24 | 38 | 12 | 88 | $5.05 \times 10^{-11}$ | **PASS** |
| **1006** | C-76F | 100 | True | 41.62 | 29 | 38 | 12 | 88 | $5.44 \times 10^{-11}$ | **PASS** |
| **1007** | C-76F | 100 | True | 36.80 | 26 | 38 | 12 | 88 | $5.07 \times 10^{-11}$ | **PASS** |
| **1008** | C-76F | 100 | True | 40.37 | 28 | 38 | 12 | 88 | $5.44 \times 10^{-11}$ | **PASS** |
| **1009** | C-76F | 100 | True | 67.26 | 45 | 38 | 12 | 50 | $5.60 \times 10^{-11}$ | **PASS** |
| **1010** | C-76F | 100 | True | 43.90 | 35 | 38 | 12 | 88 | $5.11 \times 10^{-11}$ | **PASS** |
| **1001–1010** | C-50F | 100 | True (10/10) | 22.35 (mean) | 13.7 (mean) | 29.6 (mean) | 20.4 (mean) | 75.0 (mean) | $< 6.12 \times 10^{-11}$ | **PASS** |
| **1001–1010** | C-24F | 100 | True (10/10) | 17.59 (mean) | 10.5 (mean) | 33.8 (mean) | 16.2 (mean) | 64.2 (mean) | $< 6.99 \times 10^{-11}$ | **PASS** |

---

## 4. Deep Diagnostic Investigation: The Parasitic Depletion Mechanism

### A. The Buffer Effect of Fixed Agents
- Increasing the share of fixed agents noticeably delayed resource depletion:
  - At 0% Fixed (`C-0F`), the resource dropped to $R < 25$ in **8.9 steps**.
  - At 24% Fixed (`C-24F`), depletion took **10.5 steps**.
  - At 50% Fixed (`C-50F`), depletion took **13.7 steps**.
  - At 76% Fixed (`C-76F`), depletion took **30.2 steps** (mean resource increased to $43.75$).

### B. Why 76% Fixed Agents Still Suffered 100% Extinction
Tracing the individual dynamics of `C-76F` (Seed 1001: 38 Fixed, 12 Q) reveals an extraordinary ecological tragedy:
1. **Asymmetric Energy Accumulation (Steps 1–30):**
   - When the resource crossed below $165$, all 38 fixed agents ceased harvesting and took `rest` to conserve the pool.
   - The 12 Q-learning agents continued harvesting aggressively ($12 \times 2.0 = 24.0$ request).
   - In a logistic system where maximum growth is $G_{\max} = 12.5$ units/step, **just 12 Q-learning agents harvesting aggressively exceeded the ecosystem's maximum regeneration rate**.
   - The 12 Q-learning agents accumulated maximum energy ($E \approx 20.0$), while the 38 fixed agents received 0 harvest and slowly starved ($E$ declining by $0.20$ every step).
2. **Fixed Population Collapse at Step 75–80:**
   - At step 75, after 65 steps of continuous resting, all 38 fixed agents starved to death.
   - Living population dropped from 50 to 12.
3. **The Static Replacement Trap:**
   - At replacement step 80, the static replacement rule identified a **deficit of 38 fixed agents** and **0 deficit for Q-agents** (target was 38 Fixed / 12 Q; actual living was 0 Fixed / 12 Q).
   - The system sought eligible fixed parents to fund fixed newborns.
   - But because all fixed agents were dead, **zero fixed parents existed**.
   - Although the 12 living Q-agents had surplus energy ($E = 11.90 > 10.0$), they could not legally fund fixed offspring under type inheritance.
   - All 38 vacancies were left unfunded.
4. **Final Extinction at Step 100:**
   - At step 100, the 12 Q-learning founders reached $A_{\max} = 100$ and retired.
   - With 0 living agents remaining, total demographic extinction occurred.

---

## 5. Summary Verdict for Experiment C2-C

- **Hypothesis C2-C.1 is REFUTED:**
  Even when conservative fixed harvesters make up **76% of the initial population**, they cannot buffer the resource against a 24% minority of extractive Q-learners.
- **The Ecological Parasitism Dynamic:**
  In a shared pool, conservative heuristics that voluntarily rest when resources decline inadvertently subsidize selfish agents:
  - Restraint by the majority provides the minority with sustained harvesting opportunity.
  - The selfish minority accumulates surplus energy while the conserving majority starves.
  - Once the conserving majority perishes, the minority consumes the remainder and dies of reproductive failure.

