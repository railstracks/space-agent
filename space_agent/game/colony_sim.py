"""Colony simulation — energy and production per colony.

Each colony is a self-contained economic unit with its own buildings,
stockpile, and energy budget. Energy is computed from installed
buildings (solar arrays, nuclear reactors, geothermal taps) using
the planet's physical properties. Production runs recipes against
the colony's stockpile.

This is the layer that connects the resource model (buildings,
recipes, stockpiles) to the game state (colonies, planets).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from space_agent.simulation.resources import (
    BuildingType, Recipe, RECIPES, Stockpile, Resource, Building,
    BUILD_COSTS, solar_output, geothermal_output, nuclear_output,
)
from space_agent.simulation.planet import Planet


# ── Energy Calculation ──────────────────────────────────────────────


@dataclass
class EnergyReport:
    """Result of energy calculation for a colony."""
    solar_mw: float = 0.0
    nuclear_mw: float = 0.0
    geothermal_mw: float = 0.0
    total_production_mw: float = 0.0
    total_consumption_mw: float = 0.0
    net_mw: float = 0.0

    def to_dict(self) -> dict:
        return {
            "solar_mw": round(self.solar_mw, 1),
            "nuclear_mw": round(self.nuclear_mw, 1),
            "geothermal_mw": round(self.geothermal_mw, 1),
            "total_production_mw": round(self.total_production_mw, 1),
            "total_consumption_mw": round(self.total_consumption_mw, 1),
            "net_mw": round(self.net_mw, 1),
        }


def calculate_energy(
    colony_buildings: list[dict],
    planet: Optional[Planet] = None,
    stockpile: Optional[dict] = None,
) -> EnergyReport:
    """Calculate energy production and consumption for a colony.

    Energy sources:
    - Solar arrays: output depends on solar flux at planet's orbit
    - Nuclear reactors: output depends on enriched fuel supply
    - Geothermal taps: output depends on planet's tectonic activity
    """
    report = EnergyReport()
    stockpile = stockpile or {}

    # Count buildings by type
    solar_count = 0
    nuclear_count = 0
    geothermal_count = 0
    consumption_mw = 0.0

    for b in colony_buildings:
        if b.get("status") not in ("active", "idle"):
            continue
        kind = b.get("kind", "")
        # Passive energy producers work regardless of active/idle status
        # (they have no recipe to assign, so status is cosmetic)
        if kind == "solar_array":
            solar_count += 1
        elif kind == "nuclear_reactor":
            nuclear_count += 1
        elif kind == "geothermal_tap":
            geothermal_count += 1

        # Buildings that are running a recipe consume energy (both active and idle run recipes)
        recipe_name = b.get("recipe", "")
        if recipe_name and b.get("status") in ("active", "idle"):
            recipe = RECIPES.get(recipe_name)
            if recipe:
                consumption_mw += recipe.energy_mw

    # Solar: output depends on solar flux at planet's orbit
    if solar_count > 0 and planet is not None:
        report.solar_mw = solar_output(planet.solar_flux, solar_count)

    # Nuclear: output depends on enriched fuel supply
    if nuclear_count > 0:
        fuel_available = stockpile.get("enriched_fuel", 0.0)
        # Each reactor needs 0.5 enriched fuel per turn to run
        reactors_running = min(nuclear_count, int(fuel_available / 0.5))
        report.nuclear_mw = reactors_running * 200.0
        # Consume the fuel (caller applies this)
        if reactors_running > 0:
            stockpile["enriched_fuel"] = fuel_available - reactors_running * 0.5

    # Geothermal: output depends on planet tectonics
    if geothermal_count > 0 and planet is not None:
        tectonic = "moderate"  # Default if no tectonic data on Planet yet
        # Use iron_core_fraction as proxy for tectonic activity
        if planet.iron_core_fraction > 0.35:
            tectonic = "active"
        elif planet.iron_core_fraction > 0.25:
            tectonic = "moderate"
        else:
            tectonic = "dormant"
        report.geothermal_mw = geothermal_output(
            tectonic, planet.iron_core_fraction, geothermal_count
        )

    report.total_production_mw = report.solar_mw + report.nuclear_mw + report.geothermal_mw
    report.total_consumption_mw = consumption_mw
    report.net_mw = report.total_production_mw - report.total_consumption_mw

    return report


# ── Production Simulation ──────────────────────────────────────────


@dataclass
class ProductionReport:
    """Result of running one turn of production for a colony."""
    produced: dict[str, float] = None
    consumed: dict[str, float] = None
    idle_buildings: list[dict] = None
    energy_used_mw: float = 0.0
    messages: list[str] = None

    def __post_init__(self):
        if self.produced is None:
            self.produced = {}
        if self.consumed is None:
            self.consumed = {}
        if self.idle_buildings is None:
            self.idle_buildings = []
        if self.messages is None:
            self.messages = []

    def to_dict(self) -> dict:
        return {
            "produced": {k: round(v, 1) for k, v in self.produced.items() if v > 0},
            "consumed": {k: round(v, 1) for k, v in self.consumed.items() if v > 0},
            "idle_buildings": self.idle_buildings,
            "energy_used_mw": round(self.energy_used_mw, 1),
            "messages": self.messages,
        }


def run_production(
    colony_buildings: list[dict],
    stockpile: dict[str, float],
    energy_budget_mw: float,
) -> ProductionReport:
    """Run one turn of production for all buildings in a colony.

    Buildings run in priority order:
    1. Energy generators (solar, nuclear, geothermal) — don't consume recipe energy
    2. Extractors (mines, atmospheric extractors, ice drills) — raw materials
    3. Processors (smelters, chemical processors, electrolyzers)
    4. Fabricators and assembly bays

    Returns a report of what was produced/consumed.
    """
    report = ProductionReport()
    remaining_energy = energy_budget_mw

    # Priority order for building types
    priority = {
        "solar_array": 0, "nuclear_reactor": 0, "geothermal_tap": 0,
        "mine": 1, "atmospheric_extractor": 1, "ice_drill": 1,
        "smelter": 2, "chemical_processor": 2, "electrolyzer": 2,
        "fabricator": 3, "assembly_bay": 3,
        "research_lab": 4, "terraform_engine": 4,
    }

    # Sort buildings by priority
    sorted_buildings = sorted(
        colony_buildings,
        key=lambda b: priority.get(b.get("kind", ""), 5)
    )

    for b in sorted_buildings:
        # Under construction — tick down first, before the status check
        if b.get("turns_remaining", 0) > 0 or b.get("status") == "building":
            turns_left = b.get("turns_remaining", 1) - 1
            b["turns_remaining"] = max(0, turns_left)
            if turns_left <= 0:
                # Construction complete — auto-activate passive buildings
                passive_kinds = {"solar_array", "nuclear_reactor", "geothermal_tap", "research_lab", "terraform_engine"}
                if b.get("kind", "") in passive_kinds:
                    b["status"] = "active"
                    report.messages.append(f"{b.get('id', '?')} construction complete. Now active (passive building).")
                else:
                    b["status"] = "idle"
                    report.messages.append(f"{b.get('id', '?')} construction complete. Now idle — assign a recipe.")
            else:
                report.messages.append(
                    f"{b.get('id', '?')} under construction ({turns_left} turns remaining)."
                )
            continue

        if b.get("status") not in ("active", "idle"):
            continue

        recipe_name = b.get("recipe", "")
        if not recipe_name:
            continue

        recipe = RECIPES.get(recipe_name)
        if not recipe:
            continue

        # Check energy
        if recipe.energy_mw > remaining_energy:
            report.idle_buildings.append({
                "building_id": b.get("id", "?"),
                "kind": b.get("kind", ""),
                "reason": "insufficient_energy",
            })
            continue

        # Check input materials
        can_run = True
        for resource, amount in recipe.inputs.items():
            key = resource.value if isinstance(resource, Resource) else resource
            available = stockpile.get(key, 0.0)
            if available < amount:
                can_run = False
                report.idle_buildings.append({
                    "building_id": b.get("id", "?"),
                    "kind": b.get("kind", ""),
                    "reason": f"insufficient_{key}",
                })
                break

        if not can_run:
            continue

        # Execute: consume inputs, produce outputs, spend energy
        for resource, amount in recipe.inputs.items():
            key = resource.value if isinstance(resource, Resource) else resource
            stockpile[key] = stockpile.get(key, 0.0) - amount
            report.consumed[key] = report.consumed.get(key, 0.0) + amount

        for resource, amount in recipe.outputs.items():
            key = resource.value if isinstance(resource, Resource) else resource
            stockpile[key] = stockpile.get(key, 0.0) + amount
            report.produced[key] = report.produced.get(key, 0.0) + amount

        remaining_energy -= recipe.energy_mw
        report.energy_used_mw += recipe.energy_mw

        # Mark building as active since it successfully ran
        b["status"] = "active"

    return report


# ── Colony Initialization ──────────────────────────────────────────


def initial_stockpile(planet: Planet) -> dict[str, float]:
    """Generate an initial resource stockpile when a colony is established.

    The stockpile depends on the planet's composition:
    - Ice → water
    - Atmosphere → extractable gases
    - Surface → raw minerals (iron ore, silicates)
    """
    stockpile = {}

    # Water from ice
    if planet.hydrosphere_ice_fraction > 0:
        stockpile["water"] = planet.hydrosphere_ice_fraction * 200.0

    # Atmospheric gases (if pressure is high enough to extract)
    if planet.atmosphere.total_pressure > 0.1:
        stockpile["co2"] = min(planet.atmosphere.co2 * 50, 100.0)
        stockpile["nitrogen"] = min(planet.atmosphere.nitrogen * 20, 50.0)
        stockpile["methane"] = min(planet.atmosphere.methane * 30, 20.0)

    # Raw minerals (always available from surface regolith)
    stockpile["iron_ore"] = 30.0
    stockpile["silicates"] = 50.0
    stockpile["aluminum_ore"] = 10.0

    # Refined materials from seed AI reserves — enough to bootstrap first buildings
    stockpile["refined_iron"] = 30.0
    stockpile["processed_silicon"] = 15.0

    # Trace resources
    stockpile["rare_earths"] = 1.0

    return stockpile


def initial_buildings(planet: Planet) -> list[dict]:
    """Generate starting buildings for a new colony.

    A new colony starts with:
    - 1 habitat module (implicit, always present)
    - 1 solar array (power)
    - 1 mine (raw materials)

    Additional buildings based on planet conditions:
    - Ice → ice drill
    - Thick atmosphere → atmospheric extractor
    """
    buildings = []

    # Solar array — the first power source
    buildings.append({
        "id": "solar_01",
        "kind": "solar_array",
        "recipe": "",
        "status": "active",
        "turns_remaining": 0,
    })

    # Mine — extract raw materials
    buildings.append({
        "id": "mine_01",
        "kind": "mine",
        "recipe": "mine_iron",
        "status": "active",
        "turns_remaining": 0,
    })

    # Ice drill if planet has ice
    if planet.hydrosphere_ice_fraction > 0.05:
        buildings.append({
            "id": "ice_drill_01",
            "kind": "ice_drill",
            "recipe": "drill_ice",
            "status": "active",
            "turns_remaining": 0,
        })

    # Atmospheric extractor if planet has decent atmosphere
    if planet.atmosphere.total_pressure > 0.2:
        buildings.append({
            "id": "atm_extractor_01",
            "kind": "atmospheric_extractor",
            "recipe": "extract_co2",
            "status": "active",
            "turns_remaining": 0,
        })

    return buildings


# ── Colony Turn Resolution ─────────────────────────────────────────


def resolve_colony_turn(
    colony: dict,
    planet: Planet,
) -> dict:
    """Resolve one turn for a colony: compute energy, run production.

    Updates the colony dict in place and returns a summary report.
    """
    buildings = colony.get("buildings", [])
    stockpile = colony.get("stockpile", {})

    # Calculate energy
    energy_report = calculate_energy(buildings, planet, stockpile)
    colony["energy_production_mw"] = energy_report.total_production_mw
    colony["energy_consumption_mw"] = energy_report.total_consumption_mw
    colony["energy_net_mw"] = energy_report.net_mw

    # Run production with available energy
    production_report = run_production(
        buildings, stockpile, energy_report.total_production_mw
    )

    # Update stockpile in colony
    colony["stockpile"] = stockpile

    # Sync legacy resource fields from stockpile
    colony["water"] = stockpile.get("water", 0.0)
    colony["metals"] = stockpile.get("iron_ore", 0.0) + stockpile.get("refined_iron", 0.0)
    colony["energy"] = energy_report.net_mw
    colony["organics"] = stockpile.get("carbon", 0.0) + stockpile.get("methane", 0.0)
    colony["rare_earths"] = stockpile.get("rare_earths", 0.0)

    return {
        "energy": energy_report.to_dict(),
        "production": production_report.to_dict(),
        "colony_name": colony.get("name", "?"),
        "planet_designation": colony.get("planet_designation", "?"),
    }