# Research Protocol

## Title

Endogenous turnover in mixed populations of fixed-rule and Q-learning agents sharing a renewable resource.

## Research question

When agents compete for one renewable shared resource, does replacement based on both survival and accumulated reward change the population mix and improve resilience under environmental stress?

## Primary hypotheses

1. In a stationary environment, the evolving mixed population will settle toward the agent type with the higher reproductive score.
2. Under gradual reduction in regeneration, population composition will change with a measurable lag relative to the environment.
3. Under a sudden resource drop, the evolving mixture will differ from an otherwise identical static 50/50 mixture in recovery time, population survival, or resource stability.
4. Survival-only and reward-only replacement will produce measurably different composition dynamics from joint survival-and-reward replacement.

## Operational definitions

| Term | Definition |
| --- | --- |
| Fixed-rule agent | An agent that uses a deterministic resource-threshold harvesting policy and never updates its policy. |
| Q-learning agent | An agent using a tabular Q-table to select the same actions as fixed-rule agents. |
| Population composition | Fraction of living agents that are Q-learning agents at a time step. |
| Survival | Agent age in steps, capped at the maximum reproductive age; death before a replacement event makes reproduction impossible. |
| Accumulated reward | Sum of an agent’s net energy reward over its current lifetime. |
| Reproductive score | Equal-weight normalized combination of survival and accumulated reward. |
| Turnover | Deaths and age-based vacancies being filled by offspring selected from surviving agents. |
| Resilience | Post-disturbance recovery measured by population survival, mean reward, and time to recover 90% of the pre-disturbance mean reward. |
| Coexistence | Each type remains at or above 5% of the population for at least 20% of the post-change evaluation period. |

## Minimal ecosystem

The model has a single, well-mixed renewable resource pool and a fixed population capacity of 50 agents. At each discrete time step, every living agent selects one action. Agents pay maintenance energy, potentially harvest from the shared pool, and may die if their energy reaches zero. Vacancies are filled at scheduled replacement events.

Resource dynamics are:

`R(t+1) = min(K, max(0, R(t) - H(t) + g(t) * (K - R(t))))`

where `K` is resource capacity, `H(t)` is total harvested resource, and `g(t)` is the environmental regeneration rate.

## Agent mechanics

Every agent has the same:

- Observation information: discretized resource level, own energy, and one-step resource trend.
- Action set: rest, conservative harvest, moderate harvest, aggressive harvest.
- Initial energy, maintenance cost, death threshold, and harvest conversion rate.

Energy updates are:

`E(i,t+1) = E(i,t) + harvested_energy(i,t) - maintenance_cost`

An agent dies when its energy is zero or below. To ensure turnover during favorable conditions, agents also have a maximum age.

When total requested harvest exceeds the available resource, process agents in a fresh random order for that step. Each agent receives the lesser of its requested amount and the remaining resource. This order is part of the run’s seeded randomness and is identical in distribution for both agent types.

### Fixed-rule behavior

The primary fixed policy is a threshold harvester:

- If resource is low, rest.
- If resource is medium, harvest conservatively.
- If resource is high, harvest moderately.
- It never uses aggressive harvesting.

This represents a reasonable resource-conserving heuristic and avoids a deliberately weak fixed baseline.

### Q-learning behavior

The state is the Cartesian product of:

- Resource level: low, medium, high.
- Agent energy: low, medium, high.
- Resource trend: falling, stable, rising.

The Q-learner uses epsilon-greedy action selection and updates a table after each action. Its reward is exactly the net energy change from that action. Newborn Q-learners start with an empty Q-table in the primary experiment. This prevents learned knowledge inheritance from being mistaken for evolutionary selection.

## Replacement rule

At every replacement interval, all dead agents leave the population. Living agents reaching maximum age are eligible to reproduce in that replacement event and then retire. Each vacancy is filled by sampling an eligible living parent with probability proportional to its reproductive score. Death is therefore a viability gate: an agent that fails to survive cannot reproduce.

For parent `i`:

`F(i) = 0.5 * (age(i) / Amax) + 0.5 * norm(lifetime_reward(i))`

`P(i) = exp(beta * F(i)) / sum(exp(beta * F(j)))`

