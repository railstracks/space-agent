"""Agent Protocol — Markdown I/O interface for LLM agents.

This is the primary interface for AI agents playing Space Agent. The game
is consumed entirely through structured Markdown documents:

1. STATE document — the agent reads this to understand the current game state
2. ACTION document — the agent writes this to declare its intentions
3. RESULT document — the engine returns this after processing the action

Usage:
    from space_agent.agents.protocol import AgentProtocol

    proto = AgentProtocol()
    state_md = proto.start_game(seed=42)
    print(state_md)  # Show initial state to the agent

    # Agent produces an action document:
    action_md = \"\"\"
    # Action — Turn 1

    ## Operations
    1. Establish colony on K442-III (Nova Haven)
    2. Survey K442-IV
    \"\"\"

    # Engine processes and returns result + new state:
    result_md, new_state_md = proto.submit_turn(action_md)

The protocol handles:
- Game creation and loading
- Markdown rendering of game state
- Markdown parsing of agent actions
- Turn processing and result rendering
- State persistence between turns
- Helper queries (describe planet, list recipes, etc.)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from space_agent.game.engine import GameEngine
from space_agent.game.action import ActionDocument, ActionType, parse_action_document
from space_agent.game.state import (
    GameState, Colony, Operation,
    new_game, save_game, load_game, list_saves,
    read_current, resolve_save_dir,
)
from space_agent.game.resolver import TurnResult
from space_agent.simulation.resources import RECIPES, BUILD_COSTS, BuildingType, Resource
from space_agent.simulation.planet import Planet
from space_agent.agents.renderer import render_star, render_planet_table, render_planet_detail
from space_agent.agents.describe import describe


@dataclass
class TurnResponse:
    """Result of processing a turn.

    Attributes:
        result_md: Markdown document describing what happened this turn.
        state_md: Markdown document showing the new game state.
        turn: The turn number that was just processed.
        events: List of event dicts from this turn.
    """
    result_md: str
    state_md: str
    turn: int
    events: list[dict]


class AgentProtocol:
    """The Markdown-based interface between Space Agent and an AI agent.

    This class wraps GameEngine with a clean Markdown-in/Markdown-out API
    that makes it trivial for any LLM to play Space Agent. The agent never
    needs to touch Python objects directly — it reads Markdown state, writes
    Markdown actions, and receives Markdown results.

    State is persisted to disk via JSON save files, so the game survives
    across sessions. The .current pointer tracks which save is active.
    """

    def __init__(self, save_dir: str = "saves"):
        self.save_dir = Path(save_dir)
        self.engine = GameEngine(save_dir=str(self.save_dir))

    # ── Game Lifecycle ──────────────────────────────────────────────

    def start_game(
        self,
        save_name: str = "game_001",
        seed: Optional[int] = None,
        star_name: str = "Kepler-442",
        num_planets: int = 5,
        credits: float = 5000.0,
    ) -> str:
        """Create a new game and return the initial state as Markdown.

        This is the entry point. The agent receives this document and
        decides its first action.

        Args:
            save_name: Name for the save file (no extension).
            seed: Random seed for reproducibility. None = random.
            star_name: Name of the star system.
            num_planets: Number of planets to generate.
            credits: Starting program credits.

        Returns:
            Markdown state document for turn 0.
        """
        state = new_game(
            save_name=save_name,
            seed=seed,
            star_name=star_name,
            num_planets=num_planets,
            credits=credits,
            save_dir=str(self.save_dir),
        )
        return self.engine.render_state(state)

    def load_game(self, save_name: Optional[str] = None) -> str:
        """Load an existing game and return current state as Markdown.

        Args:
            save_name: Specific save to load. None uses .current pointer.

        Returns:
            Markdown state document for the current turn.
        """
        save_dir = resolve_save_dir(self.save_dir)
        state = load_game(save_dir, save_name)
        return self.engine.render_state(state)

    # ── Turn Processing ────────────────────────────────────────────

    def submit_turn(self, action_md: str, save_name: Optional[str] = None) -> TurnResponse:
        """Process one turn from a Markdown action document.

        This is the core game loop step. The agent writes a Markdown
        action document, and this method:
        1. Parses the action
        2. Applies it to the game state
        3. Resolves the turn (colony production, events, etc.)
        4. Saves the updated state
        5. Returns the result and new state as Markdown

        Args:
            action_md: Markdown action document from the agent.
            save_name: Specific save to use. None uses .current pointer.

        Returns:
            TurnResponse with result, state, turn number, and events.
        """
        save_dir = resolve_save_dir(self.save_dir)
        current = save_name or read_current(save_dir)
        if current is None:
            raise FileNotFoundError("No current save. Use start_game() first.")

        state = load_game(save_dir, current)

        # Parse the action document
        action_doc = parse_action_document(action_md, turn=state.turn + 1)

        # Process the turn
        result = self.engine.process_turn(state, action_doc)

        # Save the updated state
        save_game(state, save_dir)

        # Render results
        result_md = self.engine.render_result(result, state)
        state_md = self.engine.render_state(state)

        return TurnResponse(
            result_md=result_md,
            state_md=state_md,
            turn=state.turn,
            events=result.events if hasattr(result, 'events') else [],
        )

    def continue_turn(self, save_name: Optional[str] = None) -> TurnResponse:
        """Process a 'continue' turn (no agent actions, just advance time).

        Useful for turns where the agent wants to wait for construction
        or operations to complete without taking new actions.

        Args:
            save_name: Specific save to use. None uses .current pointer.

        Returns:
            TurnResponse with result, state, turn number, and events.
        """
        save_dir = resolve_save_dir(self.save_dir)
        current = save_name or read_current(save_dir)
        if current is None:
            raise FileNotFoundError("No current save. Use start_game() first.")

        state = load_game(save_dir, current)
        action_doc = ActionDocument(
            turn=state.turn + 1,
            actions=[],
        )

        result = self.engine.process_turn(state, action_doc)
        save_game(state, save_dir)

        result_md = self.engine.render_result(result, state)
        state_md = self.engine.render_state(state)

        return TurnResponse(
            result_md=result_md,
            state_md=state_md,
            turn=state.turn,
            events=result.events if hasattr(result, 'events') else [],
        )

    # ── Query Methods ──────────────────────────────────────────────

    def describe_planet(self, designation: str, save_name: Optional[str] = None) -> str:
        """Get a detailed narrative description of a planet.

        Args:
            designation: Planet designation (e.g. "K442-III").
            save_name: Save to use. None uses .current pointer.

        Returns:
            Markdown document with data and narrative description.
        """
        save_dir = resolve_save_dir(self.save_dir)
        current = save_name or read_current(save_dir)
        state = load_game(save_dir, current)
        planets = state.get_planets()

        planet = None
        for p in planets:
            if p.designation == designation or p.designation.endswith(designation) or p.name == designation:
                planet = p
                break

        if planet is None:
            available = ", ".join(p.designation for p in planets)
            return f"Planet not found: {designation}\nAvailable: {available}"

        lines = [
            f"# {planet.designation} — {planet.name}",
            "",
            render_planet_detail(planet),
            "",
            "## Narrative",
            "",
            describe(planet),
        ]
        return "\n".join(lines)

    def list_recipes(self) -> str:
        """List all available production recipes as Markdown.

        Recipes define what buildings can produce, their inputs, outputs,
        energy costs, and build times. This is essential reference material
        for agents planning production chains.

        Returns:
            Markdown table of all recipes.
        """
        lines = [
            "# Production Recipes",
            "",
            "| Recipe | Building | Inputs | Outputs | Energy (MW) |",
            "|--------|----------|--------|---------|-------------|",
        ]

        for key, recipe in sorted(RECIPES.items()):
            inputs_str = ", ".join(
                f"{amt:.0f} {r.value if isinstance(r, Resource) else r}"
                for r, amt in recipe.inputs.items()
            ) or "—"
            outputs_str = ", ".join(
                f"{amt:.0f} {r.value if isinstance(r, Resource) else r}"
                for r, amt in recipe.outputs.items()
            ) or "—"
            building = recipe.building.value if hasattr(recipe.building, 'value') else str(recipe.building)
            lines.append(f"| {key} | {building} | {inputs_str} | {outputs_str} | {recipe.energy_mw:.0f} |")

        return "\n".join(lines)

    def list_buildings(self) -> str:
        """List all buildable structures as Markdown.

        Returns:
            Markdown table of building types, costs, and build times.
        """
        lines = [
            "# Building Types",
            "",
            "| Building | Build Cost | Build Turns | Description |",
            "|----------|------------|-------------|-------------|",
        ]

        for key, cost in sorted(BUILD_COSTS.items()):
            cost_str = ", ".join(
                f"{amt:.0f} {r.value if isinstance(r, Resource) else r}"
                for r, amt in cost.costs.items()
            ) or "—"
            desc = cost.name
            lines.append(f"| {key.replace('_', ' ').title()} | {cost_str} | {cost.build_turns} | {desc} |")

        return "\n".join(lines)

    def colony_status(self, colony_index: int = 0, save_name: Optional[str] = None) -> str:
        """Get detailed status of a specific colony.

        Shows buildings, stockpile, energy, and production capacity.

        Args:
            colony_index: Index of the colony in the colonies list (0-based).
            save_name: Save to use. None uses .current pointer.

        Returns:
            Markdown document with detailed colony status.
        """
        save_dir = resolve_save_dir(self.save_dir)
        current = save_name or read_current(save_dir)
        state = load_game(save_dir, current)

        if colony_index >= len(state.colonies):
            return f"No colony at index {colony_index}. Only {len(state.colonies)} colonies exist."

        c_data = state.colonies[colony_index]
        c = Colony.from_dict(c_data) if isinstance(c_data, dict) else c_data

        lines = [
            f"# Colony Status: {c.name} ({c.planet_designation})",
            "",
            f"- **Population:** {c.population}",
            f"- **Morale:** {c.morale}",
            f"- **Founded:** Turn {c.founded_turn}",
            "",
        ]

        # Energy
        energy_prod = c_data.get("energy_production_mw", 0.0) if isinstance(c_data, dict) else c.energy_production_mw
        energy_cons = c_data.get("energy_consumption_mw", 0.0) if isinstance(c_data, dict) else c.energy_consumption_mw
        energy_net = c_data.get("energy_net_mw", 0.0) if isinstance(c_data, dict) else c.energy_net_mw

        lines.append("## Energy")
        lines.append(f"- Production: **{energy_prod:.0f} MW**")
        lines.append(f"- Consumption: {energy_cons:.0f} MW")
        net_icon = "⚡" if energy_net >= 0 else "⚠️"
        lines.append(f"- Net: {net_icon} **{energy_net:+.0f} MW**")
        lines.append("")

        # Stockpile
        stockpile = c_data.get("stockpile", {}) if isinstance(c_data, dict) else {}
        if stockpile:
            lines.append("## Stockpile")
            lines.append("| Resource | Amount |")
            lines.append("|----------|--------|")
            for resource, amount in sorted(stockpile.items()):
                if amount > 0:
                    lines.append(f"| {resource.replace('_', ' ').title()} | {amount:.1f} |")
            lines.append("")

        # Buildings
        buildings = c_data.get("buildings", []) if isinstance(c_data, dict) else []
        if buildings:
            lines.append("## Buildings")
            lines.append("| ID | Type | Status | Recipe | Turns Left |")
            lines.append("|----|------|--------|--------|-------------|")
            for b in buildings:
                bid = b.get("id", "?")
                kind = b.get("kind", "?").replace("_", " ").title()
                status = b.get("status", "?")
                recipe = b.get("recipe", "—") or "—"
                turns = b.get("turns_remaining", 0)
                turns_str = str(turns) if turns > 0 else "—"
                lines.append(f"| {bid} | {kind} | {status} | {recipe} | {turns_str} |")
            lines.append("")

        # Available recipes for current buildings
        idle_buildings = [b for b in buildings if b.get("status") in ("idle",) and not b.get("recipe")]
        if idle_buildings:
            lines.append("## Unassigned Buildings")
            lines.append("These buildings are idle and need a recipe assigned:")
            for b in idle_buildings:
                bid = b.get("id", "?")
                kind = b.get("kind", "?")
                # Find applicable recipes
                applicable = [
                    name for name, recipe in RECIPES.items()
                    if hasattr(recipe, 'building_type') and
                    recipe.building_type.value == kind
                ]
                if applicable:
                    lines.append(f"- **{bid}** ({kind.replace('_', ' ')}): available recipes: {', '.join(applicable)}")
                else:
                    lines.append(f"- **{bid}** ({kind.replace('_', ' ')}): no recipes (passive building)")
            lines.append("")

        return "\n".join(lines)

    def help_document(self) -> str:
        """Return a comprehensive help document for agents.

        This document explains the game mechanics, action format, and
        available commands. It's designed to be given to an LLM agent
        as context before gameplay begins.

        Returns:
            Markdown help document.
        """
        return """# Space Agent — Agent Guide

