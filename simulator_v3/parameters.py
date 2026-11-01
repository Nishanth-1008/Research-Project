"""Parameter specifications for Version C (Parent-Funded Reproduction & Logistic Ecology)."""

from __future__ import annotations

from dataclasses import dataclass

SIMULATOR_VERSION = "sim-3.0.0"
PARAMETER_VERSION = "params-v3.0"


@dataclass(frozen=True)
class Parameters:
    # Population & Lifespan
    population_capacity: int = 50
    run_length: int = 2000
    maximum_age: int = 100
    replacement_interval: int = 20

    # Metabolic Energy
    initial_founder_energy: float = 10.0
    maximum_energy: float = 20.0
    maintenance_cost: float = 0.20
    reproduction_cost: float = 10.0  # Transferred from parent to newborn; parent must have > 10.0

    # Resource Ecology
    resource_capacity: float = 500.0
    initial_resource: float = 350.0
    baseline_regeneration: float = 0.10
    stressed_regeneration: float = 0.05
    gradual_start: int = 500
    gradual_end: int = 1000
    shock_step: int = 1000

    # Learning & Selection
    learning_rate: float = 0.10
    discount_factor: float = 0.95
    epsilon_start: float = 0.20
    epsilon_minimum: float = 0.02
    selection_strength: float = 2.0  # beta for softmax parent selection

