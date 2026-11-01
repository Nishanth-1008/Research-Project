"""Energy accounting and balance tracking for Version C."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EnergyLedger:
    initial_founder_endowment: float = 0.0
    cumulative_harvested: float = 0.0
    cumulative_maintenance: float = 0.0
    cumulative_energy_cap_losses: float = 0.0  # Excess energy clipped at Emax
    cumulative_starvation_losses: float = 0.0  # Deficit below 0 at starvation death
    cumulative_retirement_losses: float = 0.0  # Unspent energy lost when an agent retires
    cumulative_reproduction_transfers: float = 0.0

    def total_energy_inflow(self) -> float:
        return self.initial_founder_endowment + self.cumulative_harvested

    def verify_energy_balance(self, living_agents_energy: float) -> tuple[bool, float]:
        """
        Conservation law:
        Inflow (Founders + Harvest)
        - Outflow (Maintenance + Cap Losses + Retirement + Starvation)
        = Current Living Energy
        """
        expected_current = (
            self.initial_founder_endowment
            + self.cumulative_harvested
            - self.cumulative_maintenance
            - self.cumulative_energy_cap_losses
            - self.cumulative_retirement_losses
            - self.cumulative_starvation_losses
        )
        discrepancy = living_agents_energy - expected_current
        is_conserved = abs(discrepancy) < 1e-6
        return is_conserved, discrepancy
