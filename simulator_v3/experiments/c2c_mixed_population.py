"""Experiment C2-C: Mixed-Population Mechanism.

Compositions evaluated under population capacity N=50:
- C-100F: 50 Fixed (100.0%) / 0 Q (0.0%) — Frozen control from Stage 1.
- C-76F: 38 Fixed (76.0%) / 12 Q (24.0%).
- C-50F: 25 Fixed (50.0%) / 25 Q (50.0%).
- C-24F: 12 Fixed (24.0%) / 38 Q (76.0%).
- C-0F: 0 Fixed (0.0%) / 50 Q (100.0%) — Frozen control from Stage 1.

Reproduction rules:
Static composition target: vacancies are replaced by parent of the deficit type.
Parent must have energy > 10.0; parent funds 10.0 energy to newborn.
If no eligible parent of the deficit type exists, vacancy remains unfilled (unfunded).
Tracks actual living composition, type-specific energies, and extinction steps.
Uses separate random number streams: stream_env for allocation/parent sampling, stream_agents for policy.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from random import Random

# Add simulator_v3 to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import ACTIONS, HARVEST_REQUEST, Agent, AgentType
from energy_accounting import EnergyLedger
from parameters import Parameters
from reproduction import ReproductionLog
from simulator import EcosystemSimulator, StepRecord

OUTPUT_DIR = Path(__file__).parent.parent.parent / "results_v3" / "stage2_mechanism" / "c2c_mixtures"
SEEDS = tuple(range(1001, 1011))


class StaticMixtureSimulator(EcosystemSimulator):
    def __init__(
        self,
        parameters: Parameters,
        scenario: str,
        seed: int,
        fixed_target: int = 25,
        treatment_name: str = "C-50F",
    ) -> None:
        self.treatment_name = treatment_name
        self.fixed_target = fixed_target
        self.q_target = parameters.population_capacity - fixed_target
        self.stream_env = Random(seed * 1000 + 1)
        self.stream_agents = Random(seed * 1000 + 2)
        super().__init__(parameters, "static_mixture", scenario, seed)  # type: ignore[arg-type]

    def _initialize_population(self) -> None:
        self.agents = []
        for _ in range(self.fixed_target):
            self.agents.append(
                Agent(
                    identifier=self._get_next_identifier(),
                    kind="fixed",
                    energy=self.parameters.initial_founder_energy,
                    age=0,
                    lifetime_reward=0.0,
                    born_step=0,
                )
            )
        for _ in range(self.q_target):
            self.agents.append(
                Agent(
                    identifier=self._get_next_identifier(),
                    kind="q_learning",
                    energy=self.parameters.initial_founder_energy,
                    age=0,
                    lifetime_reward=0.0,
                    born_step=0,
                )
            )

    def _replace_static_vacancies(self, step_number: int) -> tuple[int, int]:
        parent_candidates = self.agents.copy()
        non_retirees = [a for a in self.agents if a.age < self.parameters.maximum_age]
        retirees = [a for a in self.agents if a.age >= self.parameters.maximum_age]
        step_retirements = len(retirees)
        self.total_retirement_deaths += step_retirements

        total_vacancies = self.parameters.population_capacity - len(non_retirees)
        newborns: list[Agent] = []
        step_unfunded = 0

        if total_vacancies > 0 and parent_candidates:
            # Current counts among non-retirees to evaluate deficits
            fixed_count = sum(a.kind == "fixed" for a in non_retirees)
            q_count = sum(a.kind == "q_learning" for a in non_retirees)

            for _ in range(total_vacancies):
                fixed_deficit = max(0, self.fixed_target - fixed_count)
                q_deficit = max(0, self.q_target - q_count)

                if fixed_deficit > 0 and q_deficit > 0:
                    chosen_kind = self.stream_env.choices(
                        ["fixed", "q_learning"], weights=[fixed_deficit, q_deficit], k=1
                    )[0]
                elif fixed_deficit > 0:
                    chosen_kind = "fixed"
                elif q_deficit > 0:
                    chosen_kind = "q_learning"
                else:
                    chosen_kind = self.stream_env.choice(["fixed", "q_learning"])

                # Eligible parents of chosen kind
                eligible = [
                    a for a in parent_candidates
                    if a.kind == chosen_kind and a.energy > self.parameters.reproduction_cost
                ]

                if not eligible:
                    step_unfunded += 1
                    self.reproduction_logs.append(
                        ReproductionLog(
                            step=step_number,
                            parent_id=None,
                            parent_type=chosen_kind,  # type: ignore[arg-type]
                            parent_energy_before=None,
                            energy_transferred=0.0,
                            parent_energy_after=None,
                            newborn_id=None,
                            newborn_type=None,
                            success=False,
                            failure_reason=f"No {chosen_kind} parent has energy > 10.0",
                        )
                    )
                    continue

                parent = self.stream_env.choice(eligible)
                e_before = parent.energy
                parent.energy -= self.parameters.reproduction_cost

                nb = Agent(
                    identifier=self._get_next_identifier(),
                    kind=parent.kind,
                    energy=self.parameters.reproduction_cost,
                    age=0,
                    lifetime_reward=0.0,
                    born_step=step_number,
                    q_table={},
                )
                newborns.append(nb)
                if chosen_kind == "fixed":
                    fixed_count += 1
                else:
                    q_count += 1

                self.reproduction_logs.append(
                    ReproductionLog(
                        step=step_number,
                        parent_id=parent.identifier,
                        parent_type=parent.kind,
                        parent_energy_before=e_before,
                        energy_transferred=self.parameters.reproduction_cost,
                        parent_energy_after=parent.energy,
                        newborn_id=nb.identifier,
                        newborn_type=nb.kind,
                        success=True,
                    )
                )

        for r in retirees:
            self.energy_ledger.cumulative_retirement_losses += r.energy

        self.agents = non_retirees + newborns
        return len(newborns), step_unfunded

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
                self.parameters.epsilon_start,
                self.parameters.epsilon_minimum,
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
        if step_number % self.parameters.replacement_interval == 0 and self.agents:
            step_births, step_unfunded = self._replace_static_vacancies(step_number)
            self.total_births += step_births
            self.total_unfunded_vacancies += step_unfunded

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
                self.parameters.learning_rate,
                self.parameters.discount_factor,
            )

        self.previous_start_resource = start_resource

        living_count = len(self.agents)
        fixed_count = sum(a.kind == "fixed" for a in self.agents)
        q_count = living_count - fixed_count
        q_share = (q_count / living_count) if living_count > 0 else None
        fixed_share = (fixed_count / living_count) if living_count > 0 else None

        fixed_energies = [a.energy for a in self.agents if a.kind == "fixed"]
        q_energies = [a.energy for a in self.agents if a.kind == "q_learning"]
        mean_fixed_e = (sum(fixed_energies) / len(fixed_energies)) if fixed_energies else None
        mean_q_e = (sum(q_energies) / len(q_energies)) if q_energies else None

        mean_reward = (
            sum(rewards[a.identifier] for a in survivors_of_starvation) / len(survivors_of_starvation)
            if survivors_of_starvation
            else None
        )
        mean_energy = sum(a.energy for a in self.agents) / living_count if living_count > 0 else None

        rec = StepRecord(
            step=step_number,
            resource=self.resource,
            total_harvest=total_step_harvest,
            living_population=living_count,
            q_learning_share=q_share,
            mean_reward=mean_reward,
            mean_energy=mean_energy,
            births=step_births,
            starvation_deaths=step_starvations,
            retirement_deaths=0,
            unfunded_vacancies=step_unfunded,
            action_counts=action_counts,
            q_action_counts=q_action_counts,
            fixed_action_counts=fixed_action_counts,
        )
        # Store extra mixed-population attributes
        rec.fixed_count = fixed_count  # type: ignore[attr-defined]
        rec.q_count = q_count  # type: ignore[attr-defined]
        rec.mean_fixed_energy = mean_fixed_e  # type: ignore[attr-defined]
        rec.mean_q_energy = mean_q_e  # type: ignore[attr-defined]
        self.records.append(rec)


def run_mixture_batch(treatment: str, fixed_target: int) -> None:
    pct_f = (fixed_target / 50) * 100
    pct_q = 100 - pct_f
    print(f"\n==========================================")
    print(f"Running Experiment C2-C Treatment: {treatment} ({fixed_target} Fixed [{pct_f:.1f}%] / {50-fixed_target} Q [{pct_q:.1f}%])")
    print(f"==========================================")
    params = Parameters()
    summaries = []
    timeseries = []

    for seed in SEEDS:
        sim = StaticMixtureSimulator(
            params,
            "stationary",
            seed,
            fixed_target=fixed_target,
            treatment_name=treatment,
        )
        res = sim.run()

        living_energy = sum(a.energy for a in sim.agents)
        is_conserved, disc = sim.energy_ledger.verify_energy_balance(living_energy)

        t_first_25 = next((r.step for r in res.records if r.resource < 25.0), None)
        t_first_1 = next((r.step for r in res.records if r.resource < 1.0), None)
        res_at_first_unfunded = next((r.resource for r in res.records if r.unfunded_vacancies > 0), None)

        s_dict = res.summary()
        s_dict["treatment"] = treatment
        s_dict["fixed_target"] = fixed_target
        s_dict["q_target"] = 50 - fixed_target
        s_dict["living_at_end"] = len(sim.agents)
        s_dict["final_fixed_count"] = sum(a.kind == "fixed" for a in sim.agents)
        s_dict["final_q_count"] = sum(a.kind == "q_learning" for a in sim.agents)
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
                "fixed_count": getattr(rec, "fixed_count", 0),
                "q_count": getattr(rec, "q_count", 0),
                "q_share": rec.q_learning_share,
                "mean_reward": rec.mean_reward,
                "mean_energy": rec.mean_energy,
                "mean_fixed_energy": getattr(rec, "mean_fixed_energy", None),
                "mean_q_energy": getattr(rec, "mean_q_energy", None),
                "births": rec.births,
                "starvation_deaths": rec.starvation_deaths,
                "retirement_deaths": rec.retirement_deaths,
                "unfunded_vacancies": rec.unfunded_vacancies,
            })

        print(f"  [{treatment} | Seed {seed}] steps={res.steps_completed:4d}, extinct={res.extinct}, final_pop={len(sim.agents):2d} (F={s_dict['final_fixed_count']}, Q={s_dict['final_q_count']}), mean_res={res.mean_resource:5.2f}, disc={disc:.2e}, conserved={is_conserved}")

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
    # C-76F: 38 Fixed (76%) / 12 Q (24%)
    run_mixture_batch("C-76F", fixed_target=38)
    # C-50F: 25 Fixed (50%) / 25 Q (50%)
    run_mixture_batch("C-50F", fixed_target=25)
    # C-24F: 12 Fixed (24%) / 38 Q (76%)
    run_mixture_batch("C-24F", fixed_target=12)
    print(f"\nExperiment C2-C complete. Outputs saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
