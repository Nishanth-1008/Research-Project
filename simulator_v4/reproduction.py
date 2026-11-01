"""Endogenous physiological reproduction and cultural inheritance mechanism for Version D."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Callable

try:
    from simulator_v4.agents import Agent, AgentType
    from simulator_v4.parameters import Parameters
except ImportError:
    from agents import Agent, AgentType
    from parameters import Parameters


@dataclass
class ReproductionLog:
    step: int
    parent_id: int
    parent_type: AgentType
    parent_age: int
    parent_energy_before: float
    energy_transferred: float
    parent_energy_after: float
    newborn_id: int | None
    newborn_type: AgentType | None
    reproduction_probability: float
    success: bool
    failure_reason: str | None = None


def calculate_reproduction_probability(
    energy: float, age: int, parameters: Parameters
) -> float:
    """
    Computes reproduction probability P_i = 0.10 * clip((E - 15)/5, 0, 1) * A_i
    where A_i = 1 for age <= 45, (60 - age)/15 for 45 < age < 60, 0 for age >= 60.
    """
    if energy < parameters.reproduction_min_energy or age >= parameters.reproduction_age_max:
        return 0.0

    energy_span = parameters.reproduction_target_energy - parameters.reproduction_min_energy
    energy_factor = min(1.0, max(0.0, (energy - parameters.reproduction_min_energy) / energy_span))

    if age <= parameters.reproduction_age_full:
        age_factor = 1.0
    elif age < parameters.reproduction_age_max:
        age_span = float(parameters.reproduction_age_max - parameters.reproduction_age_full)
        age_factor = (parameters.reproduction_age_max - age) / age_span
    else:
        age_factor = 0.0

    return parameters.reproduction_max_prob * energy_factor * age_factor


def perform_endogenous_reproduction(
    living_agents: list[Agent],
    step_number: int,
    parameters: Parameters,
    random_gen: Random,
    next_identifier_getter: Callable[[], int],
) -> tuple[list[Agent], list[ReproductionLog]]:
    """
    Executes endogenous reproduction for eligible agents:
    - Any agent with energy >= 15.0, age < 60, and reproduction_cooldown == 0 evaluates P_i.
    - If draw < P_i:
        * Parent transfers exactly 10.0 energy to newborn (parent.energy -= 10.0, newborn.energy = 10.0).
        * Parent sets reproduction_cooldown = 20 and skips cooldown decrement on birth step.
        * Newborn is created at age = 0, receives cooldown = 20, and skips cooldown and aging on birth step.
        * If Q-learning agent, newborn receives an immutable snapshot of parent's active Q-table.
    - No artificial population cap is enforced.
    """
    newborns: list[Agent] = []
    logs: list[ReproductionLog] = []

    # Snapshot eligible parents so new births during this step cannot reproduce on the same step
    eligible_candidates = [
        agent
        for agent in living_agents
        if agent.energy >= parameters.reproduction_min_energy
        and agent.age < parameters.reproduction_age_max
        and agent.reproduction_cooldown == 0
    ]

    for parent in eligible_candidates:
        # Re-verify parent still has >= 15.0 energy in case of multiple actions
        if parent.energy < parameters.reproduction_min_energy:
            continue

        prob = calculate_reproduction_probability(parent.energy, parent.age, parameters)
        if prob <= 0.0:
            continue

        # Evaluate stochastic reproduction attempt
        if random_gen.random() < prob:
            # Successful reproduction event
            energy_before = parent.energy
            parent.energy -= parameters.reproduction_cost
            energy_after = parent.energy
            parent.reproduction_cooldown = parameters.reproduction_cooldown
            parent.skip_cooldown_decrement = True

            newborn_id = next_identifier_getter()
            q_snapshot = (
                parent.get_q_snapshot(parameters.inheritance_duration)
                if parent.kind == "q_learning"
                else None
            )

            newborn = Agent(
                identifier=newborn_id,
                kind=parent.kind,
                energy=parameters.newborn_energy,
                age=0,
                born_step=step_number,
                reproduction_cooldown=parameters.reproduction_cooldown,
                skip_cooldown_decrement=True,
                skip_age_increment=True,
                q_own={},
                q_parent=q_snapshot,
            )
            newborns.append(newborn)

            logs.append(
                ReproductionLog(
                    step=step_number,
                    parent_id=parent.identifier,
                    parent_type=parent.kind,
                    parent_age=parent.age,
                    parent_energy_before=energy_before,
                    energy_transferred=parameters.reproduction_cost,
                    parent_energy_after=energy_after,
                    newborn_id=newborn_id,
                    newborn_type=parent.kind,
                    reproduction_probability=prob,
                    success=True,
                    failure_reason=None,
                )
            )
        else:
            # Failed reproduction attempt (cooldown is NOT reset)
            logs.append(
                ReproductionLog(
                    step=step_number,
                    parent_id=parent.identifier,
                    parent_type=parent.kind,
                    parent_age=parent.age,
                    parent_energy_before=parent.energy,
                    energy_transferred=0.0,
                    parent_energy_after=parent.energy,
                    newborn_id=None,
                    newborn_type=None,
                    reproduction_probability=prob,
                    success=False,
                    failure_reason="Stochastic check failed",
                )
            )

    return newborns, logs
