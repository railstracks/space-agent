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


def cmd_newgame(args):
    """Create a new game save."""
    state = new_game(
        save_name=args.name,
        seed=args.seed,
        star_name=args.star,
        num_planets=args.planets,
        credits=args.credits,
        save_dir=args.save_dir,
    )
    star = state.get_star()
    print(f"Created save: {state.save_name}")
    print(f"Star: {star.name} ({star.spectral_type}-type, {star.luminosity_solar:.2f} L☉)")
    print(f"Planets: {len(state.planets)}")
    print(f"Credits: {state.credits:.0f}")
    print(f"Seed: {state.seed}")
    print(f"Save file: {args.save_dir}/{state.save_name}.json")
    print(f"Turn: {state.turn}")


def cmd_status(args):
    """Show current game status."""
    save_dir = resolve_save_dir(args.save_dir)
    current = read_current(save_dir)
    if current is None:
        print("No current save. Use 'newgame' to create one.")
        return

    state = load_game(save_dir, current)
    star = state.get_star()
    planets = state.get_planets()

    print(f"# {state.save_name} — Turn {state.turn}")
    print(f"Last played: {state.last_played[:10]}")
    print(f"Credits: {state.credits:.0f}")
    print(f"Colonies: {len(state.colonies)}")
    print(f"Active operations: {len([o for o in state.operations if o.get('status') == 'in_progress'])}")
    print()
    print(f"## {star.name} ({star.spectral_type}-type)")
    print(f"Habitable zone: {star.habitable_zone_inner_au:.2f}–{star.habitable_zone_outer_au:.2f} AU")
    print()
    print(render_planet_table(planets))


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
    ng.add_argument("--credits", type=float, default=5000, help="Starting credits")

    # status
    sub.add_parser("status", help="Show current game status")

    # describe
    desc = sub.add_parser("describe", help="Narrative description of a planet")
    desc.add_argument("planet", help="Planet designation (e.g. Kepler-442-III)")

    # saves
    sub.add_parser("saves", help="List all saves")

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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
