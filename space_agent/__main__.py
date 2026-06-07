"""Space Agent CLI — generate systems, manage saves, run turns."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from space_agent.simulation.planet import generate_system
from space_agent.agents.renderer import render_star, render_planet_table, render_planet_detail
from space_agent.agents.describe import describe
from space_agent.game.state import (
    new_game, load_game, save_game, list_saves,
    read_current, resolve_save_dir,
)
from space_agent.game.engine import GameEngine
from space_agent.game.action import parse_action_document


def cmd_generate(args):
    """Generate a planetary system (standalone, no save)."""
    rng = random.Random(args.seed)
    star, planets = generate_system(rng, star_name=args.star, num_planets=args.planets)

    print(f"# System: {star.name}\n")
    print(render_star(star))
    print()
    print("## Planetary Survey\n")
    print(render_planet_table(planets))

    if args.detail:
        for p in planets:
            print()
            print(render_planet_detail(p))
            print()
            print("## Narrative")
            print()
            print(describe(p))


def cmd_newgame(args):
    """Create a new game save."""
    engine = GameEngine(save_dir=args.save_dir)
    state = engine.start_game(
        save_name=args.name,
        seed=args.seed,
        star_name=args.star,
        num_planets=args.planets,
    )

    # Show initial state
    print(engine.render_state(state))
    print()
    print(f"---")
    print(f"Save: {state.save_name} (seed: {state.seed})")


def cmd_status(args):
    """Show current game status."""
    engine = GameEngine(save_dir=args.save_dir)
    save_dir = resolve_save_dir(args.save_dir)
    current = read_current(save_dir)
    if current is None:
        print("No current save. Use 'newgame' to create one.")
        return

    state = load_game(save_dir, current)
    print(engine.render_state(state))


def cmd_describe(args):
    """Narrative description of a planet."""
    save_dir = resolve_save_dir(args.save_dir)
    current = read_current(save_dir)
    if current is None:
        print("No current save. Use 'newgame' to create one.")
        return

    state = load_game(save_dir, current)
    planets = state.get_planets()

    target = args.planet
    planet = None
    for p in planets:
        if p.designation == target or p.name == target or p.designation.endswith(target):
            planet = p
            break

    if planet is None:
        print(f"Planet not found: {target}")
        print(f"Available: {', '.join(p.designation for p in planets)}")
        return

    print(f"# {planet.designation} — {planet.name}")
    print()
    print(render_planet_detail(planet))
    print()
    print("## Narrative")
    print()
    print(describe(planet))


def cmd_saves(args):
    """List all save files."""
    save_dir = resolve_save_dir(args.save_dir)
    current = read_current(save_dir)
    saves = list_saves(save_dir)

    if not saves:
        print("No saves found.")
        return

    print(f"{'Current':>7}  {'Name':<20} {'Turn':>4}  {'Colonies':>8}  {'Last Played'}")
    print("-" * 70)
    for s in saves:
        marker = "  →" if s["name"] == current else ""
        print(f"{marker:>7}  {s['name']:<20} {str(s['turn']):>4}  {str(s['colonies']):>8}  {str(s.get('last_played', '?'))[:10]}")


def cmd_turn(args):
    """Process a turn from a Markdown action document.

    Reads action from stdin or --action file.
    """
    engine = GameEngine(save_dir=args.save_dir)
    save_dir = resolve_save_dir(args.save_dir)
    current = read_current(save_dir)
    if current is None:
        print("No current save. Use 'newgame' to create one.")
        return

    state = load_game(save_dir, current)

    # Read action document
    if args.action:
        action_text = Path(args.action).read_text()
    elif not sys.stdin.isatty():
        action_text = sys.stdin.read()
    else:
        # Interactive mode: show state, prompt for action
        print(engine.render_state(state))
        print()
        print("=" * 60)
        print("Enter action document (end with Ctrl+D or a line containing '---'):")
        print("=" * 60)
        lines = []
        try:
            for line in sys.stdin:
                if line.strip() == "---":
                    break
                lines.append(line)
        except EOFError:
            pass
        action_text = "".join(lines)

    if not action_text.strip():
        # No action — process a "continue" turn
        action_text = f"# Action — Turn {state.turn + 1}\n\n## Operations\n\n1. Continue current operations\n"

    # Parse and process
    action_doc = parse_action_document(action_text, turn=state.turn + 1)
    result = engine.process_turn(state, action_doc)

    # Save
    save_game(state, save_dir)

    # Render result
    print(engine.render_result(result, state))


def cmd_interact(args):
    """Interactive game mode — loop turns until quit."""
    engine = GameEngine(save_dir=args.save_dir)
    save_dir = resolve_save_dir(args.save_dir)
    current = read_current(save_dir)
    if current is None:
        print("No current save. Use 'newgame' to create one first.")
        return

    state = load_game(save_dir, current)

    while True:
        # Show current state
        print("\n" + "=" * 60)
        print(engine.render_state(state))
        print("=" * 60)

        # Get action
        print("\nEnter action (or 'quit' to exit, 'save' to save, 'describe PLANET' for details):")
        try:
            action_text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        action_text = action_text.strip()
        if not action_text:
            continue
        if action_text.lower() in ("quit", "exit", "q"):
            save_game(state, save_dir)
            print(f"Saved: {state.save_name} (turn {state.turn})")
            break
        if action_text.lower() == "save":
            save_game(state, save_dir)
            print(f"Saved: {state.save_name} (turn {state.turn})")
            continue
        if action_text.lower().startswith("describe"):
            parts = action_text.split(maxsplit=1)
            if len(parts) > 1:
                planets = state.get_planets()
                for p in planets:
                    if p.designation.endswith(parts[1]) or p.name == parts[1]:
                        print(render_planet_detail(p))
                        print()
                        print(describe(p))
                        break
                else:
                    print(f"Planet not found: {parts[1]}")
                    print(f"Available: {', '.join(p.designation for p in planets)}")
            continue

        # Process turn
        action_doc = parse_action_document(action_text, turn=state.turn + 1)
        result = engine.process_turn(state, action_doc)

        # Save after each turn
        save_game(state, save_dir)

        # Show result
        print("\n" + engine.render_result(result, state))


def cmd_play(args):
    """Start a new game and enter interactive mode."""
    engine = GameEngine(save_dir=args.save_dir)
    state = engine.start_game(
        save_name=args.name,
        seed=args.seed,
        star_name=args.star,
        num_planets=args.planets,
    )

    print(f"New game: {state.save_name} (seed: {state.seed})")
    print(f"Star: {state.get_star().name} ({state.get_star().spectral_type}-type)")
    print()

    # Enter interactive mode
    while True:
        print("\n" + "=" * 60)
        print(engine.render_state(state))
        print("=" * 60)

        print("\nEnter action (or 'quit' to exit, 'describe PLANET' for details):")
        try:
            action_text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        action_text = action_text.strip()
        if not action_text:
            continue
        if action_text.lower() in ("quit", "exit", "q"):
            save_dir = resolve_save_dir(args.save_dir)
            save_game(state, save_dir)
            print(f"Saved: {state.save_name} (turn {state.turn})")
            break

        # Handle describe
        if action_text.lower().startswith("describe"):
            parts = action_text.split(maxsplit=1)
            if len(parts) > 1:
                planets = state.get_planets()
                for p in planets:
                    if p.designation.endswith(parts[1]) or p.name == parts[1]:
                        print(render_planet_detail(p))
                        print()
                        print(describe(p))
                        break
            continue

        # Process turn
        action_doc = parse_action_document(action_text, turn=state.turn + 1)
        result = engine.process_turn(state, action_doc)

        save_dir = resolve_save_dir(args.save_dir)
        save_game(state, save_dir)

        print("\n" + engine.render_result(result, state))


def main():
    parser = argparse.ArgumentParser(
        description="Space Agent — Physics-driven space colonization simulator",
        prog="python -m space_agent",
    )
    parser.add_argument("--save-dir", default="saves", help="Save directory (default: saves/)")
    sub = parser.add_subparsers(dest="command")

    # generate
    gen = sub.add_parser("generate", help="Generate a planetary system (no save)")
    gen.add_argument("--star", default="Kepler-442", help="Star name")
    gen.add_argument("--planets", type=int, default=5, help="Number of planets")
    gen.add_argument("--seed", type=int, default=42, help="Random seed")
    gen.add_argument("--detail", action="store_true", help="Full planet details")

    # newgame
    ng = sub.add_parser("newgame", help="Create a new game")
    ng.add_argument("--name", default="game_001", help="Save name")
    ng.add_argument("--star", default="Kepler-442", help="Star name")
    ng.add_argument("--planets", type=int, default=5, help="Number of planets")
    ng.add_argument("--seed", type=int, default=None, help="Random seed (random if omitted)")

    # status
    sub.add_parser("status", help="Show current game status")

    # describe
    desc = sub.add_parser("describe", help="Narrative description of a planet")
    desc.add_argument("planet", help="Planet designation (e.g. K442-III)")

    # saves
    sub.add_parser("saves", help="List all saves")

    # turn
    turn = sub.add_parser("turn", help="Process a turn from action document")
    turn.add_argument("--action", help="File containing action document (default: stdin)")

    # interact
    sub.add_parser("interact", help="Interactive game mode (existing save)")

    # play
    play = sub.add_parser("play", help="Start new game and play interactively")
    play.add_argument("--name", default="game_001", help="Save name")
    play.add_argument("--star", default="Kepler-442", help="Star name")
    play.add_argument("--planets", type=int, default=5, help="Number of planets")
    play.add_argument("--seed", type=int, default=None, help="Random seed")

    args = parser.parse_args()
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "newgame":
        cmd_newgame(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "describe":
        cmd_describe(args)
    elif args.command == "saves":
        cmd_saves(args)
    elif args.command == "turn":
        cmd_turn(args)
    elif args.command == "interact":
        cmd_interact(args)
    elif args.command == "play":
        cmd_play(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()