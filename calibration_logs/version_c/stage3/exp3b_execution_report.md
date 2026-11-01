# Experiment 3B: Graded Harvest Quotas — Audited Execution Report

**Date:** 2026-11-01  
**Simulator Version:** `sim-3.0.0` (Version C Architecture)  
**Parameter Configuration:** `params-v3.0`  
**Demographic Rules:** Frozen `C-76F` (38 Fixed / 12 Q founders, parent-funded, strictly type-restricted, maximum age 100)  
**Seeds Executed:** 10 matched seeds (`1001`–`1010`) across 4 groups (Total: 40 runs)  
**Simulation Horizon:** 2,000 steps per run  
**Energy Conservation:** PASS across all 40 runs (maximum energy discrepancy $= 9.84 \times 10^{-11}$)  

---

## 1. Executive Summary & Core Research Findings

Experiment 3B tested whether restricting individual harvesting capacity relative to the natural regeneration capacity can prevent ecological collapse in a mixed population (38 Fixed / 12 Q, $N = 50$).

### Core Conclusions:
1. **Ecological Impact of Quotas:**  
   Under the tested Version C conditions, reducing all harvest requests by $50\%$ (Treatment B) or $62.5\%$ (Treatment C) **prevented complete resource depletion during the observed 100-step population lifespan**. No Treatment B or C run reached the complete-depletion threshold ($R < 1.0$) before population extinction at step 100.
2. **Fixed-Agent Survival vs. Action Choices:**  
   Zero Fixed agents starved in Treatments B and C. In Treatment B, Fixed agents did not harvest continuously: they rested in $36.0\%$ of decisions when $R$ dipped below $165$, and harvested `conservative` ($0.25$) in $62.0\%$ of decisions. In Treatment C, the resource stabilized higher, allowing Fixed agents to harvest `conservative` ($0.1875$) in $96.7\%$ of decisions and rest in only $0.1\%$.
3. **The Demographic Synchronization Dilemma:**  
   Although Treatments B and C prevented resource collapse, **all 40 runs experienced complete population extinction at step 100**. Because zero starvation deaths occurred during steps 1–99, zero vacancies opened. When all 50 founders reached maximum age simultaneously at step 100, they were excluded from reproduction under Version C retirement rules, resulting in synchronized demographic extinction despite a flourishing resource stock.

> **Primary Scientific Takeaway:** Ecological recovery and demographic persistence remain separate problems in this model. Limiting harvest quotas successfully stabilized the resource stock, but demographic persistence failed due to founder age synchronization and strict retirement exclusion rules.

---

## 2. Comprehensive Aggregate Comparison Across All Four Groups

