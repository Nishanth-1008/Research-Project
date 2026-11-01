"""Energy accounting and balance tracking for Version D."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EnergyLedger:
    initial_founder_endowment: float = 0.0
    cumulative_harvested: float = 0.0
    cumulative_maintenance: float = 0.0
    cumulative_energy_cap_losses: float = 0.0  # Excess energy clipped at Emax
    cumulative_starvation_losses: float = 0.0  # Deficit below 0 at starvation death
    cumulative_retirement_losses: float = 0.0  # Unspent energy lost when an agent retires
    cumulative_reproduction_transfers: float = 0.0  # Internal transfers (Delta E = 0)

    def total_energy_inflow(self) -> float:
        return self.initial_founder_endowment + self.cumulative_harvested

    def compute_discrepancy(self, living_agents_energy: float) -> float:
        expected_current = (
            self.initial_founder_endowment
            + self.cumulative_harvested
            - self.cumulative_maintenance
            - self.cumulative_energy_cap_losses
            - self.cumulative_retirement_losses
            - self.cumulative_starvation_losses
        )
        return living_agents_energy - expected_current

    def verify_energy_balance(self, living_agents_energy: float) -> tuple[bool, float]:
        """
        Thermodynamic conservation law:
        Inflow (Founders + Cumulative Harvest)
        - Outflow (Maintenance + Cap Losses + Retirement Losses + Starvation Deficits)
        = Current Living Energy.
        
        Internal reproduction transfers cancel identically:
        Delta E_parent (-10) + Delta E_newborn (+10) = 0.
        """
        discrepancy = self.compute_discrepancy(living_agents_energy)
        is_conserved = abs(discrepancy) < 1e-8
        return is_conserved, discrepancy
