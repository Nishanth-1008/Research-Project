"""Diagnostic script to inspect learned Q-values and action distributions.

Stages 1 & 2:
- Runs Q-only and Evolving-Joint in stationary scenario with baseline logistic renewal (g=0.10)
- Analyzes action frequencies over time
- Analyzes average Q-tables across states
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from parameters import Parameters
from simulator import ACTIONS, EcosystemSimulator


def run_diagnostics(group: str, seed: int = 1) -> None:
    p = Parameters(baseline_regeneration=0.10)
    sim = EcosystemSimulator(p, group, "stationary", seed)  # type: ignore[arg-type]

    # Run for 200 steps to observe initial depletion and stabilization
    for step in range(1, 201):
        sim.step(step)

    print(f"\n=======================================================")
    print(f"DIAGNOSTIC REPORT: Group={group}, Seed={seed}, Steps=200")
    print(f"=======================================================")
    print(f"Current Resource: {sim.resource:.2f} / {p.resource_capacity}")
    print(f"Living Population: {len(sim.agents)}")

    # 1. Action frequencies in different phases
    # Phase A: steps 1-20 (resource declining)
    # Phase B: steps 80-100 (depleted regime, mature agents)
    # Phase C: steps 101-120 (newborn cohort after replacement)
    def summarize_actions(start: int, end: int, label: str) -> None:
        tot: dict[str, int] = {a: 0 for a in ACTIONS}
        for rec in sim.records[start - 1 : end]:
            for a, count in rec.q_action_counts.items():
                tot[a] += count
        total_actions = sum(tot.values())
        print(f"\nQ-Action Frequencies {label} (Steps {start}-{end}, Total actions={total_actions}):")
        for a in ACTIONS:
            pct = (tot[a] / total_actions * 100) if total_actions else 0
            print(f"  {a:12s}: {tot[a]:5d} ({pct:5.1f}%)")

    summarize_actions(1, 20, "Early Decline")
    summarize_actions(80, 100, "Depleted Regime (Age 80-100)")
    summarize_actions(101, 120, "Post-Turnover Cohort (Age 1-20)")

    # 2. Inspect Learned Q-values across states
    q_table = sim.aggregate_q_tables()
    print("\nLearned Q-table (aggregated across living Q-agents at step 200):")
    print(f"{'State (Resource, Energy, Trend)':35s} | {'Rest':>7s} {'Conserv':>8s} {'Moderat':>8s} {'Aggress':>8s} | {'Preferred':>10s}")
    print("-" * 85)
    for state in sorted(q_table.keys()):
        vals = q_table[state]
        best_act = ACTIONS[vals.index(max(vals))]
        vals_str = " ".join(f"{v:8.3f}" for v in vals)
        state_str = f"({state[0]}, {state[1]}, {state[2]})"
        print(f"{state_str:35s} | {vals_str} | {best_act:>10s}")


if __name__ == "__main__":
    run_diagnostics("q_only", seed=1)
    run_diagnostics("evolving_joint", seed=1)

