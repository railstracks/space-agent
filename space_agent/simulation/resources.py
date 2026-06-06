"""Resource model and production chain simulation.

Resources are physical materials, not abstract currency. Everything
the swarm builds must be manufactured from extracted raw materials
through infrastructure-driven production chains. Energy is the
master constraint.

The resource model is:
  Raw materials → Processing → Fabrication → Assembly → Systems
       ↑              ↑             ↑             ↑
     Mine        Smelter/Processor  Fabricator   Assembly Bay

Each step requires infrastructure (buildings), energy, and time.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ── Resource Types ──────────────────────────────────────────────────


class Resource(Enum):
    """All resources in the game."""
    # Raw materials
    IRON_ORE = "iron_ore"
    ALUMINUM_ORE = "aluminum_ore"
    TITANIUM_ORE = "titanium_ore"
    SILICATES = "silicates"
    WATER = "water"
    CO2 = "co2"
    NITROGEN = "nitrogen"
    METHANE = "methane"
    URANIUM_ORE = "uranium_ore"
    THORIUM_ORE = "thorium_ore"
    RARE_EARTHS = "rare_earths"

    # Processed materials
    REFINED_IRON = "refined_iron"
    REFINED_ALUMINUM = "refined_aluminum"
    REFINED_TITANIUM = "refined_titanium"
    PROCESSED_SILICON = "processed_silicon"
    HYDROGEN = "hydrogen"
    OXYGEN = "oxygen"
    CARBON = "carbon"
    CARBON_FIBER = "carbon_fiber"
    ENRICHED_FUEL = "enriched_fuel"

    # Fabricated components
    STRUCTURAL_FRAME = "structural_frame"
    CIRCUIT_SUBSTRATE = "circuit_substrate"
    REACTOR_CELL = "reactor_cell"
    FUEL_CELL = "fuel_cell"
    SENSOR_ARRAY = "sensor_array"
    COMPUTER_CORE = "computer_core"
    PROPULSION_UNIT = "propulsion_unit"

    # Assembled systems
    SCOUT_NODE = "scout_node"
    ORBITER_NODE = "orbiter_node"
    SURFACE_NODE = "surface_node"
    RELAY_NODE = "relay_node"
    CONSTRUCTOR_NODE = "constructor_node"
    HABITAT_MODULE = "habitat_module"
    SOLAR_ARRAY = "solar_array"
    MINE = "mine"
    SMELTER = "smelter"
    CHEMICAL_PROCESSOR = "chemical_processor"
    ELECTROLYZER = "electrolyzer"
    FABRICATOR = "fabricator"
    ASSEMBLY_BAY = "assembly_bay"
    NUCLEAR_REACTOR = "nuclear_reactor"
    GEOTHERMAL_TAP = "geothermal_tap"
    RESEARCH_LAB = "research_lab"
    TERRAFORM_ENGINE = "terraform_engine"
    ICE_DRILL = "ice_drill"
    ATMOSPHERIC_EXTRACTOR = "atmospheric_extractor"


# ── Resource Stockpile ──────────────────────────────────────────────


@dataclass
class Stockpile:
    """Tracks quantities of all resources."""
    amounts: dict[str, float] = field(default_factory=dict)

    def get(self, resource: Resource) -> float:
        return self.amounts.get(resource.value, 0.0)

    def add(self, resource: Resource, amount: float) -> None:
        key = resource.value
        self.amounts[key] = self.amounts.get(key, 0.0) + amount

    def consume(self, resource: Resource, amount: float) -> bool:
        """Try to consume resources. Returns True if successful."""
        current = self.amounts.get(resource.value, 0.0)
        if current >= amount:
            self.amounts[resource.value] = current - amount
            return True
        return False

    def can_afford(self, costs: dict[Resource, float]) -> bool:
        return all(self.get(r) >= amt for r, amt in costs.items())

    def spend(self, costs: dict[Resource, float]) -> bool:
        """Atomically spend multiple resources. Returns False if insufficient."""
        if not self.can_afford(costs):
            return False
        for r, amt in costs.items():
            self.consume(r, amt)
        return True

    def to_dict(self) -> dict:
        return {k: v for k, v in self.amounts.items() if v > 0}

    @classmethod
    def from_dict(cls, d: dict) -> Stockpile:
        return cls(amounts=dict(d))


# ── Building Types ──────────────────────────────────────────────────


class BuildingType(Enum):
    """Types of infrastructure buildings."""
    MINE = "mine"
    ATMOSPHERIC_EXTRACTOR = "atmospheric_extractor"
    ICE_DRILL = "ice_drill"
    SMELTER = "smelter"
    CHEMICAL_PROCESSOR = "chemical_processor"
    ELECTROLYZER = "electrolyzer"
    FABRICATOR = "fabricator"
    ASSEMBLY_BAY = "assembly_bay"
    SOLAR_ARRAY = "solar_array"
    NUCLEAR_REACTOR = "nuclear_reactor"
    GEOTHERMAL_TAP = "geothermal_tap"
    RESEARCH_LAB = "research_lab"
    TERRAFORM_ENGINE = "terraform_engine"


# ── Production Recipes ──────────────────────────────────────────────


@dataclass
class Recipe:
    """A production recipe: input → output per turn."""
    name: str
    building: BuildingType
    inputs: dict[Resource, float]  # consumed per turn
    outputs: dict[Resource, float]  # produced per turn
    energy_mw: float  # energy consumed per turn

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "building": self.building.value,
            "inputs": {r.value: a for r, a in self.inputs.items()},
            "outputs": {r.value: a for r, a in self.outputs.items()},
            "energy_mw": self.energy_mw,
        }


# ── Build Costs ─────────────────────────────────────────────────────


@dataclass
class BuildCost:
    """Cost to construct a building or assemble a system."""
    name: str
    result: Resource  # what you get
    costs: dict[Resource, float]
    build_turns: int  # turns to construct
    requires_building: Optional[BuildingType] = None  # needs this building to construct

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "result": self.result.value,
            "costs": {r.value: a for r, a in self.costs.items()},
            "build_turns": self.build_turns,
            "requires_building": self.requires_building.value if self.requires_building else None,
        }


# ── Recipe Definitions ─────────────────────────────────────────────


RECIPES = {
    # Extraction
    "mine_iron": Recipe("Iron Mining", BuildingType.MINE,
        inputs={}, outputs={Resource.IRON_ORE: 50}, energy_mw=5),
    "mine_aluminum": Recipe("Aluminum Mining", BuildingType.MINE,
        inputs={}, outputs={Resource.ALUMINUM_ORE: 30}, energy_mw=5),
    "mine_titanium": Recipe("Titanium Mining", BuildingType.MINE,
        inputs={}, outputs={Resource.TITANIUM_ORE: 10}, energy_mw=8),
    "mine_silicates": Recipe("Silicate Mining", BuildingType.MINE,
        inputs={}, outputs={Resource.SILICATES: 60}, energy_mw=3),
    "mine_uranium": Recipe("Uranium Mining", BuildingType.MINE,
        inputs={}, outputs={Resource.URANIUM_ORE: 2}, energy_mw=10),
    "mine_rare_earths": Recipe("Rare Earth Mining", BuildingType.MINE,
        inputs={}, outputs={Resource.RARE_EARTHS: 1}, energy_mw=12),

    # Atmospheric extraction
    "extract_co2": Recipe("CO₂ Extraction", BuildingType.ATMOSPHERIC_EXTRACTOR,
        inputs={}, outputs={Resource.CO2: 40}, energy_mw=4),
    "extract_nitrogen": Recipe("Nitrogen Extraction", BuildingType.ATMOSPHERIC_EXTRACTOR,
        inputs={}, outputs={Resource.NITROGEN: 40}, energy_mw=4),
    "extract_methane": Recipe("Methane Extraction", BuildingType.ATMOSPHERIC_EXTRACTOR,
        inputs={}, outputs={Resource.METHANE: 10}, energy_mw=6),

    # Ice/water
    "drill_ice": Recipe("Ice Drilling", BuildingType.ICE_DRILL,
        inputs={}, outputs={Resource.WATER: 80}, energy_mw=6),

    # Processing
    "smelt_iron": Recipe("Iron Smelting", BuildingType.SMELTER,
        inputs={Resource.IRON_ORE: 50}, outputs={Resource.REFINED_IRON: 40}, energy_mw=15),
    "smelt_aluminum": Recipe("Aluminum Smelting", BuildingType.SMELTER,
        inputs={Resource.ALUMINUM_ORE: 30}, outputs={Resource.REFINED_ALUMINUM: 20}, energy_mw=20),
    "smelt_titanium": Recipe("Titanium Smelting", BuildingType.SMELTER,
        inputs={Resource.TITANIUM_ORE: 10}, outputs={Resource.REFINED_TITANIUM: 5}, energy_mw=25),
    "process_silicon": Recipe("Silicon Processing", BuildingType.CHEMICAL_PROCESSOR,
        inputs={Resource.SILICATES: 40}, outputs={Resource.PROCESSED_SILICON: 20}, energy_mw=12),
    "process_carbon": Recipe("Carbon Processing", BuildingType.CHEMICAL_PROCESSOR,
        inputs={Resource.CO2: 30}, outputs={Resource.CARBON: 10, Resource.OXYGEN: 15}, energy_mw=10),
    "enrich_fuel": Recipe("Fuel Enrichment", BuildingType.CHEMICAL_PROCESSOR,
        inputs={Resource.URANIUM_ORE: 2}, outputs={Resource.ENRICHED_FUEL: 1}, energy_mw=30),
    "electrolyze_water": Recipe("Water Electrolysis", BuildingType.ELECTROLYZER,
        inputs={Resource.WATER: 80}, outputs={Resource.HYDROGEN: 30, Resource.OXYGEN: 40}, energy_mw=20),

    # Fabrication
    "fab_frame": Recipe("Structural Frame Fabrication", BuildingType.FABRICATOR,
        inputs={Resource.REFINED_IRON: 20, Resource.REFINED_ALUMINUM: 5},
        outputs={Resource.STRUCTURAL_FRAME: 1}, energy_mw=8),
    "fab_circuit": Recipe("Circuit Substrate Fabrication", BuildingType.FABRICATOR,
        inputs={Resource.PROCESSED_SILICON: 15, Resource.RARE_EARTHS: 0.5},
        outputs={Resource.CIRCUIT_SUBSTRATE: 1}, energy_mw=10),
    "fab_reactor": Recipe("Reactor Cell Fabrication", BuildingType.FABRICATOR,
        inputs={Resource.ENRICHED_FUEL: 1, Resource.REFINED_TITANIUM: 2},
        outputs={Resource.REACTOR_CELL: 1}, energy_mw=12),
    "fab_fuel_cell": Recipe("Fuel Cell Fabrication", BuildingType.FABRICATOR,
        inputs={Resource.HYDROGEN: 20, Resource.OXYGEN: 20},
        outputs={Resource.FUEL_CELL: 1}, energy_mw=6),
    "fab_sensor": Recipe("Sensor Array Fabrication", BuildingType.FABRICATOR,
        inputs={Resource.PROCESSED_SILICON: 10, Resource.REFINED_ALUMINUM: 3},
        outputs={Resource.SENSOR_ARRAY: 1}, energy_mw=8),
    "fab_computer": Recipe("Computer Core Fabrication", BuildingType.FABRICATOR,
        inputs={Resource.CIRCUIT_SUBSTRATE: 2, Resource.RARE_EARTHS: 1},
        outputs={Resource.COMPUTER_CORE: 1}, energy_mw=10),
    "fab_propulsion": Recipe("Propulsion Unit Fabrication", BuildingType.FABRICATOR,
        inputs={Resource.REFINED_IRON: 10, Resource.FUEL_CELL: 2},
        outputs={Resource.PROPULSION_UNIT: 1}, energy_mw=15),
    "fab_carbon_fiber": Recipe("Carbon Fiber Fabrication", BuildingType.FABRICATOR,
        inputs={Resource.CARBON: 10, Resource.REFINED_IRON: 2},
        outputs={Resource.CARBON_FIBER: 5}, energy_mw=8),
}

BUILD_COSTS = {
    # Infrastructure buildings
    "mine": BuildCost("Mine", Resource.MINE,
        costs={Resource.REFINED_IRON: 5, Resource.SILICATES: 3}, build_turns=1),
    "atmospheric_extractor": BuildCost("Atmospheric Extractor", Resource.ATMOSPHERIC_EXTRACTOR,
        costs={Resource.REFINED_IRON: 5, Resource.SILICATES: 5}, build_turns=1),
    "ice_drill": BuildCost("Ice Drill", Resource.ICE_DRILL,
        costs={Resource.REFINED_IRON: 3, Resource.SILICATES: 2}, build_turns=1),
    "smelter": BuildCost("Smelter", Resource.SMELTER,
        costs={Resource.REFINED_IRON: 10, Resource.SILICATES: 5}, build_turns=2),
    "chemical_processor": BuildCost("Chemical Processor", Resource.CHEMICAL_PROCESSOR,
        costs={Resource.REFINED_IRON: 8, Resource.PROCESSED_SILICON: 5}, build_turns=2),
    "electrolyzer": BuildCost("Electrolyzer", Resource.ELECTROLYZER,
        costs={Resource.REFINED_IRON: 8, Resource.PROCESSED_SILICON: 3}, build_turns=2),
    "fabricator": BuildCost("Fabricator", Resource.FABRICATOR,
        costs={Resource.REFINED_IRON: 15, Resource.PROCESSED_SILICON: 10, Resource.RARE_EARTHS: 2},
        build_turns=3),
    "assembly_bay": BuildCost("Assembly Bay", Resource.ASSEMBLY_BAY,
        costs={Resource.REFINED_IRON: 12, Resource.PROCESSED_SILICON: 8}, build_turns=2),
    "solar_array": BuildCost("Solar Array", Resource.SOLAR_ARRAY,
        costs={Resource.REFINED_IRON: 3, Resource.PROCESSED_SILICON: 5}, build_turns=1),
    "nuclear_reactor": BuildCost("Nuclear Reactor", Resource.NUCLEAR_REACTOR,
        costs={Resource.REFINED_IRON: 20, Resource.RARE_EARTHS: 5, Resource.ENRICHED_FUEL: 2},
        build_turns=4, requires_building=BuildingType.ASSEMBLY_BAY),
    "research_lab": BuildCost("Research Lab", Resource.RESEARCH_LAB,
        costs={Resource.REFINED_IRON: 10, Resource.PROCESSED_SILICON: 15, Resource.RARE_EARTHS: 3},
        build_turns=3, requires_building=BuildingType.ASSEMBLY_BAY),
    "terraform_engine": BuildCost("Terraforming Engine", Resource.TERRAFORM_ENGINE,
        costs={Resource.REFINED_IRON: 25, Resource.PROCESSED_SILICON: 20, Resource.RARE_EARTHS: 5},
        build_turns=5, requires_building=BuildingType.ASSEMBLY_BAY),

    # Node types (assembled systems)
    "scout_node": BuildCost("Scout Node", Resource.SCOUT_NODE,
        costs={Resource.STRUCTURAL_FRAME: 1, Resource.COMPUTER_CORE: 1, Resource.SENSOR_ARRAY: 1,
               Resource.PROPULSION_UNIT: 1},
        build_turns=2, requires_building=BuildingType.ASSEMBLY_BAY),
    "orbiter_node": BuildCost("Orbiter Node", Resource.ORBITER_NODE,
        costs={Resource.STRUCTURAL_FRAME: 2, Resource.COMPUTER_CORE: 1, Resource.SENSOR_ARRAY: 2,
               Resource.PROPULSION_UNIT: 2, Resource.FUEL_CELL: 4},
        build_turns=3, requires_building=BuildingType.ASSEMBLY_BAY),
    "surface_node": BuildCost("Surface Node", Resource.SURFACE_NODE,
        costs={Resource.STRUCTURAL_FRAME: 1, Resource.COMPUTER_CORE: 1, Resource.SENSOR_ARRAY: 1,
               Resource.FUEL_CELL: 1},
        build_turns=2, requires_building=BuildingType.ASSEMBLY_BAY),
    "relay_node": BuildCost("Relay Node", Resource.RELAY_NODE,
        costs={Resource.STRUCTURAL_FRAME: 1, Resource.COMPUTER_CORE: 1, Resource.PROPULSION_UNIT: 1,
               Resource.FUEL_CELL: 2},
        build_turns=1, requires_building=BuildingType.ASSEMBLY_BAY),
    "constructor_node": BuildCost("Constructor Node", Resource.CONSTRUCTOR_NODE,
        costs={Resource.STRUCTURAL_FRAME: 3, Resource.COMPUTER_CORE: 2, Resource.SENSOR_ARRAY: 1,
               Resource.PROPULSION_UNIT: 1, Resource.FUEL_CELL: 3},
        build_turns=4, requires_building=BuildingType.ASSEMBLY_BAY),
}


# ── Energy Sources ──────────────────────────────────────────────────


@dataclass
class EnergySource:
    """A source of energy on a colony."""
    kind: str  # "solar", "geothermal", "nuclear"
    output_mw: float  # base output
    variable: bool = False  # output varies with conditions

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> EnergySource:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def solar_output(solar_flux_w_m2: float, num_arrays: int) -> float:
    """Calculate solar energy output in MW."""
    # Simplified: each array produces proportional to flux
    # Earth flux = 1361 W/m² → baseline array = 100 MW
    baseline = 100.0  # MW per array at Earth-equivalent flux
    return num_arrays * baseline * (solar_flux_w_m2 / 1361.0)


def geothermal_output(tectonic_activity: str, core_fraction: float, num_taps: int) -> float:
    """Calculate geothermal energy output in MW."""
    activity_factor = {
        "active": 1.0,
        "moderate": 0.5,
        "dormant": 0.1,
        "dead": 0.0,
    }.get(tectonic_activity, 0.0)
    core_factor = min(core_fraction / 0.32, 2.0)
    return num_taps * 80.0 * activity_factor * core_factor


def nuclear_output(num_reactors: int, enriched_fuel_per_turn: float) -> float:
    """Calculate nuclear energy output in MW."""
    # Each reactor: 200 MW, consumes 0.5 enriched fuel per turn
    return min(num_reactors, enriched_fuel_per_turn / 0.5) * 200.0


# ── Production Simulation ──────────────────────────────────────────


@dataclass
class Building:
    """An active building in a colony."""
    id: str
    kind: BuildingType
    recipe: str  # which recipe it's running (from RECIPES)
    status: str = "active"  # active, idle, damaged, building
    turns_remaining: int = 0  # for buildings under construction

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "recipe": self.recipe,
            "status": self.status,
            "turns_remaining": self.turns_remaining,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Building:
        return cls(
            id=d["id"],
            kind=BuildingType(d["kind"]),
            recipe=d.get("recipe", ""),
            status=d.get("status", "active"),
            turns_remaining=d.get("turns_remaining", 0),
        )


def simulate_production(
    buildings: list[Building],
    stockpile: Stockpile,
    energy_budget_mw: float,
) -> dict:
    """Run one turn of production for all buildings.

    Returns a report of what was produced and what couldn't run.
    """
    report = {
        "produced": {},
        "consumed": {},
        "idle": [],
        "energy_used_mw": 0.0,
    }

    remaining_energy = energy_budget_mw

    # Prioritize: energy generation first, then production chains
    # Sort buildings so energy sources run first
    energy_buildings = {BuildingType.SOLAR_ARRAY, BuildingType.NUCLEAR_REACTOR, BuildingType.GEOTHERMAL_TAP}
    sorted_buildings = sorted(buildings, key=lambda b: 0 if b.kind in energy_buildings else 1)

    for building in sorted_buildings:
        if building.status != "active":
            continue

        if not building.recipe:
            continue

        recipe = RECIPES.get(building.recipe)
        if not recipe:
            continue

        # Check energy
        if recipe.energy_mw > remaining_energy:
            report["idle"].append({
                "building_id": building.id,
                "reason": "insufficient_energy",
            })
            continue

        # Check input materials
        can_run = True
        for resource, amount in recipe.inputs.items():
            if stockpile.get(resource) < amount:
                can_run = False
                break

        if not can_run:
            report["idle"].append({
                "building_id": building.id,
                "reason": "insufficient_inputs",
            })
            continue

        # Execute: consume inputs, produce outputs, spend energy
        for resource, amount in recipe.inputs.items():
            stockpile.consume(resource, amount)
            key = resource.value
            report["consumed"][key] = report["consumed"].get(key, 0) + amount

        for resource, amount in recipe.outputs.items():
            stockpile.add(resource, amount)
            key = resource.value
            report["produced"][key] = report["produced"].get(key, 0) + amount

        remaining_energy -= recipe.energy_mw
        report["energy_used_mw"] += recipe.energy_mw

    return report