## Concept

You are a seed AI — a distributed intelligence sent ahead of colony ships to
prepare a star system for human colonization. The ships are coming. They will
arrive whether the planets are ready or not. Your job: make them ready.

## How to Play

Each turn, you receive a **state document** describing your colonies, resources,
and available actions. You respond with an **action document** declaring your
intentions. The engine processes your actions and returns a **result document**.

## Action Document Format

```markdown
# Action — Turn N

## Operations
1. Build mine on K442-III
2. Assign recipe mine_iron to mine_01 at K442-III
3. Deploy surface probe to K442-IV
4. Continue terraforming K442-III (CO2 injection)

## Resource Allocation
- Energy: 200 MW to production, 50 MW to research

## Research
- Begin: subsurface detection (allocate 30 MW)

## Notes
[Your reasoning — ignored by engine, useful for planning]
```

## Available Actions

- **Establish colony on [planet]** — Found a new colony on a surveyed planet
- **Build [building] on [planet]** — Construct a building at a colony
- **Assign recipe [recipe] to [building_id]** — Configure what a building produces
- **Deploy [drone_type] to [planet]** — Send a drone/probe
- **Survey [planet]** — Get detailed planetary data
- **Terraform [intervention] on [planet]** — Begin terraforming
- **Research [topic]** — Begin a research project
- **Continue** — Advance time without new actions

