"""Experiment 3A: Type-Neutral Reproduction.

Isolates the contribution of type-restricted reproduction vs resource competition
in mixed populations (initial composition: 38 Fixed / 12 Q, N=50).

Two groups:
- Control: Original Version C C-76F reproduction rules.
           Vacancies target the deficit type (38 Fixed / 12 Q).
           Only an eligible parent of the deficit type can reproduce.
           If none exists, vacancy is left unfunded.
- Treatment: Type-Neutral reproduction.
             Any living parent with energy strictly > 10.0 is eligible to fund an offspring.
             Offspring inherits parent's type.
             Parent loses exactly 10.0 energy; newborn receives exactly 10.0 energy.
             Q-learning newborns receive zero-initialized empty Q-table.
             Parent eligibility rechecked after every transfer.
             No artificial composition forcing after step 0.
             Vacancies filled up to N=50 as long as ANY eligible parent exists.
             Non-retiring agents only: agents reaching maximum age (age >= 100)
             are strictly excluded from reproduction eligibility.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from random import Random

# Add simulator_v3 to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents import ACTIONS, HARVEST_REQUEST, Agent, AgentType
from energy_accounting import EnergyLedger
from parameters import Parameters
from reproduction import ReproductionLog
from simulator import EcosystemSimulator, StepRecord

OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "results_v3" / "stage3_mechanism_isolation" / "exp3a"
SEEDS = tuple(range(1001, 1011))


class Experiment3ASimulator(EcosystemSimulator):
    def __init__(
        self,
        parameters: Parameters,
        scenario: str,
        seed: int,
        mode: str = "treatment",  # "control" or "treatment"
        fixed_target: int = 38,
    ) -> None:
        self.mode = mode
        self.fixed_target = fixed_target
        self.q_target = parameters.population_capacity - fixed_target
        self.stream_env = Random(seed * 1000 + 1)
        self.stream_agents = Random(seed * 1000 + 2)

        # Cross-type replacement metrics
        self.cross_type_q_births = 0
        self.cross_type_fixed_births = 0
        self.first_cross_type_step: int | None = None
        self.first_q_replaces_fixed_step: int | None = None
        self.first_fixed_replaces_q_step: int | None = None
        self.cumulative_cross_type_energy = 0.0

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

    def _replace_vacancies_control(
        self, step_number: int
    ) -> tuple[int, int, int, int, int, int, int, float]:
        """Control reproduction: type-restricted static quota targeting (38F / 12Q).
        
        Excludes retiring agents (age >= maximum_age) from parent eligibility.
        Preserves strict energy > 10.0 requirement.
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
        return len(newborns), step_unfunded, fixed_births, q_births, step_retirements, 0, 0, 0.0

    def _replace_vacancies_treatment(
        self, step_number: int
    ) -> tuple[int, int, int, int, int, int, int, float]:
        """
        Treatment reproduction: Type-neutral eligibility.
        Any living non-retiring parent with energy strictly > 10.0 is eligible to fund an offspring.
        Offspring inherits parent's type.
        Parent eligibility is rechecked after every transfer.
        Tracks true cross-type replacements where Q-parent reproduces when Fixed < 38,
        or Fixed-parent reproduces when Q < 12.
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
        step_cross_type_q = 0
        step_cross_type_fixed = 0
        step_cross_type_energy = 0.0

        if total_vacancies > 0:
            current_fixed = sum(a.kind == "fixed" for a in non_retirees)
            current_q = sum(a.kind == "q_learning" for a in non_retirees)

            for _ in range(total_vacancies):
                # Dynamically recheck: ANY living non-retired parent with energy > 10.0
                eligible = [a for a in parent_candidates if a.energy > self.parameters.reproduction_cost]
                if not eligible:
                    step_unfunded += 1
                    self.reproduction_logs.append(
                        ReproductionLog(
                            step=step_number,
                            parent_id=None,
                            parent_type=None,
                            parent_energy_before=None,
                            energy_transferred=0.0,
                            parent_energy_after=None,
                            newborn_id=None,
                            newborn_type=None,
                            success=False,
                            failure_reason="No parent of ANY type has energy > 10.0",
                        )
                    )
                    continue

                parent = self.stream_env.choice(eligible)
                e_before = parent.energy
                parent.energy -= self.parameters.reproduction_cost

                # Track true cross-type replacement
                if parent.kind == "q_learning" and current_fixed < self.fixed_target:
                    step_cross_type_q += 1
                    self.cross_type_q_births += 1
                    step_cross_type_energy += self.parameters.reproduction_cost
                    self.cumulative_cross_type_energy += self.parameters.reproduction_cost
                    if self.first_cross_type_step is None:
                        self.first_cross_type_step = step_number
                    if self.first_q_replaces_fixed_step is None:
                        self.first_q_replaces_fixed_step = step_number
                elif parent.kind == "fixed" and current_q < self.q_target:
                    step_cross_type_fixed += 1
                    self.cross_type_fixed_births += 1
                    step_cross_type_energy += self.parameters.reproduction_cost
                    self.cumulative_cross_type_energy += self.parameters.reproduction_cost
                    if self.first_cross_type_step is None:
                        self.first_cross_type_step = step_number
                    if self.first_fixed_replaces_q_step is None:
                        self.first_fixed_replaces_q_step = step_number

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
                if parent.kind == "fixed":
                    current_fixed += 1
                    fixed_births += 1
                else:
                    current_q += 1
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
        return (
            len(newborns),
            step_unfunded,
            fixed_births,
            q_births,
            step_retirements,
            step_cross_type_q,
            step_cross_type_fixed,
            step_cross_type_energy,
        )

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

        allocation_order = self.agents.copy()
        self.stream_env.shuffle(allocation_order)
        remaining_resource = self.resource
        harvested: dict[int, float] = {}

        for agent in allocation_order:
            requested = HARVEST_REQUEST[decisions[agent.identifier][1]]
            allocated = min(requested, remaining_resource)
            harvested[agent.identifier] = allocated
            remaining_resource -= allocated

        total_step_harvest = sum(harvested.values())
        self.energy_ledger.cumulative_harvested += total_step_harvest

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
        for agent in self.agents:
            if agent.energy > 0:
                survivors_of_starvation.append(agent)
            else:
                step_starvations += 1
                if agent.energy < 0:
                    self.energy_ledger.cumulative_starvation_losses += agent.energy

        self.total_starvation_deaths += step_starvations
        self.agents = survivors_of_starvation

        step_births = 0
        step_unfunded = 0
        step_retirements = 0
        fixed_births = 0
        q_births = 0
        step_cross_type_q = 0
        step_cross_type_fixed = 0
        step_cross_type_energy = 0.0

        if step_number % self.parameters.replacement_interval == 0 and self.agents:
            if self.mode == "control":
                (
                    step_births,
                    step_unfunded,
                    fixed_births,
                    q_births,
                    step_retirements,
                    step_cross_type_q,
                    step_cross_type_fixed,
                    step_cross_type_energy,
                ) = self._replace_vacancies_control(step_number)
            else:
                (
                    step_births,
                    step_unfunded,
                    fixed_births,
                    q_births,
                    step_retirements,
                    step_cross_type_q,
                    step_cross_type_fixed,
                    step_cross_type_energy,
                ) = self._replace_vacancies_treatment(step_number)

            self.total_births += step_births
            self.total_unfunded_vacancies += step_unfunded

        K = self.parameters.resource_capacity
        g = self.regeneration_rate(step_number)
        growth = g * remaining_resource * (1.0 - remaining_resource / K)
        self.resource = min(K, max(0.0, remaining_resource + growth))

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

        rec = StepRecord(
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
        rec.fixed_count = fixed_count  # type: ignore[attr-defined]
        rec.q_count = q_count  # type: ignore[attr-defined]
        rec.mean_fixed_energy = mean_fixed_e  # type: ignore[attr-defined]
        rec.min_fixed_energy = min_fixed_e  # type: ignore[attr-defined]
        rec.mean_q_energy = mean_q_e  # type: ignore[attr-defined]
        rec.min_q_energy = min_q_e  # type: ignore[attr-defined]
        rec.fixed_births = fixed_births  # type: ignore[attr-defined]
        rec.q_births = q_births  # type: ignore[attr-defined]
        rec.regeneration = growth  # type: ignore[attr-defined]
        rec.cross_type_q_births = step_cross_type_q  # type: ignore[attr-defined]
        rec.cross_type_fixed_births = step_cross_type_fixed  # type: ignore[attr-defined]
        rec.cross_type_energy = step_cross_type_energy  # type: ignore[attr-defined]
        rec.total_reproduction_energy = step_births * self.parameters.reproduction_cost  # type: ignore[attr-defined]
        rec.fixed_reproduction_energy = fixed_births * self.parameters.reproduction_cost  # type: ignore[attr-defined]
        rec.q_reproduction_energy = q_births * self.parameters.reproduction_cost  # type: ignore[attr-defined]
        self.records.append(rec)
