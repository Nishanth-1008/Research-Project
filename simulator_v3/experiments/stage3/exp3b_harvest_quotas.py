"""Experiment 3B: Graded Harvest Quotas.

Investigates whether restricting individual harvesting capacity relative to the
environment's natural regeneration capacity restores ecological sustainability
and enables demographic persistence in mixed populations (38 Fixed / 12 Q, N=50).

Four groups:
- Control: Baseline action space (aggressive=2.0, conservative=1.0, rest=0.0)
- Treatment A (-25% quota): (aggressive=1.5, conservative=0.75, rest=0.0)
- Treatment B (-50% quota): (aggressive=1.0, conservative=0.50, rest=0.0)
- Treatment C (-62.5% quota): (aggressive=0.75, conservative=0.375, rest=0.0)

Demographic and reproduction rules remain strictly frozen matching baseline C-76F:
- Parent-funded reproduction with strict E > 10.0.
- Type-restricted replacement (vacancies target 38 Fixed / 12 Q deficit).
- Retiring agents (age >= 100) strictly excluded from reproduction.
"""

from __future__ import annotations

import sys
from pathlib import Path
from random import Random
from typing import Literal

# Add simulator_v3 to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents import ACTIONS, Agent, AgentType
from energy_accounting import EnergyLedger
from parameters import Parameters
from reproduction import ReproductionLog
from simulator import EcosystemSimulator, StepRecord

QuotaGroup = Literal["control", "treatment_a", "treatment_b", "treatment_c"]

QUOTA_HARVEST_REQUESTS: dict[QuotaGroup, dict[str, float]] = {
    "control": {"rest": 0.0, "conservative": 0.5, "moderate": 1.0, "aggressive": 2.0},
    "treatment_a": {"rest": 0.0, "conservative": 0.375, "moderate": 0.75, "aggressive": 1.5},
    "treatment_b": {"rest": 0.0, "conservative": 0.25, "moderate": 0.50, "aggressive": 1.0},
    "treatment_c": {"rest": 0.0, "conservative": 0.1875, "moderate": 0.375, "aggressive": 0.75},
}


