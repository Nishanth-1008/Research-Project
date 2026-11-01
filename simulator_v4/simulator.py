"""Unified ecosystem simulator for Version D.1 (sim-4.1.0).

Simulates continuous interaction between tabular Q-learning and fixed-rule agents
in a closed thermodynamic renewable commons with endogenous physiological reproduction,
logistic density regulation, cultural Q-table inheritance, and multi-group dispatch.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from random import Random
from typing import Literal

try:
    from simulator_v4.agents import ACTIONS, HARVEST_REQUEST, Agent, AgentType
    from simulator_v4.energy_accounting import EnergyLedger
    from simulator_v4.parameters import (
        PARAMETER_VERSION,
        SIMULATOR_VERSION,
        Parameters,
    )
    from simulator_v4.reproduction import (
        ReproductionLog,
        perform_endogenous_reproduction,
    )
except ImportError:
    from agents import ACTIONS, HARVEST_REQUEST, Agent, AgentType
    from energy_accounting import EnergyLedger
    from parameters import (
        PARAMETER_VERSION,
        SIMULATOR_VERSION,
        Parameters,
    )
    from reproduction import (
        ReproductionLog,
        perform_endogenous_reproduction,
    )

Scenario = Literal["stationary", "gradual_decline", "sudden_shock"]


@dataclass
class StepRecord:
    step: int
    resource: float
    total_harvest: float
    requested_harvest: float
    fixed_requested_harvest: float
    q_requested_harvest: float
    fixed_allocated_harvest: float
    q_allocated_harvest: float
    living_population: int
    fixed_population: int
    q_population: int
    q_learning_share: float | None
    mean_reward: float | None
    mean_energy: float | None
    births: int
    fixed_births: int
    q_births: int
    reproduction_attempts: int
    successful_births: int
    starvation_deaths: int
    retirement_deaths: int
    regeneration: float
    action_counts: dict[str, int] = field(default_factory=dict)
    q_action_counts: dict[str, int] = field(default_factory=dict)
    fixed_action_counts: dict[str, int] = field(default_factory=dict)
    energy_ledger_discrepancy: float = 0.0

    # Extended subpopulation telemetry for sim-4.1.0
    fixed_mean_energy: float | None = None
    fixed_max_energy: float | None = None
    q_mean_energy: float | None = None
    q_max_energy: float | None = None
    fixed_eligible_count: int = 0
    q_eligible_count: int = 0
    fixed_starvation_deaths: int = 0
    q_starvation_deaths: int = 0
    fixed_retirement_deaths: int = 0
    q_retirement_deaths: int = 0
    reference_harvest: float = 0.0


@dataclass
class RunResult:
    simulator_version: str
    parameter_version: str
    scenario: Scenario
    group: str
    seed: int
    steps_completed: int
    extinct: bool
    final_population: int
    final_q_learning_share: float | None
    mean_resource: float
    mean_reward: float
    total_births: int
    total_starvation_deaths: int
    total_retirement_deaths: int
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
        scenario: Scenario = "stationary",
        seed: int = 1001,
        group: str | None = None,
    ) -> None:
        if group is not None and group != parameters.group:
            # Re-instantiate parameters with matching group
            self.parameters = Parameters.for_group(
                group=group,
                run_length=parameters.run_length,
                maximum_age=parameters.maximum_age,
                crowding_capacity=parameters.crowding_capacity,
                regulation_model=parameters.regulation_model,
                initial_founder_energy=parameters.initial_founder_energy,
                maximum_energy=parameters.maximum_energy,
                maintenance_cost=parameters.maintenance_cost,
                reproduction_cost=parameters.reproduction_cost,
                newborn_energy=parameters.newborn_energy,
                reproduction_min_energy=parameters.reproduction_min_energy,
                reproduction_target_energy=parameters.reproduction_target_energy,
                reproduction_max_prob=parameters.reproduction_max_prob,
                reproduction_age_full=parameters.reproduction_age_full,
                reproduction_age_max=parameters.reproduction_age_max,
                reproduction_cooldown=parameters.reproduction_cooldown,
                inheritance_duration=parameters.inheritance_duration,
                resource_capacity=parameters.resource_capacity,
                initial_resource=parameters.initial_resource,
                baseline_regeneration=parameters.baseline_regeneration,
                stressed_regeneration=parameters.stressed_regeneration,
                gradual_start=parameters.gradual_start,
                gradual_end=parameters.gradual_end,
                shock_step=parameters.shock_step,
                learning_rate=parameters.learning_rate,
                discount_factor=parameters.discount_factor,
                epsilon_start=parameters.epsilon_start,
                epsilon_minimum=parameters.epsilon_minimum,
            )
        else:
            self.parameters = parameters

        self.scenario = scenario
        self.group = self.parameters.group
        self.seed = seed
        self.random = Random(seed)

        self.resource = self.parameters.initial_resource
        self.previous_start_resource = self.parameters.initial_resource

        self.next_identifier = 1
        self.agents: list[Agent] = []
        self._initialize_population()

        total_initial_endowment = (
            self.parameters.initial_fixed_count + self.parameters.initial_q_count
        ) * self.parameters.initial_founder_energy
        self.energy_ledger = EnergyLedger(
            initial_founder_endowment=total_initial_endowment
        )

        self.records: list[StepRecord] = []
        self.reproduction_logs: list[ReproductionLog] = []

        self.total_births = 0
        self.total_starvation_deaths = 0
        self.total_retirement_deaths = 0

    def _get_next_identifier(self) -> int:
        idx = self.next_identifier
        self.next_identifier += 1
        return idx

    def _initialize_population(self) -> None:
        """Initializes founders at age 0 with initial energy 10.0 based on group counts."""
        # Fixed agents
        for _ in range(self.parameters.initial_fixed_count):
            self.agents.append(
                Agent(
                    identifier=self._get_next_identifier(),
                    kind="fixed",
                    energy=self.parameters.initial_founder_energy,
                    age=0,
                    born_step=0,
                    reproduction_cooldown=0,
                )
            )

        # Q-learning agents
        for _ in range(self.parameters.initial_q_count):
            self.agents.append(
                Agent(
                    identifier=self._get_next_identifier(),
                    kind="q_learning",
                    energy=self.parameters.initial_founder_energy,
                    age=0,
                    born_step=0,
                    reproduction_cooldown=0,
                )
            )

    def _get_resource_band(self, resource: float) -> str:
        if resource < 165.0:
            return "low"
        if resource <= 330.0:
            return "medium"
        return "high"

    def _get_energy_band(self, energy: float) -> str:
        if energy < 3.0:
            return "critical"
        if energy < 7.0:
            return "low"
        if energy < 14.0:
            return "medium"
        return "high"

    def _get_trend_band(self, current: float, previous: float) -> str:
        delta = current - previous
        if delta < -2.0:
            return "declining"
        if delta <= 2.0:
            return "stable"
        return "increasing"

    def _get_state(self, agent: Agent) -> tuple[str, str, str]:
        return (
            self._get_resource_band(self.resource),
            self._get_energy_band(agent.energy),
            self._get_trend_band(self.resource, self.previous_start_resource),
        )

    def _get_regeneration_rate(self, step: int) -> float:
        if self.scenario == "stationary":
            return self.parameters.baseline_regeneration
        if self.scenario == "gradual_decline":
            if step < self.parameters.gradual_start:
                return self.parameters.baseline_regeneration
            if step >= self.parameters.gradual_end:
                return self.parameters.stressed_regeneration
            fraction = (step - self.parameters.gradual_start) / float(
                self.parameters.gradual_end - self.parameters.gradual_start
            )
            return (
                self.parameters.baseline_regeneration
                + fraction
                * (
                    self.parameters.stressed_regeneration
                    - self.parameters.baseline_regeneration
                )
            )
        if self.scenario == "sudden_shock":
            # Sudden shock keeps regeneration rate at baseline throughout
            return self.parameters.baseline_regeneration
        raise ValueError(f"Unknown scenario: {self.scenario}")

    def step(self, step_number: int) -> StepRecord:
        # ---------------------------------------------------------
        # STAGE 0: Sudden Shock Halving (if sudden_shock at shock_step)
        # ---------------------------------------------------------
        if (
            self.scenario == "sudden_shock"
            and step_number == self.parameters.shock_step
        ):
            self.resource = max(0.0, self.resource * 0.50)

        start_resource = self.resource
        living_count_start = len(self.agents)

        if living_count_start == 0:
            # Extinct population
            record = StepRecord(
                step=step_number,
                resource=self.resource,
                total_harvest=0.0,
                requested_harvest=0.0,
                fixed_requested_harvest=0.0,
                q_requested_harvest=0.0,
                fixed_allocated_harvest=0.0,
                q_allocated_harvest=0.0,
                living_population=0,
                fixed_population=0,
                q_population=0,
                q_learning_share=None,
                mean_reward=None,
                mean_energy=None,
                births=0,
                fixed_births=0,
                q_births=0,
                reproduction_attempts=0,
                successful_births=0,
                starvation_deaths=0,
                retirement_deaths=0,
                regeneration=0.0,
                energy_ledger_discrepancy=0.0,
                fixed_mean_energy=None,
                fixed_max_energy=None,
                q_mean_energy=None,
                q_max_energy=None,
                fixed_eligible_count=0,
                q_eligible_count=0,
                fixed_starvation_deaths=0,
                q_starvation_deaths=0,
                fixed_retirement_deaths=0,
                q_retirement_deaths=0,
                reference_harvest=0.0,
            )
            self.records.append(record)
            return record

        # ---------------------------------------------------------
        # STAGE 1: State Observation
        # ---------------------------------------------------------
        states: dict[int, tuple[str, str, str]] = {
            agent.identifier: self._get_state(agent) for agent in self.agents
        }

        # ---------------------------------------------------------
        # STAGE 2: Action Selection
        # ---------------------------------------------------------
        actions: dict[int, str] = {}
        action_counts = {a: 0 for a in ACTIONS}
        q_action_counts = {a: 0 for a in ACTIONS}
        fixed_action_counts = {a: 0 for a in ACTIONS}

        for agent in self.agents:
            act = agent.choose_action(
                states[agent.identifier],
                self.random,
                self.parameters.maximum_age,
                self.parameters.epsilon_start,
                self.parameters.epsilon_minimum,
                self.parameters.inheritance_duration,
            )
            actions[agent.identifier] = act
            action_counts[act] += 1
            if agent.kind == "q_learning":
                q_action_counts[act] += 1
            else:
                fixed_action_counts[act] += 1

        # ---------------------------------------------------------
        # STAGE 3: Resource Allocation (Harvesting)
        # ---------------------------------------------------------
        requested_by_agent = {
            agent.identifier: HARVEST_REQUEST[actions[agent.identifier]]
            for agent in self.agents
        }
        total_requested = sum(requested_by_agent.values())
        fixed_requested = sum(
            requested_by_agent[a.identifier]
            for a in self.agents
            if a.kind == "fixed"
        )
        q_requested = sum(
            requested_by_agent[a.identifier]
            for a in self.agents
            if a.kind == "q_learning"
        )

        allocated_by_agent: dict[int, float] = {}
        if total_requested <= self.resource:
            allocated_by_agent = dict(requested_by_agent)
            total_harvest = total_requested
        else:
            scale = (
                self.resource / total_requested if total_requested > 0 else 0.0
            )
            allocated_by_agent = {
                aid: req * scale for aid, req in requested_by_agent.items()
            }
            total_harvest = self.resource

        self.resource = max(0.0, self.resource - total_harvest)
        self.energy_ledger.cumulative_harvested += total_harvest

        fixed_allocated = sum(
            allocated_by_agent[a.identifier]
            for a in self.agents
            if a.kind == "fixed"
        )
        q_allocated = sum(
            allocated_by_agent[a.identifier]
            for a in self.agents
            if a.kind == "q_learning"
        )

        # ---------------------------------------------------------
        # STAGE 4: Metabolic Deduction & Energy Updates
        # ---------------------------------------------------------
        rewards: dict[int, float] = {}
        for agent in self.agents:
            harvested = allocated_by_agent[agent.identifier]
            # Net energy change is reward
            net_change = harvested - self.parameters.maintenance_cost
            rewards[agent.identifier] = net_change
            agent.lifetime_reward += net_change

            agent.energy += harvested - self.parameters.maintenance_cost
            self.energy_ledger.cumulative_maintenance += (
                self.parameters.maintenance_cost
            )

            # Energy storage ceiling check (E_max = 25.0)
            if agent.energy > self.parameters.maximum_energy:
                excess = agent.energy - self.parameters.maximum_energy
                self.energy_ledger.cumulative_energy_cap_losses += excess
                agent.energy = self.parameters.maximum_energy

        # ---------------------------------------------------------
        # STAGE 5: Starvation Elimination
        # ---------------------------------------------------------
        living_after_metabolism: list[Agent] = []
        step_starvations = 0
        step_fixed_starvations = 0
        step_q_starvations = 0

        for agent in self.agents:
            if agent.energy <= 0.0:
                step_starvations += 1
                if agent.kind == "fixed":
                    step_fixed_starvations += 1
                else:
                    step_q_starvations += 1
                if agent.energy < 0.0:
                    self.energy_ledger.cumulative_starvation_losses += (
                        agent.energy
                    )
            else:
                living_after_metabolism.append(agent)

        self.total_starvation_deaths += step_starvations
        self.agents = living_after_metabolism

        # ---------------------------------------------------------
        # STAGE 6: Endogenous Physiological Reproduction
        # ---------------------------------------------------------
        newborns, repro_logs = perform_endogenous_reproduction(
            self.agents,
            step_number,
            self.parameters,
            self.random,
            self._get_next_identifier,
        )
        self.reproduction_logs.extend(repro_logs)

        step_births = len(newborns)
        step_fixed_births = sum(1 for n in newborns if n.kind == "fixed")
        step_q_births = sum(1 for n in newborns if n.kind == "q_learning")
        step_attempts = len(repro_logs)
        step_successes = sum(1 for log in repro_logs if log.success)

        self.total_births += step_births

        # Integrate newborns into population
        self.agents.extend(newborns)

        # ---------------------------------------------------------
        # STAGE 7: Cooldown Decrement & Age Increment
        # ---------------------------------------------------------
        for agent in self.agents:
            # Cooldown update
            if agent.skip_cooldown_decrement:
                agent.skip_cooldown_decrement = False
            elif agent.reproduction_cooldown > 0:
                agent.reproduction_cooldown -= 1

            # Age update
            if agent.skip_age_increment:
                agent.skip_age_increment = False
            else:
                agent.age += 1

        # ---------------------------------------------------------
        # STAGE 8: Senescence & Natural Retirement (Age >= 100)
        # ---------------------------------------------------------
        surviving_agents: list[Agent] = []
        step_retirements = 0
        step_fixed_retirements = 0
        step_q_retirements = 0

        for agent in self.agents:
            if agent.age >= self.parameters.maximum_age:
                step_retirements += 1
                if agent.kind == "fixed":
                    step_fixed_retirements += 1
                else:
                    step_q_retirements += 1
                self.energy_ledger.cumulative_retirement_losses += agent.energy
            else:
                surviving_agents.append(agent)

        self.total_retirement_deaths += step_retirements
        self.agents = surviving_agents

        # ---------------------------------------------------------
        # STAGE 9: Logistic Resource Regeneration
        # ---------------------------------------------------------
        regeneration_rate = self._get_regeneration_rate(step_number)
        growth = (
            regeneration_rate
            * self.resource
            * (1.0 - (self.resource / self.parameters.resource_capacity))
        )
        self.resource = min(
            self.parameters.resource_capacity, self.resource + growth
        )
        self.previous_start_resource = start_resource

        # ---------------------------------------------------------
        # STAGE 10: Q-Value Learning Update (for living Q-agents)
        # ---------------------------------------------------------
        for agent in self.agents:
            if (
                agent.kind == "q_learning"
                and agent.identifier in states
                and agent.identifier in actions
            ):
                s = states[agent.identifier]
                a = actions[agent.identifier]
                r = rewards[agent.identifier]
                s_prime = self._get_state(agent)
                agent.update_q_value(
                    s,
                    a,
                    r,
                    s_prime,
                    self.parameters.learning_rate,
                    self.parameters.discount_factor,
                    self.parameters.inheritance_duration,
                )

        # ---------------------------------------------------------
        # STAGE 11: Energy Ledger Discrepancy Verification
        # ---------------------------------------------------------
        current_living_energy = sum(agent.energy for agent in self.agents)
        discrepancy = self.energy_ledger.compute_discrepancy(
            current_living_energy
        )

        living_pop = len(self.agents)
        fixed_agents = [a for a in self.agents if a.kind == "fixed"]
        q_agents = [a for a in self.agents if a.kind == "q_learning"]

        fixed_pop = len(fixed_agents)
        q_pop = len(q_agents)
        q_share = (q_pop / living_pop) if living_pop > 0 else None
        mean_rew = (sum(rewards.values()) / len(rewards)) if rewards else None
        mean_eng = (current_living_energy / living_pop) if living_pop > 0 else None

        fixed_mean_eng = (sum(a.energy for a in fixed_agents) / fixed_pop) if fixed_pop > 0 else None
        fixed_max_eng = max((a.energy for a in fixed_agents), default=None)
        q_mean_eng = (sum(a.energy for a in q_agents) / q_pop) if q_pop > 0 else None
        q_max_eng = max((a.energy for a in q_agents), default=None)

        max_age_cutoff = (
            self.parameters.maximum_age
            if self.parameters.group in ("survival_only", "reward_only")
            else self.parameters.reproduction_age_max
        )
        fixed_elig = sum(
            1 for a in fixed_agents
            if a.energy >= self.parameters.reproduction_min_energy
            and a.age < max_age_cutoff
            and a.reproduction_cooldown == 0
        )
        q_elig = sum(
            1 for a in q_agents
            if a.energy >= self.parameters.reproduction_min_energy
            and a.age < max_age_cutoff
            and a.reproduction_cooldown == 0
        )

        mean_h_fixed = (fixed_allocated / fixed_pop) if fixed_pop > 0 else 0.0
        mean_h_q = (q_allocated / q_pop) if q_pop > 0 else 0.0
        ref_harvest = (living_pop / 2.0) * mean_h_fixed + (living_pop / 2.0) * mean_h_q

        record = StepRecord(
            step=step_number,
            resource=self.resource,
            total_harvest=total_harvest,
            requested_harvest=total_requested,
            fixed_requested_harvest=fixed_requested,
            q_requested_harvest=q_requested,
            fixed_allocated_harvest=fixed_allocated,
            q_allocated_harvest=q_allocated,
            living_population=living_pop,
            fixed_population=fixed_pop,
            q_population=q_pop,
            q_learning_share=q_share,
            mean_reward=mean_rew,
            mean_energy=mean_eng,
            births=step_births,
            fixed_births=step_fixed_births,
            q_births=step_q_births,
            reproduction_attempts=step_attempts,
            successful_births=step_successes,
            starvation_deaths=step_starvations,
            retirement_deaths=step_retirements,
            regeneration=growth,
            action_counts=action_counts,
            q_action_counts=q_action_counts,
            fixed_action_counts=fixed_action_counts,
            energy_ledger_discrepancy=discrepancy,
            fixed_mean_energy=fixed_mean_eng,
            fixed_max_energy=fixed_max_eng,
            q_mean_energy=q_mean_eng,
            q_max_energy=q_max_eng,
            fixed_eligible_count=fixed_elig,
            q_eligible_count=q_elig,
            fixed_starvation_deaths=step_fixed_starvations,
            q_starvation_deaths=step_q_starvations,
            fixed_retirement_deaths=step_fixed_retirements,
            q_retirement_deaths=step_q_retirements,
            reference_harvest=ref_harvest,
        )
        self.records.append(record)
        return record

    def run(self, steps: int | None = None) -> RunResult:
        total_steps = steps if steps is not None else self.parameters.run_length
        for t in range(total_steps):
            rec = self.step(t)
            if rec.living_population == 0:
                break

        steps_done = len(self.records)
        final_pop = len(self.agents)
        mean_res = (
            sum(r.resource for r in self.records) / steps_done
            if steps_done > 0
            else 0.0
        )
        reward_vals = [
            r.mean_reward for r in self.records if r.mean_reward is not None
        ]
        mean_rew = sum(reward_vals) / len(reward_vals) if reward_vals else 0.0
        final_q_share = (
            (sum(1 for a in self.agents if a.kind == "q_learning") / final_pop)
            if final_pop > 0
            else None
        )

        return RunResult(
            simulator_version=SIMULATOR_VERSION,
            parameter_version=PARAMETER_VERSION,
            scenario=self.scenario,
            group=self.group,
            seed=self.seed,
            steps_completed=steps_done,
            extinct=(final_pop == 0),
            final_population=final_pop,
            final_q_learning_share=final_q_share,
            mean_resource=mean_res,
            mean_reward=mean_rew,
            total_births=self.total_births,
            total_starvation_deaths=self.total_starvation_deaths,
            total_retirement_deaths=self.total_retirement_deaths,
            records=self.records,
            reproduction_logs=self.reproduction_logs,
        )
