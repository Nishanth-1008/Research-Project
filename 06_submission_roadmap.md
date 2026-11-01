# Competition Submission Roadmap

## Mission and scope lock

**Submission claim to test:**

> In a renewable shared-resource ecosystem, the population mix of fixed-rule and Q-learning agents can affect ecological resilience differently under gradual deterioration and sudden shocks; endogenous turnover may shift the mix toward conditions that recover better.

This is a controlled simulation study, not a claim that reinforcement learning is universally superior or that the model is the first of its kind. The strongest possible submission is a reproducible answer to **when a given mix is resilient, why, and whether turnover improves it**.

### Already complete

- Finalized protocol, parameter sheet, analysis template, and audit.
- Dependency-free simulator implementing the finalized rules.
- Six mechanics tests, all passing.
- Stationary calibration: 30/30 runs retained living agents; calibration accepted.

### Scope that must stay frozen

- One well-mixed renewable resource; no spatial movement or communication.
- Tabular Q-learning, not deep RL.
- Two environmental stress families run separately: gradual regeneration decline and sudden resource shock.
- Six groups: fixed-only, Q-only, static 50/50 mixture, joint turnover, survival-only turnover, reward-only turnover.
- Thirty seeds per retained condition; common seed sets for matched comparisons.

Deep RL, multiple starting ratios, spatial environments, and mutation are post-submission extensions. They should not delay this submission.

## Submission story

Build every artifact around a three-part narrative:

1. **Problem:** A renewable commons can fail when conditions change; agent policy diversity may affect resilience.
2. **Method:** Compare fixed-rule and Q-learning agents under identical observations/actions, then allow population composition to change through survival-and-reward-based turnover.
3. **Discovery:** Identify whether the resilient population composition differs by environmental tempo, and whether endogenous turnover improves recovery versus an otherwise identical static mixture.

The static 50/50 mixture is the key control. It separates benefits of simply having diverse agent types from benefits of allowing the population mix to change.

## Phase 1 — Freeze a reproducible release candidate

**Goal:** Make the existing simulator ready for the experiment batch.

### Tasks

1. Create a run manifest listing every planned group, scenario, seed, parameter version, and output path.
2. Add a main-experiment runner that executes one manifest row per simulation and writes a concise summary plus per-step time series.
3. Include simulator version, Python version, parameter values, seed, group, and scenario in every output.
4. Add a no-overwrite policy: preserve failed or incomplete runs and label them explicitly.
5. Run the mechanics tests once more before the batch; save the test output with the results.

### Acceptance gate

- The same seed and manifest row produce identical summary and time-series results.
- All tests pass.
- Each output can be traced to one explicit parameter version.

### Deliverables

- `experiment_manifest.csv`
- A batch runner and a reproducibility note
- Saved test log

### Do not do

- Do not revise policies, rewards, or parameter values after beginning the main batch.
- Do not add deep RL.

## Phase 2 — Run the core experiment first

**Goal:** Answer the main question with the smallest decisive comparison.

Run the following four groups under both stress families, using 30 seeds each:

| Priority | Groups | Scenarios | Runs |
| --- | --- | --- | ---: |
| Core | Fixed-only, Q-only, static 50/50, evolving joint | Gradual decline + sudden shock | 240 |

### Why this comes first

These four groups establish all central comparisons:

- Is either homogeneous population more resilient?
- Does a mixed population differ from homogeneous populations?
- Does endogenous turnover outperform the same initial mixture held static?

### Quality checks during the batch

- Confirm all runs reach 2,000 steps or are retained as recorded extinctions.
- Confirm final outputs contain exactly 30 runs per group/scenario.
- Inspect two random seeds from each condition manually for sensible resource, population, and composition trajectories.
- Never remove an inconvenient seed.

### Core figures to make immediately

1. Q-learning population share over time for evolving joint populations.
2. Resource level over time: static mixture versus evolving joint mixture.
3. Post-shock immediate survival fraction by group.
4. Recovery-time distribution by group.

### Decision gate

If the evolving joint group differs reproducibly from the static mixture on at least one primary outcome, preserve that effect as the central result. If it does not, a well-supported null result remains legitimate: turnover did not improve resilience in the tested parameter regime.

## Phase 3 — Establish the mechanism

**Goal:** Show whether any turnover result comes from reward, survival, or their combination.

Run the ablations under both stress families:

| Priority | Groups | Scenarios | Runs |
| --- | --- | --- | ---: |
| Mechanism | Survival-only, reward-only | Gradual decline + sudden shock | 120 |

### Required analyses

- Compare evolving joint versus survival-only versus reward-only.
- Plot parent-selection fitness components at replacement events.
- Report type composition, resource level, and recovery alongside each other.
- Explain the mechanism conservatively: selection shifts composition **only if the recorded composition and outcomes both support it**.

### Decision gate

- If joint turnover outperforms both ablations, the joint survival-and-reward mechanism is supported.
- If one ablation matches joint turnover, simplify the claim to that supported mechanism.
- If neither differs, present the ablations as evidence that the observed effect is not attributable to the intended selection rule.