class Experiment3BSimulator(EcosystemSimulator):
    def __init__(
        self,
        parameters: Parameters,
        scenario: str,
        seed: int,
        quota_group: QuotaGroup = "control",
        fixed_target: int = 38,
    ) -> None:
        self.quota_group = quota_group
        self.fixed_target = fixed_target
        self.q_target = parameters.population_capacity - fixed_target
        self.harvest_requests = QUOTA_HARVEST_REQUESTS[quota_group]

        self.stream_env = Random(seed * 1000 + 1)
        self.stream_agents = Random(seed * 1000 + 2)

        super().__init__(parameters, "static_mixture", scenario, seed)  # type: ignore[arg-type]

    def _initialize_population(self) -> None:
        self.agents = []
        for _ in range(self.fixed_target):
            self.agents.append(
                Agent(
                    identifier=self._get_next_identifier(),
                    kind="fixed",
                    energy=self.parameters.initial_founder_energy,
                    age=0,
                    lifetime_reward=0.0,
                    born_step=0,
                )
            )
        for _ in range(self.q_target):
            self.agents.append(
                Agent(
                    identifier=self._get_next_identifier(),
                    kind="q_learning",
                    energy=self.parameters.initial_founder_energy,
                    age=0,
                    lifetime_reward=0.0,
                    born_step=0,
                )
            )

    def _replace_vacancies_type_restricted(
        self, step_number: int
    ) -> tuple[int, int, int, int, int]:
        """Strict C-76F type-restricted parent-funded reproduction.
        
        - Excludes retiring agents (age >= 100) from eligibility.
        - Strict energy check: energy > 10.0 rechecked after every transfer.
        - Vacancies target 38 Fixed / 12 Q quotas.
        """
        non_retirees = [a for a in self.agents if a.age < self.parameters.maximum_age]
        retirees = [a for a in self.agents if a.age >= self.parameters.maximum_age]
        step_retirements = len(retirees)
        self.total_retirement_deaths += step_retirements

        parent_candidates = non_retirees.copy()
        total_vacancies = self.parameters.population_capacity - len(non_retirees)
        newborns: list[Agent] = []
        step_unfunded = 0
        fixed_births = 0
        q_births = 0

        if total_vacancies > 0:
            fixed_count = sum(a.kind == "fixed" for a in non_retirees)
            q_count = sum(a.kind == "q_learning" for a in non_retirees)

            for _ in range(total_vacancies):
                fixed_deficit = max(0, self.fixed_target - fixed_count)
                q_deficit = max(0, self.q_target - q_count)

                if fixed_deficit > 0 and q_deficit > 0:
                    chosen_kind = self.stream_env.choices(
                        ["fixed", "q_learning"], weights=[fixed_deficit, q_deficit], k=1
                    )[0]
                elif fixed_deficit > 0:
                    chosen_kind = "fixed"
                elif q_deficit > 0:
                    chosen_kind = "q_learning"
                else:
                    chosen_kind = self.stream_env.choice(["fixed", "q_learning"])

                eligible = [
                    a for a in parent_candidates
                    if a.kind == chosen_kind and a.energy > self.parameters.reproduction_cost
                ]

                if not eligible:
                    step_unfunded += 1
                    self.reproduction_logs.append(
                        ReproductionLog(
                            step=step_number,
                            parent_id=None,
                            parent_type=chosen_kind,  # type: ignore[arg-type]
                            parent_energy_before=None,
                            energy_transferred=0.0,
                            parent_energy_after=None,
                            newborn_id=None,
                            newborn_type=None,
                            success=False,
                            failure_reason=f"No {chosen_kind} parent has energy > 10.0",
                        )
                    )
                    continue

                parent = self.stream_env.choice(eligible)
                e_before = parent.energy
                parent.energy -= self.parameters.reproduction_cost

                nb = Agent(
                    identifier=self._get_next_identifier(),
                    kind=parent.kind,
                    energy=self.parameters.reproduction_cost,
                    age=0,
                    lifetime_reward=0.0,
                    born_step=step_number,
                    q_table={},
                )
                newborns.append(nb)
                if chosen_kind == "fixed":
                    fixed_count += 1
                    fixed_births += 1
                else:
                    q_count += 1
                    q_births += 1

                self.reproduction_logs.append(
                    ReproductionLog(
                        step=step_number,
                        parent_id=parent.identifier,
                        parent_type=parent.kind,
                        parent_energy_before=e_before,
                        energy_transferred=self.parameters.reproduction_cost,
                        parent_energy_after=parent.energy,
                        newborn_id=nb.identifier,
                        newborn_type=nb.kind,
                        success=True,
                    )
                )

        for r in retirees:
            self.energy_ledger.cumulative_retirement_losses += r.energy

        self.agents = non_retirees + newborns
        return len(newborns), step_unfunded, fixed_births, q_births, step_retirements

    def step(self, step_number: int) -> None:
        if not self.agents:
            return

        if self.scenario == "sudden_shock" and step_number == self.parameters.shock_step:
            self.resource *= 0.5

        start_resource = self.resource
        decisions: dict[int, tuple[tuple[str, str, str], str]] = {}
        action_counts = {a: 0 for a in ACTIONS}
        q_action_counts = {a: 0 for a in ACTIONS}
        fixed_action_counts = {a: 0 for a in ACTIONS}

        for agent in self.agents:
            state = self._state(agent, start_resource, self.previous_start_resource)
            act = agent.choose_action(
                state,
                self.stream_agents,
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

        # Track requested harvest by type
        fixed_requested = sum(
            self.harvest_requests[decisions[a.identifier][1]]
            for a in self.agents
            if a.kind == "fixed"
        )
        q_requested = sum(
            self.harvest_requests[decisions[a.identifier][1]]
            for a in self.agents
            if a.kind == "q_learning"
        )
        total_requested = fixed_requested + q_requested

        # Allocation in randomized order
        allocation_order = self.agents.copy()
        self.stream_env.shuffle(allocation_order)
        remaining_resource = self.resource
        harvested: dict[int, float] = {}

        for agent in allocation_order:
            requested = self.harvest_requests[decisions[agent.identifier][1]]
            allocated = min(requested, remaining_resource)
            harvested[agent.identifier] = allocated
            remaining_resource -= allocated

        fixed_allocated = sum(harvested[a.identifier] for a in self.agents if a.kind == "fixed")
        q_allocated = sum(harvested[a.identifier] for a in self.agents if a.kind == "q_learning")
        total_allocated = sum(harvested.values())
        self.energy_ledger.cumulative_harvested += total_allocated

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

        survivors_of_starvation: list[Agent] = []
        step_starvations = 0
        fixed_starvations = 0
        q_starvations = 0
        for agent in self.agents:
            if agent.energy > 0:
                survivors_of_starvation.append(agent)
            else:
                step_starvations += 1
                if agent.kind == "fixed":
                    fixed_starvations += 1
                else:
                    q_starvations += 1
                if agent.energy < 0:
                    self.energy_ledger.cumulative_starvation_losses += agent.energy

        self.total_starvation_deaths += step_starvations
        self.agents = survivors_of_starvation

        # Track reproduction eligibility before reproduction executes
        step_births = 0
        step_unfunded = 0
        step_retirements = 0
        fixed_births = 0
        q_births = 0
        pct_fixed_eligible: float | None = None
        pct_q_eligible: float | None = None

        if step_number % self.parameters.replacement_interval == 0 and self.agents:
            # Measure eligibility percentage among non-retiring living agents
            non_ret = [a for a in self.agents if a.age < self.parameters.maximum_age]
            living_f = [a for a in non_ret if a.kind == "fixed"]
            living_q = [a for a in non_ret if a.kind == "q_learning"]
            elig_f = [a for a in living_f if a.energy > self.parameters.reproduction_cost]
            elig_q = [a for a in living_q if a.energy > self.parameters.reproduction_cost]

            pct_fixed_eligible = (len(elig_f) / len(living_f) * 100.0) if living_f else 0.0
            pct_q_eligible = (len(elig_q) / len(living_q) * 100.0) if living_q else 0.0

            (
                step_births,
                step_unfunded,
                fixed_births,
                q_births,
                step_retirements,
            ) = self._replace_vacancies_type_restricted(step_number)

            self.total_births += step_births
            self.total_unfunded_vacancies += step_unfunded

        # Logistic regeneration
        K = self.parameters.resource_capacity
        g = self.regeneration_rate(step_number)
        growth = g * remaining_resource * (1.0 - remaining_resource / K)
        self.resource = min(K, max(0.0, remaining_resource + growth))

        # Q-learning updates
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

        living_count = len(self.agents)
        fixed_count = sum(a.kind == "fixed" for a in self.agents)
        q_count = living_count - fixed_count
        q_share = (q_count / living_count) if living_count > 0 else None

        fixed_energies = [a.energy for a in self.agents if a.kind == "fixed"]
        q_energies = [a.energy for a in self.agents if a.kind == "q_learning"]

        mean_fixed_e = (sum(fixed_energies) / len(fixed_energies)) if fixed_energies else None
        min_fixed_e = min(fixed_energies) if fixed_energies else None
        mean_q_e = (sum(q_energies) / len(q_energies)) if q_energies else None
        min_q_e = min(q_energies) if q_energies else None

        mean_reward = (
            sum(rewards[a.identifier] for a in survivors_of_starvation) / len(survivors_of_starvation)
            if survivors_of_starvation
            else None
        )
        mean_energy = sum(a.energy for a in self.agents) / living_count if living_count > 0 else None
        harvest_ratio = (total_allocated / growth) if growth > 0 else None

        rec = StepRecord(
            step=step_number,
            resource=self.resource,
            total_harvest=total_allocated,
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
        rec.fixed_count = fixed_count  # type: ignore[attr-defined]
        rec.q_count = q_count  # type: ignore[attr-defined]
        rec.fixed_requested = fixed_requested  # type: ignore[attr-defined]
        rec.q_requested = q_requested  # type: ignore[attr-defined]
        rec.total_requested = total_requested  # type: ignore[attr-defined]
        rec.fixed_allocated = fixed_allocated  # type: ignore[attr-defined]
        rec.q_allocated = q_allocated  # type: ignore[attr-defined]
        rec.regeneration = growth  # type: ignore[attr-defined]
        rec.harvest_regeneration_ratio = harvest_ratio  # type: ignore[attr-defined]
        rec.mean_fixed_energy = mean_fixed_e  # type: ignore[attr-defined]
        rec.min_fixed_energy = min_fixed_e  # type: ignore[attr-defined]
        rec.mean_q_energy = mean_q_e  # type: ignore[attr-defined]
        rec.min_q_energy = min_q_e  # type: ignore[attr-defined]
        rec.fixed_starvations = fixed_starvations  # type: ignore[attr-defined]
        rec.q_starvations = q_starvations  # type: ignore[attr-defined]
        rec.fixed_births = fixed_births  # type: ignore[attr-defined]
        rec.q_births = q_births  # type: ignore[attr-defined]
        rec.pct_fixed_eligible = pct_fixed_eligible  # type: ignore[attr-defined]
        rec.pct_q_eligible = pct_q_eligible  # type: ignore[attr-defined]
        self.records.append(rec)