Use min-max normalization of lifetime reward among living parent candidates at each replacement event. If every candidate has the same lifetime reward, assign every candidate a reward score of `0.5`. The primary selection strength is `beta = 2.0`. An offspring inherits only the parent’s agent type; it does not inherit the parent’s energy, age, accumulated reward, or Q-table.

For the static-mixture control, replacement fills vacancies with whichever type is below 25 living agents; if both type counts are below 25, choose the deficit type with probability proportional to its deficit. Parent selection is uniform within the required type. This preserves a 50/50 target composition without applying type selection.

## Experimental conditions

Run each condition for 2,000 steps and repeat it for 30 independent random seeds.

| Group | Initial mix | Turnover rule | Purpose |
| --- | --- | --- | --- |
| Fixed-only | 100% fixed | Replacement remains fixed | Homogeneous reference. |
| Q-only | 100% Q-learning | Replacement remains Q-learning | Homogeneous reference. |
| Static mixture | 50% fixed, 50% Q | Replacement preserves 50/50 type counts | Separates diversity from selection. |
| Evolving joint | 50% fixed, 50% Q | Joint survival-and-reward selection | Primary condition. |
| Evolving survival-only | 50% fixed, 50% Q | Survival-only selection | Ablation. |
| Evolving reward-only | 50% fixed, 50% Q | Reward-only selection | Ablation. |

### Environment family A: gradual regeneration decline

Begin with the baseline regeneration rate. From step 500 through step 1,000, reduce regeneration linearly to the stressed rate. Keep it at the stressed rate through step 2,000.

This tests compositional tracking, selection lag, and sustained resilience.

### Environment family B: sudden resource shock

Keep regeneration at the baseline rate. At step 1,000, immediately replace the resource level with 50% of its previous value. Continue through step 2,000.

This tests immediate survival and recovery. Do not combine this shock with gradual regeneration decline in the baseline study.

## Primary outcomes

Pre-register these as primary outcomes before inspecting final results:

1. Q-learning population share over time in evolving groups.
2. Mean resource level over time.
3. Mean population net reward over time.
4. Immediate post-shock survival fraction, measured after shock-step deaths and before scheduled replacement.
5. Recovery time to 90% of mean reward during the 100 steps before the disturbance; record `not recovered by step 2,000` if the threshold is never reached.

Secondary outcomes: variance in reward, extinction probability, agent lifetime, parent-selection distribution, and coexistence frequency.

## Analysis

The independent unit is one simulation run, not one agent. For every group and environment, report mean, standard deviation, 95% confidence interval, and all individual seed-level points.

Compare groups using a regression or mixed-effects model with experimental group and environment as fixed effects and seed/run as the independent replicate. For a deadline-safe analysis, also use bootstrap confidence intervals for pairwise differences in recovery time and post-disturbance survival.

Use common random numbers: run comparable conditions with the same seed set. Preserve the full time series for every seed.

## Confounds and controls

| Risk | Control |
| --- | --- |
| Learning agents receive more information | Give both types the identical state observations. |
| Fixed rule is artificially weak | Use a clearly stated conservative threshold policy. |
| Q-learning receives a different reward | Set its learning reward equal to net energy change. |
| Learning inheritance inflates Q-learning success | Reset each newborn Q-table. |
| Population size drives effects | Maintain a fixed capacity of 50. |
| One stochastic run appears decisive | Use 30 independent seeds and report distributions. |
| Environment severity drives all results | Calibrate so resources neither always collapse nor remain permanently full. |
| Survival score is constant among survivors | Use lifetime age, while death remains a reproduction gate. |
| Reward scale overwhelms survival | Normalize lifetime reward among parent candidates at every replacement event. |
| Resource contention creates order bias | Randomize the harvest order independently every step. |
| Static mixture confounds diversity with selection | Include a static 50/50 mixture with the same initial composition. |

## Deep RL feasibility

Tabular Q-learning is the correct baseline because the state space is deliberately small, inspection is straightforward, and learning behavior can be explained. A deep RL extension should be deferred unless the project adds continuous observations, spatial movement, multiple resources, longer history, or a substantially larger state space.

If extended later, use a small DQN with the same observations, actions, reward function, training horizon, and seed protocol. Treat it as a separate study rather than substituting it into the baseline comparison.

## Scope exclusions

The baseline excludes spatial structure, communication, direct attack or cooperation, multiple resources, Q-table inheritance, deep RL, and compound environmental shocks. These are future-work items, not missing features.
