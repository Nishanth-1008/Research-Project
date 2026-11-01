"""Rigorous outcome metrics and post-shock resilience analysis for Version D.1 (sim-4.1.0).

Calculates pre-registered primary outcomes according to Protocol v2.0:
1. Immediate post-shock survival fraction (S_post, Delta t = 20 and Delta t = 0).
2. Recovery time (tau_rec) to 90% of pre-shock baseline (steps 900-999) with explicit right-censoring.
3. Resource stability (mean, variance, coefficient of variation) over post-shock horizon (steps 1001-2000).
4. Paired-seed differences for common random numbers (CRN).
"""

from __future__ import annotations

import math
from typing import Any, Sequence

try:
    from simulator_v4.simulator import StepRecord
except ImportError:
    from simulator import StepRecord


def compute_immediate_survival(
    records: Sequence[StepRecord],
    shock_step: int = 1000,
    delta_t: int = 20,
) -> dict[str, float]:
    """
    Computes immediate post-shock survival fraction:
    - S_post_0: N(shock_step) / N(shock_step - 1)
    - S_post_delta: N(shock_step + delta_t) / N(shock_step - 1)
    
    If pre-shock population is 0 or run terminated prior to shock, returns 0.0.
    """
    if not records:
        return {"pre_shock_population": 0, "s_post_immediate": 0.0, "s_post_delta": 0.0}

    # Locate pre-shock step
    pre_step = shock_step - 1
    pre_rec = next((r for r in records if r.step == pre_step), None)
    if pre_rec is None or pre_rec.living_population == 0:
        return {"pre_shock_population": 0, "s_post_immediate": 0.0, "s_post_delta": 0.0}

    n_pre = float(pre_rec.living_population)

    # Immediate shock step
    shock_rec = next((r for r in records if r.step == shock_step), None)
    n_shock = float(shock_rec.living_population) if shock_rec else 0.0
    s_post_immediate = n_shock / n_pre

    # Post-shock window step
    target_step = shock_step + delta_t
    delta_rec = next((r for r in records if r.step == target_step), None)
    n_delta = float(delta_rec.living_population) if delta_rec else 0.0
    s_post_delta = n_delta / n_pre

    return {
        "pre_shock_population": int(n_pre),
        "post_shock_immediate_pop": int(n_shock),
        "post_shock_delta_pop": int(n_delta),
        "s_post_immediate": s_post_immediate,
        "s_post_delta": s_post_delta,
    }


def compute_recovery_time(
    records: Sequence[StepRecord],
    shock_step: int = 1000,
    pre_shock_window: int = 100,
    threshold_ratio: float = 0.90,
    metric: str = "reward",
    horizon: int = 2000,
) -> dict[str, Any]:
    """
    Computes time steps until metric recovers to 90% of pre-shock baseline mean:
    - Pre-shock baseline window: [shock_step - pre_shock_window, shock_step - 1] (steps 900-999).
    - Threshold: threshold_ratio * baseline_mean.
    - Right-censored as 'not recovered by step 2,000' if threshold is not reached.
    """
    if not records:
        return {
            "recovered": False,
            "recovery_time": None,
            "censored": True,
            "baseline_mean": 0.0,
            "threshold": 0.0,
            "status": "not recovered by step 2,000",
        }

    # Extract baseline window
    baseline_start = max(0, shock_step - pre_shock_window)
    baseline_end = shock_step - 1

    baseline_records = [
        r for r in records if baseline_start <= r.step <= baseline_end
    ]

    if not baseline_records:
        return {
            "recovered": False,
            "recovery_time": None,
            "censored": True,
            "baseline_mean": 0.0,
            "threshold": 0.0,
            "status": "insufficient baseline data",
        }

    if metric == "reward":
        vals = [r.mean_reward for r in baseline_records if r.mean_reward is not None]
    elif metric == "resource":
        vals = [r.resource for r in baseline_records]
    elif metric == "population":
        vals = [float(r.living_population) for r in baseline_records]
    else:
        raise ValueError(f"Unknown metric '{metric}'")

    if not vals:
        baseline_mean = 0.0
    else:
        baseline_mean = sum(vals) / len(vals)

    threshold = threshold_ratio * baseline_mean

    # Scan post-shock steps
    post_records = [r for r in records if shock_step <= r.step <= horizon]

    recovered = False
    recovery_time = None

    for r in post_records:
        if metric == "reward":
            curr = r.mean_reward if r.mean_reward is not None else -1e9
        elif metric == "resource":
            curr = r.resource
        elif metric == "population":
            curr = float(r.living_population)
        else:
            curr = 0.0

        if curr >= threshold:
            recovered = True
            recovery_time = r.step - shock_step
            break

    return {
        "recovered": recovered,
        "recovery_time": recovery_time,
        "censored": not recovered,
        "baseline_mean": baseline_mean,
        "threshold": threshold,
        "status": "recovered" if recovered else "not recovered by step 2,000",
    }


