# Experiment B2-B: Reward Design with Resource Stewardship — Formal Report

**Date:** 2026-11-01  
**Experiment:** B2-B  
**Objective:** Test whether augmenting the individual net-energy reward with resource-stewardship incentives enables Q-learning agents to learn conservation and avoid resource collapse under logistic ecological renewal, without artificially paralyzing agent actions.

---

## 1. Experimental Variants & Controls

All variants were executed across the identical **10 calibration seeds (1–10)**, the identical **3 population groups** (`fixed_only`, `q_only`, `evolving_joint`), and identical ecological parameters ($K=500, R_0=350, g=0.10, c=0.20, E_0=10.0, N=50$).

1. **Control (Baseline Net Energy):**
   $$r_t = \Delta E_t = \text{harvested} - \text{maintenance}$$
2. **Variant 1a (Proportional Stewardship Bonus, $w = 0.20$):**
   $$r_t = \Delta E_t + w \cdot \frac{R_{t+1}}{K}$$
   Rewards agents for high resource stock, offsetting maintenance when the pool is abundant.
3. **Variant 1b (Strong Proportional Stewardship Bonus, $w = 0.50$):**
   $$r_t = \Delta E_t + 0.50 \cdot \frac{R_{t+1}}{K}$$
4. **Variant 2 (Scarcity Harvesting Penalty, $w = 0.20$):**
   $$r_t = \Delta E_t - 0.20 \quad \text{if } a_t \neq \text{'rest'} \text{ and } R_t < 0.05K$$
   Directly penalizes extractive actions taken when the shared pool is critically depleted ($R_t < 25$).

---

## 2. Quantitative Results Summary (10 Seeds $\times$ 2,000 Steps)

| Variant | Group | Mean Resource (units) | Mean % Capacity | % Steps in Band (5%–95%) | % Steps Empty ($R=0$) | Extinctions |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Control (Baseline)** | `fixed_only` | 163.69 | 32.74% | 100.0% | 0.0% | 0/10 |
| | `q_only` | 0.78 | 0.16% | 0.4% | 94.8% | 0/10 |
| | `evolving_joint` | 1.15 | 0.23% | 0.7% | 93.2% | 0/10 |
| **Variant 1a ($w=0.20$)** | `fixed_only` | 163.69 | 32.74% | 100.0% | 0.0% | 0/10 |
| | `q_only` | 0.78 | 0.16% | 0.4% | 99.6% | 0/10 |
| | `evolving_joint` | 1.16 | 0.23% | 0.7% | 99.3% | 0/10 |
| **Variant 1b ($w=0.50$)** | `fixed_only` | 163.69 | 32.74% | 100.0% | 0.0% | 0/10 |
| | `q_only` | 0.94 | 0.19% | 0.5% | 99.5% | 0/10 |
| | `evolving_joint` | 1.28 | 0.26% | 0.7% | 99.2% | 0/10 |
| **Variant 2 (Penalty $0.20$)** | `fixed_only` | 163.69 | 32.74% | 100.0% | 0.0% | 0/10 |
| | `q_only` | 0.78 | 0.16% | 0.4% | 99.6% | 0/10 |
| | `evolving_joint` | 1.15 | 0.23% | 0.7% | 99.3% | 0/10 |

---

## 3. Action Policy Distributions in the Depleted Regime

Action distribution among living Q-agents during mature steps (steps 101–120):

| Variant | `rest` | `conservative` | `moderate` | `aggressive` | Total Actions |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Control** | 25.9% | 24.3% | 24.2% | 25.6% | 1,000 |
| **Variant 1a ($w=0.20$)** | 25.9% | 24.3% | 24.2% | 25.6% | 1,000 |
| **Variant 1b ($w=0.50$)** | 25.0% | 25.0% | 24.3% | 25.7% | 1,000 |
| **Variant 2 (Scarcity Penalty)** | **37.7%** | 21.8% | 19.8% | 20.7% | 1,000 |

---

## 4. Key Mechanistic Insights

1. **Why Stock-Proportional Rewards (Variants 1a & 1b) Fail to Prevent Collapse:**
   - The bonus $w \cdot (R_{t+1}/K)$ is a **public good**. It depends on the collective stock, not an individual agent's decision.
   - For an individual agent choosing between `rest` (harvest 0) and `aggressive` (request 2):
     - If the agent harvests, its own private energy increases by up to $+2.0$.
     - The shared pool decreases by at most $2.0$ units out of $K=500$, reducing the future stock by $\Delta R \le 2.0$.
     - The stewardship bonus drops by at most $w \cdot (2 / 500) = 0.0008 \cdot w$.
     - The immediate private gain ($+2.0$) overwhelms the tiny shared stock penalty ($< 0.001$).
   - The classical free-rider incentive remains essentially intact.

2. **Why the Direct Scarcity Penalty (Variant 2) Raised Resting to 37.7% but Failed to Recover the Pool:**
   - Imposing a direct $-0.20$ penalty on attempting to harvest when $R < 25$ successfully changed learned Q-values: resting became more attractive, increasing resting frequency from 25% to **37.7%**.
   - However, **in a 50-agent population with logistic renewal, a 37.7% resting rate leaves ~31 agents still attempting to harvest**.
   - Even conservative harvest by 31 agents requests $31 \times 0.5 = 15.5$ units.
   - At $R \approx 1$, logistic growth $G(R) = 0.10 \times 1 \times (1 - 1/500) \approx 0.10$ units.
   - Because $15.5 \gg 0.10$, any regenerated fraction is immediately absorbed by whichever agents harvest first in the random priority order. The pool cannot cross the critical tipping threshold back into the productive growth zone.

---

## 5. Formal Conclusion for Experiment B2-B

- **Hypothesis B2-B is disproven under decentralized tabular Q-learning:**
  - Neither diffuse stock bonuses nor localized scarcity penalties prevent ecological collapse in a 50-agent well-mixed population.
  - The collective threshold for resource recovery under logistic growth requires near-total cessation of harvesting at low stock ($>95\%$ rest), which individual decentralized Q-learners cannot coordinate without strict collective institutions or catastrophic population reduction.
- This confirms that **reward design alone within reasonable, non-paralyzing bounds does not resolve the collapse**.
- Next controlled investigation: **Experiment B2-C (Demographic Rules & Metabolic Subsidies)**.

