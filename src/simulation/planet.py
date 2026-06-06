"""Planetary generation and property computation.

Every planet is defined by primary physical properties that interact
causally. Derived properties are computed, not assigned.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

# Physical constants (SI where applicable, game-scaled for playability)
EARTH_MASS_KG = 5.972e24
EARTH_RADIUS_M = 6.371e6
STEFAN_BOLTZMANN = 5.670374419e-8  # W⋅m⁻²⋅K⁻⁴
SOLAR_LUMINOSITY = 3.828e26  # W


@dataclass
class Star:
    """Stellar properties affecting planetary environment."""
    name: str
    spectral_type: str = "G"  # O B A F G K M
    luminosity_solar: float = 1.0  # relative to Sun
    mass_solar: float = 1.0
    temperature_k: float = 5778  # surface temp
    age_gyr: float = 4.6

    @property
    def luminosity_watts(self) -> float:
        return self.luminosity_solar * SOLAR_LUMINOSITY

    @property
    def habitable_zone_inner_au(self) -> float:
        """Inner edge of habitable zone (runaway greenhouse limit)."""
        return math.sqrt(self.luminosity_solar / 1.1)

    @property
    def habitable_zone_outer_au(self) -> float:
        """Outer edge of habitable zone (maximum greenhouse limit)."""
        return math.sqrt(self.luminosity_solar / 0.53)


@dataclass
class Atmosphere:
    """Atmospheric composition and dynamics."""
    # Partial pressures in atm
    nitrogen: float = 0.0
    oxygen: float = 0.0
    co2: float = 0.0
    argon: float = 0.0
    water_vapor: float = 0.0
    methane: float = 0.0
    other: float = 0.0

    @property
    def total_pressure(self) -> float:
        return self.nitrogen + self.oxygen + self.co2 + self.argon + self.water_vapor + self.methane + self.other

    @property
    def greenhouse_factor(self) -> float:
        """Simplified greenhouse warming factor.

        CO₂ and CH₄ are the primary greenhouse gases in the model.
        Water vapor provides feedback but is mostly temperature-dependent.
        """
        co2_effect = self.co2 * 8.0  # CO₂ warming per atm
        methane_effect = self.methane * 25.0  # CH₄ is ~25x CO₂ per unit
        water_effect = self.water_vapor * 2.0  # weaker per-unit but plentiful
        return co2_effect + methane_effect + water_effect

    def summary(self) -> dict[str, float]:
        """Return composition as percentage dict."""
        total = self.total_pressure or 1.0
        return {
            "N₂": self.nitrogen / total * 100,
            "O₂": self.oxygen / total * 100,
            "CO₂": self.co2 / total * 100,
            "Ar": self.argon / total * 100,
            "H₂O": self.water_vapor / total * 100,
            "CH₄": self.methane / total * 100,
        }


@dataclass
class Planet:
    """A planet with primary and derived physical properties."""
    name: str
    designation: str  # e.g. "K442-III"

    # Primary properties
    mass_earth: float = 1.0
    radius_earth: float = 1.0
    orbital_distance_au: float = 1.0
    star: Star = field(default_factory=Star)
    rotation_period_hours: float = 24.0
    axial_tilt_degrees: float = 23.4

    # Core composition (affects magnetic field, tectonics)
    iron_core_fraction: float = 0.32  # Earth-like

    # Surface properties
    albedo: float = 0.3  # Earth average
    hydrosphere_ice_fraction: float = 0.0
    hydrosphere_liquid_fraction: float = 0.0

    # Atmosphere
    atmosphere: Atmosphere = field(default_factory=Atmosphere)

    # Derived (computed)
    _surface_gravity: Optional[float] = None
    _escape_velocity: Optional[float] = None
    _base_temperature_k: Optional[float] = None
    _magnetic_field_earth_normal: Optional[float] = None

    @property
    def surface_gravity(self) -> float:
        """Surface gravity in Earth g's."""
        if self._surface_gravity is None:
            self._surface_gravity = self.mass_earth / (self.radius_earth ** 2)
        return self._surface_gravity

    @property
    def escape_velocity(self) -> float:
        """Escape velocity relative to Earth."""
        if self._escape_velocity is None:
            self._escape_velocity = math.sqrt(
                2 * self.mass_earth / self.radius_earth
            ) * 11.186  # Earth's escape velocity in km/s
        return self._escape_velocity

    @property
    def solar_flux(self) -> float:
        """Solar flux at this planet's orbital distance (W/m²)."""
        distance_m = self.orbital_distance_au * 1.496e11
        if distance_m == 0:
            return 0
        return self.star.luminosity_watts / (4 * math.pi * distance_m ** 2)

    @property
    def equilibrium_temperature(self) -> float:
        """Blackbody equilibrium temperature in Kelvin, before greenhouse."""
        flux = self.solar_flux
        if flux <= 0:
            return 0
        return (flux * (1 - self.albedo) / (4 * STEFAN_BOLTZMANN)) ** 0.25

    @property
    def surface_temperature_k(self) -> float:
        """Surface temperature accounting for greenhouse effect."""
        if self._base_temperature_k is None:
            base = self.equilibrium_temperature
            greenhouse_warming = self.atmosphere.greenhouse_factor
            self._base_temperature_k = base + greenhouse_warming
        return self._base_temperature_k

    @property
    def surface_temperature_c(self) -> float:
        return self.surface_temperature_k - 273.15

    @property
    def magnetic_field(self) -> float:
        """Estimated magnetic field strength relative to Earth.

        Depends on core size, rotation rate, and convection.
        Simplified model.
        """
        if self._magnetic_field_earth_normal is None:
            rotation_factor = (24.0 / self.rotation_period_hours) ** 0.5
            core_factor = (self.iron_core_fraction / 0.32) ** 1.5
            mass_factor = min(self.mass_earth ** 0.3, 2.0)
            self._magnetic_field_earth_normal = rotation_factor * core_factor * mass_factor
        return self._magnetic_field_earth_normal

    @property
    def atmospheric_retention(self) -> str:
        """How well the planet retains its atmosphere."""
        if self.escape_velocity > 10 and self.surface_temperature_k < 1000:
            return "STRONG"
        elif self.escape_velocity > 5 and self.surface_temperature_k < 500:
            return "MODERATE"
        elif self.escape_velocity > 3:
            return "WEAK"
        else:
            return "NONE"

    @property
    def habitability_index(self) -> float:
        """Aggregate habitability score 0-100.

        Considers temperature, atmosphere, gravity, radiation shielding, water.
        """
        score = 0.0

        # Temperature (ideal: 0-30°C)
        temp_c = self.surface_temperature_c
        if -10 <= temp_c <= 40:
            score += 25 * (1 - abs(temp_c - 15) / 30)
        elif -40 <= temp_c <= 60:
            score += 10

        # Atmosphere (pressure 0.5-2.0 atm ideal)
        pressure = self.atmosphere.total_pressure
        if 0.5 <= pressure <= 2.0:
            score += 20
        elif 0.2 <= pressure <= 3.0:
            score += 10

        # Oxygen (need some)
        if self.atmosphere.oxygen > 0.1:
            score += 15

        # Magnetic field (radiation shielding)
        if self.magnetic_field > 0.3:
            score += 15

        # Water
        if self.hydrosphere_liquid_fraction > 0.01:
            score += 15
        if self.hydrosphere_ice_fraction > 0.05:
            score += 5

        # Gravity (0.8-1.3g ideal)
        if 0.8 <= self.surface_gravity <= 1.3:
            score += 10
        elif 0.5 <= self.surface_gravity <= 2.0:
            score += 5

        return min(score, 100.0)


