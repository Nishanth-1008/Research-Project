# Version C — Stage 2 Mechanism Experiment Plan (Revised)

**Date:** 2026-11-01  
**Status:** Revised Plan Awaiting User Approval (Execution Frozen)  
**Baseline Model:** Version C (`sim-3.0.0`, `params-v3.0`)  
**Ecosystem Architecture:** Closed metabolic feedback, parent-funded reproduction ($E_{\text{cost}} = 10.0$), logistic regeneration ($g = 0.10, K = 500, R_0 = 350$).

---

## 1. Resolution of Pre-Execution Audit Checks (7/7)

### Check 1: Verification of Baseline $\varepsilon$-Decay Schedule
- **Frozen Implementation Verified:** Checked `simulator_v3/agents.py` lines 27–29:
  ```python
  fraction = min(self.age, maximum_age) / maximum_age
  return epsilon_start + fraction * (epsilon_minimum - epsilon_start)
  ```
- **Schedule Basis:** The exploration rate $\varepsilon$ decays strictly based on **individual agent age** (not global simulation step), starting at $\varepsilon_0 = 0.20$ at age 0 and reaching $\varepsilon_{\min} = 0.02$ at maximum age $A_{\max} = 100$.
- **Clarification:** The 100-step schedule reflects the agent's full lifetime horizon. All references to 500 steps have been corrected.

### Check 2: Analytical Reward Comparison Across Resource Levels
Under treatments A0, A1, and A2, assuming full requested harvest is available:
- **A0 (Baseline Net Energy):** $r_t = \Delta E_t = H_i - 0.20$
- **A1 (Proportional Scarcity Cost):** $r_t = \Delta E_t - 0.20 \cdot (1 - R_t / K) \cdot H_i$
- **A2 (Depletion Threshold Penalty):** $r_t = \Delta E_t - 0.20$ if $H_i > 0$ and $R_t < 0.33K$

| Resource Level $R_t$ | Action ($H_i$) | Baseline A0 | Proportional A1 | Depletion A2 |
| :--- | :--- | :---: | :---: | :---: |
| **$R = 350$ (70% $K$)** | `rest` ($0.0$) | $-0.20$ | $-0.20$ (pen $= 0.000$) | $-0.20$ (pen $= 0.00$) |
| | `conservative` ($0.5$) | $+0.30$ | $+0.27$ (pen $= 0.030$) | $+0.30$ (pen $= 0.00$) |
| | `moderate` ($1.0$) | $+0.80$ | $+0.74$ (pen $= 0.060$) | $+0.80$ (pen $= 0.00$) |
| | `aggressive` ($2.0$) | $+1.80$ | $+1.68$ (pen $= 0.120$) | $+1.80$ (pen $= 0.00$) |
| **$R = 165$ (33% $K$)** | `rest` ($0.0$) | $-0.20$ | $-0.20$ (pen $= 0.000$) | $-0.20$ (pen $= 0.00$) |
| | `conservative` ($0.5$) | $+0.30$ | $+0.23$ (pen $= 0.067$) | $+0.30$ (pen $= 0.00$) |
| | `moderate` ($1.0$) | $+0.80$ | $+0.67$ (pen $= 0.134$) | $+0.80$ (pen $= 0.00$) |
| | `aggressive` ($2.0$) | $+1.80$ | $+1.53$ (pen $= 0.268$) | $+1.80$ (pen $= 0.00$) |
| **$R = 100$ (20% $K$)** | `rest` ($0.0$) | $-0.20$ | $-0.20$ (pen $= 0.000$) | $-0.20$ (pen $= 0.00$) |
| | `conservative` ($0.5$) | $+0.30$ | $+0.22$ (pen $= 0.080$) | $+0.10$ (pen $= 0.20$) |
| | `moderate` ($1.0$) | $+0.80$ | $+0.64$ (pen $= 0.160$) | $+0.60$ (pen $= 0.20$) |
| | `aggressive` ($2.0$) | $+1.80$ | $+1.48$ (pen $= 0.320$) | $+1.60$ (pen $= 0.20$) |
| **$R = 25$ (5% $K$)** | `rest` ($0.0$) | $-0.20$ | $-0.20$ (pen $= 0.000$) | $-0.20$ (pen $= 0.00$) |
| | `conservative` ($0.5$) | $+0.30$ | $+0.20$ (pen $= 0.095$) | $+0.10$ (pen $= 0.20$) |
| | `moderate` ($1.0$) | $+0.80$ | $+0.61$ (pen $= 0.190$) | $+0.60$ (pen $= 0.20$) |
| | `aggressive` ($2.0$) | $+1.80$ | $+1.42$ (pen $= 0.380$) | $+1.60$ (pen $= 0.20$) |

