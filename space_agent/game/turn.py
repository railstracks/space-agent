"""Turn context — the world state that entity hooks can access.

Entities don't reach into global state. They receive a TurnContext
that provides read/write access to exactly what they need. This keeps
entity behavior testable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from space_agent.simulation.resources import Stockpile
    from space_agent.simulation.drones import Drone
    from space_agent.simulation.planet import Planet


@dataclass
class TurnContext:
    """The world as seen by an entity during a turn.

    Provides access to game state that entity hooks need.
    Entities read from context and write their results to
    their own EntityReport, not directly to context.
    """
    turn: int = 0
    turn_period_years: float = 5.0
    seed: int = 0

    # Energy budget
    energy_available_mw: float = 0.0
    energy_consumed_mw: float = 0.0

    # The colony's stockpile (entities may read, but use report to declare consumption)
    stockpile: Optional[dict] = None  # Stockpile.to_dict()

    # Planets in system
    planets: list[dict] = field(default_factory=list)

    # Active drones in fleet
    drones: list[dict] = field(default_factory=list)

    # Colonies (planet designation → colony data)
    colonies: dict[str, dict] = field(default_factory=dict)

    # Accumulated reports this turn
    reports: list[dict] = field(default_factory=list)

    # Events that fired this turn
    events: list[dict] = field(default_factory=list)

    # Pending decisions (populated during decision phase)
    pending_decisions: list[dict] = field(default_factory=list)

    @property
    def energy_remaining_mw(self) -> float:
        return max(0.0, self.energy_available_mw - self.energy_consumed_mw)

    def consume_energy(self, mw: float) -> bool:
        """Try to consume energy. Returns True if enough available."""
        if mw <= self.energy_remaining_mw:
            self.energy_consumed_mw += mw
            return True
        return False

    def add_event(self, event_type: str, description: str, source: str = "", **details) -> None:
        self.events.append({
            "turn": self.turn,
            "type": event_type,
            "description": description,
            "source": source,
            **details,
        })

    def to_dict(self) -> dict:
        return {
            "turn": self.turn,
            "turn_period_years": self.turn_period_years,
            "energy_available_mw": self.energy_available_mw,
            "energy_consumed_mw": self.energy_consumed_mw,
            "energy_remaining_mw": self.energy_remaining_mw,
            "events": self.events,
        }
