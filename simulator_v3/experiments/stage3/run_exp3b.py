"""Batch runner and validation script for Experiment 3B (Graded Harvest Quotas)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from exp3b_harvest_quotas import Experiment3BSimulator, QuotaGroup
from parameters import Parameters

OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "results_v3" / "stage3_mechanism_isolation" / "exp3b"
SEEDS = tuple(range(1001, 1011))
GROUPS: tuple[QuotaGroup, ...] = ("control", "treatment_a", "treatment_b", "treatment_c")


def run_batch(quota_group: QuotaGroup) -> list[dict[str, object]]:
    print(f"\n==========================================")
    print(f"Running Experiment 3B Batch: group={quota_group} (10 seeds, 2000 steps, initial 38F / 12Q)")
    print(f"==========================================")
    params = Parameters()
    summaries = []
    timeseries = []
    repro_rows = []

    for seed in SEEDS:
        sim = Experiment3BSimulator(params, "stationary", seed, quota_group=quota_group, fixed_target=38)
        res = sim.run()

        living_energy = sum(a.energy for a in sim.agents)
        is_conserved, disc = sim.energy_ledger.verify_energy_balance(living_energy)

        t_first_25 = next((r.step for r in res.records if r.resource < 25.0), None)
        t_first_1 = next((r.step for r in res.records if r.resource < 1.0), None)
        min_res = min((r.resource for r in res.records), default=0.0)
        final_res = res.records[-1].resource if res.records else 0.0

        r_100_vals = [r.resource for r in res.records if r.step <= 100]
        mean_r_100 = (sum(r_100_vals) / len(r_100_vals)) if r_100_vals else 0.0

        ratio_vals = [getattr(r, "harvest_regeneration_ratio", None) for r in res.records if getattr(r, "harvest_regeneration_ratio", None) is not None]
        mean_ratio = (sum(ratio_vals) / len(ratio_vals)) if ratio_vals else None

        fixed_starvs = sum(getattr(r, "fixed_starvations", 0) for r in res.records)
        q_starvs = sum(getattr(r, "q_starvations", 0) for r in res.records)
        cum_req = sum(getattr(r, "total_requested", 0.0) for r in res.records)
        cum_fixed_req = sum(getattr(r, "fixed_requested", 0.0) for r in res.records)
        cum_q_req = sum(getattr(r, "q_requested", 0.0) for r in res.records)
        cum_fixed_alloc = sum(getattr(r, "fixed_allocated", 0.0) for r in res.records)
        cum_q_alloc = sum(getattr(r, "q_allocated", 0.0) for r in res.records)

        # Action distribution totals
        rest_counts = sum(r.action_counts.get("rest", 0) for r in res.records)
        cons_counts = sum(r.action_counts.get("conservative", 0) for r in res.records)
        mod_counts = sum(r.action_counts.get("moderate", 0) for r in res.records)
        agg_counts = sum(r.action_counts.get("aggressive", 0) for r in res.records)

        q_agg_counts = sum(r.q_action_counts.get("aggressive", 0) for r in res.records)
        q_mod_counts = sum(r.q_action_counts.get("moderate", 0) for r in res.records)
        q_cons_counts = sum(r.q_action_counts.get("conservative", 0) for r in res.records)
        q_rest_counts = sum(r.q_action_counts.get("rest", 0) for r in res.records)

        s_dict = res.summary()
        s_dict["quota_group"] = quota_group
        s_dict["mean_resource_100"] = mean_r_100
        s_dict["mean_resource_full"] = s_dict.pop("mean_resource")
        s_dict["final_resource"] = final_res
        s_dict["min_resource"] = min_res
        s_dict["complete_resource_depletion"] = (min_res < 1.0)
        s_dict["time_to_first_R_below_25"] = t_first_25
        s_dict["time_to_first_R_below_1"] = t_first_1
        s_dict["living_at_end"] = len(sim.agents)
        s_dict["final_fixed_count"] = sum(a.kind == "fixed" for a in sim.agents)
        s_dict["final_q_count"] = sum(a.kind == "q_learning" for a in sim.agents)
        s_dict["fixed_starvation_deaths"] = fixed_starvs
        s_dict["q_starvation_deaths"] = q_starvs
        s_dict["cumulative_requested_harvest"] = cum_req
        s_dict["cumulative_fixed_requested"] = cum_fixed_req
        s_dict["cumulative_q_requested"] = cum_q_req
        s_dict["cumulative_allocated_harvest"] = sim.energy_ledger.cumulative_harvested
        s_dict["cumulative_fixed_allocated"] = cum_fixed_alloc
        s_dict["cumulative_q_allocated"] = cum_q_alloc
        s_dict["mean_harvest_regeneration_ratio"] = mean_ratio
        s_dict["cumulative_maintenance"] = sim.energy_ledger.cumulative_maintenance
        s_dict["cumulative_retirement_losses"] = sim.energy_ledger.cumulative_retirement_losses
        s_dict["action_rest_total"] = rest_counts
        s_dict["action_conservative_total"] = cons_counts
        s_dict["action_moderate_total"] = mod_counts
        s_dict["action_aggressive_total"] = agg_counts
        s_dict["q_action_aggressive_total"] = q_agg_counts
        s_dict["q_action_moderate_total"] = q_mod_counts
        s_dict["q_action_conservative_total"] = q_cons_counts
        s_dict["q_action_rest_total"] = q_rest_counts
        s_dict["energy_conserved"] = is_conserved
        s_dict["energy_discrepancy"] = disc
        summaries.append(s_dict)

        for rec in res.records:
            timeseries.append({
                "quota_group": quota_group,
                "seed": seed,
                "step": rec.step,
                "resource": rec.resource,
                "total_requested": getattr(rec, "total_requested", 0.0),
                "fixed_requested": getattr(rec, "fixed_requested", 0.0),
                "q_requested": getattr(rec, "q_requested", 0.0),
                "total_harvest": rec.total_harvest,
                "fixed_allocated": getattr(rec, "fixed_allocated", 0.0),
                "q_allocated": getattr(rec, "q_allocated", 0.0),
                "regeneration": getattr(rec, "regeneration", 0.0),
                "harvest_regeneration_ratio": getattr(rec, "harvest_regeneration_ratio", None),
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
                "pct_fixed_eligible": getattr(rec, "pct_fixed_eligible", None),
                "pct_q_eligible": getattr(rec, "pct_q_eligible", None),
                "births": rec.births,
                "fixed_births": getattr(rec, "fixed_births", 0),
                "q_births": getattr(rec, "q_births", 0),
                "starvation_deaths": rec.starvation_deaths,
                "fixed_starvations": getattr(rec, "fixed_starvations", 0),
                "q_starvations": getattr(rec, "q_starvations", 0),
                "retirement_deaths": rec.retirement_deaths,
                "unfunded_vacancies": rec.unfunded_vacancies,
                "act_rest": rec.action_counts.get("rest", 0),
                "act_cons": rec.action_counts.get("conservative", 0),
                "act_mod": rec.action_counts.get("moderate", 0),
                "act_agg": rec.action_counts.get("aggressive", 0),
                "q_act_agg": rec.q_action_counts.get("aggressive", 0),
            })

        for log in res.reproduction_logs:
            repro_rows.append({
                "quota_group": quota_group,
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

        print(f"  [{quota_group:11s} | Seed {seed}] steps={res.steps_completed:4d}, extinct={res.extinct}, final_pop={len(sim.agents):2d} (F={s_dict['final_fixed_count']}, Q={s_dict['final_q_count']}), disc={disc:.2e}, conserved={is_conserved}")

    with (OUTPUT_DIR / f"{quota_group}_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    with (OUTPUT_DIR / f"{quota_group}_timeseries.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(timeseries[0].keys()))
        writer.writeheader()
        writer.writerows(timeseries)

    if repro_rows:
        with (OUTPUT_DIR / f"{quota_group}_reproduction_logs.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(repro_rows[0].keys()))
            writer.writeheader()
            writer.writerows(repro_rows)

    return summaries


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Beginning execution of all 40 Experiment 3B simulation runs...")
    all_manifest = []
    for grp in GROUPS:
        batch_summaries = run_batch(grp)
        for s in batch_summaries:
            all_manifest.append({
                "quota_group": s["quota_group"],
                "seed": s["seed"],
                "steps_completed": s["steps_completed"],
                "extinct": s["extinct"],
                "mean_resource_100": s["mean_resource_100"],
                "mean_resource_full": s["mean_resource_full"],
                "final_resource": s["final_resource"],
                "min_resource": s["min_resource"],
                "time_to_first_R_below_1": s["time_to_first_R_below_1"],
                "total_births": s["total_births"],
                "total_starvation_deaths": s["total_starvation_deaths"],
                "total_retirement_deaths": s["total_retirement_deaths"],
                "total_unfunded_vacancies": s["total_unfunded_vacancies"],
                "energy_conserved": s["energy_conserved"],
                "energy_discrepancy": s["energy_discrepancy"],
            })

    # Save complete manifest
    with (OUTPUT_DIR / "exp3b_execution_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_manifest[0].keys()))
        writer.writeheader()
        writer.writerows(all_manifest)

    print("\nExperiment 3B execution complete. Manifest and raw CSVs written.")


if __name__ == "__main__":
    main()
