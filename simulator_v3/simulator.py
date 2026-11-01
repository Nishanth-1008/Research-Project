"""Version C Ecosystem Simulator.

Implements the explicit 13-stage step order with closed parent-funded reproduction.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from random import Random
from typing import Literal

from agents import ACTIONS, HARVEST_REQUEST, Agent, AgentType
from energy_accounting import EnergyLedger
from parameters import SIMULATOR_VERSION, PARAMETER_VERSION, Parameters
from reproduction import Group, ReproductionLog, perform_parent_funded_reproduction

Scenario = Literal["stationary", "gradual_decline", "sudden_shock"]


@dataclass
class StepRecord:
    step: int
    resource: float
    total_harvest: float
    living_population: int
    q_learning_share: float | None
    mean_reward: float | None
    mean_energy: float | None
    births: int
    starvation_deaths: int
    retirement_deaths: int
    unfunded_vacancies: int
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
    total_births: int
    total_starvation_deaths: int
    total_retirement_deaths: int
    total_unfunded_vacancies: int
    records: list[StepRecord] = field(repr=False)
    reproduction_logs: list[ReproductionLog] = field(repr=False)

    def summary(self) -> dict[str, object]:
        d = asdict(self)
        del d["records"]
        del d["reproduction_logs"]
        return d


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

        self.energy_ledger = EnergyLedger(
            initial_founder_endowment=parameters.population_capacity * parameters.initial_founder_energy
        )

        self.records: list[StepRecord] = []
        self.reproduction_logs: list[ReproductionLog] = []

        self.total_births = 0
        self.total_starvation_deaths = 0
        self.total_retirement_deaths = 0
        self.total_unfunded_vacancies = 0

        self._initialize_population()

    def _get_next_identifier(self) -> int:
        idx = self.next_identifier
        self.next_identifier += 1
        return idx

    def _initialize_population(self) -> None:
        if self.group == "fixed_only":
            types = ["fixed"] * self.parameters.population_capacity
        elif self.group == "q_only":
            types = ["q_learning"] * self.parameters.population_capacity
        elif self.group == "static_mixture" or self.group == "evolving_joint":
            half = self.parameters.population_capacity // 2
            types = ["fixed"] * half + ["q_learning"] * (self.parameters.population_capacity - half)
        else:
            types = ["fixed"] * self.parameters.population_capacity

        for kind in types:
            agent = Agent(
                identifier=self._get_next_identifier(),
                kind=kind,
                energy=self.parameters.initial_founder_energy,
                age=0,
                lifetime_reward=0.0,
                born_step=0,
            )
            self.agents.append(agent)

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

    def step(self, step_number: int) -> None:
        if not self.agents:
            return

        # Sudden shock at shock step
        if self.scenario == "sudden_shock" and step_number == self.parameters.shock_step:
            self.resource *= 0.5

        # -------------------------------------------------------------
        # 1. Observation
        # -------------------------------------------------------------
        start_resource = self.resource
        decisions: dict[int, tuple[tuple[str, str, str], str]] = {}
        action_counts = {a: 0 for a in ACTIONS}
        q_action_counts = {a: 0 for a in ACTIONS}
        fixed_action_counts = {a: 0 for a in ACTIONS}

        # -------------------------------------------------------------
        # 2. Action Selection
        # -------------------------------------------------------------
        for agent in self.agents:
            state = self._state(agent, start_resource, self.previous_start_resource)
            act = agent.choose_action(
                state,
                self.random,
                self.parameters.maximum_age,
                self.parameters.epsilon_start,
                self.parameters.epsilon_minimum,
            )
            decisions[agent.identifier] = (state, act)
            action_counts[act] += 1
            if agent.kind == "q_learning":
                q_action_counts[act] += 1
            else:
                fixed_action_counts[act] += 1

        # -------------------------------------------------------------
        # 3. Randomized Harvest Allocation
        # -------------------------------------------------------------
        allocation_order = self.agents.copy()
        self.random.shuffle(allocation_order)
        remaining_resource = self.resource
        harvested: dict[int, float] = {}

        for agent in allocation_order:
            requested = HARVEST_REQUEST[decisions[agent.identifier][1]]
            allocated = min(requested, remaining_resource)
            harvested[agent.identifier] = allocated
            remaining_resource -= allocated

        total_step_harvest = sum(harvested.values())
        self.energy_ledger.cumulative_harvested += total_step_harvest

        # -------------------------------------------------------------
        # 4 & 5 & 6. Energy updates, Maintenance, Age, and Q-update
        # -------------------------------------------------------------
        rewards: dict[int, float] = {}
        for agent in self.agents:
            net_change = harvested[agent.identifier] - self.parameters.maintenance_cost
            rewards[agent.identifier] = net_change
            self.energy_ledger.cumulative_maintenance += self.parameters.maintenance_cost

            raw_energy = agent.energy + net_change
            if raw_energy > self.parameters.maximum_energy:
                excess = raw_energy - self.parameters.maximum_energy
                self.energy_ledger.cumulative_energy_cap_losses += excess
                agent.energy = self.parameters.maximum_energy
            else:
                agent.energy = raw_energy

            agent.lifetime_reward += net_change
            agent.age += 1

        # -------------------------------------------------------------
        # 7. Starvation Deaths
        # -------------------------------------------------------------
        survivors_of_starvation: list[Agent] = []
        step_starvations = 0
        for agent in self.agents:
            if agent.energy > 0:
                survivors_of_starvation.append(agent)
            else:
                step_starvations += 1
                if agent.energy < 0:
                    self.energy_ledger.cumulative_starvation_losses += agent.energy

        self.total_starvation_deaths += step_starvations
        self.agents = survivors_of_starvation

        # -------------------------------------------------------------
        # 8, 9, 10, 11. Vacancy identification, Eligible Parents,
        #               Reproduction, and Maximum-Age Retirement
        # -------------------------------------------------------------
        step_births = 0
        step_unfunded = 0
        step_retirements = 0

        if step_number % self.parameters.replacement_interval == 0 and self.agents:
            # Parents are eligible living agents before retirement
            parent_candidates = self.agents.copy()

            # Identify retirees (agents reaching maximum age)
            non_retirees = [a for a in self.agents if a.age < self.parameters.maximum_age]
            retirees = [a for a in self.agents if a.age >= self.parameters.maximum_age]
            step_retirements = len(retirees)
            self.total_retirement_deaths += step_retirements

            # Vacancies count both natural starvation vacancies and incoming retirements
            vacancies = self.parameters.population_capacity - len(non_retirees)

            newborns: list[Agent] = []
            if vacancies > 0 and parent_candidates:
                newborns, logs, unfunded = perform_parent_funded_reproduction(
                    living_agents=parent_candidates,
                    vacancies=vacancies,
                    step_number=step_number,
                    group=self.group,
                    parameters=self.parameters,
                    random_gen=self.random,
                    next_identifier_getter=self._get_next_identifier,
                )
                self.reproduction_logs.extend(logs)
                step_births = len(newborns)
                step_unfunded = unfunded
                self.total_births += step_births
                self.total_unfunded_vacancies += step_unfunded

            # Retirees leave the population after reproduction eligibility; unspent energy is logged
            for r in retirees:
                self.energy_ledger.cumulative_retirement_losses += r.energy

            # Active population becomes non-retirees plus newly funded newborns
            self.agents = non_retirees + newborns

        # -------------------------------------------------------------
        # 12. Resource Regeneration (Logistic)
        # -------------------------------------------------------------
        K = self.parameters.resource_capacity
        g = self.regeneration_rate(step_number)
        growth = g * remaining_resource * (1.0 - remaining_resource / K)
        self.resource = min(K, max(0.0, remaining_resource + growth))

        # Update Q-values for agents that acted this step
        for agent in survivors_of_starvation:
            state, action = decisions[agent.identifier]
            next_state = self._state(agent, self.resource, start_resource)
            agent.update_q_value(
                state,
                action,
                rewards[agent.identifier],
                next_state,
                self.parameters.learning_rate,
                self.parameters.discount_factor,
            )

        self.previous_start_resource = start_resource

        # -------------------------------------------------------------
        # 13. Metric Recording
        # -------------------------------------------------------------
        living_count = len(self.agents)
        q_count = sum(a.kind == "q_learning" for a in self.agents)
        q_share = (q_count / living_count) if living_count > 0 else None
        mean_reward = (
            sum(rewards[a.identifier] for a in survivors_of_starvation) / len(survivors_of_starvation)
            if survivors_of_starvation
            else None
        )
        mean_energy = sum(a.energy for a in self.agents) / living_count if living_count > 0 else None

        self.records.append(
            StepRecord(
                step=step_number,
                resource=self.resource,
                total_harvest=total_step_harvest,
                living_population=living_count,
                q_learning_share=q_share,
                mean_reward=mean_reward,
                mean_energy=mean_energy,
                births=step_births,
                starvation_deaths=step_starvations,
                retirement_deaths=step_retirements,
                unfunded_vacancies=step_unfunded,
                action_counts=action_counts,
                q_action_counts=q_action_counts,
                fixed_action_counts=fixed_action_counts,
            )
        )

    def run(self) -> RunResult:
        for s in range(1, self.parameters.run_length + 1):
            self.step(s)
            if not self.agents:
                break

        steps_completed = len(self.records)
        extinct = len(self.agents) == 0
        mean_resource = sum(r.resource for r in self.records) / steps_completed if steps_completed else 0.0
        reward_vals = [r.mean_reward for r in self.records if r.mean_reward is not None]
        mean_reward = sum(reward_vals) / len(reward_vals) if reward_vals else 0.0
        final_q_share = self.records[-1].q_learning_share if self.records else None

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
            total_births=self.total_births,
            total_starvation_deaths=self.total_starvation_deaths,
            total_retirement_deaths=self.total_retirement_deaths,
            total_unfunded_vacancies=self.total_unfunded_vacancies,
            records=self.records,
            reproduction_logs=self.reproduction_logs,
        )
