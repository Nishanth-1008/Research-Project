"""Unit Tests for Experiment 3B (Graded Harvest Quotas).

Validates:
1. Action space harvest scaling across all 4 groups (Control, A, B, C).
2. Requested vs. allocated harvest accounting.
3. Reproduction eligibility percentages tracked accurately.
4. Type-restricted reproduction enforced (matching C-76F).
5. Retiring agents (age >= 100) strictly excluded from reproduction.
6. Energy conservation holds to machine precision across all quota levels.
"""

from __future__ import annotations

import unittest
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from exp3b_harvest_quotas import Experiment3BSimulator, QUOTA_HARVEST_REQUESTS
from parameters import Parameters
from agents import Agent


class TestExperiment3B(unittest.TestCase):
    def setUp(self) -> None:
        self.params = Parameters()

    def test_1_action_space_scaling_matrix(self) -> None:
        """Requirement 1: Verify correct harvest scaling across all 4 groups."""
        expected = {
            "control": {"rest": 0.0, "conservative": 0.5, "moderate": 1.0, "aggressive": 2.0},
            "treatment_a": {"rest": 0.0, "conservative": 0.375, "moderate": 0.75, "aggressive": 1.5},
            "treatment_b": {"rest": 0.0, "conservative": 0.25, "moderate": 0.50, "aggressive": 1.0},
            "treatment_c": {"rest": 0.0, "conservative": 0.1875, "moderate": 0.375, "aggressive": 0.75},
        }
        for grp, mapping in expected.items():
            sim = Experiment3BSimulator(self.params, "stationary", 1001, quota_group=grp)
            self.assertEqual(sim.harvest_requests, mapping)

    def test_2_requested_vs_allocated_harvest_accounting(self) -> None:
        """Requirement 2: Verify requested vs allocated harvest tracking."""
        sim = Experiment3BSimulator(self.params, "stationary", 1001, quota_group="treatment_b")
        # Step with abundant resource (350.0)
        sim.step(1)
        rec = sim.records[0]
        # Total requested should equal sum of fixed and Q requested
        self.assertEqual(rec.total_requested, rec.fixed_requested + rec.q_requested)
        # Total allocated should equal sum of fixed and Q allocated
        self.assertEqual(rec.total_harvest, rec.fixed_allocated + rec.q_allocated)
        # In step 1 with R=350, resource is abundant, so allocated equals requested
        self.assertEqual(rec.total_harvest, rec.total_requested)

    def test_3_type_restricted_reproduction_enforced(self) -> None:
        """Requirement 3: Verify that Q agents cannot fund Fixed vacancies."""
        sim = Experiment3BSimulator(self.params, "stationary", 1001, quota_group="treatment_c", fixed_target=38)
        # 0 Fixed agents, 12 Q agents with surplus energy (15.0)
        sim.agents = [Agent(i, "q_learning", 15.0, age=50) for i in range(12)]
        births, unfunded, fb, qb, ret = sim._replace_vacancies_type_restricted(80)
        # Vacancies target fixed deficit (38), but 0 fixed parents exist -> 0 births, 38 unfunded
        self.assertEqual(births, 0)
        self.assertEqual(unfunded, 38)
        self.assertEqual(len(sim.agents), 12)

    def test_4_retiring_agents_cannot_reproduce(self) -> None:
        """Requirement 4: Verify agents at age >= 100 are excluded from reproduction."""
        sim = Experiment3BSimulator(self.params, "stationary", 1001, quota_group="control", fixed_target=38)
        sim.agents = [Agent(1, "fixed", 20.0, age=100)]
        births, unfunded, fb, qb, ret = sim._replace_vacancies_type_restricted(100)
        self.assertEqual(births, 0)
        self.assertEqual(ret, 1)
        self.assertEqual(unfunded, 50)
        self.assertEqual(len(sim.agents), 0)
        self.assertEqual(sim.energy_ledger.cumulative_retirement_losses, 20.0)

    def test_5_reproduction_eligibility_tracking(self) -> None:
        """Requirement 5: Verify reproduction eligibility percentage is recorded accurately."""
        sim = Experiment3BSimulator(self.params, "stationary", 1001, quota_group="treatment_a", fixed_target=38)
        # 10 Fixed with E=15.0 (eligible), 10 Fixed with E=5.0 (ineligible) -> 50% eligible
        # 5 Q with E=12.0 (eligible), 5 Q with E=8.0 (ineligible) -> 50% eligible
        fixed = [Agent(i, "fixed", 15.0, age=20) for i in range(10)] + [Agent(i+10, "fixed", 5.0, age=20) for i in range(10)]
        q = [Agent(i+20, "q_learning", 12.0, age=20) for i in range(5)] + [Agent(i+25, "q_learning", 8.0, age=20) for i in range(5)]
        sim.agents = fixed + q
        sim.step(20)
        rec = sim.records[0]
        self.assertEqual(rec.pct_fixed_eligible, 50.0)
        self.assertEqual(rec.pct_q_eligible, 50.0)

    def test_6_energy_conservation_across_all_quotas(self) -> None:
        """Requirement 6: Verify strict energy conservation across all quota groups."""
        for grp in ["control", "treatment_a", "treatment_b", "treatment_c"]:
            sim = Experiment3BSimulator(self.params, "stationary", 1001, quota_group=grp)
            for s in range(1, 25):
                sim.step(s)
            living_energy = sum(a.energy for a in sim.agents)
            conserved, disc = sim.energy_ledger.verify_energy_balance(living_energy)
            self.assertTrue(conserved, f"Energy not conserved in {grp}")
            self.assertLess(disc, 1e-10, f"Discrepancy too large in {grp}: {disc}")


if __name__ == "__main__":
    unittest.main()
