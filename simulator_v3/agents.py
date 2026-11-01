"""Agent definitions and policies for Version C."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Literal

AgentType = Literal["fixed", "q_learning"]
ACTIONS = ("rest", "conservative", "moderate", "aggressive")
HARVEST_REQUEST = {
    "rest": 0.0,
    "conservative": 0.5,
    "moderate": 1.0,
    "aggressive": 2.0,
}


@dataclass
class Agent:
    identifier: int
    kind: AgentType
    energy: float
    age: int = 0
    lifetime_reward: float = 0.0
    born_step: int = 0
    q_table: dict[tuple[str, str, str], list[float]] = field(default_factory=dict)

    def epsilon(self, maximum_age: int, epsilon_start: float, epsilon_minimum: float) -> float:
        fraction = min(self.age, maximum_age) / maximum_age
        return epsilon_start + fraction * (epsilon_minimum - epsilon_start)

    def choose_action(
        self,
        state: tuple[str, str, str],
        random_gen: Random,
        maximum_age: int,
        epsilon_start: float,
        epsilon_minimum: float,
    ) -> str:
        if self.kind == "fixed":
            resource_band = state[0]
            return {"low": "rest", "medium": "conservative", "high": "moderate"}[resource_band]

        values = self.q_table.setdefault(state, [0.0] * len(ACTIONS))
        if random_gen.random() < self.epsilon(maximum_age, epsilon_start, epsilon_minimum):
            return random_gen.choice(ACTIONS)
        maximum = max(values)
        best = [index for index, value in enumerate(values) if value == maximum]
        return ACTIONS[random_gen.choice(best)]

    def update_q_value(
        self,
        state: tuple[str, str, str],
        action: str,
        reward: float,
        next_state: tuple[str, str, str] | None,
        learning_rate: float,
        discount_factor: float,
    ) -> None:
        if self.kind != "q_learning":
            return
        action_index = ACTIONS.index(action)
        values = self.q_table.setdefault(state, [0.0] * len(ACTIONS))
        future = 0.0 if next_state is None else max(self.q_table.setdefault(next_state, [0.0] * len(ACTIONS)))
        target = reward + discount_factor * future
        values[action_index] += learning_rate * (target - values[action_index])

