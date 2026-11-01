# Parameter Specification Sheet

These are starting values for the minimal study. They are intentionally few and should be changed only during calibration, with every change logged.

## Core constants

| Parameter | Symbol | Starting value | Rule |
| --- | --- | ---: | --- |
| Population capacity | `N` | 50 | Constant across all runs. |
| Run length | `T` | 2,000 steps | Same for all conditions. |
| Independent trials | `n` | 30 seeds | Same seed set for matched conditions. |
| Resource capacity | `K` | 500 units | Resource is capped at this value. |
| Initial resource | `R0` | 350 units | Same in every run of a scenario. |
| Initial energy | `E0` | 10 units | Same for all newborn agents. |
| Maximum energy | `Emax` | 20 units | Excess harvested energy is capped. |
| Maintenance cost | `c` | 0.2 units/step | Paid by every living agent. |
| Maximum age | `Amax` | 100 steps | Forces gradual turnover. |
| Replacement interval | `I` | 20 steps | Fill all vacancies at this interval. |
| Selection strength | `beta` | 2.0 | Sensitivity analysis: 1.0 and 4.0 after baseline. |

## Resource and action parameters

| Action | Requested harvest | If unavailable | Notes |
| --- | ---: | --- | --- |
| Rest | 0 | N/A | Agent still pays maintenance. |
| Conservative | 0.5 units | Receive remaining amount | Low extraction. |
| Moderate | 1.0 units | Receive remaining amount | Default productive action. |
| Aggressive | 2.0 units | Receive remaining amount | High extraction with no bonus. |

Harvested resource converts to energy at `1 resource = 1 energy` before applying the energy cap.

## Environmental parameters

| Scenario | Parameter | Value |
| --- | --- | ---: |
| Stationary calibration | Regeneration rate | `g = 0.04` |
| Gradual decline | Initial regeneration | `g = 0.04` |
| Gradual decline | Final regeneration | `g = 0.025` |
| Gradual decline | Change window | steps 500–1,000 |
| Sudden shock | Regeneration rate | `g = 0.04` |
| Sudden shock | Shock step | 1,000 |
| Sudden shock | Shock rule | Set resource to 50% of its current level |

## Q-learning parameters

| Parameter | Symbol | Starting value |
| --- | --- | ---: |
| Learning rate | `alpha` | 0.10 |
| Discount factor | `gamma` | 0.95 |
| Initial exploration | `epsilon0` | 0.20 |
| Minimum exploration | `epsilon_min` | 0.02 |
| Exploration decay | — | Linear from step 1 to step 100 of each lifetime |
| Q-table initialization | — | All zeroes |
| Learning reward | — | Net energy change for the step |

## State discretization

| Signal | Low | Medium | High / other |
| --- | --- | --- | --- |
| Resource level | `< 0.33K` | `0.33K–0.66K` | `> 0.66K` |
| Agent energy | `< 0.33Emax` | `0.33Emax–0.66Emax` | `> 0.66Emax` |
| Resource trend | Falling if `R(t)-R(t-1) < -2` | Stable if between `-2` and `2` | Rising if `> 2` |

The state space has 27 states and four actions, so the Q-table has 108 values per learner.

## Fixed-rule policy

| Resource state | Action |
| --- | --- |
| Low | Rest |
| Medium | Conservative harvest |
| High | Moderate harvest |

This fixed policy never takes aggressive harvest. It observes the same resource state as Q-learning agents, but does not use energy or trend for decision-making.

## Reproductive score

At every replacement event, select only living candidates. Death before the event gives an agent zero reproductive opportunity. For each living candidate:

`survival_score = age / maximum_age`

`reward_score = min-max normalized lifetime accumulated net reward among living candidates`

`fitness = 0.5 * survival_score + 0.5 * reward_score`

Parent probabilities are `softmax(beta * fitness)`. If all candidate rewards are equal, set every reward score to `0.5`. In survival-only and reward-only ablations, set the unused component’s coefficient to zero and the used component’s coefficient to one.

For the static 50/50 mixture, fill each vacancy with the type currently below 25 living agents. Select its parent uniformly from living agents of that type. If no parent of the required type remains, inject a fresh founder of that type and log the event. This control preserves composition rather than selecting it.

## Calibration acceptance criteria

Before main runs, execute 10 stationary pilot seeds. Accept settings only if all conditions hold:

- At least 80% of pilot runs retain living agents through step 2,000.
- Mean resource level is neither below 5% nor above 95% of capacity for more than 80% of steps.
- Both fixed-rule and Q-learning agents can survive for at least 200 steps in their homogeneous conditions.
- At least one mixed-population pilot exhibits actual turnover.
- No more than 10% of all pilot steps end with an empty resource pool.

If calibration fails, change one parameter family at a time, beginning with regeneration rate and maintenance cost. Record all changes in a calibration log.
