# Stage 2 Scientific Audit & Narrative Correction Report

**Date:** 2026-11-01  
**Scope:** Formal audit correction of Stage 2 reports (`c2a_reward_mechanism_report.md`, `c2b_learning_mechanism_report.md`, `c2c_mixed_population_report.md`, and `stage2_synthesis_report.md`).  
**Rules Observed:** All simulation data and CSV files in `results_v3/` remain strictly frozen. This report reconciles numerical discrepancies, clarifies biological terminology, and decouples distinct mechanisms based purely on raw telemetry.

---

## 1. Audit Corrections & Reconciliations

### A. Resolution of the C-76F Vacancy Count Discrepancy
- **The Issue:** The seed-level summary table reported **88 total unfunded vacancies**, whereas the narrative text described **38 vacancies** at the fixed-extinction replacement event.
- **Raw Step-by-Step Ledger (Seed 1001 to 1010):**
  - **Steps 20, 40, 60:** Living population $= 50$. Vacancies $= 0$, unfunded $= 0$.
  - **Step 75–76:** All 38 fixed agents starve to death after exhausting their reserves during continuous resting at zero resource. Living population drops to 12 (all Q-learning agents).
  - **Step 80 (Replacement Interval 4):**
    - Target: 38 Fixed, 12 Q. Living: 0 Fixed, 12 Q.
    - Deficit: 38 Fixed, 0 Q.
    - The replacement mechanism attempts to fund 38 fixed vacancies. Because 0 living fixed parents exist, all **38 vacancies are unfunded**.
  - **Steps 81–99:** The 12 surviving Q-agents pay maintenance ($19 \times 0.20 = 3.80$ units).
  - **Step 100 (Replacement Interval 5 / Retirement):**
    - The 12 Q-learning founders reach `maximum_age = 100` and retire.
    - Population drops to 0. Total vacancies to reach capacity ($N = 50$) $= \mathbf{50}$.
    - Because 0 living parents of any type exist, all **50 vacancies are unfunded**.
  - **Cumulative Calculation:**
    $$\text{Total Cumulative Unfunded Vacancies} = 38 \text{ (at step 80)} + 50 \text{ (at step 100)} = \mathbf{88}$$
- **Reconciliation:** The number 38 refers to the **single-step event at step 80**, while 88 represents the **cumulative run total** across the entire simulation. In Seed 1009, the raw summary CSV confirms `total_unfunded_vacancies = 88` (the markdown table had a typographical omission showing 50).

---

### B. Reconciliation of Q-Agent Energy Surplus vs. Reproductive Disqualification
- **The Issue:** The C-76F trace showed Q-agents with a mean energy of **11.90 units at step 80**, yet the synthesis stated they had "no reproductive surplus remaining."
- **Exact Step-by-Step Energy Ledger for Q-Agents in C-76F:**
  - **Step 75:** Living Q-agents: 12. Energy: $\min = 12.80, \max = 13.00, \text{mean} = 12.90$.
  - **Step 80:** Living Q-agents: 12. Energy: $\min = 11.80, \max = 12.00, \text{mean} = \mathbf{11.90}$.
    - At step 80, **all 12 Q-agents possessed reproductive energy surplus ($E > 10.0$)**.
    - However, the replacement target was strictly determined by the **type-deficit**: target was 38 Fixed / 12 Q. The living population had 0 Fixed / 12 Q.
    - The 38 vacancies were exclusively **Fixed-type vacancies**. Under type inheritance, Q-parents cannot produce Fixed offspring.
    - Because the Q-type quota (12) was already full, the system did not create Q-vacancies.
    - Thus, Q-agents were **reproductively disqualified not by energy poverty at step 80, but by type-restricted static quota rules**.
  - **Step 99:** By step 99, after 19 more steps without harvest, Q-agent energy dropped to $\text{mean} = \mathbf{8.10}$ ($\max = 8.20$).
  - **Step 100:** When founders retired, all 12 Q-agents had energy $< 10.0$. At that point, they were disqualified by **both** death/retirement and energy exhaustion.
- **Correction:** The synthesis has been updated to explicitly distinguish between **reproductive isolation / type-quota barriers at step 80** and **energy starvation at step 100**.

---

### C. Scientific Framing Corrections
1. **Terminology ("Parasitism" $\to$ "Free-Riding on Collective Restraint"):**
   - The term "parasitism" has been removed from all reports.
   - The observed interaction is formally described as **free-riding on collective restraint** or **asymmetric exploitation of conservation**: fixed agents exercise unilateral conservation restraint by resting below $R=165$, and the unrestrained Q-learning minority extracts the regenerated resource, driving the conservers to extinction before exhausting itself.
2. **Reward Scope (C2-A):**
   - Corrected broad assertions that "reward design cannot work."
   - Explicitly scoped to the two tested formulations (A1: marginal scarcity cost, A2: threshold penalty).
3. **Q-Learning Information Propagation (C2-B):**
   - Corrected the assertion that Q-learning "cannot propagate delayed rewards."
   - The failure is properly attributed to the **state representation**: the local state $(R, E, \text{trend})$ does not encode the collective population trajectory or global carrying capacity, making delayed multi-step credit assignment across a fast 9-step drawdown ineffective.

---

## 2. Updated Scientific Conclusion for Stage 2

> *"Under the tested model conditions, fixed-rule agents maintained the renewable resource and population indefinitely, while the tested Q-learning populations depleted the resource and eventually became extinct. Changes to the tested reward penalties and learning parameters did not prevent this outcome. In mixed populations, increasing the proportion of fixed-rule agents delayed resource depletion (from 8.9 steps at 0% Fixed to 30.2 steps at 76% Fixed) but did not prevent extinction. Detailed event tracing reveals that asymmetric harvesting and type-restricted reproduction jointly contributed to this result: conservative fixed agents starved due to unilateral resting, while Q-learning agents with reproductive surplus at step 80 were barred by type-restricted quotas from funding fixed vacancies. Stage 3 is required to isolate the independent contribution of reproductive barriers from resource competition."*
