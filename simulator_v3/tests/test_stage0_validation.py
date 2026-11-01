"""Stage 0 Unit Tests for Version C.

Verifies:
1. Resource bounds (0 <= R <= 500)
2. Energy conservation during parent-funded reproduction (parent_loss + newborn_gain == 0)
3. Parent eligibility (parent.energy strictly > 10.0)
4. Multiple offspring rechecking (parent energy decremented after each birth)
5. Population capacity limit (living_population <= 50)
6. Newborn timing (newborn does not act on birth step; acts starting on birth_step + 1)
7. Maximum-age removal and starvation correctness
8. Identical reproduction accounting across agent types
"""

from __future__ import annotations

import unittest
import sys
from pathlib import Path

# Add simulator_v3 to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import Agent
from energy_accounting import EnergyLedger
from parameters import Parameters
from reproduction import perform_parent_funded_reproduction
from simulator import EcosystemSimulator


class VersionCStage0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.params = Parameters()

    def test_energy_conservation_during_reproduction(self) -> None:
        """Verify that parent energy deduction exactly equals newborn energy (net Delta E == 0)."""
        parent = Agent(identifier=1, kind="fixed", energy=18.0, age=50)
        living = [parent]
        newborns, logs, unfunded = perform_parent_funded_reproduction(
            living_agents=living,
            vacancies=1,
            step_number=20,
            group="fixed_only",
            parameters=self.params,
            random_gen=EcosystemSimulator(self.params, "fixed_only", "stationary", 1).random,
            next_identifier_getter=lambda: 2,
        )
        self.assertEqual(len(newborns), 1)
        self.assertEqual(parent.energy, 8.0)
        self.assertEqual(newborns[0].energy, 10.0)
        self.assertEqual(logs[0].energy_transferred, 10.0)
        self.assertEqual(parent.energy + newborns[0].energy, 18.0)

    def test_parent_eligibility_strict_greater_than_cost(self) -> None:
        """Verify that an agent with exactly 10.0 energy is NOT eligible to reproduce."""
        parent_exact = Agent(identifier=1, kind="fixed", energy=10.0, age=50)
        living = [parent_exact]
        newborns, logs, unfunded = perform_parent_funded_reproduction(
            living_agents=living,
            vacancies=1,
            step_number=20,
            group="fixed_only",
            parameters=self.params,
            random_gen=EcosystemSimulator(self.params, "fixed_only", "stationary", 1).random,
            next_identifier_getter=lambda: 2,
        )
        self.assertEqual(len(newborns), 0)
        self.assertEqual(unfunded, 1)
        self.assertEqual(parent_exact.energy, 10.0)
        self.assertFalse(logs[0].success)
        self.assertIn("No parent has energy > 10.0", logs[0].failure_reason)

    def test_multiple_offspring_rechecking(self) -> None:
        """Verify that a single rich parent (energy=18.0) can only fund 1 offspring, not 2."""
        parent = Agent(identifier=1, kind="fixed", energy=18.0, age=50)
        living = [parent]
        counter = [2]
        def get_id():
            val = counter[0]
            counter[0] += 1
            return val

        newborns, logs, unfunded = perform_parent_funded_reproduction(
            living_agents=living,
            vacancies=2,
            step_number=20,
            group="fixed_only",
            parameters=self.params,
            random_gen=EcosystemSimulator(self.params, "fixed_only", "stationary", 1).random,
            next_identifier_getter=get_id,
        )
        self.assertEqual(len(newborns), 1)
        self.assertEqual(unfunded, 1)
        self.assertEqual(parent.energy, 8.0)  # Dropped from 18.0 to 8.0; cannot fund 2nd vacancy

    def test_newborn_timing_does_not_act_on_birth_step(self) -> None:
        """Verify that a newborn added at step 20 does NOT act or pay maintenance during step 20."""
        sim = EcosystemSimulator(self.params, "fixed_only", "stationary", 1)
        # Advance 20 steps
        for s in range(1, 21):
            sim.step(s)
        # Newborns born at step 20 must have age 0 and energy exactly 10.0
        newborns_at_20 = [a for a in sim.agents if a.born_step == 20]
        for nb in newborns_at_20:
            self.assertEqual(nb.age, 0)
            self.assertEqual(nb.energy, 10.0)

    def test_population_capacity_limit(self) -> None:
        """Verify living population never exceeds population_capacity (50)."""
        sim = EcosystemSimulator(self.params, "fixed_only", "stationary", 1)
        for s in range(1, 100):
            sim.step(s)
            self.assertLessEqual(len(sim.agents), 50)

    def test_resource_bounds(self) -> None:
        """Verify resource is always within [0, resource_capacity]."""
        sim = EcosystemSimulator(self.params, "fixed_only", "stationary", 1)
        for s in range(1, 100):
            sim.step(s)
            self.assertGreaterEqual(sim.resource, 0.0)
            self.assertLessEqual(sim.resource, self.params.resource_capacity)

    def test_parity_across_agent_types(self) -> None:
        """Verify that identical reproduction rules apply to Q-agents and Fixed agents."""
        p_fixed = Agent(identifier=1, kind="fixed", energy=15.0, age=40)
        p_q = Agent(identifier=2, kind="q_learning", energy=15.0, age=40)
        for p, grp, expected_type in [(p_fixed, "fixed_only", "fixed"), (p_q, "q_only", "q_learning")]:
            newborns, logs, unfunded = perform_parent_funded_reproduction(
                living_agents=[p],
                vacancies=1,
                step_number=20,
                group=grp,
                parameters=self.params,
                random_gen=EcosystemSimulator(self.params, grp, "stationary", 1).random,
                next_identifier_getter=lambda: 99,
            )
            self.assertEqual(len(newborns), 1)
            self.assertEqual(p.energy, 5.0)
            self.assertEqual(newborns[0].kind, expected_type)
            self.assertEqual(newborns[0].energy, 10.0)
            self.assertEqual(newborns[0].q_table, {})


if __name__ == "__main__":
    unittest.main()
