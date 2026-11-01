"""Experiment B2-C: Demographic Rules and Metabolic Subsidies.

Objective:
Test whether free newborn energy and automatic vacancy replacement artificially maintain
population size and harvesting pressure during resource depletion.

Variants:
- C0: Baseline demographic rules (E0=10.0, exogenous endowment, replacement every 20 steps).
- C1: Newborn energy reduced from 10 to 2 (E0=2.0, lasts 10 steps without harvest).
- C2: Newborn energy reduced from 10 to 0 (E0=0.0).
      Execution rule: Newborn enters at step replacement. In the next step, it takes an action.
      Harvest is allocated, reward added, maintenance deducted. If harvest <= maintenance,
      energy remains <= 0 and agent dies on its first active step.
- C3: Parent-funded newborn energy:
      To reproduce, a parent candidate must have energy >= endowment (10.0 units).
      Upon selecting a parent, 10.0 energy is deducted from the parent (parent.energy -= 10.0).
      If no candidate parent has energy >= 10.0, the vacancy cannot be funded and remains unfilled.
- C4: Delayed vacancy replacement (doubled replacement interval from 20 to 40 steps, testing
      the effect of delaying scheduled replenishment on population and resource trajectory).

Controls:
- Version B logistic resource model G(R) = g * R * (1 - R/K) with g=0.10.
- Baseline net-energy reward: r_t = Delta E_t.
- Unchanged agent policies, state space, learning rate, and discount factor.
- Same 10 calibration seeds (1 to 10) x 3 groups (fixed_only, q_only, evolving_joint) x 2,000 steps.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Add simulator_v2 to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parameters import Parameters
from simulator import ACTIONS, Agent, AgentType, HARVEST_REQUEST, EcosystemSimulator, Group, StepRecord

OUTPUT_DIR = Path(__file__).parent.parent.parent / "results_v2" / "b2c_demographic_rules"


class DemographicSimulator(EcosystemSimulator):
    def __init__(
        self,
        parameters: Parameters,
        group: Group,
        scenario: str,
        seed: int,
        variant: str = "C0",
    ) -> None:
        super().__init__(parameters, group, scenario, seed)  # type: ignore[arg-type]
        self.variant = variant
        self.unfunded_vacancies = 0
        self.births = 0
        self.deaths = 0

    def _new_agent_with_energy(self, kind: AgentType, energy: float) -> Agent:
        agent = Agent(self.next_identifier, kind, energy)
        self.next_identifier += 1
        return agent

    def _replace_vacancies(self, step_number: int = 0) -> None:
        parent_candidates = self.agents.copy()
        # Retire agents reaching maximum age
        living_after_retire = [agent for agent in self.agents if agent.age < self.parameters.maximum_age]
        retirees_count = len(self.agents) - len(living_after_retire)
        self.deaths += retirees_count  # Retirement counted in natural turnover
        self.agents = living_after_retire
        vacancies = self.parameters.population_capacity - len(self.agents)

        logs: dict[int, dict[str, object]] = {}
        if self.group in ("static_mixture", "evolving_joint", "evolving_survival", "evolving_reward") and vacancies > 0:
            event_rows = self._log_replacement_candidates(step_number, parent_candidates)
            self.replacement_events.extend(event_rows)
            logs = {int(row["agent_id"]): row for row in event_rows}

        # Determine newborn initial energy
        if self.variant == "C0":
            newborn_energy = 10.0
        elif self.variant == "C1":
            newborn_energy = 2.0
        elif self.variant == "C2":
            newborn_energy = 0.0
        elif self.variant == "C3":
            newborn_energy = 10.0  # Funded by parent
        elif self.variant == "C4":
            newborn_energy = 10.0
        else:
            newborn_energy = 10.0

        for _ in range(vacancies):
            if not parent_candidates:
                break

            # Variant C3: Parent must have at least 10.0 energy to fund newborn
            if self.variant == "C3":
                eligible_parents = [p for p in parent_candidates if p.energy >= 10.0]
                if not eligible_parents:
                    self.unfunded_vacancies += 1
                    continue
                # Use eligible parents for selection
                current_candidates = eligible_parents
            else:
                current_candidates = parent_candidates

            if self.group == "fixed_only":
                kind: AgentType = "fixed"
                parent = self.random.choice(current_candidates)
            elif self.group == "q_only":
                kind = "q_learning"
                parent = self.random.choice(current_candidates)
            elif self.group == "static_mixture":
                kind = self._choose_static_kind()
                cands = [agent for agent in current_candidates if agent.kind == kind]
                if not cands:
                    self.founder_injections += 1
                    parent = None
                else:
                    parent = self.random.choice(cands)
            else:
                parent = self._weighted_parent(current_candidates, self.group)
                kind = parent.kind

            if parent is not None and self.variant == "C3":
                parent.energy -= 10.0

            if parent is not None and parent.identifier in logs:
                logs[parent.identifier]["offspring_selected"] += 1  # type: ignore[operator]

            newborn = self._new_agent_with_energy(kind, newborn_energy)
            self.agents.append(newborn)
            self.replacements += 1
            self.births += 1

    def step(self, step_number: int) -> None:
        if not self.agents:
            return

        if self.scenario == "sudden_shock" and step_number == self.parameters.shock_step:
            pre_window = self.records[-100:]
            if pre_window:
                self.pre_shock_mean_reward = sum(record.mean_reward or 0.0 for record in pre_window) / len(pre_window)
            self.resource *= 0.5
            self.pre_shock_living_population = len(self.agents)

        start_resource = self.resource
        decisions: dict[int, tuple[tuple[str, str, str], str]] = {}
        action_counts: dict[str, int] = {a: 0 for a in ACTIONS}
        q_action_counts: dict[str, int] = {a: 0 for a in ACTIONS}
        fixed_action_counts: dict[str, int] = {a: 0 for a in ACTIONS}

        for agent in self.agents:
            state = self._state(agent, start_resource, self.previous_start_resource)
            act = self._choose_action(agent, state)
            decisions[agent.identifier] = (state, act)
            action_counts[act] += 1
            if agent.kind == "q_learning":
                q_action_counts[act] += 1
            else:
                fixed_action_counts[act] += 1

        allocation_order = self.agents.copy()
        self.random.shuffle(allocation_order)
        remaining = self.resource
        harvested: dict[int, float] = {}
        for agent in allocation_order:
            requested = HARVEST_REQUEST[decisions[agent.identifier][1]]
            amount = min(requested, remaining)
            harvested[agent.identifier] = amount
            remaining -= amount

        rewards: dict[int, float] = {}
        for agent in self.agents:
            reward = harvested[agent.identifier] - self.parameters.maintenance_cost
            rewards[agent.identifier] = reward
            agent.energy = min(self.parameters.maximum_energy, agent.energy + reward)
            agent.lifetime_reward += reward
            agent.age += 1

        # Energy gate: agents with energy <= 0 die
        living = [agent for agent in self.agents if agent.energy > 0]
        step_deaths = len(self.agents) - len(living)
        self.deaths += step_deaths

        # Logistic Resource Regeneration
        K = self.parameters.resource_capacity
        g = self.regeneration_rate(step_number)
        growth = g * remaining * (1.0 - remaining / K)
        self.resource = min(K, max(0.0, remaining + growth))

        for agent in self.agents:
            state, action = decisions[agent.identifier]
            next_state = self._state(agent, self.resource, start_resource) if agent in living else None
            self._update_q_value(agent, state, action, rewards[agent.identifier], next_state)
        self.agents = living
        self.previous_start_resource = start_resource

        if self.scenario == "sudden_shock" and step_number == self.parameters.shock_step:
            denominator = self.pre_shock_living_population or 0
            self.immediate_post_shock_survival = len(self.agents) / denominator if denominator else 0.0

        # Replacement timing:
        # Variant C4 delays replacement to interval=40 steps; all others use interval=20 steps
        rep_interval = 40 if self.variant == "C4" else self.parameters.replacement_interval
        if step_number % rep_interval == 0 and self.agents:
            self._replace_vacancies(step_number)

        mean_reward = sum(rewards[agent.identifier] for agent in living) / len(living) if living else None
        mean_energy = sum(agent.energy for agent in self.agents) / len(self.agents) if self.agents else None
        q_share = sum(agent.kind == "q_learning" for agent in self.agents) / len(self.agents) if self.agents else None
        self.records.append(
            StepRecord(
                step_number,
                self.resource,
                sum(harvested.values()),
                len(self.agents),
                q_share,
                mean_reward,
                mean_energy,
                action_counts=action_counts,
                q_action_counts=q_action_counts,
                fixed_action_counts=fixed_action_counts,
            )
        )


def run_variant(variant_name: str) -> list[dict[str, object]]:
    parameters = Parameters(baseline_regeneration=0.10)
    groups: tuple[Group, ...] = ("fixed_only", "q_only", "evolving_joint")
    seeds = tuple(range(1, 11))

    summaries: list[dict[str, object]] = []
    records: list[dict[str, object]] = []

    print(f"\n==========================================")
    print(f"Running Experiment B2-C Variant: {variant_name} (10 seeds x 3 groups)")
    print(f"==========================================")

    for group in groups:
        for seed in seeds:
            sim = DemographicSimulator(parameters, group, "stationary", seed, variant=variant_name)
            result = sim.run()
            s_dict = result.summary()
            s_dict["variant"] = variant_name
            s_dict["births"] = sim.births
            s_dict["deaths"] = sim.deaths
            s_dict["unfunded_vacancies"] = sim.unfunded_vacancies
            s_dict["final_living"] = len(sim.agents)
            summaries.append(s_dict)

            for rec in result.records:
                records.append({
                    "variant": variant_name,
                    "seed": seed,
                    "group": group,
                    "step": rec.step,
                    "resource": rec.resource,
                    "total_harvest": rec.total_harvest,
                    "living_population": rec.living_population,
                    "q_share": rec.q_learning_share,
                    "mean_reward": rec.mean_reward,
                    "mean_energy": rec.mean_energy,
                })

    with (OUTPUT_DIR / f"{variant_name}_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    with (OUTPUT_DIR / f"{variant_name}_timeseries.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    # Print summary table for this variant
    for group in groups:
        g_sums = [s for s in summaries if s["group"] == group]
        mean_res = sum(float(s["mean_resource"]) for s in g_sums) / len(g_sums)
        mean_pop = sum(float(s["final_living"]) for s in g_sums) / len(g_sums)
        extinctions = sum(s["extinct"] for s in g_sums)
        g_recs = [r for r in records if r["group"] == group]
        in_band = sum(25.0 <= float(r["resource"]) <= 475.0 for r in g_recs) / len(g_recs) * 100
        empty = sum(float(r["resource"]) == 0.0 for r in g_recs) / len(g_recs) * 100
        print(f"  {group:15s} | Mean Res: {mean_res:6.2f} | In Band: {in_band:5.1f}% | Empty: {empty:5.1f}% | Final Pop: {mean_pop:4.1f} | Extinctions: {extinctions}/10")

    return summaries


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for v in ("C0", "C1", "C2", "C3", "C4"):
        run_variant(v)


if __name__ == "__main__":
    main()
