"""Minimal shared-resource ecosystem simulator for the finalized protocol."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import exp
from random import Random
from typing import Literal


SIMULATOR_VERSION = "sim-1.0.0"
PARAMETER_VERSION = "params-v1.0"

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
HARVEST_REQUEST = {"rest": 0.0, "conservative": 0.5, "moderate": 1.0, "aggressive": 2.0}


@dataclass(frozen=True)
class Parameters:
    population_capacity: int = 50
    run_length: int = 2_000
    resource_capacity: float = 500.0
    initial_resource: float = 350.0
    initial_energy: float = 10.0
    maximum_energy: float = 20.0
    maintenance_cost: float = 0.2
    maximum_age: int = 100
    replacement_interval: int = 20
    selection_strength: float = 2.0
    baseline_regeneration: float = 0.04
    stressed_regeneration: float = 0.025
    gradual_start: int = 500
    gradual_end: int = 1_000
    shock_step: int = 1_000
    learning_rate: float = 0.10
    discount_factor: float = 0.95
    epsilon_start: float = 0.20
    epsilon_minimum: float = 0.02


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


@dataclass
class RunResult:
    seed: int
    group: Group
    scenario: Scenario
    steps_completed: int
    extinct: bool
    founder_injections: int
    replacements: int
    final_q_learning_share: float | None
    mean_resource: float
    mean_reward: float
    post_disturbance_survival: float | None
    recovery_time: int | None
    records: list[StepRecord]
    replacement_events: list[dict[str, object]] = field(default_factory=list)

    def summary(self) -> dict[str, object]:
        data = asdict(self)
        data.pop("records")
        data.pop("replacement_events")
        return data


class EcosystemSimulator:
    def __init__(self, parameters: Parameters, group: Group, scenario: Scenario, seed: int):
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
        """Build per-candidate rows for the replacement-event record. Consumes no randomness."""
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
        for agent in self.agents:
            state = self._state(agent, start_resource, self.previous_start_resource)
            decisions[agent.identifier] = (state, self._choose_action(agent, state))

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
        self.resource = min(
            self.parameters.resource_capacity,
            remaining + self.regeneration_rate(step_number) * (self.parameters.resource_capacity - remaining),
        )
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
            StepRecord(step_number, self.resource, sum(harvested.values()), len(self.agents), q_share, mean_reward, mean_energy)
        )
        if self.scenario == "sudden_shock" and self.pre_shock_mean_reward is not None and self.recovery_time is None:
            if step_number >= self.parameters.shock_step and mean_reward is not None and mean_reward >= 0.9 * self.pre_shock_mean_reward:
                self.recovery_time = step_number - self.parameters.shock_step

    def run(self) -> RunResult:
        for step_number in range(1, self.parameters.run_length + 1):
            self.step(step_number)
            if not self.agents:
                break
        final_share = self.records[-1].q_learning_share if self.records else None
        mean_resource = sum(record.resource for record in self.records) / len(self.records) if self.records else 0.0
        rewards = [record.mean_reward for record in self.records if record.mean_reward is not None]
        mean_reward = sum(rewards) / len(rewards) if rewards else 0.0
        return RunResult(
            seed=self.seed,
            group=self.group,
            scenario=self.scenario,
            steps_completed=len(self.records),
            extinct=not bool(self.agents),
            founder_injections=self.founder_injections,
            replacements=self.replacements,
            final_q_learning_share=final_share,
            mean_resource=mean_resource,
            mean_reward=mean_reward,
            post_disturbance_survival=self.immediate_post_shock_survival,
            recovery_time=self.recovery_time,
            records=self.records,
            replacement_events=self.replacement_events,
        )

