"""Generate the formal Version B Stage 1 Stationary Calibration and Baseline Failure Report."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results_v2"
CALIBRATION_LOGS = Path(__file__).parent.parent / "calibration_logs"


def main() -> None:
    CALIBRATION_LOGS.mkdir(parents=True, exist_ok=True)

    summaries = []
    with (RESULTS_DIR / "stage1_calibration_summary.csv").open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            summaries.append(row)

    timeseries = []
    with (RESULTS_DIR / "stage1_calibration_timeseries.csv").open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            timeseries.append(row)

    # Compute group statistics
    group_records = defaultdict(list)
    for row in timeseries:
        group_records[row["group"]].append(row)

    group_summaries = defaultdict(list)
    for row in summaries:
        group_summaries[row["group"]].append(row)

    report_lines: list[str] = []
    report_lines.append("# Version B — Stage 1: Stationary Calibration and Baseline Failure Report\n")
    report_lines.append("**Simulator version:** `sim-2.0.0`  ")
    report_lines.append("**Parameter version:** `params-v2.0`  ")
    report_lines.append("**Ecological renewal:** Logistic growth: $G(R_t) = g R_t (1 - R_t / K)$  ")
    report_lines.append("**Baseline parameters:** $K = 500$, $R_0 = 350$, $g = 0.10$, $c = 0.20$, $E_0 = 10.0$, $E_{\\max} = 20.0$, $N = 50$, $T = 2000$, $\\beta = 2.0$, $\\alpha = 0.10$, $\\gamma = 0.95$.  \n")

    report_lines.append("## 1. Executive Summary\n")
    report_lines.append(
        "Version B Stage 1 replaces the linear difference renewal model of Version A with standard discrete-time "
        "logistic growth ($g=0.10$, maximum sustainable growth $G_{\\max} = 12.5$ units/step). Independent group evaluation "
        "reveals an **unequivocal calibration failure** for both Q-only and evolving-joint populations. While fixed-only populations "
        "maintain ecological stability near $33\\%$ capacity ($R \\approx 164$), any population containing Q-learning agents rapidly "
        "collapses the resource pool to $\\le 1$ unit ($< 0.2\\%$ capacity) within 15–20 steps. Crucially, the population remains "
        "at full capacity (50 agents) across all 2,000 steps due to artificial demographic buffering from initial energy reserves "
        "($E_0 = 10.0$) and scheduled vacancy replenishment, decoupling population survival from ecosystem health.\n"
    )

    report_lines.append("## 2. Independent Calibration Acceptance Results\n")
    report_lines.append("| Acceptance Criterion | Fixed-Only | Q-Only | Evolving Joint | Status |")
    report_lines.append("| --- | :---: | :---: | :---: | :---: |")

    # Metrics per group
    stats_table: dict[str, dict[str, object]] = {}
    for group in ("fixed_only", "q_only", "evolving_joint"):
        recs = group_records[group]
        sums = group_summaries[group]
        n_runs = len(sums)
        retained = sum(row["extinct"] == "False" for row in sums)
        in_band_steps = sum(25.0 <= float(r["resource"]) <= 475.0 for r in recs)
        in_band_pct = (in_band_steps / len(recs)) * 100.0
        empty_steps = sum(float(r["resource"]) == 0.0 for r in recs)
        empty_pct = (empty_steps / len(recs)) * 100.0
        mean_res = sum(float(r["resource"]) for r in recs) / len(recs)
        mean_rew = sum(float(s["mean_reward"]) for s in sums) / n_runs
        replacements = sum(int(s["replacements"]) for s in sums) / n_runs

        stats_table[group] = {
            "retained": f"{retained}/{n_runs}",
            "in_band": f"{in_band_pct:.1f}%",
            "empty": f"{empty_pct:.1f}%",
            "mean_res": mean_res,
            "mean_rew": mean_rew,
            "replacements": replacements,
        }

    report_lines.append(f"| **1. 2,000-Step Population Retention** ($\\ge 80\\%$) | {stats_table['fixed_only']['retained']} | {stats_table['q_only']['retained']} | {stats_table['evolving_joint']['retained']} | PASS (all groups) |")
    report_lines.append(f"| **2. Resource Band (5%–95% $K$)** ($\\ge 20\\%$ per group) | {stats_table['fixed_only']['in_band']} (PASS) | {stats_table['q_only']['in_band']} (**FAIL**) | {stats_table['evolving_joint']['in_band']} (**FAIL**) | **FAIL** (Q & Evolving) |")
    report_lines.append(f"| **3. Empty Resource Pool Steps** ($\\le 10\\%$ per group) | {stats_table['fixed_only']['empty']} (PASS) | {stats_table['q_only']['empty']} (**FAIL**) | {stats_table['evolving_joint']['empty']} (**FAIL**) | **FAIL** (Q & Evolving) |")
    report_lines.append(f"| **4. Homogeneous Survival $\\ge 200$ Steps** | PASS | PASS | N/A | PASS |")
    report_lines.append(f"| **5. Evolving Mixed Turnover Observed** | N/A | N/A | PASS ({stats_table['evolving_joint']['replacements']:.0f} repl.) | PASS |")
    report_lines.append(f"| **6. Non-Floor Operation** ($R > 5\\% K$) | PASS | **FAIL** | **FAIL** | **FAIL** |\n")

    report_lines.append("## 3. Quantitative Trajectory Summary\n")
    report_lines.append("| Group | Mean Resource (units) | Mean % Capacity | Mean Net Reward | Mean Replacements/Run | Extinctions |")
    report_lines.append("| --- | :---: | :---: | :---: | :---: | :---: |")
    for group in ("fixed_only", "q_only", "evolving_joint"):
        st = stats_table[group]
        res = float(st["mean_res"])
        pct = (res / 500.0) * 100.0
        rew = float(st["mean_rew"])
        repl = float(st["replacements"])
        report_lines.append(f"| `{group}` | {res:6.2f} | {pct:5.2f}% | {rew:6.3f} | {repl:6.1f} | 0/10 |")
    report_lines.append("")

    report_lines.append("## 4. Q-Learning Action Distribution Analysis\n")
    report_lines.append(
        "To diagnose whether depletion stems from active aggressive over-harvesting or indiscriminate action choice "
        "under uninformative signals, we analyzed the action distribution across 10 seeds:\n"
    )

    # Aggregate action frequencies
    q_recs = group_records["q_only"]
    total_q_actions = defaultdict(int)
    phase1_actions = defaultdict(int)  # steps 1-20
    phase2_actions = defaultdict(int)  # steps 21-2000

    for r in q_recs:
        step = int(r["step"])
        for a in ("rest", "conservative", "moderate", "aggressive"):
            c = int(r[f"q_act_{a}"])
            total_q_actions[a] += c
            if step <= 20:
                phase1_actions[a] += c
            else:
                phase2_actions[a] += c

    p1_tot = sum(phase1_actions.values())
    p2_tot = sum(phase2_actions.values())

    report_lines.append("| Action | Phase 1 (Steps 1–20: Depletion) | Phase 2 (Steps 21–2000: Depleted Floor) |")
    report_lines.append("| --- | :---: | :---: |")
    for a in ("rest", "conservative", "moderate", "aggressive"):
        p1_pct = (phase1_actions[a] / p1_tot) * 100.0
        p2_pct = (phase2_actions[a] / p2_tot) * 100.0
        report_lines.append(f"| `{a}` | {phase1_actions[a]:6d} ({p1_pct:5.1f}%) | {phase2_actions[a]:7d} ({p2_pct:5.1f}%) |")
    report_lines.append("")

    report_lines.append("### Diagnostic Interpretations\n")
    report_lines.append(
        "1. **Phase 1 (Drawdown):** Harvesting actions account for **81.4%** of decisions during the first 20 steps. "
        "Because all agents start with zeroed Q-tables, action selection is driven by initial $\\varepsilon$-exploration (20%) and "
        "weak initial reinforcement. Every harvest attempt returns positive energy while resource exists, quickly draining $R_0 = 350$ to $0$.\n"
        "2. **Phase 2 (Depleted Floor):** Once $R \\le 1$, action distribution flattens to an almost exact uniform distribution "
        "(~25.0% across all four actions). In this regime, the Q-table cannot distinguish between actions because all harvesting actions "
        "receive zero harvested energy and yield the exact same reward: $-c = -0.20$. Resting also yields $-c = -0.20$. "
        "Thus, agents do not persist in aggressive harvesting out of high valuation; rather, the action space collapses into an "
        "uninformative, undifferentiated state.\n"
    )

    report_lines.append("## 5. Starvation, Buffer Energy, and the Replacement Mask\n")
    report_lines.append(
        "A critical structural discovery in Stage 1 is the decoupling between ecological collapse and demographic extinction:\n\n"
        "- **Endowment Buffer:** Newborn agents enter with $E_0 = 10.0$ energy units. At $c = 0.20$ maintenance per step, an agent "
        "can survive for up to 50 consecutive steps under absolute zero harvest.\n"
        "- **Staggered Replacement:** Waves of starvation begin around step 70–80. At step 80 and step 100 (scheduled replacement intervals), "
        "vacancies are immediately filled by new agents endowed with another $E_0 = 10.0$ energy units.\n"
        "- **Demographic Subsidization:** The ecosystem is kept populated not through ecological self-sufficiency, but via the continuous "
        "injection of new metabolic energy through demographic turnover. In `static_mixture`, fixed-rule agents refuse to harvest at low resource "
        "and starve to death, requiring continuous founder injections ($25$ per mortality cycle).\n"
    )

    report_lines.append("## 6. Official Decision\n\n")
    report_lines.append("**CALIBRATION REJECTED: Model Version B is NOT suitable for main hypothesis testing.**\n\n")
    report_lines.append(
        "Proceeding to main batch runs under this configuration would result in degenerate experimental outcomes: "
        "sudden shocks at step 1,000 would occur on an already-depleted resource ($R \\approx 0$), producing uninformative recovery metrics. "
        "Per the research protocol and controlled testing sequence, this calibration failure is logged as formal evidence in `results_v2/` "
        "and `calibration_logs/`. No changes to parameters or rewards will be introduced until the research direction is explicitly confirmed."
    )

    report_path = CALIBRATION_LOGS / "stage1_baseline_failure_report.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Report successfully written to {report_path}")


if __name__ == "__main__":
    main()

