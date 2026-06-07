"""Game state management — JSON save files with .current pointer.

State is stored as JSON files in a save directory:
  saves/
    .current          → "game_001" (just the save name, no extension)
    game_001.json     → full galaxy state
    game_001.log      → turn-by-turn log (append-only Markdown)

The .current file is a single line containing the active save name.
If missing or empty, commands that need a loaded game will error.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

from space_agent.simulation.planet import Planet, Star, Atmosphere, generate_system


# ── data structures ────────────────────────────────────────────────


@dataclass
class Colony:
    """A colony on a planet."""
    name: str
    planet_designation: str  # references Planet.designation
    population: int = 0
    morale: str = "HOPEFUL"  # HOPEFUL, CAUTIOUS, OPTIMISTIC, DESPERATE, THRIVING
    founded_turn: int = 0

    # Resource stockpiles at colony
    water: float = 0.0
    metals: float = 0.0
    energy: float = 0.0
    organics: float = 0.0
    rare_earths: float = 0.0

    # Infrastructure
    habitat_modules: int = 0
    atmospheric_processors: int = 0
    mining_rigs: int = 0
    research_labs: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Colony:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Operation:
    """An active operation (survey, mission, terraforming step, etc.)."""
    id: str
    kind: str  # "probe", "colony_ship", "terraforming", "research", "asteroid_capture"
    status: str  # "in_progress", "complete", "failed"
    target: str  # planet designation or sector
    started_turn: int = 0
    eta_turn: int = 0  # turn number when it resolves
    resource_cost: dict = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert Resource keys to strings for JSON serialization
        if isinstance(d.get("resource_cost"), dict):
            d["resource_cost"] = {str(k): v for k, v in d["resource_cost"].items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Operation:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class GameState:
    """Complete game state — one JSON save file."""
    # Meta
    save_name: str = "untitled"
    created_at: str = ""
    last_played: str = ""
    turn: int = 0
    turn_period_years: float = 5.0  # how many in-game years per turn
    seed: int = 42

    # Program resources (the colonization program, not individual colonies)
    credits: float = 5000.0
    probe_capacity: int = 1
    research_points: float = 0.0

    # Galaxy
    star: Optional[dict] = None  # Star serialized
    planets: list[dict] = field(default_factory=list)  # Planet list serialized
    explored: list[str] = field(default_factory=list)  # designations with orbital data
    surveyed: list[str] = field(default_factory=list)  # designations with surface data

    # Colonies and operations
    colonies: list[dict] = field(default_factory=list)
    operations: list[dict] = field(default_factory=list)

    # Event log (turn number → event text)
    events: list[dict] = field(default_factory=list)

    # Terraforming history
    terraforming_log: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> GameState:
        known = {k for k in d if k in cls.__dataclass_fields__}
        return cls(**{k: d[k] for k in known})

    def get_star(self) -> Optional[Star]:
        if self.star is None:
            return None
        return Star(**self.star)

    def get_planets(self) -> list[Planet]:
        star = self.get_star()
        planets = []
        for pd in self.planets:
            # Deep copy to avoid mutating the stored dict
            pd = dict(pd)
            atm = pd.pop("atmosphere", {})
            pd.pop("_surface_gravity", None)
            pd.pop("_escape_velocity", None)
            pd.pop("_base_temperature_k", None)
            pd.pop("_magnetic_field_earth_normal", None)
            pd.pop("star", None)  # Use the star from game state
            atm_obj = Atmosphere(**atm) if atm else Atmosphere()
            planet = Planet(**{k: v for k, v in pd.items() if k in Planet.__dataclass_fields__},
                           star=star, atmosphere=atm_obj)
            planets.append(planet)
        return planets


# ── save file operations ───────────────────────────────────────────


def resolve_save_dir(save_dir: str | Path) -> Path:
    """Ensure save directory exists."""
    p = Path(save_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_current(save_dir: Path) -> Optional[str]:
    """Read the .current pointer file. Returns save name or None."""
    current_file = save_dir / ".current"
    if not current_file.exists():
        return None
    name = current_file.read_text().strip()
    if not name:
        return None
    # Verify the save file exists
    if not (save_dir / f"{name}.json").exists():
        return None
    return name


def write_current(save_dir: Path, save_name: str) -> None:
    """Write the .current pointer file."""
    (save_dir / ".current").write_text(save_name)


def save_game(state: GameState, save_dir: Path) -> Path:
    """Save game state to JSON. Updates .current."""
    resolve_save_dir(save_dir)
    state.last_played = datetime.now(timezone.utc).isoformat()
    path = save_dir / f"{state.save_name}.json"
    path.write_text(json.dumps(state.to_dict(), indent=2))
    write_current(save_dir, state.save_name)
    return path


def load_game(save_dir: Path, save_name: Optional[str] = None) -> GameState:
    """Load game state from JSON. Uses .current if no name given."""
    if save_name is None:
        save_name = read_current(save_dir)
        if save_name is None:
            raise FileNotFoundError("No .current save found and no name specified")

    path = save_dir / f"{save_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Save file not found: {path}")

    data = json.loads(path.read_text())
    return GameState.from_dict(data)


def list_saves(save_dir: Path) -> list[dict]:
    """List all save files with metadata."""
    saves = []
    for f in sorted(save_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            saves.append({
                "name": data.get("save_name", f.stem),
                "turn": data.get("turn", 0),
                "last_played": data.get("last_played", "unknown"),
                "colonies": len(data.get("colonies", [])),
            })
        except (json.JSONDecodeError, KeyError):
            saves.append({"name": f.stem, "turn": "?", "last_played": "?", "colonies": "?"})
    return saves


# ── new game creation ──────────────────────────────────────────────

import random as _random


def new_game(
    save_name: str = "game_001",
    seed: int | None = None,
    star_name: str = "Kepler-442",
    num_planets: int = 5,
    credits: float = 5000.0,
    save_dir: str | Path = "saves",
) -> GameState:
    """Create a new game with a generated star system."""
    if seed is None:
        seed = _random.randint(0, 2**31)

    rng = _random.Random(seed)
    star, planets = generate_system(rng, star_name=star_name, num_planets=num_planets)

    state = GameState(
        save_name=save_name,
        created_at=datetime.now(timezone.utc).isoformat(),
        last_played=datetime.now(timezone.utc).isoformat(),
        turn=0,
        seed=seed,
        credits=credits,
        star={
            "name": star.name,
            "spectral_type": star.spectral_type,
            "luminosity_solar": star.luminosity_solar,
            "mass_solar": star.mass_solar,
            "temperature_k": star.temperature_k,
            "age_gyr": star.age_gyr,
        },
        planets=[_planet_to_dict(p) for p in planets],
        events=[{
            "turn": 0,
            "text": f"Colonization program established. Target system: {star_name}.",
        }],
    )

    save_game(state, Path(save_dir))
    return state


def _planet_to_dict(p: Planet) -> dict:
    """Serialize a Planet to a JSON-safe dict."""
    d = {}
    for k in Planet.__dataclass_fields__:
        v = getattr(p, k)
        if isinstance(v, Atmosphere):
            d[k] = asdict(v)
        elif isinstance(v, Star):
            d[k] = asdict(v)
        else:
            d[k] = v
    return d