def generate_star(rng: random.Random, name: str) -> Star:
    """Generate a random star with realistic properties."""
    # Weight toward stars likely to have habitable planets
    spectral_weights = {
        "F": 0.1, "G": 0.35, "K": 0.35, "M": 0.2
    }
    spec = rng.choices(
        list(spectral_weights.keys()),
        weights=list(spectral_weights.values()),
        k=1,
    )[0]

    luminosity_map = {
        "F": (1.5, 6.0),
        "G": (0.6, 1.5),
        "K": (0.1, 0.6),
        "M": (0.01, 0.1),
    }
    lo, hi = luminosity_map[spec]
    luminosity = rng.uniform(lo, hi)

    mass_map = {
        "F": (1.04, 1.4),
        "G": (0.8, 1.04),
        "K": (0.45, 0.8),
        "M": (0.08, 0.45),
    }
    lo, hi = mass_map[spec]
    mass = rng.uniform(lo, hi)

    temp_map = {
        "F": (6000, 7500),
        "G": (5200, 6000),
        "K": (3700, 5200),
        "M": (2400, 3700),
    }
    lo, hi = temp_map[spec]
    temp = rng.uniform(lo, hi)

    return Star(
        name=name,
        spectral_type=spec,
        luminosity_solar=luminosity,
        mass_solar=mass,
        temperature_k=temp,
        age_gyr=rng.uniform(1.0, 10.0),
    )


