# Main Production Run Report: Seed 1001 Execution & Demographic Audit

**Date:** November 2026  
**Simulator Version:** `sim-4.1.0`  
**Parameter Version:** `params-v4.1`  
**Experimental Group:** `evolving_joint` (Primary Condition)  
**Scenarios Executed:** `stationary`, `sudden_shock`  
**Seed:** 1001 (Production Seed 1)  
**Output Location:** [`results_v4/phase2_core/runs/`](file:///Users/nish/home/Research%20Project/results_v4/phase2_core/runs/)  
**Status:** **EXECUTION COMPLETE — EMPIRICAL REPLICATION OF CROWDING-SENESCENCE DEADLOCK**

---

## 1. Executive Summary

A single main production run was executed for the primary experimental group (`evolving_joint`) using pre-registered **Production Seed 1001** under both `stationary` and `sudden_shock` regimes (planned horizon: 2,000 steps).

The run replicated identically across both environmental scenarios:
- **Steps Completed:** **100 / 2,000 steps** (100% early extinction).
- **Total Births:** **0 births**.
- **Mortality Pattern:** Exactly **25 Fixed agents starved** (at step 83) and exactly **25 Q-learning agents retired due to age 100 senescence** (at step 100).
- **Shock Step Reached:** **No.** The scheduled environmental shock at step 1,000 was never reached due to step-100 cohort extinction.
- **Thermodynamic Energy Balance:** Strict conservation verified across all 100 steps; maximum discrepancy was **$7.42 \times 10^{-11}$** (well within the $< 10^{-8}$ physical boundary).

---

## 2. Trajectory Overview: Step-by-Step Chronology

| Step Window | Resource Dynamics | Subpopulation Status | Vital Rates & Reproduction | Ecological Event |
| :--- | :--- | :--- | :--- | :--- |
| **Steps 0–10** | $R: 350.0 \to 266.8$ | $N = 50$ ($25\text{ Fixed}, 25\text{ Q}$)<br>$\bar{E}_F \approx 11.0, \bar{E}_Q \approx 13.2$ | Discount $= \max(0, 1 - 50/50) = 0.0$<br>$P_{\text{birth}} = 0.0$ | Commons exploitation begins; Q-learning agents rapidly scale up harvest demands. |
| **Steps 11–45** | $R: 266.8 \to 16.7$ | $N = 50$<br>$\bar{E}_F \approx 7.6, \bar{E}_Q \approx 22.9$ | Discount $= 0.0$<br>$P_{\text{birth}} = 0.0$ | Commons over-harvesting; Q-agents accumulate high somatic energy ($E > 20$), but cannot reproduce due to crowding factor. |
| **Steps 46–50** | $R: 16.7 \to 0.0$ | $N = 50$<br>$\bar{E}_F \approx 6.5, \bar{E}_Q \approx 22.2$ | Discount $= 0.0$<br>$P_{\text{birth}} = 0.0$ | **Resource Collapse:** Stock reaches $R=0.0$. Fixed agents detect low resource ($R < 165$) and enter `rest`. |
| **Steps 51–60** | $R = 0.0$ | $N = 50$<br>$\bar{E}_F: 6.5 \to 4.5$<br>$\bar{E}_Q: 22.2 \to 20.2$ | Discount $= 0.0$<br>$P_{\text{birth}} = 0.0$ | Founders age from 50 to 60. At step 60, all living agents reach reproductive senescence (`reproduction_age_max = 60`). |
| **Steps 61–83** | $R = 0.0$ | $N = 50 \to 25$<br>$\bar{E}_F \to 0.0$ (Starvation) | Discount becomes $1 - 25/50 = 0.50$, but all agents are **Age 83 > 60** ($P_{\text{birth}} = 0.0$) | Fixed agents exhaust somatic reserves paying metabolism ($c=0.20$/step). At step 83, all 25 Fixed agents starve. |
| **Steps 84–99** | $R = 0.0$ | $N = 25$ ($0\text{ Fixed}, 25\text{ Q}$)<br>$\bar{E}_Q: 15.4 \to 12.6$ | $P_{\text{birth}} = 0.0$ (Post-reproductive) | Surviving Q-agents coast on accumulated somatic surplus without foraging. |
| **Step 100** | $R = 0.0$ | $N = 25 \to 0$ | $P_{\text{birth}} = 0.0$ | **Total Extinction:** All 25 surviving Q-agents reach `maximum_age = 100` and simultaneously retire. |

---

## 3. Comparative Synthesis: Calibration vs. Production Seed 1001

The empirical behavior of Production Seed 1001 matches the findings of the 10 calibration seeds (Seeds 901–910):

| Run ID | Steps | Extinction | Total Births | Starvation Deaths | Retirement Deaths | Mean Resource | Max Energy Discrepancy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Calibration Mean (Seeds 901–910)** | 100.0 | 100% | 0.0 | 25.0 | 25.0 | $79.5 \pm 8.4$ | $8.36 \times 10^{-11}$ |
| **Production `evolving_joint_stationary_s1001`** | 100 | 100% | 0 | 25 | 25 | 86.51 | $7.42 \times 10^{-11}$ |
| **Production `evolving_joint_sudden_shock_s1001`** | 100 | 100% | 0 | 25 | 25 | 86.51 | $7.42 \times 10^{-11}$ |

---

## 4. Methodological Conclusion

1. **Deterministic Confirmation:** The demographic deadlock is not an artifact of random seed variance. Because $N_0 = 50 = K_{\text{pop}}$, initial reproduction is mathematically prohibited ($\text{discount} = 0$).
2. **Impact on Environmental Disturbances:** Because all populations collapse at step 100, neither the gradual decline ($t \in [500, 1000]$) nor the sudden resource shock ($t = 1000$) can be tested under the current parameter combination.
3. **Core Recommendation:** The proposed remediation—providing **demographic headroom** by rightsizing $K_{\text{pop}} > N_0$ (e.g. $K_{\text{pop}} = 75, N_0 = 50$) or adopting smooth logistic regulation—is required to enable multigenerational persistence before launching the complete 240-run production batch.

