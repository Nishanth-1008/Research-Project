# Version C — Stage 3 Mechanism Isolation Plan

**Date:** 2026-11-01  
**Goal:** Isolate resource competition from demographic rules and ecological regeneration limits.  
**Baseline Reference:** Version C Stage 2 `C-76F` (38 Fixed / 12 Q, 100% extinction at step 100).

---

## 1. Planned Stage 3 Experiments

### Experiment 3A: Type-Neutral Reproduction
- **Research Question:** Does the extinction of the mixed community in `C-76F` depend on type-restricted reproduction, or would Q-learning agents with surplus energy at step 80 sustain the population if permitted to fund offspring regardless of type?
- **Treatment:** In `C-76F` (38 Fixed / 12 Q initial), when vacancies open at replacement steps:
  - Any living parent with energy $> 10.0$ is eligible to fund an offspring.
  - The offspring inherits the parent's agent type (or random type if type-neutral).
  - Test both:
    - `3A-1` (Type-Inherited, Unrestricted Offspring): Any eligible parent can fund offspring of its *own* type up to capacity ($N=50$), removing the fixed-quota restriction that blocked Q-agents at step 80.
    - `3A-2` (Fully Type-Neutral): Any eligible parent can fund vacancies, but newborn type is sampled proportionally or uniformly.
- **Seeds:** 10 matched seeds (`1001`–`1010`).

### Experiment 3B: Resource-Access Control
- **Research Question:** Can fixed agents survive alongside Q-learning agents if extractive demand is capped?
- **Treatment:** Impose a maximum harvest quota on Q-learning agents (e.g. limiting maximum request to $1.0$ or restricting access when $R < 165$), without modifying the Q-learning algorithm.
- **Seeds:** 10 matched seeds (`1001`–`1010`).

### Experiment 3C: Regeneration Sensitivity
- **Research Question:** Does the collapse of mixed populations depend on the specific baseline renewal rate ($g = 0.10$)?
- **Treatment:** Test $g \in \{0.15, 0.20\}$ on the `C-76F` and `C-50F` compositions.
- **Seeds:** 10 matched seeds (`1001`–`1010`).

---

## 2. Deliverables & Isolation Structure

```
simulator_v3/
├── experiments_stage3/
│   ├── exp3a_type_neutral_reproduction.py
│   ├── exp3b_resource_access_control.py
│   └── exp3c_regeneration_sensitivity.py
│
results_v3/
├── stage3_isolation/
│   ├── exp3a/
│   ├── exp3b/
│   └── exp3c/
│
calibration_logs/version_c/stage3/
├── stage3_plan.md
├── exp3a_report.md
├── exp3b_report.md
└── exp3c_report.md
```
