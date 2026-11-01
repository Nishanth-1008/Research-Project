# Experiment B2-A: State Representation Refinement — Formal Report

**Date:** 2026-11-01  
**Experiment:** B2-A  
**Objective:** Test whether finer resource discretization—specifically introducing an explicit `exhausted` state ($R < 0.05K = 25$) distinct from ordinary `low` resource ($25 \le R < 165$)—allows Q-learning agents to perceive near-zero conditions and adaptively avoid resource collapse under the original RL reward ($r_t = \Delta E_t$).

---

## 1. Experimental Setup

- **Ecological Renewal:** Logistic growth $G(R_t) = g R_t (1 - R_t / K)$ with $g = 0.10$.
- **Reward Function:** Unchanged ($r_t = \text{harvested} - \text{maintenance} = \Delta E_t$).
- **Demographics:** Unchanged ($E_0 = 10.0, E_{\max} = 20.0, c = 0.20, N = 50, A_{\max} = 100$).
- **State Space Expansion:**
  - Original 3-band resource ($<0.33K, 0.33–0.66K, >0.66K$) expanded to 5 bands:
    1. `exhausted`: $R < 0.05K$ ($R < 25$)
    2. `low`: $0.05K \le R < 0.33K$ ($25 \le R < 165$)
    3. `medium`: $0.33K \le R \le 0.66K$ ($165 \le R \le 330$)
    4. `high`: $0.66K < R \le 0.90K$ ($330 < R \le 450$)
    5. `full`: $R > 0.90K$ ($R > 450$)
- **Sample:** 10 independent random seeds (1–10) $\times$ 3 groups (`fixed_only`, `q_only`, `evolving_joint`) $\times$ 2,000 steps.

---

## 2. Quantitative Results

| Group | Mean Resource (units) | Mean % Capacity ($K=500$) | % Steps in Band (5%–95%) | % Steps Empty ($R=0$) | Extinctions |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `fixed_only` | **163.69** | **32.74%** | **100.0%** | **0.0%** | 0/10 |
| `q_only` | **0.78** | **0.16%** | **0.4%** | **99.6%** | 0/10 |
| `evolving_joint` | **1.15** | **0.23%** | **0.7%** | **99.3%** | 0/10 |

---

## 3. Q-Value & Action Policy Analysis in the `exhausted` State

Aggregated learned Q-values at step 200 for agents in the `exhausted` condition:

| State | $Q(\text{rest})$ | $Q(\text{conservative})$ | $Q(\text{moderate})$ | $Q(\text{aggressive})$ | Optimal Action |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `('exhausted', 'medium', 'stable')` | -0.0873 | **-0.0839** | -0.0876 | -0.0883 | `conservative` |
| `('exhausted', 'low', 'stable')` | -0.1070 | -0.1092 | -0.1091 | **-0.1068** | `aggressive` |

Action distributions in `q_only` across all 2,000 steps in the `exhausted` state remain completely uniform:
- `rest`: **25.0%**
- `conservative`: **25.0%**
- `moderate`: **25.0%**
- `aggressive`: **25.0%**

---

## 4. Key Scientific Findings & Definitive Conclusion

1. **Perception Is Not the Limiting Factor:**
   Providing finer perceptual resolution allows agents to recognize that they are in an `exhausted` environment, but **it gives them no incentive to change their behavior**.
2. **The Structural Payoff Dominance Persists:**
   - For an individual agent in state `exhausted`:
     - Choosing `rest` guarantees reward $r = 0 - c = -0.20$.
     - Choosing any harvest action gives reward $r = \min(\text{request}, R_{\text{avail}}) - c \ge -0.20$.
   - Any step in which regeneration produces even a fraction of a unit of resource, an agent that attempts to harvest receives a non-negative harvest, strictly beating the guaranteed $-0.20$ loss of resting.
   - When the resource is completely empty, all four actions yield exactly $-0.20$, resulting in identical Q-values and undifferentiated uniform random action selection (25% each).
3. **Conclusion for B2-A:**
   **Refining state representation alone does NOT prevent ecological collapse.** The issue is rooted in the individual payoff structure ($r_t = \Delta E_t$), where resting is weakly or strictly dominated by harvesting, leaving agents with zero incentive to conserve the resource stock.

