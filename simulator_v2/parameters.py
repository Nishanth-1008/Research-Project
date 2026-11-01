"""Parameters specification for Version B (logistic renewal)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Parameters:
    population_capacity: int = 50
    run_length: int = 2000
    resource_capacity: float = 500.0
    initial_resource: float = 350.0
    initial_energy: float = 10.0
    maximum_energy: float = 20.0
    maintenance_cost: float = 0.2
    maximum_age: int = 100
    replacement_interval: int = 20
    selection_strength: float = 2.0
    baseline_regeneration: float = 0.10
    stressed_regeneration: float = 0.05
    gradual_start: int = 500
    gradual_end: int = 1000
    shock_step: int = 1000
    learning_rate: float = 0.10
    discount_factor: float = 0.95
    epsilon_start: float = 0.20
    epsilon_minimum: float = 0.02

