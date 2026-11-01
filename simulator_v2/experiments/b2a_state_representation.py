"""Experiment B2-A: State Representation Refinement.

Hypothesis:
Discretizing the resource into 5 levels—specifically separating severe exhaustion/scarcity (R < 0.05K = 25)
from moderate scarcity (0.05K <= R < 0.33K)—allows Q-learning agents to perceive near-zero conditions
independently of ordinary scarcity, potentially learning distinct state-value associations.

Constraints:
- Original RL reward preserved: r_t = Delta E_t = harvested - maintenance.
- Logistic regeneration preserved: G(R) = g * R * (1 - R/K), g = 0.10.
- All demographic, action, and energy parameters unchanged.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Add simulator_v2 to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parameters import Parameters
from simulator import ACTIONS, EcosystemSimulator, Group, StepRecord

OUTPUT_DIR = Path(__file__).parent.parent.parent / "results_v2" / "b2a_state_representation"


class RefinedStateSimulator(EcosystemSimulator):
    def _state(self, agent, resource: float, previous_resource: float) -> tuple[str, str, str]:
        resource_ratio = resource / self.parameters.resource_capacity
        energy_ratio = agent.energy / self.parameters.maximum_energy

        # 5-level resource discretization:
        # 'exhausted': < 0.05 (R < 25)
        # 'low': 0.05 - 0.33 (25 <= R < 165)
        # 'medium': 0.33 - 0.66 (165 <= R <= 330)
        # 'high': 0.66 - 0.90 (330 < R <= 450)
        # 'full': > 0.90 (R > 450)
        if resource_ratio < 0.05:
            resource_band = "exhausted"
        elif resource_ratio < 0.33:
            resource_band = "low"
        elif resource_ratio <= 0.66:
            resource_band = "medium"
        elif resource_ratio <= 0.90:
            resource_band = "high"
        else:
            resource_band = "full"

        energy_band = "low" if energy_ratio < 0.33 else "medium" if energy_ratio <= 0.66 else "high"
        delta = resource - previous_resource
        trend = "falling" if delta < -2 else "rising" if delta > 2 else "stable"
        return resource_band, energy_band, trend

    def _choose_action(self, agent, state: tuple[str, str, str]) -> str:
        if agent.kind == "fixed":
            resource_band = state[0]
            # Fixed rule: rest on exhausted/low, conservative on medium, moderate on high/full
            if resource_band in ("exhausted", "low"):
                return "rest"
            elif resource_band == "medium":
                return "conservative"
            else:
                return "moderate"

        values = agent.q_table.setdefault(state, [0.0] * len(ACTIONS))
        if self.random.random() < self._epsilon(agent):
            return self.random.choice(ACTIONS)
        maximum = max(values)
        best = [index for index, value in enumerate(values) if value == maximum]
        return ACTIONS[self.random.choice(best)]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    parameters = Parameters(baseline_regeneration=0.10)
    groups: tuple[Group, ...] = ("fixed_only", "q_only", "evolving_joint")
    seeds = tuple(range(1, 11))

    summaries: list[dict[str, object]] = []
    records: list[dict[str, object]] = []

    print("Running Experiment B2-A (10 seeds x 3 groups)...")
    for group in groups:
        for seed in seeds:
            sim = RefinedStateSimulator(parameters, group, "stationary", seed)
            result = sim.run()
            summaries.append(result.summary())
            for record in result.records:
                records.append({
                    "seed": seed,
                    "group": group,
                    "step": record.step,
                    "resource": record.resource,
                    "total_harvest": record.total_harvest,
                    "living_population": record.living_population,
                    "q_share": record.q_learning_share,
                    "mean_reward": record.mean_reward,
                    "mean_energy": record.mean_energy,
                    "q_act_rest": record.q_action_counts.get("rest", 0),
                    "q_act_conservative": record.q_action_counts.get("conservative", 0),
                    "q_act_moderate": record.q_action_counts.get("moderate", 0),
                    "q_act_aggressive": record.q_action_counts.get("aggressive", 0),
                })

    with (OUTPUT_DIR / "b2a_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    with (OUTPUT_DIR / "b2a_timeseries.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    # Print quick summary
    print("\n--- B2-A RESULTS SUMMARY ---")
    for group in groups:
        group_sums = [s for s in summaries if s["group"] == group]
        mean_res = sum(float(s["mean_resource"]) for s in group_sums) / len(group_sums)
        group_recs = [r for r in records if r["group"] == group]
        in_band = sum(25.0 <= float(r["resource"]) <= 475.0 for r in group_recs) / len(group_recs) * 100
        empty = sum(float(r["resource"]) == 0.0 for r in group_recs) / len(group_recs) * 100
        print(f"Group {group:15s} | Mean Resource: {mean_res:6.2f} | In Band (5-95%): {in_band:5.1f}% | Empty: {empty:5.1f}%")


if __name__ == "__main__":
    main()

