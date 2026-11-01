"""Generate ASCII trajectory plots for Version C Stage 1 Calibration."""

from __future__ import annotations

import csv
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "results_v3" / "calibration" / "stage1_timeseries.csv"
OUT_PATH = Path(__file__).parent.parent / "calibration_logs" / "version_c" / "stage1_trajectories.txt"


def generate_ascii_plot(title: str, values: list[float], max_val: float, height: int = 10, width: int = 60) -> str:
    lines = [f"=== {title} ==="]
    # Sample down to width points
    n = len(values)
    step = max(1, n // width)
    sampled = [values[i] for i in range(0, n, step)][:width]
    
    for row in range(height, -1, -1):
        level = (row / height) * max_val
        row_str = f"{level:5.1f} |"
        for val in sampled:
            if val >= level - (max_val / (2 * height)):
                row_str += "*"
            else:
                row_str += " "
        lines.append(row_str)
    lines.append("      +" + "-" * len(sampled))
    lines.append(f"      0{' ' * (len(sampled) - 10)}Steps ({n})")
    return "\n".join(lines)


def main() -> None:
    recs = list(csv.DictReader(DATA_PATH.open(encoding="utf-8")))
    output_lines: list[str] = []

    for group in ("fixed_only", "q_only", "evolving_joint"):
        g_recs = [r for r in recs if r["group"] == group and r["seed"] == "1"]
        res_vals = [float(r["resource"]) for r in g_recs]
        pop_vals = [float(r["living_population"]) for r in g_recs]

        output_lines.append(generate_ascii_plot(f"Group: {group} (Seed 1) - Resource Stock (Capacity 500)", res_vals, 500.0))
        output_lines.append("\n")
        output_lines.append(generate_ascii_plot(f"Group: {group} (Seed 1) - Living Population (Capacity 50)", pop_vals, 50.0))
        output_lines.append("\n" + "=" * 70 + "\n")

    OUT_PATH.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"Trajectory plots written to {OUT_PATH}")


if __name__ == "__main__":
    main()
