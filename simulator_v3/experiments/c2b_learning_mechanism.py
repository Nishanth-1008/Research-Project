"""Experiment C2-B: Learning Mechanism.

Treatments compared against frozen baseline B0:
- B0: Baseline Q-learning (alpha=0.10, gamma=0.95, eps: 0.20 -> 0.02 over 100 lifetime steps). Frozen control.
- B1: Low Exploration Schedule: eps: 0.05 -> 0.01 over 100 lifetime steps.
- B2: Long Planning Horizon: gamma=0.99 (longer discount factor).
- B3: Accelerated Learning Rate: alpha=0.30 (faster Q-value updates during the early drawdown).

All runs are executed under q_only across the 10 matched seeds (1001-1010).
Uses separate random number streams (stream_env for allocation/parent sampling, stream_agents for policy).
Energy conservation, step-level diagnostics, and extinction metrics recorded.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from random import Random

# Add simulator_v3 to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import ACTIONS, HARVEST_REQUEST, Agent
from energy_accounting import EnergyLedger
from parameters import Parameters
from reproduction import perform_parent_funded_reproduction
from simulator import EcosystemSimulator, StepRecord

OUTPUT_DIR = Path(__file__).parent.parent.parent / "results_v3" / "stage2_mechanism" / "c2b_learning"
SEEDS = tuple(range(1001, 1011))


class LearningMechanismSimulator(EcosystemSimulator):
    def __init__(
        self,
        parameters: Parameters,
        group: str,
        scenario: str,
        seed: int,
        treatment: str = "B1",
        alpha: float = 0.10,
        gamma: float = 0.95,
        eps_start: float = 0.20,
        eps_min: float = 0.02,
    ) -> None:
        super().__init__(parameters, group, scenario, seed)  # type: ignore[arg-type]
        self.treatment = treatment
        self.learning_rate = alpha
        self.discount_factor = gamma
        self.epsilon_start = eps_start
        self.epsilon_minimum = eps_min

        self.stream_env = Random(seed * 1000 + 1)
        self.stream_agents = Random(seed * 1000 + 2)

    def step(self, step_number: int) -> None:
        if not self.agents:
            return

        if self.scenario == "sudden_shock" and step_number == self.parameters.shock_step:
            self.resource *= 0.5

        start_resource = self.resource
        decisions: dict[int, tuple[tuple[str, str, str], str]] = {}
        action_counts = {a: 0 for a in ACTIONS}
        q_action_counts = {a: 0 for a in ACTIONS}
        fixed_action_counts = {a: 0 for a in ACTIONS}

        for agent in self.agents:
            state = self._state(agent, start_resource, self.previous_start_resource)
            act = agent.choose_action(
                state,
                self.stream_agents,
                self.parameters.maximum_age,
                self.epsilon_start,
                self.epsilon_minimum,
            )
            decisions[agent.identifier] = (state, act)
            action_counts[act] += 1
            if agent.kind == "q_learning":
                q_action_counts[act] += 1
            else:
                fixed_action_counts[act] += 1

        allocation_order = self.agents.copy()
        self.stream_env.shuffle(allocation_order)
        remaining_resource = self.resource
        harvested: dict[int, float] = {}

        for agent in allocation_order:
            requested = HARVEST_REQUEST[decisions[agent.identifier][1]]
            allocated = min(requested, remaining_resource)
            harvested[agent.identifier] = allocated
            remaining_resource -= allocated

        total_step_harvest = sum(harvested.values())
        self.energy_ledger.cumulative_harvested += total_step_harvest

        rewards: dict[int, float] = {}
        for agent in self.agents:
            net_change = harvested[agent.identifier] - self.parameters.maintenance_cost
            rewards[agent.identifier] = net_change
            self.energy_ledger.cumulative_maintenance += self.parameters.maintenance_cost

            raw_energy = agent.energy + net_change
            if raw_energy > self.parameters.maximum_energy:
                excess = raw_energy - self.parameters.maximum_energy
                self.energy_ledger.cumulative_energy_cap_losses += excess
                agent.energy = self.parameters.maximum_energy
            else:
                agent.energy = raw_energy

            agent.lifetime_reward += net_change
            agent.age += 1

        survivors_of_starvation: list[Agent] = []
        step_starvations = 0
        for agent in self.agents:
            if agent.energy > 0:
                survivors_of_starvation.append(agent)
            else:
                step_starvations += 1
                if agent.energy < 0:
                    self.energy_ledger.cumulative_starvation_losses += agent.energy

        self.total_starvation_deaths += step_starvations
        self.agents = survivors_of_starvation

        step_births = 0
        step_unfunded = 0
        step_retirements = 0

        if step_number % self.parameters.replacement_interval == 0 and self.agents:
            parent_candidates = self.agents.copy()
            non_retirees = [a for a in self.agents if a.age < self.parameters.maximum_age]
            retirees = [a for a in self.agents if a.age >= self.parameters.maximum_age]
            step_retirements = len(retirees)
            self.total_retirement_deaths += step_retirements
            vacancies = self.parameters.population_capacity - len(non_retirees)

            newborns: list[Agent] = []
            if vacancies > 0 and parent_candidates:
                newborns, logs, unfunded = perform_parent_funded_reproduction(
                    living_agents=parent_candidates,
                    vacancies=vacancies,
                    step_number=step_number,
                    group=self.group,  # type: ignore[arg-type]
                    parameters=self.parameters,
                    random_gen=self.stream_env,
                    next_identifier_getter=self._get_next_identifier,
                )
                self.reproduction_logs.extend(logs)
                step_births = len(newborns)
                step_unfunded = unfunded
                self.total_births += step_births
                self.total_unfunded_vacancies += step_unfunded

            for r in retirees:
                self.energy_ledger.cumulative_retirement_losses += r.energy

            self.agents = non_retirees + newborns

        K = self.parameters.resource_capacity
        g = self.regeneration_rate(step_number)
        growth = g * remaining_resource * (1.0 - remaining_resource / K)
        self.resource = min(K, max(0.0, remaining_resource + growth))

        for agent in survivors_of_starvation:
            state, action = decisions[agent.identifier]
            next_state = self._state(agent, self.resource, start_resource)
            agent.update_q_value(
                state,
                action,
                rewards[agent.identifier],
                next_state,
                self.learning_rate,
                self.discount_factor,
            )

        self.previous_start_resource = start_resource

        living_count = len(self.agents)
        q_count = sum(a.kind == "q_learning" for a in self.agents)
        q_share = (q_count / living_count) if living_count > 0 else None
        mean_reward = (
            sum(rewards[a.identifier] for a in survivors_of_starvation) / len(survivors_of_starvation)
            if survivors_of_starvation
            else None
        )
        mean_energy = sum(a.energy for a in self.agents) / living_count if living_count > 0 else None

        self.records.append(
            StepRecord(
                step=step_number,
                resource=self.resource,
                total_harvest=total_step_harvest,
                living_population=living_count,
                q_learning_share=q_share,
                mean_reward=mean_reward,
                mean_energy=mean_energy,
                births=step_births,
                starvation_deaths=step_starvations,
                retirement_deaths=step_retirements,
                unfunded_vacancies=step_unfunded,
                action_counts=action_counts,
                q_action_counts=q_action_counts,
                fixed_action_counts=fixed_action_counts,
            )
        )


def run_learning_batch(treatment: str, alpha: float, gamma: float, eps_start: float, eps_min: float) -> None:
    print(f"\n==========================================")
    print(f"Running Experiment C2-B Treatment: {treatment} (alpha={alpha}, gamma={gamma}, eps={eps_start}->{eps_min})")
    print(f"==========================================")
    params = Parameters()
    summaries = []
    timeseries = []

    for seed in SEEDS:
        sim = LearningMechanismSimulator(
            params,
            "q_only",
            "stationary",
            seed,
            treatment=treatment,
            alpha=alpha,
            gamma=gamma,
            eps_start=eps_start,
            eps_min=eps_min,
        )
        res = sim.run()

        living_energy = sum(a.energy for a in sim.agents)
        is_conserved, disc = sim.energy_ledger.verify_energy_balance(living_energy)

        t_first_25 = next((r.step for r in res.records if r.resource < 25.0), None)
        t_first_1 = next((r.step for r in res.records if r.resource < 1.0), None)
        res_at_first_unfunded = next((r.resource for r in res.records if r.unfunded_vacancies > 0), None)

        s_dict = res.summary()
        s_dict["treatment"] = treatment
        s_dict["alpha"] = alpha
        s_dict["gamma"] = gamma
        s_dict["epsilon_start"] = eps_start
        s_dict["epsilon_minimum"] = eps_min
        s_dict["living_at_end"] = len(sim.agents)
        s_dict["time_to_first_R_below_25"] = t_first_25
        s_dict["time_to_first_R_below_1"] = t_first_1
        s_dict["resource_at_first_unfunded"] = res_at_first_unfunded
        s_dict["cumulative_harvested"] = sim.energy_ledger.cumulative_harvested
        s_dict["cumulative_maintenance"] = sim.energy_ledger.cumulative_maintenance
        s_dict["energy_conserved"] = is_conserved
        s_dict["energy_discrepancy"] = disc
        summaries.append(s_dict)

        for rec in res.records:
            timeseries.append({
                "treatment": treatment,
                "seed": seed,
                "step": rec.step,
                "resource": rec.resource,
                "total_harvest": rec.total_harvest,
                "living_population": rec.living_population,
                "mean_reward": rec.mean_reward,
                "mean_energy": rec.mean_energy,
                "births": rec.births,
                "starvation_deaths": rec.starvation_deaths,
                "retirement_deaths": rec.retirement_deaths,
                "unfunded_vacancies": rec.unfunded_vacancies,
                "q_act_rest": rec.q_action_counts.get("rest", 0),
                "q_act_conservative": rec.q_action_counts.get("conservative", 0),
                "q_act_moderate": rec.q_action_counts.get("moderate", 0),
                "q_act_aggressive": rec.q_action_counts.get("aggressive", 0),
            })

        print(f"  [{treatment} | Seed {seed}] steps={res.steps_completed:3d}, extinct={res.extinct}, mean_res={res.mean_resource:5.2f}, disc={disc:.2e}, conserved={is_conserved}")

    with (OUTPUT_DIR / f"{treatment}_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    with (OUTPUT_DIR / f"{treatment}_timeseries.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(timeseries[0].keys()))
        writer.writeheader()
        writer.writerows(timeseries)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # B1: Low exploration (0.05 -> 0.01)
    run_learning_batch("B1", alpha=0.10, gamma=0.95, eps_start=0.05, eps_min=0.01)
    # B2: Long planning horizon (gamma=0.99)
    run_learning_batch("B2", alpha=0.10, gamma=0.99, eps_start=0.20, eps_min=0.02)
    # B3: Accelerated learning rate (alpha=0.30)
    run_learning_batch("B3", alpha=0.30, gamma=0.95, eps_start=0.20, eps_min=0.02)
    print(f"\nExperiment C2-B complete. Outputs written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