#### Analytical Insight on Rewards:
Even with these penalties, **harvesting remains strictly more rewarding than resting whenever resource is physically obtainable** (e.g., at $R=25$, conservative harvesting yields $+0.10$ to $+0.20$ vs. $-0.20$ for resting). Only when $R = 0$ does harvesting return $0.0$ harvest, yielding $-0.20$ (or $-0.40$ in A2). Treatments A1 and A2 are therefore explicitly scoped as tests of **marginal scarcity disincentives**, not as guarantees of conservation.

### Check 3: RL Operational Mechanics in Frozen Code
- **Q-table Initialization:** Empty table (`dict`). Unvisited state-action pairs default to `0.0`.
- **Tie-Breaking:** Uniform random selection among all actions sharing the maximal Q-value (`random.choice(best)`).
- **Exploration Schedule:** Linear decay based on agent age: $\varepsilon(\text{age}) = 0.20 - (\text{age} / 100) \times 0.18$.
- **Temporal Sequence of Updates:** Living agents observe state $S_t = (R_t, E_{i,t}, \text{trend}_t)$ at the start of step $t$. Allocation and energy updates occur. Resource regenerates to $R_{t+1}$. The Q-table update occurs **after regeneration**, mapping $(S_t, A_t) \to R_t \to S_{t+1} = (R_{t+1}, E_{i,t+1}, \text{trend}_{t+1})$.
- **Resource Trend Discretization:** $\Delta R = R_t - R_{t-1}$. Discretized as `'falling'` if $\Delta R < -2.0$, `'rising'` if $\Delta R > 2.0$, and `'stable'` if $|\Delta R| \le 2.0$.

### Check 4: C2-C Exact Compositions & Static Replacement Rules
For population capacity $N = 50$:
- `C-76F`: **38 Fixed (76.0%) / 12 Q (24.0%)**
- `C-50F`: **25 Fixed (50.0%) / 25 Q (50.0%)**
- `C-24F`: **12 Fixed (24.0%) / 38 Q (76.0%)**

#### Exact Static Replacement Mechanics:
When vacancies open at replacement steps (`step % 20 == 0`):
1. **Target Quotas:** Fixed target $N_{\text{target, fixed}} \in \{38, 25, 12\}$; Q target $N_{\text{target, Q}} = 50 - N_{\text{target, fixed}}$.
2. **Deficit Determination:** Count current living agents of each type. Deficit $= \max(0, N_{\text{target}} - N_{\text{living}})$.
3. **Parent Selection:** Select an eligible parent ($E > 10.0$) of the deficit type.
4. **Unfunded / Asymmetric Failure Rule:** If no eligible parent of the deficit type exists, the vacancy is **left unfilled** (no founder injection; energy must be parent-funded).
5. **Telemetry:** Record both *intended composition* and *actual composition* at every step.

### Check 5: Corrected Run Count & Control Reuse
- **Total New Simulation Runs to Execute:** Exactly **80 runs**.
- **Reused Frozen Controls (0 new compute):**
  - Stage 1 `q_only` (Seeds 1001–1010, 10 runs) reused as baseline control `A0` for C2-A and `B0` for C2-B.
  - Stage 1 `fixed_only` (Seeds 1001–1010, 10 runs) reused as 100% Fixed benchmark `C-100F` for C2-C.
  - Stage 1 `q_only` (Seeds 1001–1010, 10 runs) reused as 100% Q-only benchmark `C-0F` for C2-C.

| Experiment | Treatment Condition | Population Group | New Runs | Frozen Control Reused |
| :--- | :--- | :--- | :---: | :---: |
| **C2-A** | `A1` (Proportional Scarcity Cost) | `q_only` | 10 | `A0` (10 runs) |
| | `A2` (Depletion Avoidance Penalty) | `q_only` | 10 | |
| **C2-B** | `B1` (Low Exploration $\varepsilon_0 = 0.05$) | `q_only` | 10 | `B0` (10 runs) |
| | `B2` (Long Horizon $\gamma = 0.99$) | `q_only` | 10 | |
| | `B3` (Fast Learning $\alpha = 0.30$) | `q_only` | 10 | |
| **C2-C** | `C-76F` (38 Fixed / 12 Q) | `static_mixture` | 10 | `C-100F` & `C-0F` (20 runs) |
| | `C-50F` (25 Fixed / 25 Q) | `static_mixture` | 10 | |
| | `C-24F` (12 Fixed / 38 Q) | `static_mixture` | 10 | |
| **Total** | | | **80 new runs** | **40 control references** |

