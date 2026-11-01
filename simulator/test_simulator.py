import unittest

from simulator import EcosystemSimulator, Parameters


class SimulatorMechanicsTests(unittest.TestCase):
    def test_resource_stays_within_bounds(self) -> None:
        parameters = Parameters(run_length=100)
        result = EcosystemSimulator(parameters, "evolving_joint", "stationary", 7).run()
        self.assertTrue(all(0 <= record.resource <= parameters.resource_capacity for record in result.records))

    def test_population_never_exceeds_capacity(self) -> None:
        parameters = Parameters(run_length=150)
        result = EcosystemSimulator(parameters, "static_mixture", "stationary", 8).run()
        self.assertTrue(all(record.living_population <= parameters.population_capacity for record in result.records))

    def test_offspring_reset_learning_state(self) -> None:
        parameters = Parameters(run_length=1, maximum_age=1, replacement_interval=1)
        simulator = EcosystemSimulator(parameters, "q_only", "stationary", 9)
        simulator.run()
        self.assertEqual(simulator.replacements, parameters.population_capacity)
        self.assertTrue(all(agent.age == 0 for agent in simulator.agents))
        self.assertTrue(all(agent.lifetime_reward == 0 for agent in simulator.agents))
        self.assertTrue(all(agent.q_table == {} for agent in simulator.agents))

    def test_sudden_shock_halves_resource_at_shock(self) -> None:
        parameters = Parameters(run_length=12, shock_step=10)
        simulator = EcosystemSimulator(parameters, "fixed_only", "sudden_shock", 10)
        for step in range(1, 10):
            simulator.step(step)
        before = simulator.resource
        simulator.step(10)
        # Regeneration occurs after the halving, so resource cannot exceed the post-regeneration cap.
        self.assertLessEqual(simulator.records[-1].resource, parameters.resource_capacity)
        self.assertLess(simulator.resource, before)

    def test_shock_survival_is_measured_before_replacement(self) -> None:
        parameters = Parameters(
            run_length=1, shock_step=1, initial_energy=0.1, maintenance_cost=3.0, replacement_interval=1
        )
        result = EcosystemSimulator(parameters, "fixed_only", "sudden_shock", 12).run()
        self.assertEqual(result.post_disturbance_survival, 0.0)

    def test_fixed_policy_matches_resource_band(self) -> None:
        simulator = EcosystemSimulator(Parameters(), "fixed_only", "stationary", 11)
        agent = simulator.agents[0]
        self.assertEqual(simulator._choose_action(agent, ("low", "high", "stable")), "rest")
        self.assertEqual(simulator._choose_action(agent, ("medium", "high", "stable")), "conservative")
        self.assertEqual(simulator._choose_action(agent, ("high", "high", "stable")), "moderate")


if __name__ == "__main__":
    unittest.main()
