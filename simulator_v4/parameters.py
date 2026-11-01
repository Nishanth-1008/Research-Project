"""Parameter specifications for Version D.1 (Endogenous Reproduction & Cultural Inheritance)."""

from __future__ import annotations

from dataclasses import dataclass

SIMULATOR_VERSION = "sim-4.1.0"
PARAMETER_VERSION = "params-v4.1"


@dataclass(frozen=True)
class Parameters:
    # Group & Population Architecture
    group: str = "evolving_joint"  # "fixed_only", "q_only", "static_mixture", "evolving_joint", "survival_only", "reward_only"
    initial_population: int = 50
    initial_fixed_count: int = 25
    initial_q_count: int = 25
    run_length: int = 2000
    maximum_age: int = 100

    # Population Regulation
    regulation_model: str = "logistic"  # "logistic" or "none"
    crowding_capacity: int = 50

    # Metabolic Energy
    initial_founder_energy: float = 10.0
    maximum_energy: float = 25.0
    maintenance_cost: float = 0.20
    reproduction_cost: float = 10.0  # Transferred from parent to newborn
    newborn_energy: float = 10.0

    # Endogenous Reproduction Parameters
    reproduction_min_energy: float = 15.0
    reproduction_target_energy: float = 20.0
    reproduction_max_prob: float = 0.10
    reproduction_age_full: int = 45
    reproduction_age_max: int = 60
    reproduction_cooldown: int = 20

    # Cultural Inheritance Parameters
    inheritance_duration: int = 12

    # Resource Ecology (Frozen Version C Logistic Equation)
    resource_capacity: float = 500.0
    initial_resource: float = 350.0
    baseline_regeneration: float = 0.10
    stressed_regeneration: float = 0.05
    gradual_start: int = 500
    gradual_end: int = 1000
    shock_step: int = 1000

    # Learning & Exploration
    learning_rate: float = 0.10
    discount_factor: float = 0.95
    epsilon_start: float = 0.20
    epsilon_minimum: float = 0.02

    def __post_init__(self) -> None:
        if self.initial_population != self.initial_fixed_count + self.initial_q_count:
            raise ValueError(
                f"initial_population ({self.initial_population}) must equal "
                f"initial_fixed_count ({self.initial_fixed_count}) + "
                f"initial_q_count ({self.initial_q_count})"
            )
        allowed_groups = {
            "fixed_only",
            "q_only",
            "static_mixture",
            "evolving_joint",
            "survival_only",
            "reward_only",
        }
        if self.group not in allowed_groups:
            raise ValueError(
                f"group must be one of {allowed_groups}, got '{self.group}'"
            )
        if self.regulation_model not in {"logistic", "none"}:
            raise ValueError(
                f"regulation_model must be 'logistic' or 'none', got '{self.regulation_model}'"
            )

    @classmethod
    def for_group(cls, group: str, **kwargs) -> Parameters:
        """Helper factory to instantiate valid default counts per group."""
        if group == "fixed_only":
            init_pop = kwargs.pop("initial_population", 50)
            return cls(
                group=group,
                initial_population=init_pop,
                initial_fixed_count=init_pop,
                initial_q_count=0,
                **kwargs,
            )
        elif group == "q_only":
            init_pop = kwargs.pop("initial_population", 50)
            return cls(
                group=group,
                initial_population=init_pop,
                initial_fixed_count=0,
                initial_q_count=init_pop,
                **kwargs,
            )
        elif group in {"static_mixture", "evolving_joint", "survival_only", "reward_only"}:
            init_pop = kwargs.pop("initial_population", 50)
            half = init_pop // 2
            return cls(
                group=group,
                initial_population=init_pop,
                initial_fixed_count=half,
                initial_q_count=init_pop - half,
                **kwargs,
            )
        else:
            raise ValueError(f"Unknown group: {group}")
