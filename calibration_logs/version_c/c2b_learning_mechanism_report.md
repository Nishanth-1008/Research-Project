# Experiment C2-B: Learning Mechanism — Formal Report

**Date:** 2026-11-01  
**Experiment:** C2-B (Algorithmic Learning Mechanism)  
**Sample:** 30 new runs (10 matched seeds `1001`–`1010` $\times$ 3 treatments) $\times$ `q_only`  
**Baseline Reference:** Frozen Stage 1 `q_only` (`B0`)  
**Status:** **BATCH EXECUTION & VALIDATION COMPLETE**

---

## 1. Experimental Overview & Treatments Tested

Experiment C2-B investigated whether algorithmic modifications to the reinforcement learning process could enable tabular Q-learning agents to learn conservation and avoid resource collapse during the critical initial drawdown window (steps 1–10).

### Treatments Evaluated:
1. **B0 (Frozen Baseline Control):** $\alpha = 0.10, \gamma = 0.95, \varepsilon = 0.20 \to 0.02$ over 100 lifetime steps.
2. **B1 (Low Exploration Schedule):** $\varepsilon = 0.05 \to 0.01$ over 100 lifetime steps. (Tests whether early over-extraction was driven by exploratory random actions).
3. **B2 (Long Planning Horizon):** $\gamma = 0.99$. (Tests whether longer temporal discounting helps agents anticipate the starvation consequences of early depletion).
4. **B3 (Accelerated Learning Rate):** $\alpha = 0.30$. (Tests whether faster policy updates during steps 1–10 allow agents to adapt before the pool collapses).

---

## 2. Quantitative Results & Baseline Comparison

| Metric | B0 (Baseline) | B1 (Low Exploration) | B2 (Long Horizon $\gamma=0.99$) | B3 (Fast Learning $\alpha=0.30$) |
| :--- | :---: | :---: | :---: | :---: |
| **Extinction Rate** | **10/10 (100.0%)** | **10/10 (100.0%)** | **10/10 (100.0%)** | **10/10 (100.0%)** |
| **Mean Extinction Step** | **100.0** | **100.0** | **100.0** | **100.0** |
| **Mean Resource Level (units)** | **15.56** | **14.84** | **14.89** | **14.88** |
| **Time to First Depletion ($R < 25$)** | **Step 9.0** | **Step 8.8** | **Step 8.9** | **Step 8.9** |
| **Steps in 5%–95% Band** | **8.2%** | **7.7%** | **7.9%** | **7.8%** |
| **Steps at Zero Resource ($R = 0$)** | **91.6%** | **91.7%** | **91.6%** | **91.6%** |
| **Cumulative Harvest (Steps 1–10)** | **432.7 units** | **429.4 units** | **429.6 units** | **429.6 units** |
| **Total Funded Births / Run** | **0.0** | **0.0** | **0.0** | **0.0** |
| **Starvation Deaths / Run** | **34.0** | **34.0** | **33.7** | **33.7** |
| **Retirement Deaths / Run** | **16.0** | **16.0** | **16.3** | **16.3** |
| **Energy Conservation Verified?** | **YES** | **YES** | **YES** | **YES** |
| **Max Energy Discrepancy** | **$7.17 \times 10^{-11}$** | **$7.17 \times 10^{-11}$** | **$7.12 \times 10^{-11}$** | **$7.13 \times 10^{-11}$** |

---

## 3. Seed-Level Breakdown Across All 30 Treatment Runs

Across all 10 matched seeds (`1001`–`1010`):
- **B1 (Low Exploration):** Extinction occurred at exactly step 100 across 10/10 seeds. Mean resource ranged from $13.24$ to $16.50$. Maximum energy discrepancy was $7.17 \times 10^{-11}$.
- **B2 (Long Horizon):** Extinction occurred at step 100 across 10/10 seeds. Mean resource ranged from $13.77$ to $16.25$. Maximum energy discrepancy was $7.12 \times 10^{-11}$.
- **B3 (Fast Learning):** Extinction occurred at step 100 across 10/10 seeds. Mean resource ranged from $13.77$ to $16.21$. Maximum energy discrepancy was $7.13 \times 10^{-11}$.
- **Energy Conservation:** Conserved to machine precision in every single run ($100\% \text{ PASS}$).

---

## 4. Mechanistic Findings & Algorithmic Failure Analysis

### Why Algorithmic Hyperparameters Cannot Prevent Ecological Collapse
1. **Low Exploration (B1) Merely Solidifies Greedy Extraction:**
   When $\varepsilon$ is reduced from $0.20$ to $0.05$, agents follow their zero-initialized Q-tables more strictly. However, the first greedy harvest taken in step 1 yields positive net energy ($\Delta E > 0$). This immediately reinforces greedy harvesting over resting. Lower exploration actually reduced exploratory resting from $12.0\%$ down to $9.6\%$, accelerating resource drawdown to $R < 25$ in 8.8 steps.
2. **Longer Planning Horizon (B2) Suffers from Horizon Disconnect:**
   A high discount factor ($\gamma = 0.99$) can propagate delayed penalties backward only if the agent experiences the delayed consequence from that state. In this environment:
   - In step 1 ($R=350$), an agent harvests aggressively and transitions to step 2 ($R \approx 315$). Both states are abundant and yield positive rewards.
   - The starvation consequence does not occur until step 75–80.
   - Because the state space does not encode global ecological carrying capacity or the collective population trajectory, the agent has no tabular path to propagate the starvation reward at step 75 back to the choice of action at step 1.
3. **Fast Learning (B3) Rapidly Locks in Over-Extraction:**
   Increasing $\alpha$ from $0.10$ to $0.30$ caused Q-values for aggressive harvesting in abundant states to jump from $+0.17$ to $+0.45$ on the very first update, rapidly cementing aggressive extraction as the dominant action before any negative feedback could occur.

---

## 5. Summary Verdict for Experiment C2-B

- **Hypothesis C2-B.1 is CONFIRMED:**
  Algorithmic learning adjustments (exploration decay, discount horizon, learning rate) **cannot prevent ecological collapse and demographic extinction** in tabular Q-learning agents sharing a finite pool.
- The barrier to conservation is structural, not algorithmic: individual agents receive immediate private positive feedback for harvesting, while the negative feedback of resource exhaustion is delayed, diffuse, and shared across the entire population.

**Experiment C2-B is complete and validated. Ready to proceed to Experiment C2-C (Mixed-Population Mechanism).**

