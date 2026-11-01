# Version D Stage 1 Calibration: Audit Corrections & Equation Reconciliation

**Document:** `calibration_logs/version_d/version_d_stage1_audit_corrections.md`  
**Date:** 2026-11-01  
**Target:** Reconciliation of `stage1_calibration_report.md` with Raw CSV Data (`results_v4/calibration/`)  
**Status:** Audit Reconciliation Complete — Corrections Frozen  

---

## 1. Executive Summary of Audit Findings

An independent audit of the Version D Stage 1 Calibration outputs identified discrepancies between the text of `stage1_calibration_report.md` and the raw data files (`calibration_summary.csv`, `calibration_timeseries.csv`). 

All discrepancies have been forensically investigated, reconciled against the underlying raw CSVs, and documented in this report:

1. **Seed-Level Reporting Discrepancy:** The seed-level mean resource and peak-step columns in Section 2 were mis-mapped from scratch arrays. They have been corrected to match the canonical CSV values.
2. **Resource Depletion Timing:** The report cited depletion between steps 65 and 75. The exact raw time-series shows initial resource zeroing between steps **54 and 68 (mean: 61.2)**.
3. **Resource Equation Architecture:** Verified that `simulator_v4` implements escapement-based renewal ($G(R_t - H_t)$), exactly matching `simulator_v3` (Version C) and `simulator_v2` (Version B). The documentation formula ($R_{t+1} = R_t + G(R_t) - H_t$) was an imprecise theoretical shorthand.
4. **Post-Depletion Survival Mechanism:** Corrected the erroneous claim of "resource trickle." Telemetry proves $R = 0.0$ and $G = 0.0$ on every step post-depletion. Surviving Q-agents lived purely on stored somatic energy reserves.
5. **Causal Attribution of Q-Dominance & Inheritance:** Acknowledged the telemetry measurement gap (lack of type-stratified energy distributions) and rephrased inheritance claims as architectural features rather than isolated causal effects.

---

## 2. Reconciled Seed-Level Table