def generate_planet(
    rng: random.Random,
    name: str,
    designation: str,
    star: Star,
    orbital_distance_au: float,
    prefer_habitable: bool = False,
) -> Planet:
    """Generate a planet with physically consistent properties."""
    mass = rng.uniform(0.3, 3.5)
    if prefer_habitable:
        mass = rng.uniform(0.5, 2.5)  # Avoid extreme masses for candidates

    # Radius from mass (simplified mass-radius relation)
    # Rocky planets: R ∝ M^0.27 (roughly)
    radius = mass ** 0.27

    rotation = rng.uniform(8, 200)  # hours
    axial_tilt = rng.uniform(0, 45)

    iron_core = rng.uniform(0.15, 0.45)
    albedo = rng.uniform(0.1, 0.8)

    # Atmosphere depends on mass and temperature
    solar_flux = star.luminosity_solar / (orbital_distance_au ** 2)
    base_temp = (solar_flux * 1361 * (1 - albedo) / (4 * STEFAN_BOLTZMANN)) ** 0.25

    # Build atmosphere
    escape_v = math.sqrt(2 * mass / radius) * 11.186
    atm_retention = escape_v > 5 and base_temp < 800

    atmosphere = Atmosphere()
    if atm_retention:
        atmosphere.nitrogen = rng.uniform(0.1, 1.5)
        atmosphere.co2 = rng.uniform(0.001, 0.5)
        atmosphere.argon = rng.uniform(0.005, 0.05)
        if base_temp > 200:
            atmosphere.water_vapor = rng.uniform(0.0, 0.05)
        atmosphere.methane = rng.uniform(0.0, 0.01)
        atmosphere.oxygen = rng.uniform(0.0, 0.05)  # Rare without life

    # Hydrosphere
    hydrosphere_liquid = 0.0
    hydrosphere_ice = 0.0
    if atm_retention and atmosphere.total_pressure > 0.1:
        if base_temp > 273:
            hydrosphere_liquid = rng.uniform(0.0, 0.3)
        if base_temp < 350:
            hydrosphere_ice = rng.uniform(0.0, 0.4)

    return Planet(
        name=name,
        designation=designation,
        mass_earth=mass,
        radius_earth=radius,
        orbital_distance_au=orbital_distance_au,
        star=star,
        rotation_period_hours=rotation,
        axial_tilt_degrees=axial_tilt,
        iron_core_fraction=iron_core,
        albedo=albedo,
        hydrosphere_ice_fraction=hydrosphere_ice,
        hydrosphere_liquid_fraction=hydrosphere_liquid,
        atmosphere=atmosphere,
    )


def generate_system(rng: random.Random, star_name: str, num_planets: int = 5) -> tuple[Star, list[Planet]]:
    """Generate a complete planetary system."""
    star = generate_star(rng, star_name)

    planets = []
    # Distribute planets across system
    for i in range(num_planets):
        # Distribute distances with some randomness
        base_dist = 0.1 * (i + 1) ** 1.5
        dist = base_dist * rng.uniform(0.7, 1.3)

        designation = f"{star_name}-{['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII'][i]}"

        # Prefer habitable zone for one planet
        in_hz = star.habitable_zone_inner_au <= dist <= star.habitable_zone_outer_au
        planet = generate_planet(
            rng,
            name=f"{star_name}-{i + 1}",
            designation=designation,
            star=star,
            orbital_distance_au=dist,
            prefer_habitable=in_hz,
        )
        planets.append(planet)

    return star, planets