## Building Types

- **mine** — Extracts raw ore (assign: mine_iron, mine_aluminum, mine_titanium)
- **smelter** — Refines ore into metals (assign: smelt_iron, smelt_aluminum, smelt_titanium)
- **solar_array** — Generates electricity from starlight (passive, no recipe)
- **nuclear_reactor** — Generates electricity from enriched fuel (passive, needs fuel)
- **geothermal_tap** — Generates electricity from planetary heat (passive)
- **atmospheric_extractor** — Extracts atmospheric gases (assign: extract_co2, extract_nitrogen)
- **ice_drill** — Extracts water from ice deposits (assign: drill_ice)
- **chemical_processor** — Processes gases (assign: process_carbon, process_methane)
- **electrolyzer** — Splits water into hydrogen and oxygen (assign: electrolyze_water)
- **fabricator** — Manufactures components (assign: fab_frame, fab_circuit, fab_cell)
- **assembly_bay** — Assembles systems from components (assign: assemble_habitat, etc.)
- **research_lab** — Generates research points (passive, consumes energy)
- **terraform_engine** — Accelerates terraforming (passive, consumes energy)

## Production Chains

The key production chains are:

1. **Iron chain:** mine_iron → smelt_iron → (refined_iron for fabricators)
2. **Aluminum chain:** mine_aluminum → smelt_aluminum → (refined_aluminum for fabricators)
3. **Water chain:** drill_ice → electrolyze_water → (hydrogen + oxygen)
4. **Carbon chain:** extract_co2 → process_carbon → (carbon + carbon fiber)
5. **Electronics chain:** mine + smelter → silicates → processed_silicon → circuit_substrate
6. **Energy chain:** solar/nuclear/geothermal → powers everything
7. **Assembly chain:** structural_frame + circuit_substrate + reactor_cell → assembled systems

