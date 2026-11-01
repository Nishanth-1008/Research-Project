"""Parameter specifications for Version D (Endogenous Reproduction & Cultural Inheritance)."""

from __future__ import annotations

from dataclasses import dataclass

SIMULATOR_VERSION = "sim-4.0.0"
PARAMETER_VERSION = "params-v4.0"


@dataclass(frozen=True)
class Parameters:
    # Population & Lifespan
    initial_population: int = 50
    initial_fixed_count: int = 38
    initial_q_count: int = 12
    run_length: int = 2000
    maximum_age: int = 100

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

