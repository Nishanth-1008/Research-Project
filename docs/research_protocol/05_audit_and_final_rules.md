# Audit and Final Rules

## Audit outcome

The documentation is finalized with two substantive corrections and several explicit edge-case rules. The study remains a minimal, deadline-safe tabular Q-learning experiment; no additional features are required before implementation.

## Corrected issue 1: survival must affect selection

**Problem found:** The earlier score used survival within a 20-step replacement window. Every surviving candidate typically completed that full window, making the survival score almost constant. The rule would have behaved mostly like reward-only selection.

**Final rule:** Death before a replacement event prevents reproduction. Among agents that are alive at that event, survival contribution is `age / maximum_age`; accumulated-reward contribution is normalized lifetime net reward. An agent reaching maximum age remains eligible as a parent for that event, then retires. Both receive weight `0.5` in the joint-selection condition.

This makes survival relevant in two ways: fragile agents leave no descendants, and agents that remain alive longer receive a larger reproductive score.

## Corrected issue 2: sustainable resource throughput

**Problem found:** The prior maintenance cost and action harvest values could require substantially more resource per step than regeneration can supply, turning routine trials into unavoidable collapse.

**Final rule:** Use maintenance cost `0.2`, requested harvest values `0.5`, `1.0`, and `2.0`, baseline regeneration `0.04`, and stressed regeneration `0.025`. These are starting values only; the 10-seed calibration gate decides whether they are accepted.

## Final simulation order for each step

1. Observe the start-of-step resource, energy, and resource trend.
2. Every living agent selects one action.
3. Randomly permute living agents using the run seed; allocate requested harvest in that order until the pool is exhausted.
4. Update each agent’s energy: harvested energy minus maintenance cost, capped at maximum energy.
5. Add net energy change to the agent’s lifetime reward; increment age.
6. Remove agents with energy at or below zero.
7. Regenerate the shared resource using the scenario’s regeneration rate, capped at capacity.
8. At every 20th step, agents reaching maximum age are eligible as parents once, then retire; fill all vacancies according to the group’s replacement rule.
9. Record all run-level, step-level, and replacement-event outputs.

Applying regeneration after harvesting makes agents compete for the resource currently available, while renewal prepares the next step. Use this ordering for every condition.

## Final replacement rules

### Evolving joint condition

For every living parent candidate:

`survival_score = age / 100`

`reward_score = min_max_normalize(lifetime_net_reward)`

`fitness = 0.5 * survival_score + 0.5 * reward_score`

Sample each parent with probability `softmax(2.0 * fitness)`. If all candidate rewards are equal, give every candidate `reward_score = 0.5`.

### Evolving ablations

- Survival-only: `fitness = survival_score`.
- Reward-only: `fitness = reward_score`.

### Static 50/50 control

Maintain a target of 25 living agents of each type. When filling a vacancy, create the type with the larger current deficit. If both deficits are nonzero, choose the type proportional to its deficit. Select its parent uniformly among living agents of that type. If that type has no living parent, inject a fresh founder of the required type and log the founder event; otherwise a static-composition control could not preserve its stated composition after an extinction.

### Homogeneous controls

Every offspring has the single permitted type. Parent selection is uniform because type composition cannot change.

## Final inheritance and initialization rules

- Offspring inherits agent type only.
- Offspring begins with energy 10, age 0, and lifetime reward 0.
- Q-learning offspring begins with an all-zero Q-table and a fresh exploration schedule.
- The exploration schedule decays linearly from `0.20` to `0.02` over the agent’s 100-step maximum lifetime.
- No mutation, policy copying, or Q-table inheritance appears in the baseline study.

## Final analysis rules

- A simulation run is one independent observation.
- Use the same 30 seeds for matched conditions.
- Preserve failures and report them as extinction or non-recovery, never discard them.
- Measure sudden-shock survival after shock-step deaths and before scheduled replacement restores population capacity.
- If recovery to 90% of pre-disturbance reward does not occur by step 2,000, record `not recovered`; do not substitute a shorter value.
- Analyze gradual decline and sudden shock separately.
- Treat deep RL, spatial movement, and compound shocks as explicitly out of scope.

## Implementation gate

Implementation may begin only after the 10-seed stationary calibration satisfies every criterion in `02_parameter_spec_sheet.md`. If it fails, alter regeneration rate or maintenance cost one at a time, log the change, and repeat calibration.