def compute_resource_stability(
    records: Sequence[StepRecord],
    start_step: int = 1001,
    end_step: int = 2000,
) -> dict[str, float]:
    """
    Computes statistical stability of resource stock over a defined post-shock window:
    - Mean resource (mu_R)
    - Variance of resource (sigma_R^2)
    - Standard deviation of resource (sigma_R)
    - Coefficient of variation (CV_R = sigma_R / mu_R)
    - Minimum resource stock
    - Number of severe depletion steps (R <= 1.0)
    """
    window_records = [r for r in records if start_step <= r.step <= end_step]
    if not window_records:
        return {
            "mean_resource": 0.0,
            "var_resource": 0.0,
            "std_resource": 0.0,
            "cv_resource": 0.0,
            "min_resource": 0.0,
            "depletion_steps": 0,
        }

    resources = [r.resource for r in window_records]
    n = len(resources)
    mean_r = sum(resources) / n
    var_r = sum((x - mean_r) ** 2 for x in resources) / n if n > 1 else 0.0
    std_r = math.sqrt(var_r)
    cv_r = (std_r / mean_r) if mean_r > 1e-8 else 0.0
    min_r = min(resources)
    depletion_steps = sum(1 for x in resources if x <= 1.0)

    return {
        "mean_resource": mean_r,
        "var_resource": var_r,
        "std_resource": std_r,
        "cv_resource": cv_r,
        "min_resource": min_r,
        "depletion_steps": depletion_steps,
    }


def compute_paired_differences(
    primary_records: list[dict[str, Any]],
    control_records: list[dict[str, Any]],
    matched_key: str = "seed",
    metric_keys: Sequence[str] = ("mean_resource", "mean_reward", "final_population"),
) -> dict[str, dict[str, float]]:
    """
    Computes paired seed-level differences (Primary - Control) under Common Random Numbers:
    Delta Y = Y_primary(seed) - Y_control(seed).
    
    Returns sample mean difference, standard deviation, standard error, and paired t-statistic.
    """
    ctrl_by_seed = {r[matched_key]: r for r in control_records if matched_key in r}
    matched_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []

    for prim in primary_records:
        seed = prim.get(matched_key)
        if seed in ctrl_by_seed:
            matched_pairs.append((prim, ctrl_by_seed[seed]))

    results: dict[str, dict[str, float]] = {}
    n_pairs = len(matched_pairs)

    for key in metric_keys:
        diffs: list[float] = []
        for prim, ctrl in matched_pairs:
            v_prim = prim.get(key)
            v_ctrl = ctrl.get(key)
            if v_prim is not None and v_ctrl is not None:
                diffs.append(float(v_prim) - float(v_ctrl))

        m = len(diffs)
        if m == 0:
            results[key] = {
                "n": 0,
                "mean_diff": 0.0,
                "std_diff": 0.0,
                "se_diff": 0.0,
                "t_stat": 0.0,
            }
            continue

        mean_diff = sum(diffs) / m
        var_diff = sum((d - mean_diff) ** 2 for d in diffs) / (m - 1) if m > 1 else 0.0
        std_diff = math.sqrt(var_diff)
        se_diff = std_diff / math.sqrt(m) if m > 0 else 0.0
        t_stat = (mean_diff / se_diff) if se_diff > 1e-12 else 0.0

        results[key] = {
            "n": m,
            "mean_diff": mean_diff,
            "std_diff": std_diff,
            "se_diff": se_diff,
            "t_stat": t_stat,
        }

    return results

