"""Unit Tests for Experiment 3A (Type-Neutral Reproduction).

Validates all 9 critical diagnostic requirements:
1. Exactly 10.0 energy cannot reproduce (strict inequality check).
2. 18.0 energy funds only one birth (drops to 8.0, cannot fund 2nd).
3. 20.0 energy funds only one birth under strict > 10.0 (drops to 10.0, which is not > 10.0).
4. Q parent can fill a fixed deficit in treatment.
5. Fixed parent can fill a Q deficit in treatment.
6. Retiring agents (age >= 100) cannot reproduce.
7. Newborns do not act or pay maintenance on their birth step (age 0, energy 10.0).
8. Q newborns receive fresh, zero-initialized empty Q-tables.
9. Population capacity (N <= 50) is never violated.
"""

from __future__ import annotations

import unittest
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from exp3a_type_neutral_reproduction import Experiment3ASimulator
from parameters import Parameters
from agents import Agent


class TestExperiment3A(unittest.TestCase):
    def setUp(self) -> None:
        self.params = Parameters()

    def test_1_exact_10_energy_cannot_reproduce(self) -> None:
        """Requirement 1: Exactly 10.0 energy cannot reproduce (strict > 10.0 required)."""
        sim = Experiment3ASimulator(self.params, "stationary", 1001, mode="treatment", fixed_target=38)
        # 1 agent with exactly 10.0 energy, age 50
        sim.agents = [Agent(1, "q_learning", 10.0, age=50)]
        res = sim._replace_vacancies_treatment(20)
        births, unfunded = res[0], res[1]
        self.assertEqual(births, 0)
        self.assertEqual(unfunded, 49)  # 50 - 1 = 49 vacancies
        self.assertEqual(sim.agents[0].energy, 10.0)

    def test_2_eighteen_energy_funds_only_one_birth(self) -> None:
        """Requirement 2: 18.0 energy funds only one birth (drops to 8.0, cannot fund 2nd)."""
        sim = Experiment3ASimulator(self.params, "stationary", 1001, mode="treatment", fixed_target=38)
        sim.agents = [Agent(1, "q_learning", 18.0, age=50)]
        res = sim._replace_vacancies_treatment(20)
        births, unfunded = res[0], res[1]
        self.assertEqual(births, 1)
        self.assertEqual(unfunded, 48)  # 49 vacancies, 1 filled, 48 unfunded
        self.assertEqual(len(sim.agents), 2)
        # Parent energy drops from 18.0 to 8.0
        self.assertEqual(sim.agents[0].energy, 8.0)
        # Newborn receives 10.0
        self.assertEqual(sim.agents[1].energy, 10.0)
        self.assertEqual(sim.agents[0].energy + sim.agents[1].energy, 18.0)

    def test_3_twenty_energy_funds_only_one_birth_under_strict_inequality(self) -> None:
        """Requirement 3: 20.0 energy funds only one birth under strict > 10.0 (drops to 10.0, which is not > 10.0)."""
        sim = Experiment3ASimulator(self.params, "stationary", 1001, mode="treatment", fixed_target=38)
        sim.agents = [Agent(1, "fixed", 20.0, age=50)]
        res = sim._replace_vacancies_treatment(20)
        births, unfunded = res[0], res[1]
        self.assertEqual(births, 1)
        self.assertEqual(unfunded, 48)
        self.assertEqual(len(sim.agents), 2)
        # Parent energy is exactly 10.0, which is NOT > 10.0
        self.assertEqual(sim.agents[0].energy, 10.0)
        self.assertEqual(sim.agents[1].energy, 10.0)

    def test_4_q_parent_fills_fixed_deficit_in_treatment(self) -> None:
        """Requirement 4: Q parent can fill a fixed deficit in treatment."""
        sim = Experiment3ASimulator(self.params, "stationary", 1001, mode="treatment", fixed_target=38)
        # 0 Fixed agents, 5 Q agents with 15.0 energy
        sim.agents = [Agent(i, "q_learning", 15.0, age=50) for i in range(5)]
        res = sim._replace_vacancies_treatment(80)
        births, unfunded, fb, qb = res[0], res[1], res[2], res[3]
        step_cross_q = res[5]
        self.assertEqual(births, 5)
        self.assertEqual(qb, 5)
        self.assertEqual(fb, 0)
        self.assertEqual(step_cross_q, 5)
        self.assertEqual(sim.cross_type_q_births, 5)
        self.assertEqual(sim.first_cross_type_step, 80)
        self.assertEqual(sim.first_q_replaces_fixed_step, 80)
        self.assertEqual(sim.cumulative_cross_type_energy, 50.0)

    def test_5_fixed_parent_fills_q_deficit_in_treatment(self) -> None:
        """Requirement 5: Fixed parent can fill a Q deficit in treatment."""
        sim = Experiment3ASimulator(self.params, "stationary", 1001, mode="treatment", fixed_target=38)
        # 38 Fixed agents with 15.0 energy, 0 Q agents (q_target is 12)
        sim.agents = [Agent(i, "fixed", 15.0, age=50) for i in range(38)]
        res = sim._replace_vacancies_treatment(80)
        births, unfunded, fb, qb = res[0], res[1], res[2], res[3]
        step_cross_fixed = res[6]
        # 12 vacancies exist (50 - 38 = 12). 12 Fixed parents fund births
        self.assertEqual(births, 12)
        self.assertEqual(fb, 12)
        self.assertEqual(qb, 0)
        self.assertEqual(step_cross_fixed, 12)
        self.assertEqual(sim.cross_type_fixed_births, 12)
        self.assertEqual(sim.first_cross_type_step, 80)
        self.assertEqual(sim.first_fixed_replaces_q_step, 80)
        self.assertEqual(sim.cumulative_cross_type_energy, 120.0)

    def test_6_retiring_agents_cannot_reproduce(self) -> None:
        """Requirement 6: Retiring agents (age >= 100) cannot reproduce."""
        sim = Experiment3ASimulator(self.params, "stationary", 1001, mode="treatment", fixed_target=38)
        # Agent has reached age 100 with plenty of energy (20.0)
        sim.agents = [Agent(1, "q_learning", 20.0, age=100)]
        res = sim._replace_vacancies_treatment(100)
        births, unfunded, fb, qb, retirements = res[0], res[1], res[2], res[3], res[4]
        self.assertEqual(births, 0)
        self.assertEqual(retirements, 1)
        self.assertEqual(unfunded, 50)  # 50 vacancies, all unfunded
        self.assertEqual(len(sim.agents), 0)  # Agent retired, population extinct
        # Unspent energy logged to retirement losses
        self.assertEqual(sim.energy_ledger.cumulative_retirement_losses, 20.0)

    def test_7_newborns_do_not_act_or_pay_maintenance_on_birth_step(self) -> None:
        """Requirement 7: Newborns do not act or pay maintenance on their birth step (age 0, energy 10.0)."""
        sim = Experiment3ASimulator(self.params, "stationary", 1001, mode="treatment", fixed_target=38)
        # Setup 1 agent with 15.0 energy, age 19
        sim.agents = [Agent(1, "fixed", 15.0, age=19)]
        # Run step 20
        sim.step(20)
        # At step 20:
        # Agent 1 acts, harvests, pays maintenance 0.20, ages to 20.
        # Then reproduction occurs: Agent 1 funds 1 newborn.
        # Newborn is created with age 0 and energy 10.0.
        self.assertEqual(len(sim.agents), 2)
        newborn = [a for a in sim.agents if a.identifier != 1][0]
        self.assertEqual(newborn.age, 0)
        self.assertEqual(newborn.energy, 10.0)
        self.assertEqual(newborn.born_step, 20)

    def test_8_q_newborn_receives_empty_q_table(self) -> None:
        """Requirement 8: Q newborns receive fresh, zero-initialized empty Q-tables."""
        sim = Experiment3ASimulator(self.params, "stationary", 1001, mode="treatment", fixed_target=38)
        parent = Agent(1, "q_learning", 15.0, age=50)
        parent.q_table = {("low", "low", "falling"): {"harvest": 5.0, "rest": 0.0}}
        sim.agents = [parent]
        res = sim._replace_vacancies_treatment(80)
        self.assertEqual(res[0], 1)
        newborn = [a for a in sim.agents if a.identifier != 1][0]
        self.assertEqual(newborn.kind, "q_learning")
        self.assertEqual(newborn.q_table, {})
        self.assertIsNot(newborn.q_table, parent.q_table)

    def test_9_population_capacity_never_exceeded(self) -> None:
        """Requirement 9: Population capacity (N <= 50) is never violated."""
        sim = Experiment3ASimulator(self.params, "stationary", 1001, mode="treatment", fixed_target=38)
        # 45 living agents with 20.0 energy
        sim.agents = [Agent(i, "fixed", 20.0, age=50) for i in range(45)]
        res = sim._replace_vacancies_treatment(80)
        births = res[0]
        self.assertEqual(births, 5)  # Exactly 5 vacancies exist to reach 50
        self.assertEqual(len(sim.agents), 50)


if __name__ == "__main__":
    unittest.main()
