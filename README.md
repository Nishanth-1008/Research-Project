# Adaptive Agents in a Shared Resource Ecosystem

This research project investigates the co-evolution of resource dynamics, foraging strategies, and population turnover in mixed communities of fixed-rule heuristic agents and reinforcement learning (tabular Q-learning) agents sharing a renewable commons.

---

## 🧭 Master Project Lineage & Current Status

For the complete, audited scientific lineage from Version A through Stage 3B and the Version D roadmap, see **[MASTER_RESEARCH_LINEAGE.md](file:///Users/nish/home/Research%20Project/MASTER_RESEARCH_LINEAGE.md)**.

| Model / Stage | Focus Mechanism | Empirical Outcome | Status |
| :--- | :--- | :--- | :---: |
| **Version A** (`sim-1.0.0`) | Linear renewal, exogenous subsidies ($E_0=10$) | Tragedy of the commons masked by fixed agents. | **Frozen** |
| **Version B** (`sim-2.0.0`) | Logistic renewal, demographic audit (`B2-A/B/C`) | Proved 97.4% of system energy came from subsidies; removing subsidies caused 100% extinction. | **Frozen** |
| **Version C** (`sim-3.0.0`) | Closed parent-funded system ($\Delta E=0$, strict $E>10$) | Confirmed 100% extinction at step 100; tragedy of the commons robust to reward shaping. | **Frozen** |
| **Stage 3A** | Type-neutral reproduction (Q fills Fixed vacancies) | 40 births; delayed extinction to step 131; resource remained at 0 (demographics decoupled from ecology). | **Frozen** |
| **Stage 3B** | Graded harvest quotas (Universal action scaling) | $-50\%$ and $-62.5\%$ quotas saved resource ($R \approx 164–279$) and eliminated starvation, but synchronized age caused extinction at 100. | **Frozen** |
| **Stage 3C** | Distributed founder age structure | Investigates whether asynchronous retirements solve the demographic cliff under sustainable harvest quotas. | **Proposed, Not Executed** |
| **Version D** (`sim-4.0.0`) | Energy-dependent, age-dependent reproduction with Q-table inheritance | Replaces artificial vacancy quotas with endogenous vital rates and cultural policy transmission. | **Drafting Specification** |

---

## 📂 Repository Navigation

- **[MASTER_RESEARCH_LINEAGE.md](file:///Users/nish/home/Research%20Project/MASTER_RESEARCH_LINEAGE.md)**: Master roadmap and synthesis table across all experimental stages.
- **[docs/](file:///Users/nish/home/Research%20Project/docs/README.md)**: Foundational research protocols, parameter specifications, checklists, and publication roadmap.
- **[calibration_logs/](file:///Users/nish/home/Research%20Project/calibration_logs/)**: Independent audit reports, execution manifests, and pre-execution reviews for each completed stage.
  - [Version B Failure & Audit Reports](file:///Users/nish/home/Research%20Project/calibration_logs/version_b/stage2_synthesis_audit_report.md)
  - [Version C Stage 1 Calibration Report](file:///Users/nish/home/Research%20Project/calibration_logs/version_c/stage1_calibration_report.md)
  - [Version C Stage 2 Synthesis Report](file:///Users/nish/home/Research%20Project/calibration_logs/version_c/stage2_audit_correction_report.md)
  - [Experiment 3A Final Report](file:///Users/nish/home/Research%20Project/calibration_logs/version_c/stage3/exp3a_execution_report.md)
  - [Experiment 3B Final Report](file:///Users/nish/home/Research%20Project/calibration_logs/version_c/stage3/exp3b_execution_report.md)
  - [Version D Model Specification](file:///Users/nish/home/Research%20Project/calibration_logs/version_d/version_d_model_specification.md)
- **`simulator/`**: Version A simulator (`sim-1.0.0`).
- **`simulator_v2/`**: Version B simulator (`sim-2.0.0`).
- **`simulator_v3/`**: Version C simulator (`sim-3.0.0`) and Stage 3 mechanism isolation experiments.
- **`results_v3/`**: Frozen CSV summaries, time-series, and execution manifests for Version C, Stage 2, and Stage 3.