## Phase 4 — Analyze without overstating

**Goal:** Produce results that judges can audit quickly.

### Primary outcomes, in order

1. Immediate post-shock survival fraction.
2. Recovery time to 90% of pre-shock reward; record non-recovery rather than imputing a time.
3. Mean resource level and resource stability.
4. Final and time-varying Q-learning share.

### Statistical workflow

1. Treat one simulation run as one independent data point.
2. Use all 30 seed-level values per condition.
3. Report mean, median, standard deviation, and 95% bootstrap confidence interval.
4. For the headline comparison, calculate the paired seed-level difference between evolving joint and static mixture because they use the same seeds.
5. Show individual seed points in plots; do not show only bars or smoothed averages.
6. Label simulations that do not recover by the horizon; report their count separately.

### Interpretation rules

- Say “in this model and parameter range,” not “in real ecosystems.”
- Say “consistent with selection favoring…” only when composition change and performance change align.
- Do not infer causality from a composition shift alone.
- Keep the literature claim modest: this is a candidate integration gap combining mixed fixed/RL populations, renewable resources, shocks, and explicit turnover.

## Phase 5 — Build the actual submission

**Goal:** Convert evidence into a clear, judge-friendly package.

### Written report structure

1. **Title:** Emphasize resilience, mixed populations, and endogenous turnover.
2. **Abstract:** Problem, method, most important quantitative result, and bounded conclusion.
3. **Background:** Explain renewable commons and why fixed rules versus learning may create a resilience trade-off. Cite prior work as adjacent, not absent.
4. **Question and hypotheses:** State the environment-tempo question and pre-specified primary outcomes.
5. **Method:** One diagram of the timestep and a short parameter table. Point to the full spec in an appendix.
6. **Results:** Lead with four core figures. Use ablations as mechanism evidence.
7. **Discussion:** Explain the supported result, nulls, limitations, and deep-RL/spatial extensions.
8. **Reproducibility appendix:** Seeds, parameter sheet, run manifest, source code, and test/calibration evidence.

### Presentation or video structure (3–5 minutes)

1. `0:00–0:25` — The renewable-commons problem and the question.
2. `0:25–0:55` — Show the simple agent/resource world and the two agent types.
3. `0:55–1:25` — Explain static mixture versus endogenous turnover.
4. `1:25–2:30` — Show gradual-change and sudden-shock result figures.
5. `2:30–3:10` — Show the ablation or most important mechanism figure.
6. `3:10–3:40` — State the discovery and why it is bounded.
7. `3:40–4:00` — Limitations, reproducibility, and next step.

### Visual assets required

- One clean ecosystem diagram.
- One lifecycle/timestep diagram: observe → choose → harvest → energy/death → regenerate → replacement.
- Four result figures from Phase 2.
- One ablation figure from Phase 3.
- One small table of fixed parameters.

Avoid a live demo unless it is completely rehearsed. A short recorded simulation clip is safer.

## Phase 6 — Final quality and submission audit

**Goal:** Ensure the submission can survive judging scrutiny.

### Scientific audit

- [ ] Every claim maps to a displayed number, figure, or confidence interval.
- [ ] All primary outcomes and all failed/non-recovered runs are reported.
- [ ] Static versus evolving comparison uses identical initial mixes and matched seeds.
- [ ] Fixed and Q-learning agents have the same action set and resource observations.
- [ ] The report distinguishes model findings from real-world claims.
- [ ] Literature wording says “candidate integration gap,” not “first-ever study.”

### Reproducibility audit

- [ ] Fresh clone or clean folder runs tests successfully.
- [ ] One documented command reproduces calibration.
- [ ] One documented command reproduces the main batch.
- [ ] Manifest, parameter sheet, seeds, source, and raw CSVs are included.
- [ ] Figures are generated from saved raw data, not manually transcribed numbers.

### Presentation audit

- [ ] The first minute explains the question without assuming ML expertise.
- [ ] Every plot has a readable title, units, sample size, and scenario label.
- [ ] The final slide answers: what changed, under which stress, compared with what, and why it matters.
- [ ] The submission is exported and opened on a second device/account before upload.

## Deadline triage

### If time remains for only one further phase

Complete **Phase 2**, then write the report around the four core groups. A clean static-versus-evolving comparison is stronger than an incomplete set of ablations.

### If time remains for two phases

Complete **Phases 2 and 5**. Mention survival-only and reward-only as planned follow-up analysis if they cannot be completed.

### If time remains for the full study

Complete **Phases 2–6**. Do not spend the extra time expanding the model; spend it on replicated runs, transparent figures, and reproducibility.

## Definition of “ready to ship”

The submission is ready when it has:

1. A frozen implementation that passes mechanics tests.
2. Calibration evidence and a parameter manifest.
3. At least the 240-run core experiment with 30 seeds per retained condition.
4. Four readable core figures with seed-level uncertainty.
5. A concise report or presentation whose conclusions do not exceed the data.
6. A reproducibility folder containing code, parameters, seeds, raw data, and instructions.

At that point, ship. Deep RL is not a prerequisite for a strong submission.
