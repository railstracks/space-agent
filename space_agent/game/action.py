"""Action parser — converts Markdown action documents to structured commands.

The agent writes Markdown. The engine needs structured data. This module
bridges the gap by parsing action documents into BuildAction, DeployAction,
ResearchAction, TerraformAction, and AllocationAction objects.

Action format (from AGENT-PROTOCOL.md):

    # Action — Turn N

    ## Resource Allocation
    - Energy: 600 MW to terraforming, 180 MW to production, 60 MW to operations
    - Metals: 200 to construction, 50 to maintenance

    ## Operations
    1. Continue terraforming K442-III (CO₂ injection, maintain current rate)
    2. Deploy surface node to anomaly 7-G — build ice drill
    3. Queue scout node construction (when fabricator free)

    ## Research
    - Begin: subsurface detection methods (allocate 40 MW to research lab)

    ## Notes
    [Free-form agent reasoning — ignored by engine]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Action Types ──────────────────────────────────────────────────


class ActionType(Enum):
    """Categories of actions the agent can take."""
    BUILD = "build"           # Construct a building
    DEPLOY = "deploy"         # Deploy a drone/probe to a location
    ASSIGN = "assign"         # Assign a recipe to a building
    RESEARCH = "research"     # Begin a research project
    TERRAFORM = "terraform"   # Initiate terraforming intervention
    ALLOCATE = "allocate"     # Allocate energy/resources
    CONTINUE = "continue"     # Continue current operations unchanged
    SURVEY = "survey"         # Survey a planet/sector


@dataclass
class Action:
    """A single action from the agent."""
    action_type: ActionType
    target: str = ""          # What it targets (planet, building, etc.)
    params: dict = field(default_factory=dict)  # Action-specific parameters
    priority: int = 0         # Execution priority (0 = first)
    notes: str = ""           # Agent's reasoning (preserved but not executed)

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type.value,
            "target": self.target,
            "params": self.params,
            "priority": self.priority,
            "notes": self.notes,
        }


@dataclass
class ActionDocument:
    """A complete action document from the agent for one turn."""
    turn: int
    actions: list[Action] = field(default_factory=list)
    energy_allocation: dict[str, float] = field(default_factory=dict)
    resource_allocation: dict[str, dict[str, float]] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "turn": self.turn,
            "actions": [a.to_dict() for a in self.actions],
            "energy_allocation": self.energy_allocation,
            "resource_allocation": self.resource_allocation,
            "notes": self.notes,
        }


# ── Parsing ────────────────────────────────────────────────────────

from space_agent.simulation.resources import RECIPES as RECIPES_REGISTRY

# Building names that can appear in actions
BUILDING_KEYWORDS = {
    "mine": "mine",
    "smelter": "smelter",
    "fabricator": "fabricator",
    "assembly bay": "assembly_bay",
    "assembly": "assembly_bay",
    "solar array": "solar_array",
    "solar": "solar_array",
    "nuclear reactor": "nuclear_reactor",
    "reactor": "nuclear_reactor",
    "geothermal tap": "geothermal_tap",
    "geothermal": "geothermal_tap",
    "chemical processor": "chemical_processor",
    "processor": "chemical_processor",
    "electrolyzer": "electrolyzer",
    "atmospheric extractor": "atmospheric_extractor",
    "extractor": "atmospheric_extractor",
    "ice drill": "ice_drill",
    "research lab": "research_lab",
    "lab": "research_lab",
    "terraform engine": "terraform_engine",
    "terraform": "terraform_engine",
}

DRONE_KEYWORDS = {
    "scout": "scout",
    "explorer": "scout",
    "orbiter": "orbiter",
    "surface node": "surface_node",
    "surface probe": "surface_node",
    "deep scout": "deep_scout",
    "cargo shuttle": "cargo_shuttle",
    "asteroid miner": "asteroid_miner",
    "miner": "asteroid_miner",
    "relay": "relay",
    "constructor": "constructor",
    "drone carrier": "drone_carrier",
    "carrier": "drone_carrier",
    "ice driller": "ice_driller",
    "terraform drone": "terraform_drone",
}

TERRAFORM_KEYWORDS = {
    "co2 injection": "co2_injection",
    "co₂ injection": "co2_injection",
    "carbon dioxide": "co2_injection",
    "orbital mirror": "orbital_mirror",
    "mirror": "orbital_mirror",
    "shade": "orbital_shade",
    "orbital shade": "orbital_shade",
    "asteroid bombardment": "asteroid_bombardment",
    "bombardment": "asteroid_bombardment",
    "biome seeding": "biome_seeding",
    "seeding": "biome_seeding",
    "magnetic field": "magnetic_field_generator",
    "magnetosphere": "magnetic_field_generator",
    "crustal": "crustal_engineering",
    "geothermal tap": "geothermal_tap",
}

RESEARCH_KEYWORDS = {
    "subsurface detection": "subsurface_detection",
    "detection": "subsurface_detection",
    "atmospheric processing": "atmospheric_processing",
    "advanced mining": "advanced_mining",
    "terraforming efficiency": "terraforming_efficiency",
    "propulsion": "advanced_propulsion",
    "construction": "advanced_construction",
    "energy storage": "energy_storage",
    "sensor": "sensor_technology",
    "communication": "communication_relays",
}


def parse_action_document(text: str, turn: int = 0) -> ActionDocument:
    """Parse a Markdown action document into structured actions.

    This is a flexible parser that handles the agent protocol format.
    It's deliberately lenient — it extracts what it can and ignores
    what it doesn't understand.
    """
    doc = ActionDocument(turn=turn)

    lines = text.strip().split("\n")
    current_section = None
    action_index = 0

    for line in lines:
        stripped = line.strip()

        # Section headers
        if stripped.startswith("# "):
            # Top-level header — extract turn number if present
            turn_match = re.search(r"turn\s+(\d+)", stripped, re.IGNORECASE)
            if turn_match:
                doc.turn = int(turn_match.group(1))
            continue

        if stripped.startswith("## "):
            section_name = stripped[3:].lower().strip()
            if "resource" in section_name and "alloc" in section_name:
                current_section = "energy_allocation"
            elif "operation" in section_name:
                current_section = "operations"
            elif "research" in section_name:
                current_section = "research"
            elif "note" in section_name:
                current_section = "notes"
            else:
                current_section = section_name
            continue

        # Skip empty lines
        if not stripped:
            continue

        # Parse based on current section
        if current_section == "energy_allocation":
            _parse_energy_line(stripped, doc)

        elif current_section == "operations":
            action = _parse_operation_line(stripped, action_index)
            if action:
                doc.actions.append(action)
                action_index += 1

        elif current_section == "research":
            action = _parse_research_line(stripped, action_index)
            if action:
                doc.actions.append(action)
                action_index += 1

        elif current_section == "notes":
            doc.notes += stripped + "\n"

    return doc


def _parse_energy_line(line: str, doc: ActionDocument) -> None:
    """Parse an energy allocation line like 'Energy: 600 MW to terraforming'."""
    # "Energy: 600 MW to terraforming, 180 MW to production"
    energy_match = re.findall(r"(\d+(?:\.\d+)?)\s*MW\s+to\s+(\w+(?:\s+\w+)*)", line)
    for amount_str, category in energy_match:
        doc.energy_allocation[category.strip().lower().replace(" ", "_")] = float(amount_str)

    # "Metals: 200 to construction, 50 to maintenance"
    resource_match = re.match(r"(\w+)\s*:\s+(.+)", line, re.IGNORECASE)
    if resource_match:
        resource_name = resource_match.group(1).lower()
        if resource_name not in ("energy", "e"):
            allocations = re.findall(r"(\d+(?:\.\d+)?)\s+to\s+(\w+)", resource_match.group(2))
            if allocations:
                doc.resource_allocation[resource_name] = {
                    cat: float(amt) for amt, cat in allocations
                }


def _parse_operation_line(line: str, index: int) -> Optional[Action]:
    """Parse a numbered operation line like '1. Build mine on K442-III'."""
    # Strip leading number
    line = re.sub(r"^\d+[\.\)]\s*", "", line)
    line_lower = line.lower().strip()

    if not line_lower:
        return None

    # Build actions
    for keyword, building_type in BUILDING_KEYWORDS.items():
        if keyword in line_lower and ("build" in line_lower or "construct" in line_lower or "queue" in line_lower):
            # Extract planet target
            planet = _extract_planet(line)
            return Action(
                action_type=ActionType.BUILD,
                target=planet or "",
                params={"building_type": building_type},
                priority=index,
                notes=line,
            )

    # Deploy actions
    if "deploy" in line_lower:
        planet = _extract_planet(line)
        for keyword, drone_type in DRONE_KEYWORDS.items():
            if keyword in line_lower:
                return Action(
                    action_type=ActionType.DEPLOY,
                    target=planet or "",
                    params={"drone_type": drone_type},
                    priority=index,
                    notes=line,
                )
        # Generic deploy
        return Action(
            action_type=ActionType.DEPLOY,
            target=planet or "",
            params={},
            priority=index,
            notes=line,
        )

    # Assign actions (assign recipe to building)
    if "assign" in line_lower or "set" in line_lower or "configure" in line_lower:
        # Try to match known recipe names from RECIPES first
        recipe_name = ""
        for rkey in RECIPES_REGISTRY:
            if rkey in line_lower:
                recipe_name = rkey
                break

        # If no recipe found, try extracting after 'recipe' keyword
        if not recipe_name:
            recipe_match = re.search(r"recipe\s+(\w+(?:_\w+)*)", line_lower)
            if recipe_match:
                recipe_name = recipe_match.group(1)

        # Extract building ID (e.g., mine_02)
        building_id = _extract_building_id(line)
        planet = _extract_planet(line)

        return Action(
            action_type=ActionType.ASSIGN,
            target=building_id,
            params={"recipe": recipe_name, "planet": planet},
            priority=index,
            notes=line,
        )

    # Terraform actions
    for keyword, intervention in TERRAFORM_KEYWORDS.items():
        if keyword in line_lower:
            planet = _extract_planet(line)
            return Action(
                action_type=ActionType.TERRAFORM,
                target=planet or "",
                params={"intervention": intervention},
                priority=index,
                notes=line,
            )

    # Survey actions
    if "survey" in line_lower:
        planet = _extract_planet(line)
        return Action(
            action_type=ActionType.SURVEY,
            target=planet or "",
            params={},
            priority=index,
            notes=line,
        )

    # Establish colony actions
    if "establish" in line_lower or "colon" in line_lower or "settle" in line_lower or "found" in line_lower:
        planet = _extract_planet(line)
        return Action(
            action_type=ActionType.BUILD,
            target=planet or "",
            params={"building_type": "colony"},
            priority=index,
            notes=line,
        )

    # Continue actions
    if "continue" in line_lower:
        return Action(
            action_type=ActionType.CONTINUE,
            target=_extract_planet(line) or "",
            params={},
            priority=index,
            notes=line,
        )

    # Unrecognized — store as a note action
    return Action(
        action_type=ActionType.CONTINUE,
        target="",
        params={"unparsed": True},
        priority=index,
        notes=line,
    )


def _parse_research_line(line: str, index: int) -> Optional[Action]:
    """Parse a research line like 'Begin: subsurface detection methods'."""
    line = re.sub(r"^[-•]\s*", "", line)
    line_lower = line.lower().strip()

    # Extract topic
    topic = ""
    if ":" in line:
        topic = line.split(":", 1)[1].strip()
    elif line_lower.startswith(("begin", "start", "research")):
        topic = re.sub(r"^(begin|start|research)\s*", "", line_lower).strip()

    research_key = ""
    for keyword, key in RESEARCH_KEYWORDS.items():
        if keyword in topic.lower():
            research_key = key
            break

    if not research_key and topic:
        research_key = topic.lower().replace(" ", "_")

    # Extract MW allocation
    mw = 0.0
    mw_match = re.search(r"(\d+(?:\.\d+)?)\s*MW", line)
    if mw_match:
        mw = float(mw_match.group(1))

    return Action(
        action_type=ActionType.RESEARCH,
        target=research_key or "unknown",
        params={"energy_mw": mw},
        priority=index,
        notes=line,
    )


def _extract_planet(text: str) -> str:
    """Extract a planet designation from text.

    Matches patterns like:
    - K442-III, K442-III, Kepler-442-III
    - "planet 3", "the third planet"
    - Any word starting with capital K followed by digits
    """
    # Match K###-X pattern
    match = re.search(r"[Kk]\d+-[IVXivx]+", text)
    if match:
        return match.group(0).upper()

    # Match Kepler-###-X pattern
    match = re.search(r"Kepler-\d+-[IVXivx]+", text, re.IGNORECASE)
    if match:
        return match.group(0)

    # Match "planet N" or "the Nth planet"
    match = re.search(r"planet\s+(\d+|[IVXivx]+)", text, re.IGNORECASE)
    if match:
        return match.group(1)

    return ""


def _extract_building_id(text: str) -> str:
    """Extract a building ID from text.

    Matches patterns like:
    - mine_01, smelter_02, fabricator_01
    - "building mine_01"
    """
    match = re.search(r"(\w+_\d{2})", text)
    if match:
        return match.group(1)
    return ""