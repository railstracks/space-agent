"""Entity system — base classes and lifecycle hooks for game entities.

Every object that participates in turn resolution is an Entity. Entities
register hook methods that the turn resolver calls in order. Each entity
type overrides the hooks it cares about.

Hook lifecycle per turn:
  on_production()  — generate/consume resources
  on_intelligence() — gather data, update sensors
  on_decision()    — process queued orders (for autonomous entities)
  on_resolution()  — apply physics, propagate effects, check for events

The turn resolver doesn't know what entities *are*. It just calls hooks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from space_agent.simulation.resources import Stockpile
    from space_agent.game.turn import TurnContext


class EntityType(Enum):
    """Top-level entity categories."""
    BUILDING = "building"
    DRONE = "drone"
    COLONY = "colony"
    PLANET = "planet"


class EntityStatus(Enum):
    """Common statuses across all entity types."""
    ACTIVE = "active"
    IDLE = "idle"
    BUILDING = "building"
    DEPLOYING = "deploying"
    DAMAGED = "damaged"
    DISABLED = "disabled"
    DESTROYED = "destroyed"
    LOST = "lost"


@dataclass
class EntityReport:
    """Result from a single hook call on a single entity."""
    entity_id: str
    entity_type: str
    hook: str
    success: bool = True
    messages: list[str] = field(default_factory=list)
    produced: dict[str, float] = field(default_factory=dict)
    consumed: dict[str, float] = field(default_factory=dict)
    events: list[dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "hook": self.hook,
            "success": self.success,
            "messages": self.messages,
            "produced": self.produced,
            "consumed": self.consumed,
            "events": self.events,
        }


class Entity(ABC):
    """Base class for all game entities.

    Entities are the atomic units of the simulation. Each one owns
    its own state and behavior. The turn resolver calls hooks in order;
    entities respond as appropriate.
    """

    def __init__(
        self,
        entity_id: str,
        entity_type: EntityType,
        name: str,
        status: EntityStatus = EntityStatus.ACTIVE,
        location: str = "",
    ):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.name = name
        self.status = status
        self.location = location

    # ── Lifecycle hooks ─────────────────────────────────────────────

    def on_production(self, ctx: TurnContext) -> EntityReport:
        """Hook: resource production and consumption."""
        return EntityReport(
            entity_id=self.entity_id,
            entity_type=self.entity_type.value,
            hook="production",
        )

    def on_intelligence(self, ctx: TurnContext) -> EntityReport:
        """Hook: sensor data gathering, telemetry updates."""
        return EntityReport(
            entity_id=self.entity_id,
            entity_type=self.entity_type.value,
            hook="intelligence",
        )

    def on_decision(self, ctx: TurnContext) -> EntityReport:
        """Hook: process queued orders or autonomous behavior."""
        return EntityReport(
            entity_id=self.entity_id,
            entity_type=self.entity_type.value,
            hook="decision",
        )

    def on_resolution(self, ctx: TurnContext) -> EntityReport:
        """Hook: physics propagation, event checking."""
        return EntityReport(
            entity_id=self.entity_id,
            entity_type=self.entity_type.value,
            hook="resolution",
        )

    # ── Serialization ───────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize entity to dict. Subclasses override to add fields."""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "status": self.status.value,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Entity:
        """Deserialize entity. Dispatches to correct subclass."""
        # Will be overridden by registry
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.entity_id} ({self.status.value})>"


# ── Entity Registry ─────────────────────────────────────────────────
# Maps entity_type values to their classes for deserialization.

_ENTITY_CLASSES: dict[str, type[Entity]] = {}


def register_entity(cls: type[Entity]) -> type[Entity]:
    """Decorator to register an entity class for deserialization."""
    key = cls.__name__
    _ENTITY_CLASSES[key] = cls
    return cls


def deserialize_entity(d: dict) -> Entity:
    """Deserialize a dict into the correct Entity subclass."""
    class_key = d.get("_class", d.get("entity_type", ""))
    cls = _ENTITY_CLASSES.get(class_key)
    if cls is None:
        # Fallback: try to match by entity_type enum
        raise ValueError(f"Unknown entity class: {class_key}")
    return cls.from_dict(d)
