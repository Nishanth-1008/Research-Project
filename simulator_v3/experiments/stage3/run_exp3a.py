"""Batch runner and validation script for Experiment 3A."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from exp3a_type_neutral_reproduction import Experiment3ASimulator
from parameters import Parameters

OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "results_v3" / "stage3_mechanism_isolation" / "exp3a"
SEEDS = tuple(range(1001, 1011))


def run_batch(mode: str) -> None:
    print(f"\n==========================================")
    print(f"Running Experiment 3A Batch: mode={mode} (10 seeds, 2000 steps, initial 38F / 12Q)")
    print(f"==========================================")
    params = Parameters()
    summaries = []
    timeseries = []
    repro_rows = []

    for seed in SEEDS:
        sim = Experiment3ASimulator(params, "stationary", seed, mode=mode, fixed_target=38)
        res = sim.run()

        living_energy = sum(a.energy for a in sim.agents)
        is_conserved, disc = sim.energy_ledger.verify_energy_balance(living_energy)

        t_first_25 = next((r.step for r in res.records if r.resource < 25.0), None)
        t_first_1 = next((r.step for r in res.records if r.resource < 1.0), None)
        min_res = min((r.resource for r in res.records), default=0.0)
        final_res = res.records[-1].resource if res.records else 0.0

        s_dict = res.summary()
        s_dict["mode"] = mode
        s_dict["living_at_end"] = len(sim.agents)
        s_dict["final_fixed_count"] = sum(a.kind == "fixed" for a in sim.agents)
        s_dict["final_q_count"] = sum(a.kind == "q_learning" for a in sim.agents)
        s_dict["final_resource"] = final_res
        s_dict["min_resource"] = min_res
        s_dict["complete_resource_depletion"] = (min_res < 1.0)
        s_dict["time_to_first_R_below_25"] = t_first_25
        s_dict["time_to_first_R_below_1"] = t_first_1
        s_dict["cross_type_replacements"] = sim.cross_type_q_births + sim.cross_type_fixed_births
        s_dict["cross_type_q_births"] = sim.cross_type_q_births
        s_dict["cross_type_fixed_births"] = sim.cross_type_fixed_births
        s_dict["first_cross_type_step"] = sim.first_cross_type_step
        s_dict["first_q_replaces_fixed_step"] = sim.first_q_replaces_fixed_step
        s_dict["first_fixed_replaces_q_step"] = sim.first_fixed_replaces_q_step
        s_dict["cumulative_cross_type_energy"] = sim.cumulative_cross_type_energy
        s_dict["cumulative_harvested"] = sim.energy_ledger.cumulative_harvested
        s_dict["cumulative_maintenance"] = sim.energy_ledger.cumulative_maintenance
        s_dict["cumulative_retirement_losses"] = sim.energy_ledger.cumulative_retirement_losses
        s_dict["energy_conserved"] = is_conserved
        s_dict["energy_discrepancy"] = disc
        summaries.append(s_dict)

        for rec in res.records:
            timeseries.append({
                "mode": mode,
                "seed": seed,
                "step": rec.step,
                "resource": rec.resource,
                "total_harvest": rec.total_harvest,
                "regeneration": getattr(rec, "regeneration", 0.0),
                "living_population": rec.living_population,
                "fixed_count": getattr(rec, "fixed_count", 0),
                "q_count": getattr(rec, "q_count", 0),
                "q_share": rec.q_learning_share,
                "mean_reward": rec.mean_reward,
                "mean_energy": rec.mean_energy,
                "mean_fixed_energy": getattr(rec, "mean_fixed_energy", None),
                "min_fixed_energy": getattr(rec, "min_fixed_energy", None),
                "mean_q_energy": getattr(rec, "mean_q_energy", None),
                "min_q_energy": getattr(rec, "min_q_energy", None),
                "births": rec.births,
                "fixed_births": getattr(rec, "fixed_births", 0),
                "q_births": getattr(rec, "q_births", 0),
                "cross_type_q_births": getattr(rec, "cross_type_q_births", 0),
                "cross_type_fixed_births": getattr(rec, "cross_type_fixed_births", 0),
                "cross_type_energy": getattr(rec, "cross_type_energy", 0.0),
                "total_reproduction_energy": getattr(rec, "total_reproduction_energy", 0.0),
                "fixed_reproduction_energy": getattr(rec, "fixed_reproduction_energy", 0.0),
                "q_reproduction_energy": getattr(rec, "q_reproduction_energy", 0.0),
                "starvation_deaths": rec.starvation_deaths,
                "retirement_deaths": rec.retirement_deaths,
                "unfunded_vacancies": rec.unfunded_vacancies,
            })

        for log in res.reproduction_logs:
            repro_rows.append({
                "mode": mode,
                "seed": seed,
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

        print(f"  [{mode:9s} | Seed {seed}] steps={res.steps_completed:4d}, extinct={res.extinct}, final_pop={len(sim.agents):2d} (F={s_dict['final_fixed_count']}, Q={s_dict['final_q_count']}), disc={disc:.2e}, conserved={is_conserved}")

    with (OUTPUT_DIR / f"{mode}_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    with (OUTPUT_DIR / f"{mode}_timeseries.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(timeseries[0].keys()))
        writer.writeheader()
        writer.writerows(timeseries)

    if repro_rows:
        with (OUTPUT_DIR / f"{mode}_reproduction_logs.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(repro_rows[0].keys()))
            writer.writeheader()
            writer.writerows(repro_rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Starting execution of Experiment 3A batches...")
    run_batch("control")
    run_batch("treatment")
    print("\nExperiment 3A execution completed successfully.")


if __name__ == "__main__":
    main()