| Metric | Control (Baseline) | Treatment A ($-25\%$) | Treatment B ($-50\%$) | Treatment C ($-62.5\%$) |
| :--- | :---: | :---: | :---: | :---: |
| **Harvest Scaling Factor** | $\times 1.000$ | $\times 0.750$ | $\times 0.500$ | $\times 0.375$ |
| **Aggressive / Moderate Requests** | $2.000$ / $1.000$ | $1.500$ / $0.750$ | $1.000$ / $0.500$ | $0.750$ / $0.375$ |
| **Conservative / Rest Requests** | $0.500$ / $0.000$ | $0.375$ / $0.000$ | $0.250$ / $0.000$ | $0.1875$ / $0.000$ |
| **Theoretical 12 Q Max Demand** | $24.0$ units/step | $18.0$ units/step | $12.0$ units/step | $9.0$ units/step |
| **Full Pop ($N=50$) Max Demand** | $100.0$ units/step | $75.0$ units/step | $50.0$ units/step | $37.5$ units/step |
| **Extinction Count** | **10 / 10** | **10 / 10** | **10 / 10** | **10 / 10** |
| **Mean Survival Steps** | 100.0 | 100.0 | 100.0 | 100.0 |
| **Mean Resource (Steps 1–100)** | **43.75** | **102.12** | **199.28** | **278.87** |
| **Mean Final Resource (Step 100)** | 0.00 | 0.00 | **163.50** | **218.65** |
| **Complete Depletion Count ($R < 1.0$)** | **10 / 10 (100%)** | **10 / 10 (100%)** | **0 / 10 (0%)** | **0 / 10 (0%)** |
| **Step to First $R < 1.0$** | 31.7 (range 23–49) | 69.8 (range 48–96) | **Never depleted** | **Never depleted** |
| **Step to First $R < 25.0$** | 30.2 (range 22–47) | 67.3 (range 46–93) | **Never < 25** | **Never < 25** |
| **Total Starvation Deaths** | **380** (F=380, Q=0) | **380** (F=380, Q=0) | **0 (F=0, Q=0)** | **0 (F=0, Q=0)** |
| **Total Retirement Deaths** | **120** (F=0, Q=120) | **120** (F=0, Q=120) | **500 (F=380, Q=120)**| **500 (F=380, Q=120)**|
| **Total Births** | 0 | 0 | 0 | 0 |
| **Total Unfunded Vacancies** | 842 | 500 | 500 | 500 |
| **Cumulative Harvest Requested** | 1,410.0 | 1,345.3 | 1,304.3 | 1,351.2 |
| **Cumulative Harvest Allocated** | 616.5 | 981.4 | **1,304.3** | **1,351.2** |
| **Unmet Harvest Demand** | **793.6 (56.3%)** | **364.0 (27.1%)** | **0.0 (0.0%)** | **0.0 (0.0%)** |
| **Fixed Action Distribution** | $87.5\%$ Rest, $11.2\%$ Cons, $1.3\%$ Mod | $80.4\%$ Rest, $18.4\%$ Cons, $1.2\%$ Mod | $36.0\%$ Rest, $62.0\%$ Cons, $2.0\%$ Mod | $0.1\%$ Rest, $96.7\%$ Cons, $3.2\%$ Mod |
| **Max Energy Discrepancy** | $5.98 \times 10^{-11}$ | $7.20 \times 10^{-11}$ | $9.84 \times 10^{-11}$ | $9.70 \times 10^{-11}$ |

---

## 3. Disaggregated Seed-Level Results

| Seed | Control Mean $R$ (1–100) | Trt A Mean $R$ (1–100) | Trt B Mean $R$ (1–100) | Trt C Mean $R$ (1–100) | Trt B Final $R$ | Trt C Final $R$ | Trt B/C Depleted ($R<1$)? | Max Energy Disc |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1001** | 52.54 | 122.84 | 199.30 | 276.71 | 163.78 | 212.72 | **No** | $9.74 \times 10^{-11}$ |
| **1002** | 40.27 | 99.82 | 207.31 | 277.10 | 168.32 | 203.88 | **No** | $9.56 \times 10^{-11}$ |
| **1003** | 46.59 | 108.93 | 197.64 | 281.63 | 162.77 | 227.13 | **No** | $9.82 \times 10^{-11}$ |
| **1004** | 34.19 | 92.89 | 199.27 | 257.94 | 161.98 | 172.99 | **No** | $9.77 \times 10^{-11}$ |
| **1005** | 33.96 | 139.29 | 195.42 | 287.82 | 161.46 | 240.23 | **No** | $9.79 \times 10^{-11}$ |
| **1006** | 41.62 | 106.69 | 196.72 | 286.23 | 160.29 | 246.05 | **No** | $9.78 \times 10^{-11}$ |
| **1007** | 36.80 | 76.08 | 195.96 | 264.55 | 162.29 | 213.91 | **No** | $9.66 \times 10^{-11}$ |
| **1008** | 40.37 | 74.22 | 194.27 | 271.30 | 162.33 | 217.38 | **No** | $9.84 \times 10^{-11}$ |
| **1009** | 67.26 | 105.51 | 199.98 | 288.16 | 161.91 | 229.07 | **No** | $9.77 \times 10^{-11}$ |
| **1010** | 43.90 | 94.94 | 206.91 | 297.26 | 169.90 | 223.18 | **No** | $9.70 \times 10^{-11}$ |

---

## 4. Reconciled Audit Items & Clarifications

