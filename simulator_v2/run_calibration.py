"""Execute Version B Stage 1 calibration across 10 seeds and produce raw CSV records."""

from __future__ import annotations

import csv
from pathlib import Path

from parameters import Parameters
from simulator import EcosystemSimulator, Group

OUTPUT_DIR = Path(__file__).parent.parent / "results_v2"
CALIBRATION_GROUPS: tuple[Group, ...] = ("fixed_only", "q_only", "evolving_joint")
SEEDS = tuple(range(1, 11))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    parameters = Parameters(baseline_regeneration=0.10)
    summaries: list[dict[str, object]] = []
    records: list[dict[str, object]] = []

    for group in CALIBRATION_GROUPS:
        for seed in SEEDS:
            sim = EcosystemSimulator(parameters, group, "stationary", seed)
            result = sim.run()
            summaries.append(result.summary())
            for record in result.records:
                records.append({
                    "seed": seed,
                    "group": group,
                    "scenario": "stationary",
                    "step": record.step,
                    "resource": record.resource,
                    "total_harvest": record.total_harvest,
                    "living_population": record.living_population,
                    "q_learning_share": record.q_learning_share,
                    "mean_reward": record.mean_reward,
                    "mean_energy": record.mean_energy,
                    "q_act_rest": record.q_action_counts.get("rest", 0),
                    "q_act_conservative": record.q_action_counts.get("conservative", 0),
                    "q_act_moderate": record.q_action_counts.get("moderate", 0),
                    "q_act_aggressive": record.q_action_counts.get("aggressive", 0),
                    "fixed_act_rest": record.fixed_action_counts.get("rest", 0),
                    "fixed_act_conservative": record.fixed_action_counts.get("conservative", 0),
                    "fixed_act_moderate": record.fixed_action_counts.get("moderate", 0),
                    "fixed_act_aggressive": record.fixed_action_counts.get("aggressive", 0),
                })

    with (OUTPUT_DIR / "stage1_calibration_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    with (OUTPUT_DIR / "stage1_calibration_timeseries.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    print(f"Calibration run complete. Saved {len(summaries)} summaries and {len(records)} step records.")


if __name__ == "__main__":
    main()

