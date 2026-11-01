"""Run the required stationary calibration and write reproducible CSV evidence."""

from __future__ import annotations

import csv
from pathlib import Path

from simulator import EcosystemSimulator, Group, Parameters


OUTPUT_DIR = Path(__file__).parent / "results"
CALIBRATION_GROUPS: tuple[Group, ...] = ("fixed_only", "q_only", "evolving_joint")
SEEDS = tuple(range(1, 11))


def acceptance_summary(
    parameters: Parameters, results: list[dict[str, object]], all_records: list[dict[str, object]]
) -> tuple[list[tuple[str, str]], bool]:
    retained = sum(not bool(row["extinct"]) for row in results)
    resource_band_steps = sum(
        0.05 * parameters.resource_capacity <= float(row["resource"]) <= 0.95 * parameters.resource_capacity
        for row in all_records
    )
    fixed_and_q_survive = all(
        any(row["group"] == group and int(row["steps_completed"]) >= 200 for row in results)
        for group in ("fixed_only", "q_only")
    )
    turnover = any(int(row["replacements"]) > 0 for row in results if row["group"] == "evolving_joint")
    empty_resource_steps = sum(float(row["resource"]) == 0 for row in all_records)
    checks = [
        ("Runs retaining living agents through step 2000", f"{retained}/{len(results)} (need >= 24/30)"),
        ("Resource in 5%-95% capacity band", f"{resource_band_steps}/{len(all_records)} steps (need >= 20%)"),
        ("Fixed-only and Q-only survive at least 200 steps", str(fixed_and_q_survive)),
        ("At least one evolving mixed run has turnover", str(turnover)),
        ("Empty-resource steps", f"{empty_resource_steps}/{len(all_records)} (need <= 10%)"),
    ]
    accepted = (
        retained >= 0.8 * len(results)
        and resource_band_steps >= 0.2 * len(all_records)
        and fixed_and_q_survive
        and turnover
        and empty_resource_steps <= 0.1 * len(all_records)
    )
    return checks, accepted


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    parameters = Parameters()
    summaries: list[dict[str, object]] = []
    records: list[dict[str, object]] = []
    for group in CALIBRATION_GROUPS:
        for seed in SEEDS:
            result = EcosystemSimulator(parameters, group, "stationary", seed).run()
            summaries.append(result.summary())
            for record in result.records:
                records.append({"seed": seed, "group": group, "scenario": "stationary", **record.__dict__})

    with (OUTPUT_DIR / "stationary_calibration_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    with (OUTPUT_DIR / "stationary_calibration_timeseries.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    checks, accepted = acceptance_summary(parameters, summaries, records)
    with (OUTPUT_DIR / "stationary_calibration_report.md").open("w", encoding="utf-8") as handle:
        handle.write("# Stationary Calibration Report\n\n")
        handle.write("Parameters: baseline specification in `02_parameter_spec_sheet.md`.\n\n")
        handle.write("| Criterion | Observed |\n| --- | --- |\n")
        for criterion, observed in checks:
            handle.write(f"| {criterion} | {observed} |\n")
        decision = "ACCEPTED: proceed to main experiments." if accepted else "NOT ACCEPTED: revise one parameter family and rerun calibration."
        handle.write(f"\n## Decision\n\n{decision}\n")
        handle.write("\nCalibration evidence is stored in the accompanying CSV files.\n")
    for criterion, observed in checks:
        print(f"{criterion}: {observed}")
    print("Calibration decision: " + ("ACCEPTED" if accepted else "NOT ACCEPTED"))


if __name__ == "__main__":
    main()
