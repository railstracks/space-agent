"""Space Agent CLI — generate systems, render planets, run turns."""

from __future__ import annotations

import argparse
import random
import sys

from src.simulation.planet import generate_system
from src.agents.renderer import render_star, render_planet_table, render_planet_detail


def cmd_generate(args):
    """Generate a planetary system."""
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


def main():
    parser = argparse.ArgumentParser(
        description="Space Agent — Physics-driven space colonization simulator"
    )
    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="Generate a planetary system")
    gen.add_argument("--star", default="Kepler-442", help="Star name")
    gen.add_argument("--planets", type=int, default=5, help="Number of planets")
    gen.add_argument("--seed", type=int, default=42, help="Random seed")
    gen.add_argument("--detail", action="store_true", help="Show full planet details")

    args = parser.parse_args()
    if args.command == "generate":
        cmd_generate(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
