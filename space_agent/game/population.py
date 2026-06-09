"""Population and colony development dynamics.

The seed AI prepares worlds for colonists who are still in cryogenic sleep
aboard the colony ships. Population mechanics give the game its emotional
spine: every habitat module built is a future home, every resource surplus
is a safety margin for people who haven't woken up yet.

Colony stages:
  OUTPOST     — 0–50 settlers. Basic survival. Limited building options.
  SETTLEMENT  — 51–500 settlers. Infrastructure expands. More recipes.
  COLONY      — 501–5000 settlers. Industry scales. Assembly bays.
  CITY        — 5001+ settlers. Full capabilities. Terraforming.

Population grows based on:
  - Habitat capacity (can't exceed housing)
  - Morale (higher morale → faster growth)
  - Resource availability (food/water/energy surplus)
  - Colony stage bonuses (larger colonies attract more settlers)

The fleet arrival timer is the game's clock. When it hits zero, colonists
wake up and need to fit into the habitat capacity you've built. Shortfall
is measured in lives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Colony Stages ───────────────────────────────────────────────────


class ColonyStage(Enum):
    """Development stages for a colony.

    Each stage unlocks additional capabilities and affects
    population growth rate, resource consumption, and morale.
    """
    OUTPOST = "outpost"
    SETTLEMENT = "settlement"
    COLONY = "colony"
    CITY = "city"


# Stage thresholds (population)
STAGE_THRESHOLDS = {
    ColonyStage.OUTPOST: 0,       # 0–50
    ColonyStage.SETTLEMENT: 51,    # 51–500
    ColonyStage.COLONY: 501,      # 501–5000
    ColonyStage.CITY: 5001,       # 5001+
}

# Stage labels for display
STAGE_NAMES = {
    ColonyStage.OUTPOST: "Outpost",
    ColonyStage.SETTLEMENT: "Settlement",
    ColonyStage.COLONY: "Colony",
    ColonyStage.CITY: "City",
}

# Population capacity per habitat module
HABITAT_CAPACITY = 50

# Base population growth rate (fraction per turn, before modifiers)
BASE_GROWTH_RATE = 0.08  # 8% per turn (5-year turns = ~1.5% per year)

# Morale modifiers on growth rate
MORALE_GROWTH_MODIFIER = {
    "DESPERATE": -0.02,  # Population declining
    "STRUGGLING": 0.0,   # Stagnant
    "CAUTIOUS": 0.02,    # Slow growth
    "HOPEFUL": 0.04,     # Normal growth
    "OPTIMISTIC": 0.06,  # Strong growth
    "THRIVING": 0.08,    # Boom
}

# Morale thresholds (fraction of needs met → morale level)
# Needs = (water per capita, energy per capita, habitat capacity %)
MORALE_THRESHOLDS = {
    # (water_sufficiency, energy_sufficiency, housing_sufficiency) → morale
    # These are checked from top to bottom; first match wins
    "DESPERATE":  lambda w, e, h: w < 0.5 or e < 0.3 or h < 0.5,
    "STRUGGLING": lambda w, e, h: w < 0.7 or e < 0.5 or h < 0.7,
    "CAUTIOUS":   lambda w, e, h: w < 0.85 or e < 0.7 or h < 0.85,
    "OPTIMISTIC": lambda w, e, h: w >= 1.0 and e >= 0.9 and h >= 1.0,
    "THRIVING":   lambda w, e, h: w >= 1.2 and e >= 1.1 and h >= 1.2,
    "HOPEFUL":    lambda w, e, h: True,  # Default: adequate but not exceptional
}

# Per-capita resource consumption per turn (5-year turn)
WATER_PER_CAPITA = 2.0      # units of water per person per turn
ENERGY_PER_CAPITA = 0.5     # MW per person per turn (life support, etc.)

# Stage-specific building unlocks
STAGE_BUILDING_UNLOCKS = {
    ColonyStage.OUTPOST: {
        # Can build: mine, solar_array, ice_drill, atmospheric_extractor, habitat_module
        "allowed": {"mine", "solar_array", "ice_drill", "atmospheric_extractor", "geothermal_tap", "habitat_module"},
    },
    ColonyStage.SETTLEMENT: {
        # Unlocks: smelter, chemical_processor, electrolyzer
        "allowed": {"mine", "solar_array", "ice_drill", "atmospheric_extractor",
                     "geothermal_tap", "smelter", "chemical_processor", "electrolyzer"},
    },
    ColonyStage.COLONY: {
        # Unlocks: fabricator, assembly_bay
        "allowed": {"mine", "solar_array", "ice_drill", "atmospheric_extractor",
                     "geothermal_tap", "smelter", "chemical_processor", "electrolyzer",
                     "fabricator", "assembly_bay", "nuclear_reactor"},
    },
    ColonyStage.CITY: {
        # Unlocks: research_lab, terraform_engine
        "allowed": {"mine", "solar_array", "ice_drill", "atmospheric_extractor",
                     "geothermal_tap", "smelter", "chemical_processor", "electrolyzer",
                     "fabricator", "assembly_bay", "nuclear_reactor",
                     "research_lab", "terraform_engine"},
    },
}


# ── Fleet Arrival ───────────────────────────────────────────────────


@dataclass
class FleetStatus:
    """Track the approaching colony fleet.

    The fleet is the game's clock. Colonists are in cryogenic sleep,
    traveling at sub-FTL speeds. They will arrive at a known turn,
    and the seed AI must have habitat capacity and resources ready.

    The fleet size determines how many colonists arrive. If the colony's
    total habitat capacity is less than the fleet size, the shortfall
    represents people waking up to inadequate conditions.
    """
    total_colonists: int = 200000   # Total people aboard the fleet
    arrival_turn: int = 40          # Turn when the fleet arrives (200 years = 40 turns × 5yr)
    distance_ly: float = 18.0      # Light-years from departure system
    fleet_speed_fraction_c: float = 0.04  # 4% of light speed
    status: str = "en_route"       # en_route, arrived, settled

    @property
    def turns_until_arrival(self) -> int:
        """How many turns until the fleet arrives."""
        # This is computed externally and set on arrival_turn
        # The fleet's travel time = distance / speed in years
        # Turn number = travel_time / years_per_turn
        # This is set at game creation, not computed each time
        return max(0, self.arrival_turn)

    @property
    def years_until_arrival(self) -> float:
        """How many in-game years until arrival."""
        return self.turns_until_arrival * 5.0  # 5 years per turn

    @property
    def colonists_per_habitat_module(self) -> int:
        """How many colonists each habitat module houses."""
        return HABITAT_CAPACITY

    def to_dict(self) -> dict:
        return {
            "total_colonists": self.total_colonists,
            "arrival_turn": self.arrival_turn,
            "distance_ly": self.distance_ly,
            "fleet_speed_fraction_c": self.fleet_speed_fraction_c,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FleetStatus:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Population Resolution ───────────────────────────────────────────


@dataclass
class PopulationReport:
    """Result of resolving population for one turn."""
    colony_name: str = ""
    planet_designation: str = ""
    population_before: int = 0
    population_after: int = 0
    growth: int = 0
    morale: str = "HOPEFUL"
    morale_change: str = ""  # "improved", "declined", "stable"
    habitat_capacity: int = 0
    habitat_occupancy: float = 0.0  # percentage
    water_sufficiency: float = 0.0
    energy_sufficiency: float = 0.0
    housing_sufficiency: float = 0.0
    stage: str = "outpost"
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "colony_name": self.colony_name,
            "planet_designation": self.planet_designation,
            "population_before": self.population_before,
            "population_after": self.population_after,
            "growth": self.growth,
            "morale": self.morale,
            "morale_change": self.morale_change,
            "habitat_capacity": self.habitat_capacity,
            "habitat_occupancy": round(self.habitat_occupancy, 1),
            "water_sufficiency": round(self.water_sufficiency, 2),
            "energy_sufficiency": round(self.energy_sufficiency, 2),
            "housing_sufficiency": round(self.housing_sufficiency, 2),
            "stage": self.stage,
            "messages": self.messages,
        }


def determine_stage(population: int) -> ColonyStage:
    """Determine colony development stage from population."""
    if population >= STAGE_THRESHOLDS[ColonyStage.CITY]:
        return ColonyStage.CITY
    elif population >= STAGE_THRESHOLDS[ColonyStage.COLONY]:
        return ColonyStage.COLONY
    elif population >= STAGE_THRESHOLDS[ColonyStage.SETTLEMENT]:
        return ColonyStage.SETTLEMENT
    else:
        return ColonyStage.OUTPOST


def calculate_habitat_capacity(buildings: list[dict]) -> int:
    """Calculate total population capacity from habitat modules.

    Each habitat_module building provides HABITAT_CAPACITY slots.
    """
    capacity = 0
    for b in buildings:
        if b.get("kind") == "habitat_module" and b.get("status") in ("active", "idle"):
            capacity += HABITAT_CAPACITY
    return capacity


def calculate_morale(
    water_available: float,
    energy_net_mw: float,
    habitat_capacity: int,
    population: int,
) -> str:
    """Determine morale from resource sufficiency.

    Sufficiency is a ratio: available / needed. Values > 1.0 mean surplus.
    """
    if population <= 0:
        return "HOPEFUL"

    water_needed = population * WATER_PER_CAPITA
    energy_needed = population * ENERGY_PER_CAPITA

    water_sufficiency = water_available / water_needed if water_needed > 0 else 1.0
    energy_sufficiency = energy_net_mw / energy_needed if energy_needed > 0 else 1.0
    housing_sufficiency = habitat_capacity / population if population > 0 else 1.0

    # Check from worst to best; first match wins
    # Within "good" range, check from best (THRIVING) to worst (HOPEFUL)
    # so that higher morale levels are matched before lower ones
    for morale, check in [
        ("DESPERATE", MORALE_THRESHOLDS["DESPERATE"]),
        ("STRUGGLING", MORALE_THRESHOLDS["STRUGGLING"]),
        ("CAUTIOUS", MORALE_THRESHOLDS["CAUTIOUS"]),
        ("THRIVING", MORALE_THRESHOLDS["THRIVING"]),
        ("OPTIMISTIC", MORALE_THRESHOLDS["OPTIMISTIC"]),
        ("HOPEFUL", MORALE_THRESHOLDS["HOPEFUL"]),
    ]:
        if check(water_sufficiency, energy_sufficiency, housing_sufficiency):
            return morale

    return "HOPEFUL"  # Should never reach here


def resolve_population_turn(
    colony: dict,
    planet: dict = None,
) -> PopulationReport:
    """Resolve one turn of population dynamics for a colony.

    Updates colony dict in place with new population, morale, etc.
    Returns a report of what happened.
    """
    report = PopulationReport()

    population = colony.get("population", 0)
    report.population_before = population

    # Get current resources
    stockpile = colony.get("stockpile", {})
    water_available = stockpile.get("water", 0.0)
    energy_net_mw = colony.get("energy_net_mw", 0.0)

    # Count habitat capacity
    buildings = colony.get("buildings", [])
    habitat_capacity = calculate_habitat_capacity(buildings)

    # If no population yet, this is an automated outpost
    # Population arrives when first habitat module is built
    if population <= 0:
        report.morale = "HOPEFUL"
        report.habitat_capacity = habitat_capacity

        # Check if first habitat just completed — settlers arrive
        if habitat_capacity > 0:
            # First wave of settlers: 20% of habitat capacity, minimum 10
            initial_settlers = max(10, int(habitat_capacity * 0.2))
            colony["population"] = initial_settlers
            report.population_after = initial_settlers
            report.growth = initial_settlers
            report.messages.append(
                f"First wave of settlers arrives: {initial_settlers} colonists. "
                f"The outpost becomes real."
            )
            report.stage = ColonyStage.OUTPOST.value
            colony["morale"] = "HOPEFUL"
            return report

        # No habitat yet — purely automated
        report.population_after = 0
        report.stage = ColonyStage.OUTPOST.value
        colony["morale"] = "HOPEFUL"
        return report

    # Calculate morale
    morale = calculate_morale(water_available, energy_net_mw, habitat_capacity, population)
    old_morale = colony.get("morale", "HOPEFUL")
    colony["morale"] = morale

    # Morale change tracking
    morale_order = ["DESPERATE", "STRUGGLING", "CAUTIOUS", "HOPEFUL", "OPTIMISTIC", "THRIVING"]
    old_idx = morale_order.index(old_morale) if old_morale in morale_order else 3
    new_idx = morale_order.index(morale) if morale in morale_order else 3
    if new_idx > old_idx:
        report.morale_change = "improved"
    elif new_idx < old_idx:
        report.morale_change = "declined"
    else:
        report.morale_change = "stable"

    # Calculate sufficiency ratios
    water_needed = population * WATER_PER_CAPITA
    energy_needed = population * ENERGY_PER_CAPITA
    water_sufficiency = water_available / water_needed if water_needed > 0 else 1.0
    energy_sufficiency = energy_net_mw / energy_needed if energy_needed > 0 else 1.0
    housing_sufficiency = habitat_capacity / population if population > 0 else 1.0

    report.water_sufficiency = water_sufficiency
    report.energy_sufficiency = energy_sufficiency
    report.housing_sufficiency = housing_sufficiency

    # Population growth
    growth_modifier = MORALE_GROWTH_MODIFIER.get(morale, 0.02)
    growth_rate = BASE_GROWTH_RATE + growth_modifier

    # Housing constraint: can't exceed capacity
    if habitat_capacity > 0 and population >= habitat_capacity:
        # At or over capacity — no growth, possible decline
        if morale in ("DESPERATE", "STRUGGLING"):
            # Overcrowding + desperation = population loss
            loss = max(1, int(population * 0.02))
            population = max(0, population - loss)
            report.growth = -loss
            report.messages.append(f"Overcrowding and {morale.lower()} conditions: {loss} colonists lost.")
        else:
            # At capacity but stable — no growth
            report.growth = 0
            report.messages.append("Habitat at full capacity. Population stable.")
    else:
        # Room to grow
        growth = max(0, int(population * growth_rate))
        # Stage bonus: larger colonies attract more settlers
        stage = determine_stage(population)
        if stage == ColonyStage.SETTLEMENT:
            growth += max(1, int(population * 0.01))  # 1% immigration
        elif stage == ColonyStage.COLONY:
            growth += max(2, int(population * 0.02))  # 2% immigration
        elif stage == ColonyStage.CITY:
            growth += max(5, int(population * 0.03))  # 3% immigration

        # Don't exceed habitat capacity
        if habitat_capacity > 0:
            room = habitat_capacity - population
            growth = min(growth, room)

        population += growth
        report.growth = growth

        if growth > 0:
            if growth > population * 0.05:
                report.messages.append(f"Population boom: +{growth} settlers. Morale: {morale.lower()}.")
            else:
                report.messages.append(f"Population growth: +{growth} settlers. Total: {population}.")

    # Consume water for population (life support)
    water_consumed = population * WATER_PER_CAPITA
    if water_available > 0:
        actual_consumed = min(water_consumed, water_available)
        stockpile["water"] = max(0, water_available - actual_consumed)
        if actual_consumed < water_consumed:
            report.messages.append(
                f"⚠ Water shortage! Need {water_consumed:.0f} but only {water_available:.0f} available. "
                f"Colony rationing."
            )

    # Consume energy for life support (deducted from colony energy budget)
    # This is handled at the colony level — population life support is a fixed drain
    energy_for_life_support = population * ENERGY_PER_CAPITA
    colony["energy_consumption_mw"] = colony.get("energy_consumption_mw", 0.0) + energy_for_life_support
    colony["energy_net_mw"] = colony.get("energy_production_mw", 0.0) - colony.get("energy_consumption_mw", 0.0)

    # Determine stage
    stage = determine_stage(population)
    report.stage = stage.value

    # Stage transition messages
    old_stage = determine_stage(report.population_before)
    if stage != old_stage:
        stage_name = STAGE_NAMES[stage]
        report.messages.append(
            f"🏘️ Colony stage: {STAGE_NAMES[old_stage]} → {stage_name}! "
            f"New buildings and capabilities unlocked."
        )

    report.population_after = population
    report.morale = morale
    report.habitat_capacity = habitat_capacity
    report.habitat_occupancy = (population / habitat_capacity * 100) if habitat_capacity > 0 else 0.0

    # Update colony
    colony["population"] = population
    colony["morale"] = morale

    return report


def can_build_building(building_type: str, colony: dict) -> tuple[bool, str]:
    """Check if a colony's stage allows building a given type.

    Returns (can_build, reason).
    """
    population = colony.get("population", 0)
    stage = determine_stage(population)
    allowed = STAGE_BUILDING_UNLOCKS.get(stage, {}).get("allowed", set())

    if building_type not in allowed:
        stage_name = STAGE_NAMES[stage]
        required = None
        for s, data in STAGE_BUILDING_UNLOCKS.items():
            if building_type in data["allowed"]:
                required = STAGE_NAMES[s]
                break
        if required:
            return False, f"Requires {required} stage (population {STAGE_THRESHOLDS[s]}+). Current: {stage_name} (pop {population})."
        else:
            return False, f"Building type '{building_type}' not available at any stage."

    return True, "OK"


def evaluate_fleet_readiness(
    colonies: list[dict],
    fleet: FleetStatus,
    current_turn: int,
) -> dict:
    """Evaluate how ready the colonies are for fleet arrival.

    This is the game's core tension: are you prepared?
    """
    total_habitat_capacity = 0
    total_population = 0
    total_water = 0.0
    total_energy_net = 0.0
    colony_readiness = []

    for c_data in colonies:
        buildings = c_data.get("buildings", [])
        habitat_cap = calculate_habitat_capacity(buildings)
        pop = c_data.get("population", 0)
        water = c_data.get("stockpile", {}).get("water", 0.0)
        energy_net = c_data.get("energy_net_mw", 0.0)

        total_habitat_capacity += habitat_cap
        total_population += pop
        total_water += water
        total_energy_net += energy_net

        colony_readiness.append({
            "name": c_data.get("name", "?"),
            "planet": c_data.get("planet_designation", "?"),
            "population": pop,
            "habitat_capacity": habitat_cap,
            "stage": determine_stage(pop).value,
            "water_surplus": max(0, water - pop * WATER_PER_CAPITA),
            "energy_net_mw": energy_net,
        })

    colonists_coming = fleet.total_colonists
    housing_shortfall = max(0, colonists_coming - total_habitat_capacity)
    housing_surplus = max(0, total_habitat_capacity - colonists_coming)

    # Water sustainability (5-turn supply at current surplus)
    water_per_turn = total_population * WATER_PER_CAPITA
    water_surplus_per_turn = max(0, total_water - water_per_turn)
    turns_of_water = total_water / water_per_turn if water_per_turn > 0 else float('inf')

    turns_remaining = max(0, fleet.arrival_turn - current_turn)
    years_remaining = turns_remaining * 5.0

    # Overall readiness score (0–100)
    housing_score = min(100, (total_habitat_capacity / colonists_coming) * 100) if colonists_coming > 0 else 0
    water_score = min(100, (turns_of_water / 10) * 100)  # 10 turns of water = 100%
    energy_score = min(100, (total_energy_net / (colonists_coming * ENERGY_PER_CAPITA)) * 100) if colonists_coming > 0 else 0

    overall_score = (housing_score * 0.5 + water_score * 0.25 + energy_score * 0.25)

    return {
        "turns_until_arrival": turns_remaining,
        "years_until_arrival": years_remaining,
        "colonists_coming": colonists_coming,
        "total_habitat_capacity": total_habitat_capacity,
        "total_population": total_population,
        "housing_shortfall": housing_shortfall,
        "housing_surplus": housing_surplus,
        "water_sustainability_turns": round(turns_of_water, 1),
        "energy_net_mw": total_energy_net,
        "energy_for_colonists_mw": colonists_coming * ENERGY_PER_CAPITA,
        "readiness_score": round(overall_score, 1),
        "housing_score": round(housing_score, 1),
        "water_score": round(water_score, 1),
        "energy_score": round(energy_score, 1),
        "colony_readiness": colony_readiness,
    }