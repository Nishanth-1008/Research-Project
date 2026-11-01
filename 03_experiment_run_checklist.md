# Experiment Run Checklist

## Before implementation

- [ ] Treat `02_parameter_spec_sheet.md` as the source of truth.
- [ ] Assign and store the 30 random seeds before viewing results.
- [ ] Define one output row per run and one time-series record per step.
- [ ] Define a version label for the simulator and parameters.

## Build validation order

- [ ] Resource regenerates correctly and never goes below zero or above capacity.
- [ ] Every living agent pays maintenance once per step.
- [ ] Harvest is allocated fairly and total harvest never exceeds available resource.
- [ ] Agents die at zero energy and at maximum age.
- [ ] Vacancies are filled only at the replacement interval.
- [ ] Offspring inherit agent type but reset energy, age, reward history, and Q-table.
- [ ] Fixed-rule policy produces the specified action for each resource state.
- [ ] Q-learning action selection and Q-value updates use the defined state, reward, and action set.
- [ ] Population capacity stays at 50 after each replacement event.
- [ ] Every run records seed, group, scenario, parameter version, and full time series.

## Calibration

- [ ] Run 10 stationary pilot seeds for fixed-only, Q-only, and evolving joint mixture.
- [ ] Check the calibration acceptance criteria in the parameter sheet.
- [ ] If needed, modify only regeneration rate or maintenance cost first.
- [ ] Log every parameter revision and rerun affected pilots.
- [ ] Freeze the parameter sheet before main experiments.

## Main experiments

For each of the six groups, run 30 seeds in each environmental family.

- [ ] Stationary reference: `6 groups x 30 seeds`.
- [ ] Gradual regeneration decline: `6 groups x 30 seeds`.
- [ ] Sudden resource shock: `6 groups x 30 seeds`.
- [ ] Confirm every condition completed 2,000 steps.
- [ ] Flag and preserve crashes or invalid runs; do not silently replace them.

Total planned baseline runs: `540`.

## Required outputs per run

- [ ] Run-level summary: seed, group, scenario, final composition, mean reward, mean resource, survival fraction, recovery time, extinction flag.
- [ ] Per-step time series: resource level, total harvest, living population, Q-learning share, mean reward, mean energy.
- [ ] Per-agent replacement-event record: type, age, survival score, reward score, fitness, parent selected.

## Analysis checks

- [ ] Use simulation run, not individual agent, as the independent replicate.
- [ ] Plot all seed-level points or a transparent distribution, not only means.
- [ ] Calculate 95% confidence intervals for primary comparisons.
- [ ] Compare evolving joint mixture against static mixture first.
- [ ] Compare joint mixture against survival-only and reward-only ablations second.
- [ ] Separate gradual-change and sudden-shock analyses.
- [ ] Report null findings as results, not failed experiments.

## Stop rule for deadline

If time is insufficient for all 540 runs, prioritize in this order:

1. Evolving joint versus static mixture under gradual decline and sudden shock.
2. Fixed-only and Q-only references under both stress families.
3. Survival-only and reward-only ablations.
4. Stationary references.

Do not reduce below 20 seeds per retained condition without stating the reduced precision in the report.