## Energy

Energy is the master constraint. Every building that runs a recipe consumes energy.
If your colony's energy production < consumption, buildings go idle.

**Solar output** depends on the planet's distance from the star:
- Inner planets (close orbit): Very high solar, but very hot
- Outer planets (habitable zone): Moderate solar, livable temperatures
- Far planets: Minimal solar, but you can use nuclear or geothermal

**Nuclear reactors** need enriched_fuel (from uranium_ore + processing).
**Geothermal taps** work better on tectonically active planets (high iron core fraction).

## Tips

1. **Start with survey** — Survey planets before committing to colonization
2. **Build power first** — Solar arrays are cheap; nuclear needs fuel infrastructure
3. **Mine before processing** — Raw materials must come before refining
4. **Watch energy budget** — Energy deficit = idle buildings = wasted turns
5. **Production chains matter** — A fabricator without refined metals is useless
6. **Habitability isn't everything** — A harsh world with good energy might outproduce a comfortable one
7. **Use the colony_status command** to see what buildings need recipes
8. **Inner planets have extreme solar flux** — 800+ MW per array, but lethal temperatures
9. **Assign recipes to idle buildings** — Idle buildings with no recipe produce nothing
"""

    # ── Convenience Methods ─────────────────────────────────────────

    def get_state(self, save_name: Optional[str] = None) -> str:
        """Get the current game state as Markdown (without processing a turn).

        Useful for refreshing the agent's view of the game state.

        Args:
            save_name: Save to use. None uses .current pointer.

        Returns:
            Markdown state document.
        """
        save_dir = resolve_save_dir(self.save_dir)
        current = save_name or read_current(save_dir)
        if current is None:
            raise FileNotFoundError("No current save. Use start_game() first.")

        state = load_game(save_dir, current)
        return self.engine.render_state(state)

    def get_raw_state(self, save_name: Optional[str] = None) -> GameState:
        """Get the raw GameState object for programmatic access.

        For advanced use cases where Markdown isn't enough.

        Args:
            save_name: Save to use. None uses .current pointer.

        Returns:
            GameState object.
        """
        save_dir = resolve_save_dir(self.save_dir)
        current = save_name or read_current(save_dir)
        if current is None:
            raise FileNotFoundError("No current save. Use start_game() first.")

        return load_game(save_dir, current)

    def list_saves(self) -> str:
        """List all save files as a Markdown table.

        Returns:
            Markdown table of save files.
        """
        save_dir = resolve_save_dir(self.save_dir)
        saves = list_saves(save_dir)

        if not saves:
            return "No saves found."

        lines = [
            "# Save Files",
            "",
            "| Current | Name | Turn | Colonies | Last Played |",
            "|---------|------|------|----------|-------------|",
        ]

        current = read_current(save_dir)
        for s in saves:
            marker = "→" if s["name"] == current else ""
            lines.append(
                f"| {marker} | {s['name']} | {s['turn']} | {s['colonies']} | "
                f"{str(s.get('last_played', '?'))[:10]} |"
            )

        return "\n".join(lines)

    def delete_save(self, save_name: str) -> str:
        """Delete a save file.

        Args:
            save_name: Name of the save to delete.

        Returns:
            Confirmation message.
        """
        save_dir = resolve_save_dir(self.save_dir)
        path = save_dir / f"{save_name}.json"
        if not path.exists():
            return f"Save not found: {save_name}"

        path.unlink()

        # Clear .current if this was the active save
        current = read_current(save_dir)
        if current == save_name:
            (save_dir / ".current").unlink(missing_ok=True)
            return f"Deleted {save_name} (was active save)."
        return f"Deleted {save_name}."