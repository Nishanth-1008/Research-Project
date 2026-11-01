"""Endogenous physiological reproduction and cultural inheritance mechanism for Version D.1."""

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
    energy: float,
    age: int,
    parameters: Parameters,
    living_population: int = 0,
) -> float:
    """
    Computes reproduction probability P_i' subject to group vital-rate rules and logistic crowding:
    - Standard (evolving_joint, static_mixture, fixed_only, q_only):
      P_i = P_max * clip((E - 15)/5, 0, 1) * A(age) * discount
    - Survival-only:
      P_i = P_max * (age / A_max) * discount (subject to E >= 15.0)
    - Reward-only:
      P_i = P_max * clip((E - 15)/5, 0, 1) * 1.0 * discount
    where discount = max(0, 1 - living_population / crowding_capacity) if regulation_model == 'logistic'.
    """
    if energy < parameters.reproduction_min_energy:
        return 0.0

    # Group-specific vital rate base calculation
    if parameters.group == "survival_only":
        if age >= parameters.maximum_age:
            return 0.0
        # Age-based survival proxy: scales reproductive probability linearly with age
        # (rewards achieved longevity as an age-based proxy, not direct survival fitness)
        base_prob = parameters.reproduction_max_prob * (age / float(parameters.maximum_age))
    elif parameters.group == "reward_only":
        energy_span = parameters.reproduction_target_energy - parameters.reproduction_min_energy
        energy_factor = min(1.0, max(0.0, (energy - parameters.reproduction_min_energy) / energy_span))
        base_prob = parameters.reproduction_max_prob * energy_factor
    else:
        # Standard joint survival & reward vital rate
        if age >= parameters.reproduction_age_max:
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

        base_prob = parameters.reproduction_max_prob * energy_factor * age_factor

    # Population regulation attenuation
    if parameters.regulation_model == "logistic":
        density_discount = max(
            0.0, 1.0 - (living_population / float(parameters.crowding_capacity))
        )
    else:
        density_discount = 1.0

    return base_prob * density_discount


def perform_endogenous_reproduction(
    living_agents: list[Agent],
    step_number: int,
    parameters: Parameters,
    random_gen: Random,
    next_identifier_getter: Callable[[], int],
) -> tuple[list[Agent], list[ReproductionLog]]:
    """
    Executes endogenous reproduction for eligible agents:
    - Any agent with energy >= 15.0, age < max_age, and reproduction_cooldown == 0 evaluates P_i'.
    - If draw < P_i':
        * Parent transfers exactly 10.0 energy to newborn (parent.energy -= 10.0, newborn.energy = 10.0).
        * Parent sets reproduction_cooldown = 20 and skips cooldown decrement on birth step.
        * Newborn is created at age = 0, receives cooldown = 20, and skips cooldown and aging on birth step.
        * Newborn type is assigned via clonal lineage, except in static_mixture which uses deficit-targeted assignment.
        * If Q-learning agent, newborn receives parent's active Q-table snapshot (or clean table if Fixed parent in static mix).
    """
    newborns: list[Agent] = []
    logs: list[ReproductionLog] = []

    # Maximum age check depends on group
    max_age_cutoff = (
        parameters.maximum_age
        if parameters.group in ("survival_only", "reward_only")
        else parameters.reproduction_age_max
    )

    eligible_candidates = [
        agent
        for agent in living_agents
        if agent.energy >= parameters.reproduction_min_energy
        and agent.age < max_age_cutoff
        and agent.reproduction_cooldown == 0
    ]

    for parent in eligible_candidates:
        # Re-verify parent still has >= 15.0 energy in case of multiple actions
        if parent.energy < parameters.reproduction_min_energy:
            continue

        # Effective current living population includes living agents + newborns already produced this step
        current_living_count = len(living_agents) + len(newborns)

        prob = calculate_reproduction_probability(
            parent.energy,
            parent.age,
            parameters,
            living_population=current_living_count,
        )
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

            # Offspring type determination
            if parameters.group == "static_mixture":
                current_fixed = sum(1 for a in living_agents if a.kind == "fixed") + sum(1 for a in newborns if a.kind == "fixed")
                current_q = sum(1 for a in living_agents if a.kind == "q_learning") + sum(1 for a in newborns if a.kind == "q_learning")
                total_current = current_fixed + current_q

                # Deficit-targeted assignment with strict priority hierarchy:
                # Priority 1: Extinction Recovery (reintroduce extinct type if count is zero)
                if current_fixed == 0 and current_q > 0:
                    newborn_kind: AgentType = "fixed"
                elif current_q == 0 and current_fixed > 0:
                    newborn_kind = "q_learning"
                # Priority 2: Deficit Elimination (assign to whichever type has lower count / larger deficit)
                # Note: Holds uniformly for N < 50, N == 50, and N > 50 since (25 - fixed > 25 - q) <=> fixed < q
                elif current_fixed < current_q:
                    newborn_kind = "fixed"
                elif current_q < current_fixed:
                    newborn_kind = "q_learning"
                # Priority 3: Parity Tie-Breaking (fair Bernoulli trial when counts are exactly equal)
                else:
                    newborn_kind = "fixed" if random_gen.random() < 0.5 else "q_learning"

                # Inheritance isolation for static mixture
                if newborn_kind == "fixed":
                    q_snapshot = None
                else:
                    # Q-newborn inherits parent Q only if parent was Q; Fixed parent yields clean tabula rasa
                    q_snapshot = (
                        parent.get_q_snapshot(parameters.inheritance_duration)
                        if parent.kind == "q_learning"
                        else None
                    )
            elif parameters.group == "fixed_only":
                newborn_kind = "fixed"
                q_snapshot = None
            elif parameters.group == "q_only":
                newborn_kind = "q_learning"
                q_snapshot = parent.get_q_snapshot(parameters.inheritance_duration)
            else:
                # Clonal lineage inheritance (evolving_joint, survival_only, reward_only)
                newborn_kind = parent.kind
                q_snapshot = (
                    parent.get_q_snapshot(parameters.inheritance_duration)
                    if parent.kind == "q_learning"
                    else None
                )

            newborn = Agent(
                identifier=newborn_id,
                kind=newborn_kind,
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
                    newborn_type=newborn_kind,
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
