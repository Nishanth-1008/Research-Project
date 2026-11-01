"""Experiment B2-B: Reward Design with Resource Stewardship.

Objective:
Test whether augmenting the individual net-energy reward with a resource-stewardship component
enables Q-learning agents to learn sustainable harvesting policies without rendering them artificially inactive.

Formulation:
Control reward:
    r_base = harvested - maintenance = Delta E

Experimental reward:
We consider two controlled variants to compare against the baseline:
Variant 1 (Depletion penalty / Resource-proportional reward):
    r_steward = Delta E + w_r * (R_next / K)
    where w_r is a stewardship weight (e.g., w_r = 0.20, matching the scale of maintenance cost).
    When R is near capacity, agents receive a bonus (+0.20), offsetting maintenance and making conservation attractive.
    When R -> 0, bonus -> 0, so failing to conserve offers no ecological buffer.

Variant 2 (Exhaustion penalty when harvesting depleted pool):
    r_penalty = Delta E - penalty if (harvest_attempted and R_t < 0.05 K) else Delta E
    with penalty = 0.20 (penalizing extractive actions when the pool is in critical scarcity).

We implement both cleanly and evaluate them against the control across the identical 10 seeds and 3 groups.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Add simulator_v2 to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parameters import Parameters
from simulator import ACTIONS, HARVEST_REQUEST, EcosystemSimulator, Group, StepRecord

OUTPUT_DIR = Path(__file__).parent.parent.parent / "results_v2" / "b2b_reward_design"


class StewardshipRewardSimulator(EcosystemSimulator):
    def __init__(
        self,
        parameters: Parameters,
        group: Group,
        scenario: str,
        seed: int,
        reward_mode: str = "stewardship_proportional",  # "baseline", "stewardship_proportional", "scarcity_penalty"
        stewardship_weight: float = 0.20,
    ) -> None:
        super().__init__(parameters, group, scenario, seed)  # type: ignore[arg-type]
        self.reward_mode = reward_mode
        self.stewardship_weight = stewardship_weight

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

        # Energy update (always physical net energy)
        physical_energy_delta: dict[int, float] = {}
        for agent in self.agents:
            delta_e = harvested[agent.identifier] - self.parameters.maintenance_cost
            physical_energy_delta[agent.identifier] = delta_e
            agent.energy = min(self.parameters.maximum_energy, agent.energy + delta_e)
            agent.lifetime_reward += delta_e  # Physical lifetime reward for selection
            agent.age += 1

        living = [agent for agent in self.agents if agent.energy > 0]

        # Logistic Resource Regeneration
        K = self.parameters.resource_capacity
        g = self.regeneration_rate(step_number)
        growth = g * remaining * (1.0 - remaining / K)
        self.resource = min(K, max(0.0, remaining + growth))

        # RL Learning Rewards
        learning_rewards: dict[int, float] = {}
        for agent in self.agents:
            delta_e = physical_energy_delta[agent.identifier]
            action_taken = decisions[agent.identifier][1]

            if self.reward_mode == "baseline":
                r_learn = delta_e
            elif self.reward_mode == "stewardship_proportional":
                # r = delta_e + w * (R_next / K)
                r_learn = delta_e + self.stewardship_weight * (self.resource / K)
            elif self.reward_mode == "scarcity_penalty":
                # If harvesting when resource is in critical scarcity (< 0.05 K), penalize
                if action_taken != "rest" and (start_resource / K) < 0.05:
                    r_learn = delta_e - self.stewardship_weight
                else:
                    r_learn = delta_e
            else:
                r_learn = delta_e

            learning_rewards[agent.identifier] = r_learn
            state, action = decisions[agent.identifier]
            next_state = self._state(agent, self.resource, start_resource) if agent in living else None
            self._update_q_value(agent, state, action, r_learn, next_state)

        self.agents = living
        self.previous_start_resource = start_resource

        if self.scenario == "sudden_shock" and step_number == self.parameters.shock_step:
            denominator = self.pre_shock_living_population or 0
            self.immediate_post_shock_survival = len(self.agents) / denominator if denominator else 0.0

        if step_number % self.parameters.replacement_interval == 0 and self.agents:
            self._replace_vacancies(step_number)

        mean_reward = sum(physical_energy_delta[agent.identifier] for agent in living) / len(living) if living else None
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


def run_reward_variant(variant_name: str, mode: str, weight: float = 0.20) -> list[dict[str, object]]:
    parameters = Parameters(baseline_regeneration=0.10)
    groups: tuple[Group, ...] = ("fixed_only", "q_only", "evolving_joint")
    seeds = tuple(range(1, 11))

    summaries: list[dict[str, object]] = []
    records: list[dict[str, object]] = []

    print(f"\nRunning B2-B variant: {variant_name} (mode={mode}, weight={weight})...")
    for group in groups:
        for seed in seeds:
            sim = StewardshipRewardSimulator(
                parameters, group, "stationary", seed, reward_mode=mode, stewardship_weight=weight
            )
            result = sim.run()
            summary_dict = result.summary()
            summary_dict["variant"] = variant_name
            summaries.append(summary_dict)
            for record in result.records:
                records.append({
                    "variant": variant_name,
                    "seed": seed,
                    "group": group,
                    "step": record.step,
                    "resource": record.resource,
                    "total_harvest": record.total_harvest,
                    "living_population": record.living_population,
                    "q_share": record.q_learning_share,
                    "mean_reward": record.mean_reward,
                    "mean_energy": record.mean_energy,
                    "q_act_rest": record.q_action_counts.get("rest", 0),
                    "q_act_conservative": record.q_action_counts.get("conservative", 0),
                    "q_act_moderate": record.q_action_counts.get("moderate", 0),
                    "q_act_aggressive": record.q_action_counts.get("aggressive", 0),
                })

    with (OUTPUT_DIR / f"{variant_name}_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    with (OUTPUT_DIR / f"{variant_name}_timeseries.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    # Print summary
    for group in groups:
        g_sums = [s for s in summaries if s["group"] == group]
        mean_res = sum(float(s["mean_resource"]) for s in g_sums) / len(g_sums)
        g_recs = [r for r in records if r["group"] == group]
        in_band = sum(25.0 <= float(r["resource"]) <= 475.0 for r in g_recs) / len(g_recs) * 100
        empty = sum(float(r["resource"]) == 0.0 for r in g_recs) / len(g_recs) * 100
        print(f"  {group:15s} | Mean Res: {mean_res:6.2f} | In Band (5-95%): {in_band:5.1f}% | Empty: {empty:5.1f}%")

    return summaries


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Variant 1: Stewardship proportional bonus w=0.20
    run_reward_variant("v1_stewardship_proportional_w02", "stewardship_proportional", 0.20)
    # Variant 1b: Higher stewardship weight w=0.50
    run_reward_variant("v1b_stewardship_proportional_w05", "stewardship_proportional", 0.50)
    # Variant 2: Scarcity harvest penalty w=0.20
    run_reward_variant("v2_scarcity_penalty_w02", "scarcity_penalty", 0.20)


if __name__ == "__main__":
    main()

