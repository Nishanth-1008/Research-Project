"""Version D Stage 1 Calibration Runner.

Executes 10 seeds (1001-1010) x 500 steps.
Preserves complete step-level time-series data, reproduction logs, and summary metrics.
Tracks population dynamics, resource trajectories, energy ledger, and Q-table inheritance.
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

# Add simulator_v4 to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator_v4.parameters import Parameters
from simulator_v4.simulator import EcosystemSimulator

OUTPUT_DIR = Path(__file__).parent.parent / "results_v4" / "calibration"
SEEDS = tuple(range(1001, 1011))
RUN_LENGTH = 500


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    params = Parameters(run_length=RUN_LENGTH)

    summaries: list[dict[str, object]] = []
    timeseries: list[dict[str, object]] = []
    repro_events: list[dict[str, object]] = []
    manifest: list[dict[str, object]] = []

    print(f"Starting Version D Calibration: 10 seeds (1001-1010) x {RUN_LENGTH} steps...")

    for seed in SEEDS:
        start_time = time.time()
        sim = EcosystemSimulator(parameters=params, scenario="stationary", seed=seed)
        result = sim.run()
        elapsed = time.time() - start_time

        # Analyze trajectory metrics
        peak_pop = max(r.living_population for r in result.records)
        peak_step = next(r.step for r in result.records if r.living_population == peak_pop)
        depleted = any(r.resource < 1.0 for r in result.records)
        depletion_step = next((r.step for r in result.records if r.resource < 1.0), None)

        total_fixed_births = sum(r.fixed_births for r in result.records)
        total_q_births = sum(r.q_births for r in result.records)
        total_attempts = sum(r.reproduction_attempts for r in result.records)
        total_successes = sum(r.successful_births for r in result.records)
        repro_rate = (total_successes / total_attempts) if total_attempts > 0 else 0.0

        max_disc = max(abs(r.energy_ledger_discrepancy) for r in result.records)
        living_energy = sum(a.energy for a in sim.agents)
        is_conserved, final_disc = sim.energy_ledger.verify_energy_balance(living_energy)

        final_fixed_pop = sum(1 for a in sim.agents if a.kind == "fixed")
        final_q_pop = sum(1 for a in sim.agents if a.kind == "q_learning")

        # Summary entry
        s_dict = {
            "seed": seed,
            "simulator_version": result.simulator_version,
            "parameter_version": result.parameter_version,
            "steps_completed": result.steps_completed,
            "extinct": result.extinct,
            "initial_population": params.initial_population,
            "final_population": result.final_population,
            "final_fixed_population": final_fixed_pop,
            "final_q_population": final_q_pop,
            "final_q_share": result.final_q_learning_share,
            "peak_population": peak_pop,
            "peak_population_step": peak_step,
            "mean_resource": result.mean_resource,
            "final_resource": result.records[-1].resource if result.records else 0.0,
            "resource_depleted": depleted,
            "depletion_step": depletion_step,
            "mean_reward": result.mean_reward,
            "total_births": result.total_births,
            "total_fixed_births": total_fixed_births,
            "total_q_births": total_q_births,
            "total_reproduction_attempts": total_attempts,
            "total_successful_births": total_successes,
            "reproduction_success_rate": repro_rate,
            "total_starvation_deaths": result.total_starvation_deaths,
            "total_retirement_deaths": result.total_retirement_deaths,
            "energy_conserved": is_conserved,
            "max_energy_discrepancy": max_disc,
            "final_energy_discrepancy": final_disc,
        }
        summaries.append(s_dict)

        # Manifest entry
        manifest.append({
            "run_id": f"calib_seed_{seed}",
            "seed": seed,
            "status": "COMPLETED",
            "steps_completed": result.steps_completed,
            "extinct": result.extinct,
            "final_population": result.final_population,
            "total_births": result.total_births,
            "total_starvations": result.total_starvation_deaths,
            "total_retirements": result.total_retirement_deaths,
            "final_resource": s_dict["final_resource"],
            "max_energy_discrepancy": max_disc,
            "elapsed_seconds": round(elapsed, 4),
        })

        # Step time-series entries
        for rec in result.records:
            timeseries.append({
                "seed": seed,
                "step": rec.step,
                "resource": rec.resource,
                "total_harvest": rec.total_harvest,
                "requested_harvest": rec.requested_harvest,
                "fixed_requested_harvest": rec.fixed_requested_harvest,
                "q_requested_harvest": rec.q_requested_harvest,
                "fixed_allocated_harvest": rec.fixed_allocated_harvest,
                "q_allocated_harvest": rec.q_allocated_harvest,
                "regeneration": rec.regeneration,
                "living_population": rec.living_population,
                "fixed_population": rec.fixed_population,
                "q_population": rec.q_population,
                "q_share": rec.q_learning_share,
                "mean_reward": rec.mean_reward,
                "mean_energy": rec.mean_energy,
                "births": rec.births,
                "fixed_births": rec.fixed_births,
                "q_births": rec.q_births,
                "reproduction_attempts": rec.reproduction_attempts,
                "successful_births": rec.successful_births,
                "starvation_deaths": rec.starvation_deaths,
                "retirement_deaths": rec.retirement_deaths,
                "act_rest": rec.action_counts.get("rest", 0),
                "act_conservative": rec.action_counts.get("conservative", 0),
                "act_moderate": rec.action_counts.get("moderate", 0),
                "act_aggressive": rec.action_counts.get("aggressive", 0),
                "q_act_rest": rec.q_action_counts.get("rest", 0),
                "q_act_conservative": rec.q_action_counts.get("conservative", 0),
                "q_act_moderate": rec.q_action_counts.get("moderate", 0),
                "q_act_aggressive": rec.q_action_counts.get("aggressive", 0),
                "fixed_act_rest": rec.fixed_action_counts.get("rest", 0),
                "fixed_act_conservative": rec.fixed_action_counts.get("conservative", 0),
                "fixed_act_moderate": rec.fixed_action_counts.get("moderate", 0),
                "fixed_act_aggressive": rec.fixed_action_counts.get("aggressive", 0),
                "energy_ledger_discrepancy": rec.energy_ledger_discrepancy,
            })

        # Reproduction log entries
        for log in result.reproduction_logs:
            repro_events.append({
                "seed": seed,
                "step": log.step,
                "parent_id": log.parent_id,
                "parent_type": log.parent_type,
                "parent_age": log.parent_age,
                "parent_energy_before": log.parent_energy_before,
                "energy_transferred": log.energy_transferred,
                "parent_energy_after": log.parent_energy_after,
                "newborn_id": log.newborn_id,
                "newborn_type": log.newborn_type,
                "reproduction_probability": log.reproduction_probability,
                "success": log.success,
                "failure_reason": log.failure_reason,
            })

        print(
            f"  [Seed {seed}] completed {result.steps_completed:3d} steps in {elapsed:.3f}s. "
            f"Final Pop={result.final_population:2d} (Peak={peak_pop:2d}), "
            f"Births={result.total_births:3d}, "
            f"Starv={result.total_starvation_deaths:2d}, "
            f"Retire={result.total_retirement_deaths:2d}, "
            f"Final Res={s_dict['final_resource']:6.2f}, "
            f"Max Disc={max_disc:.2e}"
        )

    # Save CSV files
    summary_path = OUTPUT_DIR / "calibration_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    timeseries_path = OUTPUT_DIR / "calibration_timeseries.csv"
    with timeseries_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(timeseries[0].keys()))
        writer.writeheader()
        writer.writerows(timeseries)

    repro_path = OUTPUT_DIR / "calibration_reproduction_logs.csv"
    with repro_path.open("w", newline="", encoding="utf-8") as f:
        if repro_events:
            writer = csv.DictWriter(f, fieldnames=list(repro_events[0].keys()))
            writer.writeheader()
            writer.writerows(repro_events)
        else:
            f.write("seed,step,parent_id,parent_type,parent_age,parent_energy_before,energy_transferred,parent_energy_after,newborn_id,newborn_type,reproduction_probability,success,failure_reason\n")

    manifest_path = OUTPUT_DIR / "calibration_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest[0].keys()))
        writer.writeheader()
        writer.writerows(manifest)

    print("\nCalibration execution completed successfully!")
    print(f"Summary written to: {summary_path}")
    print(f"Time-series written to: {timeseries_path}")
    print(f"Reproduction logs written to: {repro_path}")
    print(f"Manifest written to: {manifest_path}")


if __name__ == "__main__":
    main()