The table below reconciles the Section 2 reporting discrepancies against [`calibration_summary.csv`](file:///Users/nish/home/Research%20Project/results_v4/calibration/calibration_summary.csv) and [`calibration_timeseries.csv`](file:///Users/nish/home/Research%20Project/results_v4/calibration/calibration_timeseries.csv):

| Seed | Completed Steps | Extinct | Peak Pop | Peak Step (Corrected) | First Zero Step | Total Births (Q / F) | Starvations | Retirements | Mean Resource (Corrected) | Max Energy Discrepancy |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1001** | 148 | Yes | 68 | **70** | 66 | 18 (18 / 0) | 48 | 20 | **86.78** | $1.58 \times 10^{-10}$ |
| **1002** | 144 | Yes | 72 | **77** | 62 | 22 (22 / 0) | 56 | 16 | **81.38** | $1.63 \times 10^{-10}$ |
| **1003** | 137 | Yes | 74 | **67** | 59 | 24 (24 / 0) | 56 | 18 | **78.98** | $1.57 \times 10^{-10}$ |
| **1004** | 144 | Yes | 69 | **64** | 56 | 19 (19 / 0) | 50 | 19 | **80.11** | $1.60 \times 10^{-10}$ |
| **1005** | 139 | Yes | 70 | **70** | 63 | 20 (20 / 0) | 52 | 18 | **85.89** | $1.52 \times 10^{-10}$ |
| **1006** | 144 | Yes | 70 | **78** | 68 | 20 (20 / 0) | 52 | 18 | **89.44** | $1.50 \times 10^{-10}$ |
| **1007** | 143 | Yes | 70 | **62** | 58 | 20 (20 / 0) | 51 | 19 | **78.91** | $1.55 \times 10^{-10}$ |
| **1008** | 131 | Yes | 70 | **76** | 54 | 20 (20 / 0) | 52 | 18 | **82.24** | $1.55 \times 10^{-10}$ |
| **1009** | 146 | Yes | 68 | **60** | 63 | 18 (18 / 0) | 49 | 19 | **86.26** | $1.59 \times 10^{-10}$ |
| **1010** | 141 | Yes | 68 | **73** | 63 | 18 (18 / 0) | 48 | 20 | **90.89** | $1.55 \times 10^{-10}$ |
| **Mean** | **141.7** | **100%** | **69.9** | **69.7** | **61.2** | **19.9 (19.9 / 0)** | **51.4** | **18.5** | **84.09** | **$1.56 \times 10^{-10}$** |

*Note: While individual seed values in the initial draft were misaligned, the group mean values (completed steps 141.7, mean resource 84.09, peak pop 69.9, births 19.9) were correct.*

---

## 3. Forensic Investigation of the Resource Regeneration Equation

### The Issue Raised:
In Seed 1001, Step 0:
- Starting resource: $R_0 = 350.0$
- Total harvest: $H_0 = 24.0$
- Logged regeneration: $G = 11.3448$
- Evaluation at start: $G(350) = 0.10 \times 350 \times (1 - 350/500) = 35 \times 0.30 = 10.5000$
- Evaluation post-harvest: $G(350 - 24) = G(326) = 0.10 \times 326 \times (1 - 326/500) = 32.6 \times 0.348 = 11.3448$

The logged regeneration matches the post-harvest calculation.

### Source Code Lineage Inspection:
A line-by-line inspection across the entire historical codebase revealed:
1. **Version B (`simulator_v2/simulator.py:330-333`):**
   ```python
   remaining = self.resource - total_harvest
   growth = g * remaining * (1.0 - remaining / K)
   self.resource = min(K, max(0.0, remaining + growth))
   ```
2. **Version C (`simulator_v3/simulator.py:284-287`):**
   ```python
   remaining_resource = self.resource - total_step_harvest
   growth = g * remaining_resource * (1.0 - remaining_resource / K)
   self.resource = min(K, max(0.0, remaining_resource + growth))
   ```
3. **Version D (`simulator_v4/simulator.py:423-432`):**
   ```python
   # In Stage 3: self.resource = max(0.0, self.resource - total_harvest)
   # In Stage 9:
   growth = regeneration_rate * self.resource * (1.0 - self.resource / self.parameters.resource_capacity)
   self.resource = min(self.parameters.resource_capacity, self.resource + growth)
   ```

### Resolution & Reconciliation:
- **Finding:** The implementation across Versions B, C, and D has **always been 100% identical and consistent**. All models implement discrete-time biological *escapement dynamics* (Schaefer / Beverton-Holt model):
  $$X_t = \max(0, R_t - H_t)$$
  $$R_{t+1} = \min\left(K, X_t + g X_t \left(1 - \frac{X_t}{K}\right)\right)$$
- **Ecological Justification:** In natural biological systems, reproduction occurs from the residual spawning stock remaining after harvest ($X_t$). If all biomass is harvested ($X_t = 0$), recruitment must be zero ($G(0) = 0$). Calculating $G(R_t)$ on pre-harvest stock would allow a completely depleted stock to generate 10.5 units of phantom growth.
- **Root Cause of Confusion:** Prior theoretical documentation casually wrote $R_{t+1} = R_t + G(R_t) - H_t$ as a shorthand for continuous renewal, rather than stating the explicit discrete-time intra-step escapement order.
- **Action Taken:** The formal specification in `version_d_model_specification.md` and the report have been updated to explicitly specify escapement renewal.

---

## 4. Correction of Substantive Reporting Claims

### A. Resource Dynamics Post-Depletion
- **Draft Claim:** Surviving second-generation Q-agents were sustained by "residual reserves and resource trickle."
- **Raw Data Fact:** In [`calibration_timeseries.csv`](file:///Users/nish/home/Research%20Project/results_v4/calibration/calibration_timeseries.csv), for all steps after depletion ($t > 68$), `resource == 0.0` and `regeneration == 0.0` in 100% of records across all 10 seeds.
- **Correction:** There was strictly zero resource regeneration once depleted ($X_t = 0 \implies G(0) = 0$). Surviving Q-agents lived entirely off accumulated somatic energy reserves ($E > 0$) until somatic burn ($m = 0.20$/step) led to starvation.

### B. Telemetry Limitation on Fixed Agent Reproduction
- **Draft Claim:** Fixed agents failed to reproduce because they "conservatively rested when resources became scarce."
- **Audit Assessment:** While ecologically plausible, the current time-series aggregated `mean_energy` across all living agents, without breaking out per-agent energy distributions or eligibility counts for Fixed vs. Q agents.
- **Correction:** Documented as an observational limitation. Future experiments must add:
  - `fixed_mean_energy`, `fixed_max_energy`, and `q_mean_energy`, `q_max_energy`.
  - `fixed_eligible_count` and `q_eligible_count` (agents with $E \ge 15.0$, $a < 60$, cooldown $= 0$).

### C. Causal Attribution of Q-Table Inheritance
- **Draft Claim:** Inheritance prevented exploratory errors and sustained harvesting efficiency.
- **Audit Assessment:** Inheritance was verified to function algorithmically ($\lambda_t$ decay, snapshot isolation). However, without a matched control experiment lacking inheritance ($\lambda_t = 0$), its specific causal contribution to demographic persistence cannot be disentangled from base Q-learning.
- **Correction:** Rephrased as an architectural property under calibration, reserving causal claims for controlled ablation experiments in Stage 2.

---

## 5. Artifacts Updated

- [`calibration_logs/version_d/stage1_calibration_report.md`](file:///Users/nish/home/Research%20Project/calibration_logs/version_d/stage1_calibration_report.md): Corrected all tables, depletion ranges, escapement formulas, and interpretive claims.
- [`calibration_logs/version_d/version_d_model_specification.md`](file:///Users/nish/home/Research%20Project/calibration_logs/version_d/version_d_model_specification.md): Reconciled mathematical notation to explicit escapement renewal $G(R_t - H_t)$.
- All raw CSV outputs in `results_v4/calibration/` remain **strictly frozen and unmodified**.

