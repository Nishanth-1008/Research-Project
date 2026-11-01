# Stage 2 Synthesis and Demographic Validation Audit Report

**Date:** 2026-11-01  
**Scope:** Formal audit of Experiment B2-C variants (C0–C4) and overarching synthesis across Stage 2 investigations (B2-A, B2-B, B2-C).  
**Core Question Investigated:** *Can a population appear resilient because of its demographic replacement system, even when its shared resource ecosystem is no longer sustainable?*

---

## 1. Targeted Demographic Validation Audits (B2-C Variants)

### Audit A: Exogenous Subsidy Accounting in C0 (Baseline)
- **Question:** How much external energy enters the simulation through newborns compared to resource harvesting?
- **Audit Findings (Seed 1, Q-only across 2,000 steps):**
  - Total demographic replacements / births: **1,611 agents**.
  - At $E_0 = 10.0$ units per newborn, **total external energy injected = 16,110.0 energy units**.
  - In contrast, total energy harvested from the ecosystem over 2,000 steps = **431.6 energy units**.
  - Total metabolic maintenance demanded by living agents = **17,126.4 energy units**.
  - **Verdict:** **97.4% of all energy consumed by the Q-learning population was injected exogenously via newborn subsidies**, not harvested from the ecosystem. The apparent 2,000-step population survival is an artifact of demographic subsidization.

### Audit B: Starvation and Extinction Sequencing in C1 ($E_0 = 2.0$)
- **Question:** What is the exact sequence leading to extinction?
- **Audit Findings:**
  1. Steps 1–10: Founder cohort draws the resource from $R_0 = 350$ down to $R = 0.0$.
  2. Steps 11–79: Founders survive on their initial $E_0=10.0$ endowment.
  3. Steps 80–99: Starvation deaths begin; living population drops to 17 agents by step 99.
  4. Step 100: All surviving founders reach `maximum_age = 100` and retire. 50 vacancies are filled by 50 newborns endowed with $E_0 = 2.0$.
  5. Steps 101–110: With resource depleted ($R \approx 0$), newborns harvest $0.0$ and burn $0.20$ maintenance per step. Over 10 steps, they consume exactly $10 \times 0.20 = 2.0$ units.
  6. Step 111: At the start of step 111, all 50 agents reach energy $\le 0.0$ and die simultaneously.
  7. **Verdict:** Extinction is clean, biological, and directly driven by metabolic starvation in an exhausted environment once the endowment buffer is rightsized.

### Audit C: Boundary Condition Analysis of C2 ($E_0 = 0.0$)
- **Question:** Why did fixed agents fail in C2 if their resource stock was healthy?
- **Audit Findings:**
  - In C2, fixed-rule agents maintained healthy stock ($R \approx 160–175$) and reproduced at step 100 with zero deaths.
  - At step 200, the second generation retired and 50 newborns entered with $E_0 = 0.0$.
  - At step 201, $R = 159.85$ ($31.97\%$ of capacity). By design, the fixed rule specifies: if $R < 0.33K$, take `rest`.
  - Because $R / K < 0.33$, all 50 newborns took `rest`, requested 0 harvest, paid $0.20$ maintenance, and entered the energy check with $E = 0.0 - 0.20 = -0.20$.
  - All 50 newborns perished on step 201 purely due to resting with zero starting energy.
  - **Verdict:** **Confirmed.** As identified, C2 represents an extreme mathematical boundary condition where starting energy is zero, causing immediate death if resting. It is not evidence of ecological failure by fixed-rule agents.

### Audit D: Reproduction Accounting Audit in C3 (Parent-Funded)
- **Question:** How was parent eligibility calculated, when was energy deducted, and was parity preserved across agent types?
- **Audit Findings:**
  - **Eligibility Criterion:** An agent is eligible to parent only if `agent.energy >= 10.0`.
  - **Deduction Timing:** Energy is deducted (`parent.energy -= 10.0`) upon offspring creation, guaranteeing parents cannot drop into negative energy.
  - **Unfunded Rule:** If no candidate parent possesses $\ge 10.0$ energy, vacancies remain unfilled (`unfunded_vacancies += 1`).
  - **Parity:** The exact same rule applies to all agent types. Fixed agents maintain high energy ($\sim 14.5$ units) because they conserve the resource, allowing them to fund 1,000 births over 2,000 steps with 0 extinctions. Q-learners deplete the resource, average only $\sim 1.7$ energy by step 60, and produce 0 eligible parents, halting reproduction completely and going extinct when founders retire at step 100.
  - **Verdict:** Accounting is fully consistent, biologically grounded, and identical across agent types.

### Audit E: Timing Verification in C4 (Delayed Replacement)
- **Question:** Did any rule change besides replacement frequency?
- **Audit Findings:**
  - Verification confirmed that all equations, parameters, newborn energies ($E_0 = 10.0$), and age limits ($A_{\max} = 100$) were identical to C0.
  - Only the conditional check changed from `step % 20 == 0` to `step % 40 == 0`.
  - This reduced total replacements from 1,607 down to 1,207, but because each replacement still injected 10 free energy units, the Q-population remained artificially propped up.
  - **Verdict:** C4 cleanly isolated replacement timing; delaying intervals alone does not stop the subsidy effect.

### Audit F: Precise Operational Definition of Extinction
- In all experiments, **Extinction** is strictly defined as:
  $$\text{living\_population} = 0$$
  This occurs when all living agents have either died from starvation ($\text{energy} \le 0$) or reached maximum age ($A_{\max} = 100$), leaving zero viable parents to replenish the cohort.

---

## 2. Definitive Stage 2 Synthesis: B2-A, B2-B, and B2-C

| Investigation | Hypothesis Tested | Observed Outcome | Scientific Conclusion |
| :--- | :--- | :--- | :--- |
| **B2-A: Perception** | Expanding state discretization (5 bands, explicit `exhausted` state). | Mean resource remained at $0.78$; actions remained uniform (~25%). | **Finer state perception alone does not stop collapse.** In an exhausted pool, harvesting weakly/strictly dominates resting in immediate energy return. |
| **B2-B: Incentives** | Adding public-good stewardship bonuses ($w=0.2, 0.5$) and scarcity penalties. | Penalties increased resting to $37.7\%$, but $62.3\%$ harvesting still overwhelmed logistic renewal. | **Decentralized individual reward adjustments cannot solve the free-rider dilemma** in a 50-agent well-mixed pool. |
| **B2-C: Demographics** | Reducing or removing exogenous newborn subsidies ($E_0=2$, parent-funded). | Q-learning populations went **10/10 extinct**, while fixed-rule populations survived 2,000 steps. | **Demographic subsidies artificially masked ecological collapse.** Apparent population survival was fueled by external energy injections. |

---

## 3. Scientific Impact on the Research Question

These findings elevate the study beyond a standard fixed-vs-RL comparison:
1. **Separation of Concepts:** Population survival must not be conflated with ecosystem resilience. Under exogenous demographic replacement, an agent population can persist indefinitely on life support while completely destroying its resource base.
2. **True Ecological Resilience:** A resilient system requires a coupled feedback loop where demographic reproduction depends on ecological sustainability (as demonstrated by parent funding in C3 or bounded endowments in C1). Under closed metabolic feedback, Q-learning over-exploitation leads to demographic collapse, whereas conservative heuristic agents thrive.

