"""Version C Stage 1 Calibration Runner.

Executes 30 runs: 10 seeds x 3 groups (fixed_only, q_only, evolving_joint) x 2,000 steps.
Saves raw summaries and detailed step timeseries in results_v3/calibration/.
Logs reproduction events and energy balances.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Add simulator_v3 to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from parameters import Parameters
from simulator import EcosystemSimulator, Group

OUTPUT_DIR = Path(__file__).parent.parent / "results_v3" / "calibration"
GROUPS: tuple[Group, ...] = ("fixed_only", "q_only", "evolving_joint")
SEEDS = tuple(range(1, 11))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    params = Parameters()

    summaries: list[dict[str, object]] = []
    timeseries: list[dict[str, object]] = []
    repro_events: list[dict[str, object]] = []

    print(f"Starting Version C Stage 1 Calibration ({len(GROUPS)} groups x {len(SEEDS)} seeds = 30 runs)...")

    for group in GROUPS:
        for seed in SEEDS:
            sim = EcosystemSimulator(params, group, "stationary", seed)
            result = sim.run()

            # Verify energy conservation at termination
            living_energy = sum(a.energy for a in sim.agents)
            is_conserved, discrepancy = sim.energy_ledger.verify_energy_balance(living_energy)

            s_dict = result.summary()
            s_dict["living_at_end"] = len(sim.agents)
            s_dict["initial_endowment"] = sim.energy_ledger.initial_founder_endowment
            s_dict["cumulative_harvested"] = sim.energy_ledger.cumulative_harvested
            s_dict["cumulative_maintenance"] = sim.energy_ledger.cumulative_maintenance
            s_dict["cumulative_cap_losses"] = sim.energy_ledger.cumulative_energy_cap_losses
            s_dict["cumulative_starvation_losses"] = sim.energy_ledger.cumulative_starvation_losses
            s_dict["cumulative_retirement_losses"] = sim.energy_ledger.cumulative_retirement_losses
            s_dict["energy_conserved"] = is_conserved
            s_dict["energy_discrepancy"] = discrepancy
            summaries.append(s_dict)

            for rec in result.records:
                timeseries.append({
                    "seed": seed,
                    "group": group,
                    "step": rec.step,
                    "resource": rec.resource,
                    "total_harvest": rec.total_harvest,
                    "living_population": rec.living_population,
                    "q_share": rec.q_learning_share,
                    "mean_reward": rec.mean_reward,
                    "mean_energy": rec.mean_energy,
                    "births": rec.births,
                    "starvation_deaths": rec.starvation_deaths,
                    "retirement_deaths": rec.retirement_deaths,
                    "unfunded_vacancies": rec.unfunded_vacancies,
                    "act_rest": rec.action_counts.get("rest", 0),
                    "act_conservative": rec.action_counts.get("conservative", 0),
                    "act_moderate": rec.action_counts.get("moderate", 0),
                    "act_aggressive": rec.action_counts.get("aggressive", 0),
                })

            for log in result.reproduction_logs:
                repro_events.append({
                    "seed": seed,
                    "group": group,
                    "step": log.step,
                    "parent_id": log.parent_id,
                    "parent_type": log.parent_type,
                    "parent_energy_before": log.parent_energy_before,
                    "energy_transferred": log.energy_transferred,
                    "parent_energy_after": log.parent_energy_after,
                    "newborn_id": log.newborn_id,
                    "newborn_type": log.newborn_type,
                    "success": log.success,
                    "failure_reason": log.failure_reason,
                })

            print(f"  [{group:15s} | s{seed:2d}] completed {result.steps_completed:4d} steps. Extinct={result.extinct}, Living={len(sim.agents):2d}, Res={result.mean_resource:6.2f}, Conserved={is_conserved}")

    with (OUTPUT_DIR / "stage1_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    with (OUTPUT_DIR / "stage1_timeseries.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(timeseries[0].keys()))
        writer.writeheader()
        writer.writerows(timeseries)

    if repro_events:
        with (OUTPUT_DIR / "stage1_reproduction_events.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(repro_events[0].keys()))
            writer.writeheader()
            writer.writerows(repro_events)

    print(f"\nStage 1 calibration runs finished. Output written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

