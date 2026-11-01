"""Parent-funded reproduction mechanisms for Version C."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from random import Random
from typing import Literal

from agents import Agent, AgentType
from parameters import Parameters

Group = Literal["fixed_only", "q_only", "evolving_joint", "static_mixture"]


@dataclass
class ReproductionLog:
    step: int
    parent_id: int | None
    parent_type: AgentType | None
    parent_energy_before: float | None
    energy_transferred: float
    parent_energy_after: float | None
    newborn_id: int | None
    newborn_type: AgentType | None
    success: bool
    failure_reason: str | None = None


def normalize_rewards(candidates: list[Agent]) -> dict[int, float]:
    values = [agent.lifetime_reward for agent in candidates]
    minimum, maximum = min(values), max(values)
    if maximum == minimum:
        return {agent.identifier: 0.5 for agent in candidates}
    return {agent.identifier: (agent.lifetime_reward - minimum) / (maximum - minimum) for agent in candidates}


def select_eligible_parent(
    eligible_candidates: list[Agent],
    group: Group,
    parameters: Parameters,
    random_gen: Random,
) -> Agent:
    if group == "fixed_only" or group == "q_only":
        return random_gen.choice(eligible_candidates)

    # Evolving joint selection among eligible candidates
    scores = normalize_rewards(eligible_candidates)
    fitness: list[float] = []
    for agent in eligible_candidates:
        survival = agent.age / parameters.maximum_age
        reward = scores[agent.identifier]
        fitness.append(0.5 * survival + 0.5 * reward)
    weights = [exp(parameters.selection_strength * value) for value in fitness]
    return random_gen.choices(eligible_candidates, weights=weights, k=1)[0]


def perform_parent_funded_reproduction(
    living_agents: list[Agent],
    vacancies: int,
    step_number: int,
    group: Group,
    parameters: Parameters,
    random_gen: Random,
    next_identifier_getter: callable,
) -> tuple[list[Agent], list[ReproductionLog], int]:
    """
    Executes parent-funded reproduction:
    - Candidate must have energy > reproduction_cost (10.0).
    - Energy is transferred: parent.energy -= 10.0, newborn.energy = 10.0.
    - Parent energy is rechecked after each transfer.
    - Newborns are created with age = 0, born_step = step_number.
    - Returns: (newborns_created, reproduction_logs, unfunded_vacancies)
    """
    newborns: list[Agent] = []
    logs: list[ReproductionLog] = []
    unfunded_vacancies = 0

    for _ in range(vacancies):
        # Dynamically filter eligible parents who currently have energy > reproduction_cost
        # Strictly > 10.0 so parent retains positive energy after birth
        eligible = [agent for agent in living_agents if agent.energy > parameters.reproduction_cost]
        if not eligible:
            unfunded_vacancies += 1
            logs.append(
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
                    failure_reason="No parent has energy > 10.0",
                )
            )
            continue

        parent = select_eligible_parent(eligible, group, parameters, random_gen)
        e_before = parent.energy
        parent.energy -= parameters.reproduction_cost
        e_after = parent.energy

        newborn_id = next_identifier_getter()
        newborn = Agent(
            identifier=newborn_id,
            kind=parent.kind,
            energy=parameters.reproduction_cost,
            age=0,
            lifetime_reward=0.0,
            born_step=step_number,
            q_table={},  # zero-initialized empty table
        )
        newborns.append(newborn)

        logs.append(
            ReproductionLog(
                step=step_number,
                parent_id=parent.identifier,
                parent_type=parent.kind,
                parent_energy_before=e_before,
                energy_transferred=parameters.reproduction_cost,
                parent_energy_after=e_after,
                newborn_id=newborn.identifier,
                newborn_type=newborn.kind,
                success=True,
            )
        )

    return newborns, logs, unfunded_vacancies

