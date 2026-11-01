"""Agent definitions, action spaces, and Q-table inheritance policies for Version D."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Literal

AgentType = Literal["fixed", "q_learning"]
ACTIONS = ("rest", "conservative", "moderate", "aggressive")

# 50% harvest-quota treatment (calibrated in Stage 3B as Treatment B)
HARVEST_REQUEST = {
    "rest": 0.0,
    "conservative": 0.25,
    "moderate": 0.5,
    "aggressive": 1.0,
}


@dataclass
class Agent:
    identifier: int
    kind: AgentType
    energy: float
    age: int = 0
    lifetime_reward: float = 0.0
    born_step: int = 0
    reproduction_cooldown: int = 0
    q_own: dict[tuple[str, str, str], list[float]] = field(default_factory=dict)
    q_parent: dict[tuple[str, str, str], list[float]] | None = None
    skip_cooldown_decrement: bool = False
    skip_age_increment: bool = False

    def inheritance_lambda(self, inheritance_duration: int = 12) -> float:
        """Computes parental influence weight lambda_t in [0.0, 1.0]."""
        if self.q_parent is None:
            return 0.0
        lam = 1.0 - min(self.age, inheritance_duration) / float(inheritance_duration)
        return max(0.0, min(1.0, lam))

    def get_active_q(
        self, state: tuple[str, str, str], inheritance_duration: int = 12
    ) -> list[float]:
        """
        Returns blended Q-values:
        Q_active(s, a) = (1 - lambda_t) * Q_own(s, a) + lambda_t * Q_parent(s, a)
        """
        own_values = self.q_own.setdefault(state, [0.0] * len(ACTIONS))
        lam = self.inheritance_lambda(inheritance_duration)
        if lam <= 0.0 or self.q_parent is None:
            return list(own_values)
        parent_values = self.q_parent.get(state, [0.0] * len(ACTIONS))
        return [
            (1.0 - lam) * o + lam * p for o, p in zip(own_values, parent_values)
        ]

    def epsilon(
        self, maximum_age: int, epsilon_start: float, epsilon_minimum: float
    ) -> float:
        fraction = min(self.age, maximum_age) / float(maximum_age)
        return epsilon_start + fraction * (epsilon_minimum - epsilon_start)

    def choose_action(
        self,
        state: tuple[str, str, str],
        random_gen: Random,
        maximum_age: int,
        epsilon_start: float,
        epsilon_minimum: float,
        inheritance_duration: int = 12,
    ) -> str:
        if self.kind == "fixed":
            resource_band = state[0]
            return {
                "low": "rest",
                "medium": "conservative",
                "high": "moderate",
            }[resource_band]

        if random_gen.random() < self.epsilon(
            maximum_age, epsilon_start, epsilon_minimum
        ):
            return random_gen.choice(ACTIONS)

        active_values = self.get_active_q(state, inheritance_duration)
        maximum = max(active_values)
        best = [index for index, value in enumerate(active_values) if value == maximum]
        return ACTIONS[random_gen.choice(best)]

    def update_q_value(
        self,
        state: tuple[str, str, str],
        action: str,
        reward: float,
        next_state: tuple[str, str, str] | None,
        learning_rate: float,
        discount_factor: float,
        inheritance_duration: int = 12,
    ) -> None:
        if self.kind != "q_learning":
            return
        action_index = ACTIONS.index(action)
        own_values = self.q_own.setdefault(state, [0.0] * len(ACTIONS))

        if next_state is None:
            future = 0.0
        else:
            next_active = self.get_active_q(next_state, inheritance_duration)
            future = max(next_active)

        target = reward + discount_factor * future
        own_values[action_index] += learning_rate * (target - own_values[action_index])

    def get_q_snapshot(
        self, inheritance_duration: int = 12
    ) -> dict[tuple[str, str, str], list[float]]:
        """Captures an immutable snapshot of current active Q-values for offspring inheritance."""
        all_states = set(self.q_own.keys())
        if self.q_parent is not None:
            all_states.update(self.q_parent.keys())
        snapshot: dict[tuple[str, str, str], list[float]] = {}
        for s in all_states:
            snapshot[s] = list(self.get_active_q(s, inheritance_duration))
        return snapshot

