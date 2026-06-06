"""Drone and node types — mobile units controlled by the swarm.

Drones differ from buildings in three key ways:
1. They're mobile — can be deployed, relocated, and lost
2. They may be FTL-capable — allowing inter-system operations
3. They have operational ranges and fuel requirements

Drones are the swarm's eyes, hands, and reach.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DroneType(Enum):
    """All drone/node types in the swarm."""
    # Exploration
    EXPLORER = "explorer"            # Scanner probe — charts planets, flyby surveys
    DEEP_SCOUT = "deep_scout"        # Long-range explorer — can reach adjacent systems

    # Transport
    DRONE_CARRIER = "drone_carrier"  # Mobile dock — FTL, carries smaller drones between systems
    CARGO_SHUTTLE = "cargo_shuttle"  # Resource transport — moves materials between locations

    # Resource extraction
    ASTEROID_MINER = "asteroid_miner" # Mining drone — extracts from asteroids
    ORBITAL_SMELTER = "orbital_smelter" # Mobile furnace — processes raw ore in orbit

    # Surface operations
    SURFACE_PROBE = "surface_probe"  # Landed sensor package — detailed surface data
    CONSTRUCTOR = "constructor"      # Builds infrastructure on-site
    ICE_DRILLER = "ice_driller"      # Extracts water from ice deposits

    # Specialized
    RELAY = "relay"                  # Communication node — extends network range
    TERRAFORM_DRONE = "terraform_drone" # Atmospheric modification unit


@dataclass
class DroneSpec:
    """Specification for a drone type — what it does, what it costs."""
    drone_type: DroneType
    name: str
    description: str
    ftl_capable: bool = False
    survey_capability: float = 0.0     # 0-1: quality of sensor data
    mining_rate: float = 0.0           # units of ore per turn
    processing_rate: float = 0.0       # units of refined material per turn
    cargo_capacity: float = 0.0        # units of cargo
    drone_capacity: int = 0            # how many drones it can carry
    build_cost: dict = field(default_factory=dict)  # Resource → amount
    build_turns: int = 1
    fuel_per_turn: float = 0.0         # fuel cells consumed per turn of operation
    energy_per_turn_mw: float = 0.0    # energy consumed while operating

    def to_dict(self) -> dict:
        return {
            "drone_type": self.drone_type.value,
            "name": self.name,
            "description": self.description,
            "ftl_capable": self.ftl_capable,
            "survey_capability": self.survey_capability,
            "mining_rate": self.mining_rate,
            "processing_rate": self.processing_rate,
            "cargo_capacity": self.cargo_capacity,
            "drone_capacity": self.drone_capacity,
            "build_cost": self.build_cost,
            "build_turns": self.build_turns,
            "fuel_per_turn": self.fuel_per_turn,
            "energy_per_turn_mw": self.energy_per_turn_mw,
        }


# ── Drone Specifications ───────────────────────────────────────────

DRONE_SPECS = {
    DroneType.EXPLORER: DroneSpec(
        drone_type=DroneType.EXPLORER,
        name="Explorer Drone",
        description=(
            "A nimble scanner probe designed for rapid planetary surveys. "
            "Equipped with spectral analyzers, gravimetric sensors, and atmospheric sniffers. "
            "Cheap to produce, expendable, and fast. The workhorse of early exploration."
        ),
        survey_capability=0.6,
        build_cost={
            "structural_frame": 1,
            "computer_core": 1,
            "sensor_array": 1,
            "propulsion_unit": 1,
            "fuel_cell": 2,
        },
        build_turns=1,
        fuel_per_turn=0.5,
    ),

    DroneType.DEEP_SCOUT: DroneSpec(
        drone_type=DroneType.DEEP_SCOUT,
        name="Deep Scout",
        description=(
            "A long-range exploration vessel with FTL capability. "
            "Slower and more expensive than the explorer, but capable of reaching "
            "adjacent star systems to chart new colonization candidates. "
            "Carries enhanced sensor arrays for deep-space observation."
        ),
        ftl_capable=True,
        survey_capability=0.8,
        build_cost={
            "structural_frame": 3,
            "computer_core": 2,
            "sensor_array": 2,
            "propulsion_unit": 2,
            "fuel_cell": 8,
        },
        build_turns=3,
        fuel_per_turn=1.0,
    ),

    DroneType.DRONE_CARRIER: DroneSpec(
        drone_type=DroneType.DRONE_CARRIER,
        name="Drone Carrier",
        description=(
            "A mobile operations base with FTL drive and docking bays for smaller drones. "
            "Serves as a relay point and resupply station, extending the swarm's reach "
            "across interstellar distances. Essential for multi-system operations."
        ),
        ftl_capable=True,
        drone_capacity=10,
        cargo_capacity=500,
        build_cost={
            "structural_frame": 8,
            "computer_core": 3,
            "sensor_array": 1,
            "propulsion_unit": 4,
            "fuel_cell": 20,
            "carbon_fiber": 10,
        },
        build_turns=5,
        fuel_per_turn=2.0,
        energy_per_turn_mw=5.0,
    ),

    DroneType.CARGO_SHUTTLE: DroneSpec(
        drone_type=DroneType.CARGO_SHUTTLE,
        name="Cargo Shuttle",
        description=(
            "A heavy-lift transport for moving resources between orbital and surface locations, "
            "or between colonies in the same system. No FTL — system-local only. "
            "The logistical backbone once you have multiple extraction sites."
        ),
        cargo_capacity=200,
        build_cost={
            "structural_frame": 3,
            "computer_core": 1,
            "propulsion_unit": 2,
            "fuel_cell": 6,
        },
        build_turns=2,
        fuel_per_turn=1.0,
    ),

    DroneType.ASTEROID_MINER: DroneSpec(
        drone_type=DroneType.ASTEROID_MINER,
        name="Asteroid Mining Drone",
        description=(
            "An autonomous mining rig designed to latch onto asteroids and extract raw ore. "
            "Slower than surface mining but independent of planetary conditions. "
            "Particularly valuable for rare earths and fissiles, which concentrate in "
            "differentiated asteroid bodies."
        ),
        mining_rate=30.0,
        cargo_capacity=100,
        build_cost={
            "structural_frame": 2,
            "computer_core": 1,
            "sensor_array": 1,
            "propulsion_unit": 1,
            "fuel_cell": 4,
        },
        build_turns=2,
        fuel_per_turn=0.5,
    ),

    DroneType.ORBITAL_SMELTER: DroneSpec(
        drone_type=DroneType.ORBITAL_SMELTER,
        name="Orbital Smelter",
        description=(
            "A mobile processing facility that refines raw ore in orbit using solar or nuclear energy. "
            "Frees up colony surface space and can service multiple mining operations. "
            "Processes ore from asteroid miners or surface mines with limited local infrastructure."
        ),
        processing_rate=25.0,
        cargo_capacity=150,
        build_cost={
            "structural_frame": 4,
            "computer_core": 1,
            "reactor_cell": 1,
            "propulsion_unit": 1,
            "fuel_cell": 6,
        },
        build_turns=3,
        fuel_per_turn=0.5,
        energy_per_turn_mw=10.0,
    ),

    DroneType.SURFACE_PROBE: DroneSpec(
        drone_type=DroneType.SURFACE_PROBE,
        name="Surface Probe",
        description=(
            "A hardened sensor package designed for planetary landing. "
            "Provides detailed surface composition data, seismic readings, and weather monitoring. "
            "Single-use or long-duration — can operate for years on a planet's surface "
            "feeding data back to the swarm."
        ),
        survey_capability=0.95,
        build_cost={
            "structural_frame": 1,
            "computer_core": 1,
            "sensor_array": 2,
            "fuel_cell": 1,
        },
        build_turns=1,
        energy_per_turn_mw=0.5,
    ),

    DroneType.CONSTRUCTOR: DroneSpec(
        drone_type=DroneType.CONSTRUCTOR,
        name="Constructor Drone",
        description=(
            "A heavy-duty assembly platform that can build infrastructure on-site. "
            "Essential for establishing new colonies — lands with building materials "
            "and constructs the first mines, smelters, and power systems. "
            "The slowest drone to produce but the most transformative."
        ),
        build_cost={
            "structural_frame": 4,
            "computer_core": 2,
            "sensor_array": 1,
            "propulsion_unit": 1,
            "fuel_cell": 4,
        },
        build_turns=4,
        fuel_per_turn=1.0,
        energy_per_turn_mw=3.0,
    ),

    DroneType.ICE_DRILLER: DroneSpec(
        drone_type=DroneType.ICE_DRILLER,
        name="Ice Driller Drone",
        description=(
            "A specialized extraction drone for ice and frozen volatile deposits. "
            "Melts and filters ice into purified water, with byproducts of trapped gases. "
            "Deploy to ice caps, frozen moons, or comet fragments. "
            "Often the fastest path to water on arid worlds with polar ice."
        ),
        mining_rate=60.0,
        cargo_capacity=80,
        build_cost={
            "structural_frame": 2,
            "computer_core": 1,
            "propulsion_unit": 1,
            "fuel_cell": 3,
        },
        build_turns=1,
        fuel_per_turn=0.5,
    ),

    DroneType.RELAY: DroneSpec(
        drone_type=DroneType.RELAY,
        name="Relay Node",
        description=(
            "A communication relay that extends the swarm's network range. "
            "Essential for maintaining contact with distant operations. "
            "Without relays, drones beyond a certain range lose real-time coordination "
            "and must operate autonomously."
        ),
        build_cost={
            "structural_frame": 1,
            "computer_core": 1,
            "propulsion_unit": 1,
            "fuel_cell": 2,
        },
        build_turns=1,
        energy_per_turn_mw=0.5,
    ),

    DroneType.TERRAFORM_DRONE: DroneSpec(
        drone_type=DroneType.TERRAFORM_DRONE,
        name="Terraforming Drone",
        description=(
            "An atmospheric modification unit capable of processing and releasing gases "
            "in precise quantities. The active instrument of planetary engineering — "
            "injects greenhouse gases, seeds biofilms, or filters toxins. "
            "Requires enormous energy and constant monitoring."
        ),
        build_cost={
            "structural_frame": 3,
            "computer_core": 2,
            "sensor_array": 1,
            "fuel_cell": 6,
        },
        build_turns=3,
        fuel_per_turn=1.5,
        energy_per_turn_mw=15.0,
    ),
}


# ── Active Drone Instance ──────────────────────────────────────────


@dataclass
class Drone:
    """An active drone in the swarm."""
    id: str
    drone_type: DroneType
    status: str = "idle"  # idle, deploying, active, returning, damaged, lost
    location: str = ""    # planet designation, "orbit:K442-III", "deep_space", "carrier:DRN-042"
    mission: str = ""     # current mission description
    cargo: dict = field(default_factory=dict)  # resource → amount being carried
    fuel_remaining: float = 0.0
    turns_on_mission: int = 0

    @property
    def spec(self) -> DroneSpec:
        return DRONE_SPECS[self.drone_type]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "drone_type": self.drone_type.value,
            "status": self.status,
            "location": self.location,
            "mission": self.mission,
            "cargo": self.cargo,
            "fuel_remaining": self.fuel_remaining,
            "turns_on_mission": self.turns_on_mission,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Drone:
        return cls(
            id=d["id"],
            drone_type=DroneType(d["drone_type"]),
            status=d.get("status", "idle"),
            location=d.get("location", ""),
            mission=d.get("mission", ""),
            cargo=d.get("cargo", {}),
            fuel_remaining=d.get("fuel_remaining", 0.0),
            turns_on_mission=d.get("turns_on_mission", 0),
        )


# ── Fleet Summary ──────────────────────────────────────────────────


def fleet_summary(drones: list[Drone]) -> dict:
    """Summarize the drone fleet by type and status."""
    summary = {}
    for drone in drones:
        key = drone.drone_type.value
        if key not in summary:
            summary[key] = {
                "name": drone.spec.name,
                "total": 0,
                "active": 0,
                "idle": 0,
                "deploying": 0,
                "damaged": 0,
                "lost": 0,
            }
        entry = summary[key]
        entry["total"] += 1
        if drone.status in entry:
            entry[drone.status] += 1
        elif drone.status == "active":
            entry["active"] += 1
    return summary
