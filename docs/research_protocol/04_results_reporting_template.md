# Results and Reporting Template

## One-sentence study aim

We tested whether population replacement based jointly on survival and accumulated reward changes the composition and resilience of fixed-rule and tabular Q-learning agents sharing a renewable resource.

## Methods summary

The model contained 50 agents competing for one renewable, well-mixed resource over 2,000 time steps. Agents were either deterministic threshold harvesters or tabular Q-learners with the same actions and resource observations. In evolving populations, offspring type was sampled from survivors using a reproductive score combining normalized survival and accumulated reward equally. We compared homogeneous populations, a static 50/50 mixture, and evolving mixtures under gradual regeneration decline and a separate sudden resource shock. Each condition used 30 independent seeds.

## Results table

Fill one row per group and environmental scenario.

| Environment | Group | Mean final Q share | Mean resource | Mean reward | Post-disturbance survival | Recovery time | Extinction rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Gradual decline | Fixed-only | 0.00 |  |  |  |  |  |
| Gradual decline | Q-only | 1.00 |  |  |  |  |  |
| Gradual decline | Static mixture | 0.50 |  |  |  |  |  |
| Gradual decline | Evolving joint |  |  |  |  |  |  |
| Gradual decline | Survival-only |  |  |  |  |  |  |
| Gradual decline | Reward-only |  |  |  |  |  |  |
| Sudden shock | Fixed-only | 0.00 |  |  |  |  |  |
| Sudden shock | Q-only | 1.00 |  |  |  |  |  |
| Sudden shock | Static mixture | 0.50 |  |  |  |  |  |
| Sudden shock | Evolving joint |  |  |  |  |  |  |
| Sudden shock | Survival-only |  |  |  |  |  |  |
| Sudden shock | Reward-only |  |  |  |  |  |  |

Report each primary mean with a 95% confidence interval.

## Required figures

1. **Population composition over time** — Q-learning share across time, one panel for gradual decline and one for sudden shock. Include an uncertainty band across seeds.
2. **Resource level over time** — compare static mixture and evolving joint mixture, marking the change or shock time.
3. **Recovery comparison** — seed-level dot plot or box plot of recovery time for fixed-only, Q-only, static mixture, and evolving joint mixture.
4. **Resilience trade-off** — scatter plot of mean resource level against mean population reward, with one point per seed.

## Interpretation guide

Use only claims supported by the observed data.

### If evolving mixtures shift toward Q-learning during gradual decline

> Under gradual environmental deterioration, replacement based on survival and accumulated reward increased the share of Q-learning agents. This is consistent with learning being favored when agents can adapt across a slowly changing resource regime.

### If fixed-rule agents persist or dominate after sudden shock

> After abrupt resource loss, fixed-rule agents remained competitive or became more common. This suggests that the immediate cost of exploration or re-learning can offset the advantages of adaptive learning during acute disruption.

### If both types coexist

> The system maintained both agent types, suggesting an ecological trade-off rather than universal dominance. The fixed policy may stabilize resource use while learning agents exploit changing conditions.

### If no composition shift occurs

> Within the tested parameter range, endogenous turnover did not produce a reliable change in agent composition. This constrains the conditions under which learning provides an evolutionary advantage in the model.

## Limitations paragraph

This model uses one well-mixed resource, a fixed population capacity, one conservative fixed-rule policy, and a small tabular Q-learning state space. It therefore isolates the interaction between learning, turnover, and environmental stress, but does not establish behavior in spatial ecosystems, multi-resource systems, communicating populations, or deep reinforcement-learning settings.

## Final conclusion template

> Our results show that [joint survival-and-reward turnover did/did not] change the composition and resilience of mixed populations under [environment]. The strongest effect was [result], while [secondary finding] indicated that [interpretation]. These findings support the view that the value of learning depends on environmental tempo and on how ecological success is converted into reproduction.
