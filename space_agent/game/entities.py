"""Concrete entity types — buildings and drones as game entities.

Each entity type overrides the hooks it cares about. The turn resolver
calls hooks in order; entities respond as appropriate.

BuildingEntity  → fixed infrastructure on a planet surface
DroneEntity    → mobile unit in the swarm
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from space_agent.game.entity import (
    Entity, EntityType, EntityStatus, EntityReport,
    register_entity,
)
from space_agent.simulation.resources import (
    BuildingType, Recipe, RECIPES, Stockpile, Resource,
)
from space_agent.simulation.drones import (
    DroneType, DroneSpec, DRONE_SPECS, Drone,
)

if TYPE_CHECKING:
    from space_agent.game.turn import TurnContext


@register_entity
class BuildingEntity(Entity):
    """A fixed building on a planet surface.

    Buildings run recipes during the production phase. They consume
    inputs and energy from the colony stockpile and produce outputs.
    """

    def __init__(
        self,
        entity_id: str,
        name: str,
        building_type: BuildingType,
        planet: str,
        recipe: str = "",
        status: EntityStatus = EntityStatus.ACTIVE,
        turns_remaining: int = 0,
    ):
        super().__init__(
            entity_id=entity_id,
            entity_type=EntityType.BUILDING,
            name=name,
            status=status,
            location=planet,
        )
        self.building_type = building_type
        self.recipe = recipe
        self.turns_remaining = turns_remaining

    def on_production(self, ctx: TurnContext) -> EntityReport:
        report = EntityReport(
            entity_id=self.entity_id,
            entity_type="building",
            hook="production",
        )

        # Under construction — tick down
        if self.status == EntityStatus.BUILDING:
            self.turns_remaining -= 1
            if self.turns_remaining <= 0:
                self.status = EntityStatus.IDLE
                report.messages.append(f"{self.name} construction complete.")
            else:
                report.messages.append(f"{self.name} under construction ({self.turns_remaining} turns remaining).")
            return report

        # Not running
        if self.status not in (EntityStatus.ACTIVE, EntityStatus.IDLE):
            return report

        # No recipe assigned
        if not self.recipe:
            report.messages.append(f"{self.name} idle — no recipe assigned.")
            return report

        recipe = RECIPES.get(self.recipe)
        if not recipe:
            report.success = False
            report.messages.append(f"{self.name}: unknown recipe '{self.recipe}'")
            return report

        # Check energy
        if not ctx.consume_energy(recipe.energy_mw):
            report.success = False
            report.messages.append(f"{self.name} idle — insufficient energy (need {recipe.energy_mw} MW, {ctx.energy_remaining_mw:.0f} MW available).")
            return report

        # Check inputs (read from stockpile dict)
        stockpile = ctx.stockpile or {}
        for resource, amount in recipe.inputs.items():
            available = stockpile.get(resource.value, 0)
            if available < amount:
                report.success = False
                report.messages.append(f"{self.name} idle — insufficient {resource.value} (need {amount}, have {available:.1f}).")
                return report

        # Consume inputs
        for resource, amount in recipe.inputs.items():
            key = resource.value
            stockpile[key] = stockpile.get(key, 0) - amount
            report.consumed[key] = report.consumed.get(key, 0) + amount

        # Produce outputs
        for resource, amount in recipe.outputs.items():
            key = resource.value
            stockpile[key] = stockpile.get(key, 0) + amount
            report.produced[key] = report.produced.get(key, 0) + amount

        self.status = EntityStatus.ACTIVE
        report.messages.append(f"{self.name} running: {recipe.name}.")
        return report

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "_class": self.__class__.__name__,
            "building_type": self.building_type.value,
            "recipe": self.recipe,
            "turns_remaining": self.turns_remaining,
        })
        return d

    @classmethod
    def from_dict(cls, d: dict) -> BuildingEntity:
        return cls(
            entity_id=d["entity_id"],
            name=d["name"],
            building_type=BuildingType(d["building_type"]),
            planet=d["location"],
            recipe=d.get("recipe", ""),
            status=EntityStatus(d.get("status", "active")),
            turns_remaining=d.get("turns_remaining", 0),
        )


@register_entity
class DroneEntity(Entity):
    """A mobile drone in the swarm.

    Drones differ from buildings: they have fuel, can be deployed to
    locations, and may operate autonomously. Their hooks handle
    mission progression rather than production.
    """

    def __init__(
        self,
        entity_id: str,
        name: str,
        drone_type: DroneType,
        status: EntityStatus = EntityStatus.IDLE,
        location: str = "",
        mission: str = "",
        fuel_remaining: float = 0.0,
        cargo: Optional[dict] = None,
    ):
        super().__init__(
            entity_id=entity_id,
            entity_type=EntityType.DRONE,
            name=name,
            status=status,
            location=location,
        )
        self.drone_type = drone_type
        self.mission = mission
        self.fuel_remaining = fuel_remaining
        self.cargo = cargo or {}

    @property
    def spec(self) -> DroneSpec:
        return DRONE_SPECS[self.drone_type]

    def on_production(self, ctx: TurnContext) -> EntityReport:
        report = EntityReport(
            entity_id=self.entity_id,
            entity_type="drone",
            hook="production",
        )

        if self.status != EntityStatus.ACTIVE:
            return report

        # Drones that extract or process do so during production
        spec = self.spec

        # Asteroid miners produce ore
        if spec.mining_rate > 0 and "mining" in self.mission.lower():
            ore_type = self.mission_data.get("ore_type", "iron_ore")
            report.produced[ore_type] = spec.mining_rate
            report.messages.append(f"{self.name} mined {spec.mining_rate:.0f} {ore_type}.")

        # Orbital smelters process ore
        if spec.processing_rate > 0 and "smelting" in self.mission.lower():
            # Check if we have ore to process
            stockpile = ctx.stockpile or {}
            ore_available = stockpile.get("iron_ore", 0)
            to_process = min(spec.processing_rate, ore_available)
            if to_process > 0:
                stockpile["iron_ore"] = ore_available - to_process
                stockpile["refined_iron"] = stockpile.get("refined_iron", 0) + to_process * 0.8
                report.consumed["iron_ore"] = to_process
                report.produced["refined_iron"] = to_process * 0.8
                report.messages.append(f"{self.name} refined {to_process:.0f} iron ore → {to_process * 0.8:.0f} refined iron.")
            else:
                report.messages.append(f"{self.name} idle — no ore to process.")

        return report

    def on_intelligence(self, ctx: TurnContext) -> EntityReport:
        report = EntityReport(
            entity_id=self.entity_id,
            entity_type="drone",
            hook="intelligence",
        )

        if self.status != EntityStatus.ACTIVE:
            return report

        # Drones with survey capability gather data
        spec = self.spec
        if spec.survey_capability > 0 and "survey" in self.mission.lower():
            report.messages.append(
                f"{self.name} collected survey data at {self.location} "
                f"(quality: {spec.survey_capability:.0%})."
            )

        return report

    def on_resolution(self, ctx: TurnContext) -> EntityReport:
        report = EntityReport(
            entity_id=self.entity_id,
            entity_type="drone",
            hook="resolution",
        )

        if self.status != EntityStatus.ACTIVE:
            return report

        # Consume fuel
        spec = self.spec
        if spec.fuel_per_turn > 0:
            self.fuel_remaining -= spec.fuel_per_turn
            if self.fuel_remaining <= 0:
                self.fuel_remaining = 0
                self.status = EntityStatus.DISABLED
                report.messages.append(f"{self.name} has run out of fuel and is now disabled.")
                ctx.add_event("drone_disabled", f"{self.name} ran out of fuel at {self.location}.", source=self.entity_id)

        # Consume energy
        if spec.energy_per_turn_mw > 0:
            if not ctx.consume_energy(spec.energy_per_turn_mw):
                self.status = EntityStatus.DISABLED
                report.messages.append(f"{self.name} disabled — insufficient energy.")
                ctx.add_event("drone_disabled", f"{self.name} lost power at {self.location}.", source=self.entity_id)

        return report

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "_class": self.__class__.__name__,
            "drone_type": self.drone_type.value,
            "mission": self.mission,
            "fuel_remaining": self.fuel_remaining,
            "cargo": self.cargo,
        })
        return d

    @classmethod
    def from_dict(cls, d: dict) -> DroneEntity:
        return cls(
            entity_id=d["entity_id"],
            name=d["name"],
            drone_type=DroneType(d["drone_type"]),
            status=EntityStatus(d.get("status", "idle")),
            location=d.get("location", ""),
            mission=d.get("mission", ""),
            fuel_remaining=d.get("fuel_remaining", 0.0),
            cargo=d.get("cargo", {}),
        )


@register_entity
class DroneCarrierEntity(DroneEntity):
    """A drone carrier — mobile base that can carry and service drones.

    Overrides hooks to manage docked drones: refuels them, processes
    their cargo, and coordinates their deployment.
    """

    def __init__(
        self,
        entity_id: str,
        name: str,
        status: EntityStatus = EntityStatus.IDLE,
        location: str = "",
        mission: str = "",
        fuel_remaining: float = 0.0,
        cargo: Optional[dict] = None,
        docked_drones: Optional[list[str]] = None,
    ):
        super().__init__(
            entity_id=entity_id,
            name=name,
            drone_type=DroneType.DRONE_CARRIER,
            status=status,
            location=location,
            mission=mission,
            fuel_remaining=fuel_remaining,
            cargo=cargo or {},
        )
        self.docked_drones = docked_drones or []

    def on_production(self, ctx: TurnContext) -> EntityReport:
        report = EntityReport(
            entity_id=self.entity_id,
            entity_type="drone_carrier",
            hook="production",
        )

        if self.status != EntityStatus.ACTIVE:
            return report

        # Process cargo from docked drones
        # (In full implementation, would look up drone entities by ID
        # and transfer their cargo to the carrier's stockpile access)
        if self.docked_drones:
            report.messages.append(
                f"{self.name} servicing {len(self.docked_drones)} docked drones."
            )

        return report

    def on_intelligence(self, ctx: TurnContext) -> EntityReport:
        report = EntityReport(
            entity_id=self.entity_id,
            entity_type="drone_carrier",
            hook="intelligence",
        )

        if self.status != EntityStatus.ACTIVE:
            return report

        # Carrier aggregates sensor data from docked drones
        if self.docked_drones:
            report.messages.append(
                f"{self.name} coordinating data from {len(self.docked_drones)} drones "
                f"at {self.location}."
            )

        return report

    def on_resolution(self, ctx: TurnContext) -> EntityReport:
        report = super().on_resolution(ctx)

        # Refuel docked drones if we have fuel cells
        if self.status == EntityStatus.ACTIVE and self.docked_drones:
            report.messages.append(
                f"{self.name} refueling and resupplying docked drones."
            )

        return report

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["_class"] = self.__class__.__name__
        d["docked_drones"] = self.docked_drones
        return d

    @classmethod
    def from_dict(cls, d: dict) -> DroneCarrierEntity:
        return cls(
            entity_id=d["entity_id"],
            name=d["name"],
            status=EntityStatus(d.get("status", "idle")),
            location=d.get("location", ""),
            mission=d.get("mission", ""),
            fuel_remaining=d.get("fuel_remaining", 0.0),
            cargo=d.get("cargo", {}),
            docked_drones=d.get("docked_drones", []),
        )