### Check 6: Expanded Diagnostic Metrics
In addition to baseline telemetry, the following metrics will be logged at step- and run-levels:
1. **Reproductive Energy Surplus:** Distribution of candidate parent energy above the reproduction threshold: $\max(0, E_{\text{parent}} - 10.0)$.
2. **Actual Population Composition:** Tracking living fixed count, living Q count, and realized percentage share at every step.
3. **Resource at First Reproductive Failure:** Resource stock recorded at the exact step where an unfunded vacancy first occurs.
4. **Time to First Resource Depletion:** Step number at which $R_t$ first falls below $25.0$ (5% capacity) and below $1.0$.
5. **Q-Value Advantage ($\Delta Q$):** Spread between maximal harvesting action and resting: $\max(Q_{\text{cons}}, Q_{\text{mod}}, Q_{\text{agg}}) - Q_{\text{rest}}$ by state.
6. **Energy Distribution by Type:** Mean, min, and max energy reported separately for fixed agents and Q-agents in mixed runs.

### Check 7: Code and Result Isolation
- Version A, Version B, and Version C Stage 0/1 baselines remain strictly untouched.
- All Stage 2 implementations reside in `simulator_v3/experiments/`.
- All outputs write to `results_v3/stage2_mechanism/`.

---

## 2. Parameter Comparison Matrix (Frozen vs. Treatments)

| Parameter / Setting | Version C Baseline | C2-A (A1 / A2) | C2-B (B1 / B2 / B3) | C2-C (C-76F / C-50F / C-24F) |
| :--- | :---: | :---: | :---: | :---: |
| **Population Capacity ($N$)** | 50 | 50 | 50 | 50 |
| **Simulation Duration ($T$)** | 2,000 steps | 2,000 steps | 2,000 steps | 2,000 steps |
| **Resource Capacity ($K$)** | 500.0 | 500.0 | 500.0 | 500.0 |
| **Initial Resource ($R_0$)** | 350.0 | 350.0 | 350.0 | 350.0 |
| **Regeneration Rate ($g$)** | 0.10 (Logistic) | 0.10 (Logistic) | 0.10 (Logistic) | 0.10 (Logistic) |
| **Maintenance Cost ($c$)** | 0.20 | 0.20 | 0.20 | 0.20 |
| **Reproduction Cost ($E_{\text{cost}}$)**| 10.0 | 10.0 | 10.0 | 10.0 |
| **Eligibility Threshold** | $E_{\text{parent}} > 10.0$ | $E_{\text{parent}} > 10.0$ | $E_{\text{parent}} > 10.0$ | $E_{\text{parent}} > 10.0$ |
| **Reward Function ($r_t$)** | Net Energy ($\Delta E$) | **A1: Prop. / A2: Thresh.** | Net Energy ($\Delta E$) | Net Energy ($\Delta E$) |
| **Learning Rate ($\alpha$)** | 0.10 | 0.10 | **B3: 0.30** (B1, B2: 0.10) | 0.10 |
| **Discount Factor ($\gamma$)** | 0.95 | 0.95 | **B2: 0.99** (B1, B3: 0.95) | 0.95 |
| **Exploration ($\varepsilon_0 \to \varepsilon_{\min}$)** | $0.20 \to 0.02$ | $0.20 \to 0.02$ | **B1: $0.05 \to 0.01$** | $0.20 \to 0.02$ |
| **Initial Population Split** | 100% Q (or 50/50) | 100% Q | 100% Q | **38/12, 25/25, 12/38** |

---

## 3. Directory Layout for Stage 2

```
simulator_v3/
├── experiments/
│   ├── c2a_reward_mechanism.py
│   ├── c2b_learning_mechanism.py
│   └── c2c_mixed_population.py
│
results_v3/
├── stage2_mechanism/
│   ├── c2a_reward/
│   ├── c2b_learning/
│   └── c2c_mixtures/
│
calibration_logs/version_c/
├── stage2_experimental_plan.md        <-- (This Document)
├── c2a_reward_mechanism_report.md
├── c2b_learning_mechanism_report.md
├── c2c_mixed_population_report.md
└── stage2_synthesis_report.md
```

---

## 4. Execution Approval Request

The Stage 2 experimental plan has been fully updated to incorporate all seven pre-execution review requirements. 

**Execution is frozen until user review and explicit approval.**