### A. Clarification on Carrying Capacity & Aggregate Demand
The theoretical capacity calculations in the plan compared Q-only maximum demand against peak regeneration ($G_{\max} = 12.5$). However, total aggregate extraction depends on both Fixed and Q agents. 
- At step 1 ($R_0 = 350$), Fixed agents choose `moderate` ($1.0$ in Control, $0.75$ in A, $0.50$ in B, $0.375$ in C). Initial Fixed demand alone was $38.0$ in Control, $28.5$ in A, $19.0$ in B, and $14.25$ in C.
- Initial total demand exceeded initial regeneration ($G(350) = 10.5$) in all groups, causing $R$ to decline initially.
- In Control and A, total demand continuously exceeded regeneration, driving $R \to 0$.
- In B and C, as $R$ dropped below $330$, Fixed agents switched to `conservative` ($0.25$ in B, $0.1875$ in C). At this point, aggregate extraction fell below local replenishment, allowing the system to stabilize dynamically.

### B. Fixed Agent Action Distribution Across Groups
Fixed agents select actions according to the fixed policy: `{"low": "rest", "medium": "conservative", "high": "moderate"}` based on $R_{\text{band}}$:
- **Control (29,450 decisions prior to step 76–81 starvation):**
  - `rest` ($R < 165$): $25,764$ ($87.5\%$)
  - `conservative` ($165 \le R \le 330$): $3,306$ ($11.2\%$)
  - `moderate` ($R > 330$): $380$ ($1.3\%$)
  - Total: $100.0\%$
- **Treatment A (31,388 decisions prior to step 76–96 starvation):**
  - `rest` ($R < 165$): $25,232$ ($80.4\%$)
  - `conservative` ($165 \le R \le 330$): $5,776$ ($18.4\%$)
  - `moderate` ($R > 330$): $380$ ($1.2\%$)
  - Total: $100.0\%$
- **Treatment B (38,000 decisions across full 100 steps):**
  - `rest` ($R < 165$): $13,680$ ($36.0\%$)
  - `conservative` ($165 \le R \le 330$): $23,560$ ($62.0\%$)
  - `moderate` ($R > 330$): $760$ ($2.0\%$)
  - Total: $100.0\%$
- **Treatment C (38,000 decisions across full 100 steps):**
  - `rest` ($R < 165$): $38$ ($0.1\%$)
  - `conservative` ($165 \le R \le 330$): $36,746$ ($96.7\%$)
  - `moderate` ($R > 330$): $1,216$ ($3.2\%$)
  - Total: $100.0\%$

### C. Resource Depletion Timing Specification
- In Control: All 10 runs reached complete resource depletion ($R < 1.0$) between steps 23 and 49 (mean: step 31.7).
- In Treatment A: All 10 runs reached complete resource depletion ($R < 1.0$) between steps 48 and 96 (mean: step 69.8).
- In Treatments B and C: **No run reached the complete-depletion threshold ($R < 1.0$) or the critical stress threshold ($R < 25.0$) before population extinction at step 100.** Because all runs ended at step 100 due to synchronized founder retirement, long-term post-100 ecological stability was unobservable.

---

## 5. Artifacts and Audit Deliverables

All 40 simulation runs are fully documented, preserved, and indexed:
- **Execution Manifest:** [exp3b_execution_manifest.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/exp3b_execution_manifest.csv)
- **Summary Datasets:**
  - Control: [control_summary.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/control_summary.csv)
  - Treatment A: [treatment_a_summary.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/treatment_a_summary.csv)
  - Treatment B: [treatment_b_summary.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/treatment_b_summary.csv)
  - Treatment C: [treatment_c_summary.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/treatment_c_summary.csv)
- **Time-Series Datasets:**
  - Control: [control_timeseries.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/control_timeseries.csv)
  - Treatment A: [treatment_a_timeseries.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/treatment_a_timeseries.csv)
  - Treatment B: [treatment_b_timeseries.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/treatment_b_timeseries.csv)
  - Treatment C: [treatment_c_timeseries.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/treatment_c_timeseries.csv)
- **Reproduction Logs:**
  - Control: [control_reproduction_logs.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/control_reproduction_logs.csv)
  - Treatment A: [treatment_a_reproduction_logs.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/treatment_a_reproduction_logs.csv)
  - Treatment B: [treatment_b_reproduction_logs.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/treatment_b_reproduction_logs.csv)
  - Treatment C: [treatment_c_reproduction_logs.csv](file:///Users/nish/home/Research%20Project/results_v3/stage3_mechanism_isolation/exp3b/treatment_c_reproduction_logs.csv)
