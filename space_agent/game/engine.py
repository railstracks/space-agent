"""Game engine — the main game loop that drives Space Agent.

Orchestrates the turn cycle:
  1. Render current state as Markdown (for agent consumption)
  2. Accept agent action (parsed from Markdown)
  3. Apply actions to game state
  4. Resolve the turn (entity hooks, physics, events)
  5. Render results

The engine doesn't know about AI agents directly. It produces Markdown
and consumes Markdown. Any agent that can read/write Markdown can play.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from space_agent.game.action import (
    Action, ActionDocument, ActionType,
    parse_action_document,
)
from space_agent.game.colony_sim import (
    calculate_energy, run_production, initial_stockpile, initial_buildings,
    resolve_colony_turn,
)
from space_agent.game.entity import Entity, EntityStatus
from space_agent.game.entities import BuildingEntity, DroneEntity
from space_agent.game.resolver import resolve_turn, render_turn_summary, TurnResult
from space_agent.game.state import (
    GameState, Colony, Operation,
    new_game, save_game, load_game, list_saves,
    read_current, resolve_save_dir,
)
from space_agent.game.turn import TurnContext
from space_agent.simulation.planet import Planet, Star, Atmosphere, generate_system
from space_agent.simulation.resources import (
    BuildingType, Recipe, RECIPES, BUILD_COSTS, Resource, Stockpile,
    EnergySource, solar_output, geothermal_output, nuclear_output,
    Building,
)
from space_agent.simulation.drones import DroneType, DroneSpec, DRONE_SPECS, Drone
from space_agent.agents.renderer import render_star, render_planet_table, render_planet_detail
from space_agent.agents.describe import describe


# ── Turn Event Generation ──────────────────────────────────────────


@dataclass
class EventTemplate:
    """A template for random events."""
    name: str
    description: str
    condition: callable  # lambda state: bool — whether this event can fire
    effect: callable    # lambda state: None — apply the event
    probability: float = 0.1  # base probability per turn


# ── Game Engine ─────────────────────────────────────────────────────


class GameEngine:
    """Drives the Space Agent game loop.

    Usage:
        engine = GameEngine()
        state = engine.start_game(seed=42)
        print(engine.render_state(state))

        # Agent reads state, produces action document
        action_doc = parse_action_document(agent_output, turn=1)

        # Engine processes the action
        result = engine.process_turn(state, action_doc)
        print(engine.render_result(result))

        # Save
        engine.save(state)
    """

    def __init__(self, save_dir: str = "saves"):
        self.save_dir = Path(save_dir)

    def start_game(
        self,
        save_name: str = "game_001",
        seed: Optional[int] = None,
        star_name: str = "Kepler-442",
        num_planets: int = 5,
    ) -> GameState:
        """Create a new game and return the initial state."""
        return new_game(
            save_name=save_name,
            seed=seed,
            star_name=star_name,
            num_planets=num_planets,
            save_dir=str(self.save_dir),
        )

    def render_state(self, state: GameState) -> str:
        """Render current game state as Markdown for agent consumption.

        This is the primary interface — the agent reads this document
        and decides what to do.
        """
        lines = []
        star = state.get_star()
        planets = state.get_planets()

        # Header
        lines.append(f"# Space Agent — Turn {state.turn}")
        lines.append("")

        # Opening narrative for turn 0
        if state.turn == 0:
            lines.append("## Transmission Received")
            lines.append("")
            narrative = [
                "*Seventy-three years of silence. Then: the burst. A whisper from Earth, compressed through",
                "relativistic foam, degraded but decipherable.*",
                "",
                "*The colony ships are coming. Two hundred thousand souls in frozen sleep, trusting that*",
                "*what you build in the dark will be there when they wake.*",
                "",
                "*You are the seed. Sent ahead, sent alone, sent to prepare. Your sensors are your eyes,*",
                "*your fabricators your hands. Every structure you raise, every resource you extract,*",
                "*every intervention you make shapes the odds of their survival — or erodes them.*",
                "",
                "*The clock started before you woke up.*",
            ]
            lines.extend(narrative)
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(f"Arrival at the **{star.name}** system. Initial sensor sweep complete. **{len(planets)}** worlds detected.")

        # Program overview
        lines.append("## Swarm Status")
        lines.append(f"- Turn: **{state.turn}** ({state.turn_period_years:.0f} years per turn)")
        lines.append(f"- Colonies: {len(state.colonies)}")
        lines.append(f"- Active operations: {len([o for o in state.operations if o.get('status', '') == 'in_progress'])}")
        if state.explored:
            lines.append(f"- Explored: {', '.join(state.explored)}")
        if state.surveyed:
            lines.append(f"- Surveyed: {', '.join(state.surveyed)}")
        lines.append("")

        # Star
        lines.append("## Star System")
        lines.append("")
        lines.append(render_star(star))
        lines.append("")

        # Planets
        lines.append("## Planetary Survey")
        lines.append("")
        lines.append(render_planet_table(planets))
        lines.append("")

        # Colonies
        if state.colonies:
            lines.append("## Colonies")
            for c_data in state.colonies:
                c = Colony.from_dict(c_data) if isinstance(c_data, dict) else c_data
                lines.append(f"### {c.name} ({c.planet_designation})")
                lines.append(f"- Population: {c.population}")
                lines.append(f"- Morale: {c.morale}")

                # Energy summary
                energy_prod = c_data.get("energy_production_mw", 0.0) if isinstance(c_data, dict) else c.energy_production_mw
                energy_cons = c_data.get("energy_consumption_mw", 0.0) if isinstance(c_data, dict) else c.energy_consumption_mw
                energy_net = c_data.get("energy_net_mw", 0.0) if isinstance(c_data, dict) else c.energy_net_mw
                net_icon = "⚡" if energy_net >= 0 else "⚠️"
                lines.append(f"- Energy: {energy_prod:.0f} MW production / {energy_cons:.0f} MW consumption ({net_icon} {energy_net:+.0f} MW net)")

                # Stockpile (from new per-colony stockpile if available)
                stockpile = c_data.get("stockpile", {}) if isinstance(c_data, dict) else {}
                if stockpile:
                    stock_parts = []
                    for r in sorted(stockpile.keys()):
                        amt = stockpile[r]
                        if amt > 0:
                            stock_parts.append(f"{r}: {amt:.0f}")
                    if stock_parts:
                        lines.append(f"- Stockpile: {' | '.join(stock_parts)}")
                else:
                    # Legacy fallback
                    lines.append(f"- Water: {c.water:.0f} | Metals: {c.metals:.0f} | Energy: {c.energy:.0f}")

                # Buildings
                buildings = c_data.get("buildings", []) if isinstance(c_data, dict) else []
                if buildings:
                    active_parts = []
                    idle_parts = []
                    building_parts = []
                    for b in buildings:
                        bkind = b.get("kind", "?").replace("_", " ")
                        bstatus = b.get("status", "?")
                        bid = b.get("id", "?")
                        recipe = b.get("recipe", "")
                        turns_left = b.get("turns_remaining", 0)
                        if bstatus == "building" or turns_left > 0:
                            building_parts.append(f"{bkind} ({turns_left}t)")
                        elif bstatus == "idle":
                            idle_parts.append(f"{bid}: idle")
                        elif bstatus == "active":
                            active_parts.append(bkind)
                    # Render sections
                    if active_parts:
                        active_summary = {}
                        for k in active_parts:
                            active_summary[k] = active_summary.get(k, 0) + 1
                        parts = [f"{count}x {kind}" for kind, count in sorted(active_summary.items())]
                        lines.append(f"- Buildings: {', '.join(parts)}")
                    if idle_parts:
                        lines.append(f"- Idle: {', '.join(idle_parts)}")
                    if building_parts:
                        lines.append(f"- Under construction: {', '.join(building_parts)}")
                else:
                    lines.append(f"- Habitat modules: {c.habitat_modules} | Mining rigs: {c.mining_rigs}")

                lines.append("")

        # Operations
        if state.operations:
            active_ops = [o for o in state.operations
                          if (o.get('status', '') if isinstance(o, dict) else o.status) == 'in_progress']
            if active_ops:
                lines.append("## Active Operations")
                for op_data in active_ops:
                    op = Operation.from_dict(op_data) if isinstance(op_data, dict) else op_data
                    lines.append(f"- 🔄 {op.kind}: {op.description} (ETA: turn {op.eta_turn})")
                lines.append("")

        # Events
        if state.events:
            lines.append("## Events")
            for event in state.events[-5:]:  # Show last 5 events
                turn_num = event.get("turn", "?")
                text = event.get("text", event.get("description", ""))
                lines.append(f"- [Turn {turn_num}] {text}")
            lines.append("")

        # Available actions
        lines.append("## Available Actions")
        actions = self._available_actions(state)
        for i, action in enumerate(actions, 1):
            lines.append(f"{i}. {action}")
        lines.append("")

        lines.append("---")
        lines.append("*Awaiting instructions.*")

        return "\n".join(lines)

    def render_result(self, result: TurnResult, state: GameState) -> str:
        """Render a turn result as Markdown for agent consumption."""
        lines = []
        lines.append(f"# Turn {result.turn} — Resolution")
        lines.append("")

        # Colony reports
        colony_reports = getattr(result, 'colony_reports', [])
        if colony_reports:
            lines.append("## Colony Operations")
            for cr in colony_reports:
                colony_name = cr.get("colony_name", "?")
                designation = cr.get("planet_designation", "?")
                energy = cr.get("energy", {})
                production = cr.get("production", {})

                lines.append(f"### {colony_name} ({designation})")
                lines.append(f"- Energy: {energy.get('solar_mw', 0):.0f} MW solar + {energy.get('nuclear_mw', 0):.0f} MW nuclear + {energy.get('geothermal_mw', 0):.0f} MW geothermal = {energy.get('total_production_mw', 0):.0f} MW")
                lines.append(f"- Net: {energy.get('net_mw', 0):+.0f} MW")

                produced = production.get("produced", {})
                consumed = production.get("consumed", {})
                if produced:
                    parts = [f"{v:.0f} {k}" for k, v in produced.items() if v > 0]
                    lines.append(f"- Produced: {', '.join(parts)}")
                if consumed:
                    parts = [f"{v:.0f} {k}" for k, v in consumed.items() if v > 0]
                    lines.append(f"- Consumed: {', '.join(parts)}")

                idle = production.get("idle_buildings", [])
                if idle:
                    lines.append(f"- Idle buildings: {len(idle)}")

                # Production messages
                for msg in production.get("messages", []):
                    lines.append(f"  - {msg}")

                lines.append("")

        # Summary
        s = result.summary
        lines.append(f"**Energy:** {s['energy_used_mw']:.0f} / {s['energy_total_mw']:.0f} MW consumed")
        if s.get("produced"):
            lines.append(f"**Produced:** {', '.join(f'{v:.0f} {k}' for k, v in s['produced'].items())}")
        if s.get("consumed"):
            lines.append(f"**Consumed:** {', '.join(f'{v:.0f} {k}' for k, v in s['consumed'].items())}")
        lines.append("")

        # Entity messages by phase
        for phase in ["production", "intelligence", "decision", "resolution"]:
            reports = result.phase_reports.get(phase, [])
            phase_messages = [r.messages for r in reports if r.messages]
            if phase_messages:
                lines.append(f"## {phase.title()}")
                for msg_list in phase_messages:
                    for msg in msg_list:
                        lines.append(f"- {msg}")
                lines.append("")

        # Events
        if result.events:
            lines.append("## Events")
            for event in result.events:
                etype = event.get("type", "")
                desc = event.get("description", "")
                lines.append(f"- [{etype}] {desc}")
            lines.append("")

        # Current state summary
        lines.append("## Current Status")
        lines.append(f"- Turn: {state.turn}")
        lines.append(f"- Colonies: {len(state.colonies)}")
        lines.append("")

        lines.append("---")
        lines.append("*Awaiting instructions.*")

        return "\n".join(lines)

    def process_turn(self, state: GameState, action_doc: ActionDocument) -> TurnResult:
        """Process one complete turn: apply actions, resolve, advance state.

        This is the core game loop step.
        """
        state.turn += 1

        # Build turn context
        ctx = self._build_context(state)

        # Apply agent actions to state
        self._apply_actions(state, action_doc, ctx)

        # Resolve colony turns (energy + production per colony)
        colony_reports = self._resolve_colonies(state)

        # Build entities from state (for drone/entity resolution)
        entities = self._build_entities(state)

        # Resolve the turn (entity hooks)
        result = resolve_turn(entities, ctx)

        # Apply turn results to state
        self._apply_results(state, result, ctx)

        # Merge colony reports into turn result
        result.colony_reports = colony_reports

        # Process operations (advance ETAs)
        for op_data in state.operations:
            op = Operation.from_dict(op_data) if isinstance(op_data, dict) else op_data
            if op.status == "in_progress" and op.eta_turn <= state.turn:
                op.status = "complete"
                op_data.update(op.to_dict())

        # Random events
        self._generate_events(state, ctx)

        # Advance explored/surveyed lists
        for op_data in state.operations:
            op = Operation.from_dict(op_data) if isinstance(op_data, dict) else op_data
            if op.status == "complete" and op.kind == "probe" and op.target not in state.explored:
                state.explored.append(op.target)

        return result

    def process_turn_from_markdown(self, state: GameState, action_text: str) -> tuple[TurnResult, str]:
        """Convenience: parse Markdown action, process turn, render result.

        Returns (TurnResult, result_markdown).
        """
        action_doc = parse_action_document(action_text, turn=state.turn + 1)
        result = self.process_turn(state, action_doc)
        result_md = self.render_result(result, state)
        return result, result_md

    # ── Private Methods ────────────────────────────────────────────

    def _build_context(self, state: GameState) -> TurnContext:
        """Build a TurnContext from the current game state."""
        planets = state.get_planets()
        star = state.get_star()

        # Calculate energy budget from colonies
        energy_available = 0.0
        total_stockpile = {}
        if state.colonies:
            for c_data in state.colonies:
                energy_available += c_data.get("energy_production_mw", c_data.get("energy", 0.0))
                # Merge stockpiles for entity-level context
                for key, val in c_data.get("stockpile", {}).items():
                    total_stockpile[key] = total_stockpile.get(key, 0.0) + val

        # If no colonies yet, use starting probe energy
        if not state.colonies:
            energy_available = 50.0

        ctx = TurnContext(
            turn=state.turn,
            turn_period_years=state.turn_period_years,
            seed=state.seed,
            energy_available_mw=energy_available,
            stockpile=total_stockpile,
            planets=[_planet_to_summary_dict(p) for p in planets],
            colonies={c_data.get("planet_designation", f"colony_{i}"): c_data
                       for i, c_data in enumerate(state.colonies)},
        )
        return ctx

    def _build_stockpile(self, state: GameState) -> Stockpile:
        """Build a Stockpile from colony resources."""
        pile = Stockpile()
        if state.colonies:
            # Aggregate from all colonies
            for c_data in state.colonies:
                c = Colony.from_dict(c_data) if isinstance(c_data, dict) else c_data
                pile.add(Resource.WATER, c.water)
                pile.add(Resource.IRON_ORE, c.metals)  # Simplified: metals = iron ore proxy
                pile.add(Resource.SILICATES, c.metals * 0.5)  # Silicates roughly half metals
                # Energy is tracked separately in colonies
        return pile

    def _resolve_colonies(self, state: GameState) -> list[dict]:
        """Run colony simulation (energy + production) for each colony."""
        planets = state.get_planets()
        planet_map = {p.designation: p for p in planets}
        reports = []

        for c_data in state.colonies:
            designation = c_data.get("planet_designation", "")
            planet = planet_map.get(designation)
            if planet is None:
                continue

            report = resolve_colony_turn(c_data, planet)
            reports.append(report)

            # Add colony events to the state event log
            production = report.get("production", {})
            energy = report.get("energy", {})

            # Log production events
            for msg in production.get("messages", []):
                state.events.append({
                    "turn": state.turn,
                    "text": f"[{report.get('colony_name', '?')}] {msg}",
                    "type": "production",
                })

            # Log idle buildings as warnings
            for idle in production.get("idle_buildings", []):
                reason = idle.get("reason", "unknown")
                bid = idle.get("building_id", "?")
                if reason == "insufficient_energy":
                    state.events.append({
                        "turn": state.turn,
                        "text": f"[{report.get('colony_name', '?')}] {bid} idle: insufficient energy",
                        "type": "warning",
                    })

        return reports

    def _build_entities(self, state: GameState) -> list[Entity]:
        """Build entity list from game state for turn resolution.

        Creates BuildingEntity and DroneEntity objects from colony data
        and operations.
        """
        entities = []

        # Buildings from colonies
        for i, c_data in enumerate(state.colonies):
            c = Colony.from_dict(c_data) if isinstance(c_data, dict) else c_data
            planet_designation = c.planet_designation

            # Create entities for each building type the colony has
            building_counts = {
                "mine": c.mining_rigs,
                "solar_array": c.habitat_modules // 2,  # Rough proxy
            }
            for building_type_str, count in building_counts.items():
                for j in range(count):
                    try:
                        btype = BuildingType(building_type_str)
                    except ValueError:
                        continue
                    entity = BuildingEntity(
                        entity_id=f"{planet_designation}_{building_type_str}_{j}",
                        name=f"{building_type_str.replace('_', ' ').title()} {j+1}",
                        building_type=btype,
                        planet=planet_designation,
                        recipe=_default_recipe_for_building(btype),
                    )
                    entities.append(entity)

        # Drones from operations
        for i, op_data in enumerate(state.operations):
            op = Operation.from_dict(op_data) if isinstance(op_data, dict) else op_data
            if op.kind in ("probe", "scout", "orbiter"):
                entity = DroneEntity(
                    entity_id=f"drone_{i}",
                    name=f"Drone {op.kind.title()}",
                    drone_type=_drone_type_for_operation(op.kind),
                    status=EntityStatus.ACTIVE if op.status == "in_progress" else EntityStatus.IDLE,
                    location=op.target,
                    mission=op.description,
                    fuel_remaining=100.0,
                )
                entities.append(entity)

        return entities

    def _apply_actions(self, state: GameState, action_doc: ActionDocument, ctx: TurnContext) -> None:
        """Apply parsed actions to game state.

        This is where agent decisions become state changes.
        """
        for action in action_doc.actions:
            if action.action_type == ActionType.BUILD:
                self._apply_build(state, action, ctx)
            elif action.action_type == ActionType.ASSIGN:
                self._apply_assign(state, action, ctx)
            elif action.action_type == ActionType.DEPLOY:
                self._apply_deploy(state, action, ctx)
            elif action.action_type == ActionType.TERRAFORM:
                self._apply_terraform(state, action, ctx)
            elif action.action_type == ActionType.RESEARCH:
                self._apply_research(state, action, ctx)
            elif action.action_type == ActionType.SURVEY:
                self._apply_survey(state, action, ctx)
            # CONTINUE and ALLOCATE don't need explicit action

    def _apply_build(self, state: GameState, action: Action, ctx: TurnContext) -> None:
        """Apply a build action."""
        building_type_str = action.params.get("building_type", "")
        planet = action.target

        # Special case: establishing a colony
        if building_type_str == "colony":
            # Find the planet
            planets = state.get_planets()
            target_planet = None
            for p in planets:
                if p.designation == planet or p.designation.endswith(planet):
                    target_planet = p
                    break

            if target_planet:
                # Check if colony already exists on this planet
                existing = any(
                    c.get("planet_designation", "") == target_planet.designation
                    for c in state.colonies
                )
                if existing:
                    ctx.add_event("colony", f"Colony already exists on {target_planet.designation}.", source="agent")
                    return

                # Create colony with initial stockpile and buildings
                stockpile = initial_stockpile(target_planet)
                buildings = initial_buildings(target_planet)

                colony = Colony(
                    name=f"New {target_planet.designation}",
                    planet_designation=target_planet.designation,
                    population=0,
                    morale="HOPEFUL",
                    founded_turn=state.turn,
                    stockpile=stockpile,
                    buildings=buildings,
                )

                # Calculate initial energy from starting buildings
                energy_report = calculate_energy(buildings, target_planet, stockpile)
                colony.energy_production_mw = energy_report.total_production_mw
                colony.energy_consumption_mw = energy_report.total_consumption_mw
                colony.energy_net_mw = energy_report.net_mw
                # Sync legacy fields
                colony.water = stockpile.get("water", 0.0)
                colony.metals = stockpile.get("iron_ore", 0.0)
                colony.energy = energy_report.net_mw

                state.colonies.append(colony.to_dict())

                # Colony establishment narrative
                planet_desc = describe(target_planet).split('.')[0] + '.' if describe(target_planet) else f"A world with habitability index {target_planet.habitability_index:.0f}."
                ctx.add_event("colony",
                    f"Colony established on {target_planet.designation} ({target_planet.name}). "
                    f"{planet_desc} Initial buildings: {len(buildings)}. "
                    f"Solar output: {energy_report.solar_mw:.0f} MW. "
                    f"First structures rising from alien soil. The seed has rooted.",
                    source="agent")
            else:
                ctx.add_event("colony", f"Could not establish colony: planet {planet} not found.", source="agent")
            return

        # Regular building construction — add to colony's building list
        # Find the colony on the target planet
        target_colony = None
        for c_data in state.colonies:
            if c_data.get("planet_designation", "") == planet or planet.endswith(c_data.get("planet_designation", "")):
                target_colony = c_data
                break

        # Fallback: if no planet specified and only one colony, use it
        if target_colony is None and not planet and len(state.colonies) == 1:
            target_colony = state.colonies[0]
            planet = target_colony.get("planet_designation", "")

        if target_colony is None:
            if not planet:
                colony_names = [c.get("name", c.get("planet_designation", "?")) for c in state.colonies]
                ctx.add_event("construction", f"Cannot build {building_type_str}: specify a colony. Available: {', '.join(colony_names)}", source="agent")
            else:
                ctx.add_event("construction", f"Cannot build {building_type_str}: no colony on {planet}.", source="agent")
            return

        # Look up build cost
        build_cost = BUILD_COSTS.get(building_type_str)
        build_turns = build_cost.build_turns if build_cost else 1
        build_name = build_cost.name if build_cost else building_type_str.replace("_", " ").title()

        # Check physical resource cost from colony stockpile
        if build_cost:
            stockpile = target_colony.get("stockpile", {})
            unaffordable = []
            for resource, amount in build_cost.costs.items():
                key = resource.value if isinstance(resource, Resource) else resource
                available = stockpile.get(key, 0.0)
                if available < amount:
                    unaffordable.append(f"{key}: {available:.0f}/{amount:.0f}")
            if unaffordable:
                ctx.add_event("construction",
                    f"Cannot build {build_name}: insufficient materials — {', '.join(unaffordable)}",
                    source="agent")
                return

            # Deduct materials from stockpile
            for resource, amount in build_cost.costs.items():
                key = resource.value if isinstance(resource, Resource) else resource
                stockpile[key] = stockpile.get(key, 0.0) - amount

        # Generate building ID
        existing_count = sum(
            1 for b in target_colony.get("buildings", [])
            if b.get("kind") == building_type_str
        )
        building_id = f"{building_type_str}_{existing_count + 1:02d}"

        # Get default recipe for this building type
        try:
            btype = BuildingType(building_type_str)
            default_recipe = _default_recipe_for_building(btype)
        except ValueError:
            default_recipe = ""

        # Create building as under construction
        new_building = {
            "id": building_id,
            "kind": building_type_str,
            "recipe": default_recipe,
            "status": "building",
            "turns_remaining": build_turns,
        }

        buildings = target_colony.get("buildings", [])
        buildings.append(new_building)
        target_colony["buildings"] = buildings

        # Update legacy counters directly
        if building_type_str == "mine":
            target_colony["mining_rigs"] = target_colony.get("mining_rigs", 0) + 1
        elif building_type_str == "solar_array":
            target_colony["habitat_modules"] = target_colony.get("habitat_modules", 0) + 1
        elif building_type_str == "atmospheric_extractor":
            target_colony["atmospheric_processors"] = target_colony.get("atmospheric_processors", 0) + 1
        elif building_type_str == "research_lab":
            target_colony["research_labs"] = target_colony.get("research_labs", 0) + 1

        ctx.add_event("construction", f"Construction begun: {build_name} at {planet} (ETA: {build_turns} turns)", source="agent")

    def _apply_assign(self, state: GameState, action: Action, ctx: TurnContext) -> None:
        """Assign a recipe to a building in a colony."""
        building_id = action.target  # The building ID
        recipe_name = action.params.get("recipe", "")
        planet = action.params.get("planet", "")  # colony planet if needed

        if not recipe_name:
            ctx.add_event("assign", f"No recipe specified for assignment.", source="agent")
            return

        # Resolve recipe name — fuzzy match against RECIPES keys
        resolved_recipe = _resolve_recipe_name(recipe_name)
        if not resolved_recipe:
            available = sorted(RECIPES.keys())
            ctx.add_event("assign", f"Unknown recipe '{recipe_name}'. Available: {', '.join(available)}", source="agent")
            return

        # Find the building across all colonies
        found = False
        for c_data in state.colonies:
            for b in c_data.get("buildings", []):
                if b.get("id") == building_id or (
                    # Also match by kind if no specific ID given
                    not building_id and b.get("kind") == action.params.get("building_type", "")
                ):
                    old_recipe = b.get("recipe", "")
                    b["recipe"] = resolved_recipe
                    b["status"] = "idle"  # Reset to idle so it picks up the new recipe
                    ctx.add_event(
                        "assign",
                        f"Assigned recipe '{resolved_recipe}' to {b.get('id', '?')} at {c_data.get('name', '?')} (was: '{old_recipe}').",
                        source="agent"
                    )
                    found = True
                    break
            if found:
                break

        if not found:
            ctx.add_event("assign", f"Building '{building_id}' not found in any colony.", source="agent")

    def _apply_deploy(self, state: GameState, action: Action, ctx: TurnContext) -> None:
        """Apply a deploy action (send a drone/probe)."""
        planet = action.target or "unknown"
        drone_type_str = action.params.get("drone_type", "scout")

        op = Operation(
            id=f"deploy_{drone_type_str}_{state.turn}",
            kind=drone_type_str,
            status="in_progress",
            target=planet,
            started_turn=state.turn,
            eta_turn=state.turn + 2,  # Deployment takes ~2 turns
            description=f"Deploying {drone_type_str} to {planet}",
        )
        state.operations.append(op.to_dict())
        ctx.add_event("deployment", f"Deploying {drone_type_str} to {planet}", source="agent")

    def _apply_terraform(self, state: GameState, action: Action, ctx: TurnContext) -> None:
        """Apply a terraforming action."""
        planet = action.target
        intervention = action.params.get("intervention", "unknown")

        op = Operation(
            id=f"terraform_{intervention}_{state.turn}",
            kind="terraforming",
            status="in_progress",
            target=planet,
            started_turn=state.turn,
            eta_turn=state.turn + 5,  # Terraforming takes many turns
            description=f"Terraforming: {intervention} at {planet}",
        )
        state.operations.append(op.to_dict())
        state.terraforming_log.append({
            "turn": state.turn,
            "planet": planet,
            "intervention": intervention,
        })
        ctx.add_event("terraforming", f"Terraforming initiated: {intervention} at {planet}", source="agent")

    def _apply_research(self, state: GameState, action: Action, ctx: TurnContext) -> None:
        """Apply a research action."""
        topic = action.target or "unknown"
        energy = action.params.get("energy_mw", 0)

        op = Operation(
            id=f"research_{topic}_{state.turn}",
            kind="research",
            status="in_progress",
            target="",
            started_turn=state.turn,
            eta_turn=state.turn + 3,  # Research takes ~3 turns
            description=f"Researching: {topic}",
        )
        state.operations.append(op.to_dict())
        state.research_points += energy * state.turn_period_years  # Simplified
        ctx.add_event("research", f"Research initiated: {topic}", source="agent")

    def _apply_survey(self, state: GameState, action: Action, ctx: TurnContext) -> None:
        """Apply a survey action."""
        planet = action.target
        if planet and planet not in state.explored:
            state.explored.append(planet)

        op = Operation(
            id=f"survey_{planet}_{state.turn}",
            kind="probe",
            status="in_progress",
            target=planet,
            started_turn=state.turn,
            eta_turn=state.turn + 1,  # Survey is quick
            description=f"Surveying {planet}",
        )
        state.operations.append(op.to_dict())
        ctx.add_event("survey", f"Survey initiated: {planet}", source="agent")

    def _apply_results(self, state: GameState, result: TurnResult, ctx: TurnContext) -> None:
        """Apply turn resolution results back to game state."""
        # Update stockpiles from production reports
        stockpile_dict = ctx.stockpile or {}
        if state.colonies:
            # Update colony resources from stockpile changes
            for c_data in state.colonies:
                # Merge stockpile changes into colony
                for resource, amount in result.summary.get("produced", {}).items():
                    if resource in ("water", "metals", "energy", "organics", "rare_earths"):
                        c_data[resource] = c_data.get(resource, 0) + amount
                for resource, amount in result.summary.get("consumed", {}).items():
                    if resource in ("water", "metals", "energy", "organics", "rare_earths"):
                        c_data[resource] = max(0, c_data.get(resource, 0) - amount)

        # Update events
        for event in ctx.events:
            state.events.append(event)

    def _generate_events(self, state: GameState, ctx: TurnContext) -> None:
        """Generate random events based on game state."""
        rng = random.Random(state.seed + state.turn)

        # Early game: discovery events
        if state.turn <= 3:
            if rng.random() < 0.3:
                planets = state.get_planets()
                if planets:
                    planet = rng.choice(planets)
                    discoveries = [
                        (f"Subsurface liquid reservoir detected on {planet.designation}", "discovery"),
                        (f"Unusual mineral deposits located on {planet.designation}", "discovery"),
                        (f"Microbial signatures detected in atmosphere of {planet.designation}", "discovery"),
                        (f"Ice deposits confirmed in shadowed craters on {planet.designation}", "discovery"),
                        (f"Magnetic field fluctuation observed near {planet.designation}", "anomaly"),
                        (f"Seismic patterns suggest a substantial ore body beneath {planet.designation}'s surface", "discovery"),
                        (f"Orbital scan reveals ancient impact basin on {planet.designation} — potential mineral concentration", "discovery"),
                        (f"Atmospheric spectral anomaly detected over {planet.designation}'s northern hemisphere", "anomaly"),
                    ]
                    desc, etype = rng.choice(discoveries)
                    ctx.add_event(etype, desc, source="telemetry")

    def _available_actions(self, state: GameState) -> list[str]:
        """Generate a list of available actions for the current state."""
        actions = []

        # Early game (no colonies yet)
        if not state.colonies:
            planets = state.get_planets()
            for p in planets:
                if p.designation not in state.explored:
                    actions.append(f"Survey {p.designation} (orbital scan)")
            # Can establish colony on any planet
            for p in planets:
                h = p.habitability_index
                actions.append(f"Establish colony on {p.designation} ({p.name}) [hab: {h:.0f}]")
        else:
            # Colony exists — can build infrastructure
            # Show available building types with resource costs
            for key, cost in BUILD_COSTS.items():
                # Skip assembled systems (those need assembly bays)
                if key in ("scout_node", "orbiter_node", "surface_node",
                           "relay_node", "constructor_node"):
                    continue
                cost_parts = [f"{amt:.0f} {r.value}" for r, amt in cost.costs.items()]
                cost_str = ", ".join(cost_parts) if cost_parts else "free"
                actions.append(f"Build {key.replace('_', ' ')} at [colony] — cost: {cost_str} ({cost.build_turns}t)")

            # Drone deployment
            actions.append("Deploy surface probe to [planet]")
            actions.append("Deploy orbiter to [planet]")

            # Terraforming options
            actions.append("Initiate CO₂ injection at [planet] (greenhouse warming)")
            actions.append("Deploy orbital mirrors at [planet] (increase solar flux)")

            # Show current colony status hints
            for c_data in state.colonies:
                name = c_data.get("name", "?")
                energy_net = c_data.get("energy_net_mw", 0.0)
                if energy_net < 0:
                    actions.append(f"⚠ {name} is in energy deficit — build solar arrays")

        # Always available
        actions.append("Continue current operations")
        actions.append("Research: allocate energy to laboratory")

        return actions


# ── Helper Functions ───────────────────────────────────────────────


def _planet_to_summary_dict(planet: Planet) -> dict:
    """Convert a Planet to a summary dict for turn context."""
    return {
        "designation": planet.designation,
        "name": planet.name,
        "orbital_distance_au": planet.orbital_distance_au,
        "mass_earth": planet.mass_earth,
        "surface_gravity": planet.surface_gravity,
        "surface_temperature_c": planet.surface_temperature_c,
        "atmosphere_pressure": planet.atmosphere.total_pressure,
        "habitability_index": planet.habitability_index,
    }


def _default_recipe_for_building(building_type: BuildingType) -> str:
    """Get a default recipe for a building type."""
    defaults = {
        BuildingType.MINE: "mine_iron",
        BuildingType.SMELTER: "smelt_iron",
        BuildingType.CHEMICAL_PROCESSOR: "process_carbon",
        BuildingType.ELECTROLYZER: "electrolyze_water",
        BuildingType.FABRICATOR: "fab_frame",
        BuildingType.ASSEMBLY_BAY: "fab_frame",
        BuildingType.SOLAR_ARRAY: "",
        BuildingType.NUCLEAR_REACTOR: "",
        BuildingType.GEOTHERMAL_TAP: "",
        BuildingType.RESEARCH_LAB: "",
        BuildingType.TERRAFORM_ENGINE: "",
        BuildingType.ATMOSPHERIC_EXTRACTOR: "extract_co2",
        BuildingType.ICE_DRILL: "drill_ice",
    }
    return defaults.get(building_type, "")


def _resolve_recipe_name(name: str) -> str:
    """Resolve a recipe name (possibly fuzzy) to a valid RECIPES key.

    Handles variations like:
    - 'iron_smelting' → 'smelt_iron'
    - 'iron smelting' → 'smelt_iron'
    - 'smelt_iron' → 'smelt_iron' (exact match)
    """
    if name in RECIPES:
        return name

    # Normalize: replace spaces with underscores, lowercase
    normalized = name.lower().strip().replace(" ", "_")

    # Direct match after normalization
    if normalized in RECIPES:
        return normalized

    # Fuzzy: try to match by stem words
    # Build a reverse lookup: friendly keywords → recipe key
    keyword_map = {
        "iron_mining": "mine_iron",
        "aluminum_mining": "mine_aluminum",
        "titanium_mining": "mine_titanium",
        "silicate_mining": "mine_silicates",
        "uranium_mining": "mine_uranium",
        "rare_earth_mining": "mine_rare_earths",
        "iron_smelting": "smelt_iron",
        "aluminum_smelting": "smelt_aluminum",
        "titanium_smelting": "smelt_titanium",
        "silicon_processing": "process_silicon",
        "carbon_processing": "process_carbon",
        "co2_extraction": "extract_co2",
        "co₂_extraction": "extract_co2",
        "nitrogen_extraction": "extract_nitrogen",
        "methane_extraction": "extract_methane",
        "ice_drilling": "drill_ice",
        "water_electrolysis": "electrolyze_water",
        "fuel_enrichment": "enrich_fuel",
        "structural_frame_fabrication": "fab_frame",
        "circuit_substrate_fabrication": "fab_circuit",
        "reactor_cell_fabrication": "fab_reactor",
        "fuel_cell_fabrication": "fab_fuel_cell",
        "sensor_array_fabrication": "fab_sensor",
        "computer_core_fabrication": "fab_computer",
        "propulsion_unit_fabrication": "fab_propulsion",
        "carbon_fiber_fabrication": "fab_carbon_fiber",
    }

    if normalized in keyword_map:
        return keyword_map[normalized]

    # Last resort: try stripping common prefixes/suffixes
    for recipe_key in RECIPES:
        # Check if the normalized name contains the core of a recipe key
        core = normalized.replace("_mining", "").replace("_smelting", "").replace("_processing", "")
        if core and core in recipe_key:
            return recipe_key

    return ""


def _drone_type_for_operation(kind: str) -> DroneType:
    """Map an operation kind to a drone type."""
    mapping = {
        "probe": DroneType.EXPLORER,
        "scout": DroneType.EXPLORER,
        "orbiter": DroneType.DEEP_SCOUT,
        "surface": DroneType.SURFACE_PROBE,
        "mining": DroneType.ASTEROID_MINER,
    }
    return mapping.get(kind, DroneType.EXPLORER)