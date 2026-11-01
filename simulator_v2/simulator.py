"""Version B Simulator with Logistic Renewal and Diagnostics.

Implements:
- Logistic regeneration: G(R) = g * R * (1 - R/K), R_next = min(K, max(0, remaining + G(remaining)))
- Action-frequency and Q-value telemetry logging
- Detailed StepRecord including action distributions
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import exp
from random import Random
from typing import Literal

from parameters import Parameters

SIMULATOR_VERSION = "sim-2.0.0"
PARAMETER_VERSION = "params-v2.0"

AgentType = Literal["fixed", "q_learning"]
Group = Literal[
    "fixed_only",
    "q_only",
    "static_mixture",
    "evolving_joint",
    "evolving_survival",
    "evolving_reward",
]
Scenario = Literal["stationary", "gradual_decline", "sudden_shock"]

ACTIONS = ("rest", "conservative", "moderate", "aggressive")
HARVEST_REQUEST = {
    "rest": 0.0,
    "conservative": 0.5,
    "moderate": 1.0,
    "aggressive": 2.0,
}


@dataclass
class Agent:
    identifier: int
    kind: AgentType
    energy: float
    age: int = 0
    lifetime_reward: float = 0.0
    q_table: dict[tuple[str, str, str], list[float]] = field(default_factory=dict)


@dataclass
class StepRecord:
    step: int
    resource: float
    total_harvest: float
    living_population: int
    q_learning_share: float | None
    mean_reward: float | None
    mean_energy: float | None
    action_counts: dict[str, int] = field(default_factory=dict)
    q_action_counts: dict[str, int] = field(default_factory=dict)
    fixed_action_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class RunResult:
    simulator_version: str
    parameter_version: str
    group: Group
    scenario: Scenario
    seed: int
    steps_completed: int
    extinct: bool
    final_q_learning_share: float | None
    mean_resource: float
    mean_reward: float
    replacements: int
    founder_injections: int
    post_disturbance_survival: float | None
    recovery_time: int | None
    records: list[StepRecord] = field(repr=False)
    replacement_events: list[dict[str, object]] = field(repr=False)

    def summary(self) -> dict[str, object]:
        data = asdict(self)
        del data["records"]
        del data["replacement_events"]
        return data


class EcosystemSimulator:
    def __init__(
        self,
        parameters: Parameters,
        group: Group,
        scenario: Scenario,
        seed: int,
    ) -> None:
        self.parameters = parameters
        self.group = group
        self.scenario = scenario
        self.seed = seed
        self.random = Random(seed)
        self.resource = parameters.initial_resource
        self.previous_start_resource = parameters.initial_resource
        self.agents: list[Agent] = []
        self.next_identifier = 0
        self.founder_injections = 0
        self.replacements = 0
        self.records: list[StepRecord] = []
        self.replacement_events: list[dict[str, object]] = []
        self.pre_shock_mean_reward: float | None = None
        self.pre_shock_living_population: int | None = None
        self.immediate_post_shock_survival: float | None = None
        self.recovery_time: int | None = None
        self._initialize_population()

    def _initialize_population(self) -> None:
        if self.group == "fixed_only":
            types = ["fixed"] * self.parameters.population_capacity
        elif self.group == "q_only":
            types = ["q_learning"] * self.parameters.population_capacity
        else:
            half = self.parameters.population_capacity // 2
            types = ["fixed"] * half + ["q_learning"] * (self.parameters.population_capacity - half)
        self.agents = [self._new_agent(kind) for kind in types]

    def _new_agent(self, kind: AgentType) -> Agent:
        agent = Agent(self.next_identifier, kind, self.parameters.initial_energy)
        self.next_identifier += 1
        return agent

    def regeneration_rate(self, step: int) -> float:
        if self.scenario != "gradual_decline":
            return self.parameters.baseline_regeneration
        if step < self.parameters.gradual_start:
            return self.parameters.baseline_regeneration
        if step > self.parameters.gradual_end:
            return self.parameters.stressed_regeneration
        progress = (step - self.parameters.gradual_start) / (
            self.parameters.gradual_end - self.parameters.gradual_start
        )
        return self.parameters.baseline_regeneration + progress * (
            self.parameters.stressed_regeneration - self.parameters.baseline_regeneration
        )

    def _state(self, agent: Agent, resource: float, previous_resource: float) -> tuple[str, str, str]:
        resource_ratio = resource / self.parameters.resource_capacity
        energy_ratio = agent.energy / self.parameters.maximum_energy
        resource_band = "low" if resource_ratio < 0.33 else "medium" if resource_ratio <= 0.66 else "high"
        energy_band = "low" if energy_ratio < 0.33 else "medium" if energy_ratio <= 0.66 else "high"
        delta = resource - previous_resource
        trend = "falling" if delta < -2 else "rising" if delta > 2 else "stable"
        return resource_band, energy_band, trend

    def _epsilon(self, agent: Agent) -> float:
        fraction = min(agent.age, self.parameters.maximum_age) / self.parameters.maximum_age
        return self.parameters.epsilon_start + fraction * (self.parameters.epsilon_minimum - self.parameters.epsilon_start)

    def _choose_action(self, agent: Agent, state: tuple[str, str, str]) -> str:
        if agent.kind == "fixed":
            resource_band = state[0]
            return {"low": "rest", "medium": "conservative", "high": "moderate"}[resource_band]
        values = agent.q_table.setdefault(state, [0.0] * len(ACTIONS))
        if self.random.random() < self._epsilon(agent):
            return self.random.choice(ACTIONS)
        maximum = max(values)
        best = [index for index, value in enumerate(values) if value == maximum]
        return ACTIONS[self.random.choice(best)]

    def _update_q_value(
        self,
        agent: Agent,
        state: tuple[str, str, str],
        action: str,
        reward: float,
        next_state: tuple[str, str, str] | None,
    ) -> None:
        if agent.kind != "q_learning":
            return
        action_index = ACTIONS.index(action)
        values = agent.q_table.setdefault(state, [0.0] * len(ACTIONS))
        future = 0.0 if next_state is None else max(agent.q_table.setdefault(next_state, [0.0] * len(ACTIONS)))
        target = reward + self.parameters.discount_factor * future
        values[action_index] += self.parameters.learning_rate * (target - values[action_index])

    def _normalize_rewards(self, candidates: list[Agent]) -> dict[int, float]:
        values = [agent.lifetime_reward for agent in candidates]
        minimum, maximum = min(values), max(values)
        if maximum == minimum:
            return {agent.identifier: 0.5 for agent in candidates}
        return {agent.identifier: (agent.lifetime_reward - minimum) / (maximum - minimum) for agent in candidates}

    def _weighted_parent(self, candidates: list[Agent], mode: Group) -> Agent:
        scores = self._normalize_rewards(candidates)
        fitness: list[float] = []
        for agent in candidates:
            survival = agent.age / self.parameters.maximum_age
            reward = scores[agent.identifier]
            if mode == "evolving_survival":
                fitness.append(survival)
            elif mode == "evolving_reward":
                fitness.append(reward)
            else:
                fitness.append(0.5 * survival + 0.5 * reward)
        weights = [exp(self.parameters.selection_strength * value) for value in fitness]
        return self.random.choices(candidates, weights=weights, k=1)[0]

    def _choose_static_kind(self) -> AgentType:
        fixed_count = sum(agent.kind == "fixed" for agent in self.agents)
        q_count = len(self.agents) - fixed_count
        fixed_deficit = max(0, self.parameters.population_capacity // 2 - fixed_count)
        q_target = self.parameters.population_capacity - self.parameters.population_capacity // 2
        q_deficit = max(0, q_target - q_count)
        if fixed_deficit and q_deficit:
            return self.random.choices(["fixed", "q_learning"], weights=[fixed_deficit, q_deficit], k=1)[0]
        if fixed_deficit:
            return "fixed"
        return "q_learning"

    def _log_replacement_candidates(self, step_number: int, candidates: list[Agent]) -> list[dict[str, object]]:
        scores = self._normalize_rewards(candidates)
        rows: list[dict[str, object]] = []
        for agent in candidates:
            survival = agent.age / self.parameters.maximum_age
            reward = scores[agent.identifier]
            if self.group == "evolving_survival":
                fitness: float | None = survival
            elif self.group == "evolving_reward":
                fitness = reward
            elif self.group == "evolving_joint":
                fitness = 0.5 * survival + 0.5 * reward
            else:
                fitness = None
            rows.append(
                {
                    "step": step_number,
                    "agent_id": agent.identifier,
                    "agent_type": agent.kind,
                    "age": agent.age,
                    "lifetime_reward": agent.lifetime_reward,
                    "survival_score": survival,
                    "reward_score": reward,
                    "fitness": fitness,
                    "offspring_selected": 0,
                }
            )
        return rows

    def _replace_vacancies(self, step_number: int = 0) -> None:
        parent_candidates = self.agents.copy()
        self.agents = [agent for agent in self.agents if agent.age < self.parameters.maximum_age]
        vacancies = self.parameters.population_capacity - len(self.agents)
        logs: dict[int, dict[str, object]] = {}
        if self.group in ("static_mixture", "evolving_joint", "evolving_survival", "evolving_reward") and vacancies > 0:
            event_rows = self._log_replacement_candidates(step_number, parent_candidates)
            self.replacement_events.extend(event_rows)
            logs = {int(row["agent_id"]): row for row in event_rows}
        for _ in range(vacancies):
            if not parent_candidates:
                break
            if self.group == "fixed_only":
                kind: AgentType = "fixed"
            elif self.group == "q_only":
                kind = "q_learning"
            elif self.group == "static_mixture":
                kind = self._choose_static_kind()
            else:
                parent = self._weighted_parent(parent_candidates, self.group)
                kind = parent.kind
                logs[parent.identifier]["offspring_selected"] += 1  # type: ignore[operator]

            if self.group == "static_mixture":
                candidates = [agent for agent in parent_candidates if agent.kind == kind]
                if not candidates:
                    self.founder_injections += 1
                else:
                    chosen = self.random.choice(candidates)
                    logs[chosen.identifier]["offspring_selected"] += 1  # type: ignore[operator]
            self.agents.append(self._new_agent(kind))
            self.replacements += 1

    def step(self, step_number: int) -> None:
        if not self.agents:
            return
        if self.scenario == "sudden_shock" and step_number == self.parameters.shock_step:
            pre_window = self.records[-100:]
            if pre_window:
                self.pre_shock_mean_reward = sum(record.mean_reward or 0.0 for record in pre_window) / len(pre_window)
            self.resource *= 0.5
            self.pre_shock_living_population = len(self.agents)

        start_resource = self.resource
        decisions: dict[int, tuple[tuple[str, str, str], str]] = {}
        action_counts: dict[str, int] = {a: 0 for a in ACTIONS}
        q_action_counts: dict[str, int] = {a: 0 for a in ACTIONS}
        fixed_action_counts: dict[str, int] = {a: 0 for a in ACTIONS}

        for agent in self.agents:
            state = self._state(agent, start_resource, self.previous_start_resource)
            act = self._choose_action(agent, state)
            decisions[agent.identifier] = (state, act)
            action_counts[act] += 1
            if agent.kind == "q_learning":
                q_action_counts[act] += 1
            else:
                fixed_action_counts[act] += 1

        allocation_order = self.agents.copy()
        self.random.shuffle(allocation_order)
        remaining = self.resource
        harvested: dict[int, float] = {}
        for agent in allocation_order:
            requested = HARVEST_REQUEST[decisions[agent.identifier][1]]
            amount = min(requested, remaining)
            harvested[agent.identifier] = amount
            remaining -= amount

        rewards: dict[int, float] = {}
        for agent in self.agents:
            reward = harvested[agent.identifier] - self.parameters.maintenance_cost
            rewards[agent.identifier] = reward
            agent.energy = min(self.parameters.maximum_energy, agent.energy + reward)
            agent.lifetime_reward += reward
            agent.age += 1

        living = [agent for agent in self.agents if agent.energy > 0]

        # Logistic Resource Regeneration
        K = self.parameters.resource_capacity
        g = self.regeneration_rate(step_number)
        growth = g * remaining * (1.0 - remaining / K)
        self.resource = min(K, max(0.0, remaining + growth))

        for agent in self.agents:
            state, action = decisions[agent.identifier]
            next_state = self._state(agent, self.resource, start_resource) if agent in living else None
            self._update_q_value(agent, state, action, rewards[agent.identifier], next_state)
        self.agents = living
        self.previous_start_resource = start_resource

        if self.scenario == "sudden_shock" and step_number == self.parameters.shock_step:
            denominator = self.pre_shock_living_population or 0
            self.immediate_post_shock_survival = len(self.agents) / denominator if denominator else 0.0

        if step_number % self.parameters.replacement_interval == 0 and self.agents:
            self._replace_vacancies(step_number)

        mean_reward = sum(rewards[agent.identifier] for agent in living) / len(living) if living else None
        mean_energy = sum(agent.energy for agent in self.agents) / len(self.agents) if self.agents else None
        q_share = sum(agent.kind == "q_learning" for agent in self.agents) / len(self.agents) if self.agents else None
        self.records.append(
            StepRecord(
                step_number,
                self.resource,
                sum(harvested.values()),
                len(self.agents),
                q_share,
                mean_reward,
                mean_energy,
                action_counts=action_counts,
                q_action_counts=q_action_counts,
                fixed_action_counts=fixed_action_counts,
            )
        )

    def aggregate_q_tables(self) -> dict[tuple[str, str, str], list[float]]:
        """Returns the average Q-table across all currently living Q-learning agents."""
        tables = [agent.q_table for agent in self.agents if agent.kind == "q_learning"]
        if not tables:
            return {}
        all_states = {s for t in tables for s in t}
        result: dict[tuple[str, str, str], list[float]] = {}
        for s in all_states:
            avg_vals = [0.0] * len(ACTIONS)
            count = 0
            for t in tables:
                if s in t:
                    count += 1
                    for idx, val in enumerate(t[s]):
                        avg_vals[idx] += val
            if count > 0:
                result[s] = [val / count for val in avg_vals]
        return result

    def run(self) -> RunResult:
        for step_number in range(1, self.parameters.run_length + 1):
            self.step(step_number)
            if not self.agents:
                break
        steps_completed = len(self.records)
        extinct = len(self.agents) == 0
        mean_resource = sum(record.resource for record in self.records) / steps_completed if steps_completed else 0.0
        reward_records = [record.mean_reward for record in self.records if record.mean_reward is not None]
        mean_reward = sum(reward_records) / len(reward_records) if reward_records else 0.0
        final_q_share = self.records[-1].q_learning_share if self.records else None

        if self.scenario == "sudden_shock" and self.pre_shock_mean_reward is not None:
            target = 0.9 * self.pre_shock_mean_reward
            post_shock = self.records[self.parameters.shock_step :]
            recovery_index = next(
                (
                    index
                    for index, record in enumerate(post_shock, start=1)
                    if record.mean_reward is not None and record.mean_reward >= target
                ),
                None,
            )
            self.recovery_time = recovery_index

        return RunResult(
            simulator_version=SIMULATOR_VERSION,
            parameter_version=PARAMETER_VERSION,
            group=self.group,
            scenario=self.scenario,
            seed=self.seed,
            steps_completed=steps_completed,
            extinct=extinct,
            final_q_learning_share=final_q_share,
            mean_resource=mean_resource,
            mean_reward=mean_reward,
            replacements=self.replacements,
            founder_injections=self.founder_injections,
            post_disturbance_survival=self.immediate_post_shock_survival,
            recovery_time=self.recovery_time,
            records=self.records,
            replacement_events=self.replacement_events,
        )

