# Protocol Amendments: Version 2.0 (Version D.1 Specification)

**Document:** `docs/research_protocol/07_protocol_v2_amendments.md`  
**Date:** 2026-11-02  
**Target:** Formal Protocol v2.0 Amendments to [`docs/research_protocol/01_research_protocol.md`](file:///Users/nish/home/Research%20Project/docs/research_protocol/01_research_protocol.md) and [`docs/research_protocol/02_parameter_spec_sheet.md`](file:///Users/nish/home/Research%20Project/docs/research_protocol/02_parameter_spec_sheet.md)  
**Status:** FORMALLY AUTHORIZED BY PI  
**Implemented In:** Version D.1 (`sim-4.1.0`, `params-v4.1`)  

---

## 1. Overview & Authority

By formal authorization of the Principal Investigator (PI) on 2026-11-02, the following five protocol amendments are ratified as **Protocol v2.0**. These amendments supersede specific legacy provisions of the initial protocol while locking all foundational constants.

---

## 2. Formal Protocol Amendments

### Amendment 1: Demographic Architecture (Vital Rates with Logistic Crowding)
- **Supersedes:** `01_research_protocol.md` Section 3.3 (Softmax Tournament Replacement) & `02_parameter_spec_sheet.md:19` (Global Replacement Interval $I=20$).
- **Amended Specification:**
  Population turnover operates via decentralized, bioenergetic vital rates rather than competitive tournament lotteries. Living agents evaluate independent reproduction attempts at each step.
  - **Eligibility:** Agent energy $E_i \ge 15.0$, age $a_i < 60$, reproduction cooldown $\le 0$.
  - **Thermodynamic Deduction:** A successful birth deducts exactly 10.0 energy units from the parent ($E_{\text{parent}} \leftarrow E_{\text{parent}} - 10.0$). The parent retains $\ge 5.0$ energy. The newborn receives exactly 10.0 initial energy. Dyadic energy is strictly conserved ($\Delta E_{\text{birth}} = 0.000$).
  - **Fertility Probability with Logistic Crowding:**
    $$P_i'(t) = P_{\max} \cdot \operatorname{clip}\left(\frac{E_i(t) - 15.0}{5.0}, 0, 1\right) \cdot A(a_i(t)) \cdot \max\left(0, 1 - \frac{N(t)}{K_{\text{pop}}}\right)$$
    where $P_{\max} = 0.10$, $K_{\text{pop}} = 50$, and $A(a_i)$ is linear reproductive senescence from age 45 to 60 ($A = 1.0$ for $a \le 45$; $A = (60 - a)/15$ for $45 < a < 60$; $A = 0$ for $a \ge 60$).
  - Cooldown: Cooldown of 20 steps applies to the parent upon a successful birth.

### Amendment 2: Cultural Transmission (Gradual Q-Table Inheritance)
- **Supersedes:** `01_research_protocol.md` Section 3.4 (Tabula Rasa Zero Inheritance).
- **Amended Specification:**
  Newborn Q-learning agents inherit an immutable snapshot of their parent's active Q-table at birth ($Q_{\text{parent}}$). During the first 12 steps of life, the offspring's active decision policy blends parental values with its own learned experience via linear decay:
  $$\lambda_t = \max\left(0.0, 1.0 - \frac{\text{age}}{12}\right)$$
  $$Q_{\text{active}}(s, a) = (1 - \lambda_t) \cdot Q_{\text{own}}(s, a) + \lambda_t \cdot Q_{\text{parent}}(s, a)$$
  Offspring Q-learning updates apply strictly to $Q_{\text{own}}$. Parent Q-snapshots are immutable.

### Amendment 3: Static Mixture Control (Deficit-Targeted Offspring Assignment)
- **Supersedes:** `01_research_protocol.md` Section 4.1 (Static Mixture Replacement).
- **Amended Specification:**
  In `static_mixture`, population composition is maintained near 50/50 without selection via Deficit-Targeted Offspring Assignment. When any eligible parent (Fixed or Q) reproduces (paying 10.0 energy), newborn type assignment follows a **strict, non-overlapping priority hierarchy**:
  1. **Priority 1 (Extinction Recovery):** If one subpopulation has count zero ($N_{\text{fixed}} = 0$ or $N_Q = 0$), the newborn is mandatorily assigned to the extinct type, injecting a founder at age 0 with 10.0 energy funded by the surviving type.
  2. **Priority 2 (Deficit Elimination):** If type counts are unequal ($N_{\text{fixed}} \ne N_Q$), the newborn is assigned to whichever type currently has the lower count (larger deficit relative to parity). This holds uniformly for $N < 50$, $N = 50$, and $N > 50$, since $(25 - N_{\text{fixed}} > 25 - N_Q) \iff N_{\text{fixed}} < N_Q$.
  3. **Priority 3 (Parity Tie-Breaking):** If type counts are exactly equal ($N_{\text{fixed}} = N_Q$), the newborn type is assigned via fair Bernoulli trial ($p = 0.50$).
  - **Inheritance Boundary:** If a Fixed parent funds a Q newborn, the child receives a clean, zero-initialized Q-table ($Q=0$). A Q-parent funding a Fixed newborn gives the child the standard Fixed rule table.

### Amendment 4: Mechanism Ablations (Vital-Rate Formulations)
- **Supersedes:** `01_research_protocol.md` Section 4.2 & `02_parameter_spec_sheet.md:86` (Tournament Fitness Ablations).
- **Amended Specification:**
  - **Survival-Only Group (`survival_only`):** Birth probability is driven by an **age-based survival proxy** that scales linearly with chronological age:
    $$P_i' = P_{\max} \cdot \left(\frac{a_i}{A_{\max}}\right) \cdot \max\left(0, 1 - \frac{N(t)}{K_{\text{pop}}}\right) \quad \text{subject to } E_i \ge 15.0$$
    *Methodological Note:* This formulation rewards individuals that have survived longer by granting higher reproductive probability with advancing age. It operates as an **age-based survival proxy**, not as a direct measure of survival fitness. Somatic energy ($E \ge 15.0$) functions strictly as an thermodynamic feasibility gate (parent pays 10.0) without shaping probability above 15.0.
  - **Reward-Only Group (`reward_only`):** Birth probability is driven by instantaneous somatic energy surplus:
    $$P_i' = P_{\max} \cdot \operatorname{clip}\left(\frac{E_i - 15.0}{5.0}, 0, 1\right) \cdot \max\left(0, 1 - \frac{N(t)}{K_{\text{pop}}}\right)$$
    Age-fertility decline is disabled ($A(a_i) = 1.0$ for all ages until senescence retirement at $a = 100$).

### Amendment 5: Observation State Space (36 States)
- **Supersedes:** `02_parameter_spec_sheet.md:58-64` (27-State Space).
- **Amended Specification:**
  The observation space consists of $3 \times 4 \times 3 = \mathbf{36\text{ discrete states}}$ (144 Q-values per learner):
  1. **Resource Band (3):** Low ($R < 165.0$), Medium ($165.0 \le R \le 330.0$), High ($R > 330.0$).
  2. **Energy Band (4):** Critical ($E < 3.0$), Low ($3.0 \le E < 7.0$), Medium ($7.0 \le E < 14.0$), High ($E \ge 14.0$).
  3. **Resource Trend Band (3):** Declining ($\Delta R < -2.0$), Stable ($-2.0 \le \Delta R \le 2.0$), Increasing ($\Delta R > 2.0$).
  The addition of the `critical` band provides an essential starvation-warning signal for biological survival.

---

## 3. Scope Lock Invariants & Disjoint Seed Ranges
- **Commons capacity:** $K = 500.0, R_0 = 350.0$.
- **Baseline regeneration:** $g = 0.10$, stressed regeneration $g = 0.05$.
- **Biological maintenance cost:** $c = 0.20$ energy/step.
- **Senescence retirement age:** $A_{\max} = 100$ steps.
- **Harvest quotas (Treatment B):** Rest = 0.0, Conservative = 0.25, Moderate = 0.50, Aggressive = 1.0.
- **Strict Seed Disjointness (Zero Overlap):**
  - **Dedicated Calibration Batch:** Seeds **901–910** (10 independent seeds, 2,000 steps).
  - **Core Production Batch (Phase 2):** Seeds **1001–1030** (30 pre-registered seeds, 2,000 steps).
  - **Mechanism Ablation Batch (Phase 3):** Seeds **1001–1030** (30 paired seeds, 2,000 steps).
  - Calibration and production seed sets are strictly disjoint ($[901, 910] \cap [1001, 1030] = \emptyset$). Calibration data will never be pooled into production analysis.
- Q-learning hyperparameters: $\alpha = 0.10, \gamma = 0.95, \epsilon_0 = 0.20 \to 0.02$.
- Production run horizon: $T = 2,000$ steps.
- Common matched seeds for production: Seeds 1001–1030 (30 seeds).

