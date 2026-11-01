# Deadline Research Pack: Adaptive Agents in a Shared Resource Ecosystem

This folder contains a deliberately small, defensible study design for testing whether endogenous population turnover changes the mix of fixed-rule and learning agents under resource stress.

## Files

- `01_research_protocol.md` — research question, hypotheses, design, controls, and analysis plan.
- `02_parameter_spec_sheet.md` — exact starting parameters and implementation rules.
- `03_experiment_run_checklist.md` — ordered build, calibration, and experiment checklist.
- `04_results_reporting_template.md` — tables, plots, and wording for the final report or presentation.
- `05_audit_and_final_rules.md` — audit findings and the final unambiguous simulation rules.
- `06_submission_roadmap.md` — phase-by-phase plan from calibrated simulator to competition submission.

## Scope lock

The baseline study uses tabular Q-learning only. Deep reinforcement learning is explicitly a future extension. The environment has one shared renewable resource, a fixed population size of 50, and two environmental stress families tested separately: gradual regeneration decline and a sudden resource shock.

## Core claim being tested

> When replacement depends jointly on survival and accumulated reward, does the population composition shift toward the agent type that produces greater resilience under gradual versus sudden resource stress?

Read `05_audit_and_final_rules.md` first, then implement the parameter sheet and checklist. Do not add spatial movement, communication, extra resources, or deep RL before completing the baseline runs.
