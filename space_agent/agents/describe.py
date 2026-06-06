"""Narrative description generator for planets.

Produces prose descriptions from physical properties. This is a
rendering concern — the simulation engine only deals with physics.
The describe() function takes a planet dict and returns human-readable
text suitable for game transcripts and showcase material.

Descriptions are generated per-category and composed. Each category
keys off property ranges to select appropriate text, then fills in
planet-specific details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from space_agent.simulation.planet import Planet


def describe(planet: Planet) -> str:
    """Generate a full narrative description of a planet.

    Composes per-category descriptions into a single readable block.
    """
    sections = []

    # Sky and atmosphere
    atm = _describe_atmosphere(planet)
    if atm:
        sections.append(atm)

    # Surface conditions
    surface = _describe_surface(planet)
    if surface:
        sections.append(surface)

    # Gravity and movement
    gravity = _describe_gravity(planet)
    if gravity:
        sections.append(gravity)

    # Magnetic field and radiation
    radiation = _describe_radiation(planet)
    if radiation:
        sections.append(radiation)

    # Resources and geology
    geology = _describe_geology(planet)
    if geology:
        sections.append(geology)

    # Habitability summary
    habitability = _describe_habitability(planet)
    if habitability:
        sections.append(habitability)

    return "\n\n".join(sections)


def _describe_atmosphere(planet: Planet) -> str:
    """Describe atmospheric appearance and feel."""
    atm = planet.atmosphere
    pressure = atm.total_pressure
    temp_c = planet.surface_temperature_c
    comp = atm.summary()

    # Determine dominant gas
    dominant = max(comp, key=comp.get)
    dominant_pct = comp[dominant]

    parts = []

    # Pressure character
    if pressure < 0.01:
        parts.append("The planet's surface lies exposed to the void, with only the faintest wisp of gas marking where atmosphere should be. Stars burn cold and brilliant in the black sky, their light unfiltered by any atmospheric veil. Any liquid water would boil away instantly in this near-perfect vacuum, while the ground itself radiates heat into space with brutal efficiency.")
    elif pressure < 0.3:
        parts.append("A gossamer veil of gas drapes across the landscape, so ethereal it barely registers against the skin. The sky appears as a deep indigo during daylight, transitioning to an inky blackness where stars twinkle with crystal clarity even when the sun is high. Winds, when they come, whisper rather than howl, carrying fine dust in delicate patterns across the barren terrain. The thin atmosphere offers minimal protection from solar radiation, leaving the surface bathed in harsh ultraviolet light that would be lethal to most Earth life.")
    elif pressure < 0.7:
        parts.append("The atmosphere wraps the planet in a modest embrace, substantial enough to create visible weather patterns yet still thinner than Earth's. During daylight hours, the sky displays a pale blue hue, deepening to violet near the horizon. Clouds form in wispy, delicate formations, occasionally releasing sparse precipitation that evaporates before reaching the ground in many regions. Temperature swings between day and night remain extreme, with the thin air unable to effectively redistribute heat across the surface.")
    elif pressure <= 1.5:
        parts.append("Breathable and familiar, the atmosphere envelops the planet with Earth-like pressure, supporting complex and dynamic weather systems. The sky presents a rich blue canvas during daytime, occasionally painted with towering cumulus clouds or streaked with cirrus formations. Weather patterns vary dramatically by region and season, from gentle breezes to violent storms that can span continents. The atmospheric blanket effectively moderates temperature extremes, creating habitable conditions across much of the planet's surface.")
    elif pressure <= 3.0:
        parts.append("The air presses down with palpable weight, creating a sensation akin to perpetual mild compression. Colors appear more vibrant and saturated through the dense medium, while distant objects seem closer than they truly are. Cloud formations are massive and imposing, often developing into tremendous storm systems that can last for weeks. The thick atmosphere acts as an efficient heat distributor, reducing temperature variations between day and night but potentially creating oppressive humidity in equatorial regions.")
    else:
        parts.append("A crushing ocean of air bears down relentlessly on the surface, creating conditions that would collapse most Earth structures. The sky appears as a deep, almost purple blue, with the sun's disk noticeably dimmed even at zenith. Atmospheric phenomena dominate the landscape, with permanent storm systems and bizarre cloud formations that defy Earth-based meteorological understanding. The extreme pressure forces gases into unusual states, potentially creating strange chemical compounds that only exist under such crushing conditions.")

    # Composition and color
    co2_pct = comp.get("CO₂", 0)
    so2_present = atm.other > 0.005 or atm.methane > 0.01
    h2o_pct = comp.get("H₂O", 0)

    if dominant == "CO₂" and dominant_pct > 50:
        if temp_c > 100:
            parts.append(
                "The sky is a perpetual, hazy orange-yellow under a crushing blanket of carbon dioxide. "
                "Thick clouds of sulfuric acid and dust swirl in the oppressive heat, creating a hellish greenhouse effect. "
                "The atmosphere is so dense that the sun appears as a dim, reddish disk even at noon. "
                "The air shimmers with heat distortion, and the pressure is so immense it would crush unprotected life instantly."
            )
        elif temp_c > 0:
            parts.append(
                "A thick carbon dioxide atmosphere bathes the world in an eerie, pale orange glow. "
                "High-altitude clouds form a perpetual ceiling, diffusing sunlight into a uniform, shadowless illumination. "
                "The air is still and heavy, with occasional wisps of fog that hug the ground in the cooler hours. "
                "Colors appear washed out and muted, as if viewed through a permanent smog filter."
            )
        else:
            parts.append(
                "The carbon dioxide atmosphere creates a haunting amber sky that never fully darkens. "
                "Even in the coldest hours, the greenhouse effect provides a faint warmth that barely penetrates the chill. "
                "Dry ice snow occasionally falls from the thin clouds, sublimating before reaching the ground. "
                "The landscape is cast in perpetual twilight, with long, soft shadows that never completely disappear."
            )
    elif dominant == "N₂" and dominant_pct > 60:
        if h2o_pct > 1:
            parts.append(
                "The nitrogen sky is a deep, rich blue that darkens to violet near the horizon. "
                "Fluffy white clouds drift across the heavens, occasionally gathering into impressive thunderheads. "
                "The air carries the crisp scent of ozone before storms, and rainbows frequently arc across the sky after showers. "
                "Morning fog hugs low-lying areas, burning off as the sun climbs higher."
            )
        else:
            parts.append(
                "The nitrogen atmosphere creates a pristine, crystal-clear sky of intense blue that darkens to almost black at the zenith. "
                "Without significant water vapor, the sky remains cloudless most days, revealing the stark beauty of the cosmos. "
                "Stars are visible even during daylight hours near the sun's position, creating an ethereal display. "
                "The air is remarkably transparent, allowing visibility to the distant horizon with perfect clarity."
            )
    elif dominant == "N₂" and co2_pct > 15:
        parts.append(
            "The nitrogen sky carries subtle hints of orange and pink, especially near sunrise and sunset. "
            "Wispy clouds occasionally streak across the heavens, catching the light in brilliant displays. "
            "The air feels slightly heavier than a pure nitrogen atmosphere, with a faint metallic tang detectable on the tongue. "
            "During certain atmospheric conditions, the CO₂ creates spectacular light refraction effects, turning the sky into a canvas of shifting pastels."
        )
    elif pressure < 0.01:
        pass  # already handled above
    else:
        parts.append(
            f"The atmosphere is primarily {dominant.replace('₂', '')} "
            f"({dominant_pct:.0f}%), with a composition unlike anything familiar."
        )

    # Toxicity note
    o2_pct = comp.get("O₂", 0)
    if o2_pct < 5 and pressure > 0.1:
        if o2_pct < 0.5:
            parts.append("The air is entirely unbreathable — no free oxygen is detectable.")
        else:
            parts.append("Trace oxygen is present but far below what would sustain respiration.")

    return " ".join(parts) if parts else ""


def _describe_surface(planet: Planet) -> str:
    """Describe surface conditions and terrain."""
    temp_c = planet.surface_temperature_c
    liquid = planet.hydrosphere_liquid_fraction
    ice = planet.hydrosphere_ice_fraction

    parts = []

    # Temperature feel
    if temp_c > 200:
        parts.append("The world's surface blazes with an infernal fury, a hellish landscape where temperatures soar high enough to reduce lead to molten rivers and vaporize organic matter in moments. The air itself seems to shimmer and distort with heat, creating mirages that dance across a terrain of cracked, baked rock. Any probe landing here would need extraordinary cooling systems just to survive long enough to transmit data before its components begin to fail in the relentless thermal assault.")
    elif temp_c > 100:
        parts.append("The planet's surface is a scorching wasteland, where the sun beats down with merciless intensity. Rocks glow dull red in the perpetual heat, and the atmosphere carries the acrid scent of vaporized minerals. Unprotected equipment would rapidly degrade as plastics warped, metals expanded, and electronics succumbed to thermal stress. Only the most specialized heat-resistant materials could withstand this hostile environment for more than a few hours.")
    elif temp_c > 50:
        parts.append("A harsh, unforgiving heat blankets this world's surface, creating an environment that pushes the limits of even our most advanced technology. The landscape appears bleached and weathered by constant thermal stress, with heat ripples constantly disturbing the horizon. Biological systems would rapidly dehydrate and fail, while conventional electronics would require extensive cooling to prevent catastrophic failure. This is a world that demands respect and careful engineering to explore.")
    elif temp_c > 30:
        parts.append("The surface radiates a dry, oppressive heat reminiscent of the hottest deserts on Earth. While challenging for human physiology, this temperature range remains within the operational parameters of well-designed exploration equipment. The terrain likely features heat-adapted geological formations, perhaps with mineral deposits that have been baked into interesting crystalline patterns by the persistent warmth. Careful thermal management would be essential for extended surface operations.")
    elif temp_c > 15:
        parts.append("The surface offers a surprisingly temperate climate, with temperatures falling within a comfortable range for human activity. This world's environment feels remarkably familiar, with conditions that would allow for extended exploration without extreme protective measures. The landscape might support complex geological features shaped by moderate thermal cycles, potentially including erosion patterns similar to those found in temperate regions of Earth. This temperature range represents a rare and valuable find in the cosmos.")
    elif temp_c > 0:
        parts.append("A crisp coolness dominates the surface, with temperatures hovering just above the freezing point of water. The landscape likely features a fascinating interplay between liquid and solid states, perhaps with frost patterns that shift with daily temperature variations. While chilly by human standards, this environment would be manageable with proper insulation. The cool temperatures might preserve interesting geological features and potentially support unique chemical processes that would be impossible in warmer climates.")
    elif temp_c > -30:
        parts.append("The surface is gripped by a persistent cold that would challenge any explorer. Ice likely blankets much of the terrain, creating a crystalline wonderland of frozen formations. The landscape appears stark and pristine, with sharp edges preserved by the freezing temperatures. Specialized equipment with robust heating systems would be essential for any surface operations, as conventional machinery would quickly succumb to the cold. This world exists in a state of suspended animation, its features locked in place by the deep freeze.")
    elif temp_c > -80:
        parts.append("An extreme arctic environment dominates this world, with temperatures that render most materials brittle and unworkable. The surface is likely a frozen desert where even the most resilient Earth-based equipment would struggle to function. The atmosphere itself might be partially condensed, creating unusual optical phenomena in the sky. Only specially engineered probes with exotic materials capable of maintaining ductility at these temperatures could effectively explore this frozen realm, where molecular motion has been reduced to a mere crawl.")
    else:
        parts.append("This world exists in a state of profound cold that challenges our understanding of temperature extremes. The surface is so frigid that even carbon dioxide would freeze and fall as dry ice snow, creating an alien landscape of exotic crystalline formations. The atmosphere itself might be nearly frozen, with only the thinnest of gases remaining in a gaseous state. Exploring such an environment would require technology that pushes the boundaries of material science, as conventional physics begins to behave strangely at these temperature extremes, where quantum effects might become visible on a macroscopic scale.")

    # Hydrosphere
    if liquid > 0.15:
        parts.append(f"Vast oceans dominate the world, with shimmering azure waves lapping across {liquid * 100:.0f}% of the planet's surface, their depths hiding countless mysteries.")
    elif liquid > 0.01:
        parts.append(f"Scattered across the landscape, crystalline lakes and winding rivers cover approximately {liquid * 100:.0f}% of the surface, their surfaces reflecting the sky like mirrors.")
    elif liquid > 0:
        parts.append("In sheltered valleys and deep craters, small pockets of liquid water persist — rare oases that might sustain life in an otherwise arid world.")
    if ice > 0.2:
        parts.append(f"Magnificent glaciers and frozen tundras blanket {ice * 100:.0f}% of the planet, creating a dazzling white landscape that sparkles under the light of distant stars.")
    elif ice > 0.01:
        parts.append(f"Patches of permafrost and seasonal ice cover about {ice * 100:.0f}% of the surface, forming intricate patterns of frost that transform the terrain with the changing seasons.")

   # Terrain hint from temperature + composition
    if temp_c > 100 and planet.atmosphere.co2 > 0.3:
        parts.append("The planet's surface is a hellscape of volcanic plains stretching to the horizon. Dark basaltic rock forms vast, cracked flats that shimmer with heat distortion. Towering shield volcanoes dot the landscape, their slopes streaked with glowing lava flows. Fumaroles punctuate the terrain, spewing columns of toxic gases into the oppressive atmosphere. The ground itself seems to breathe, with periodic tremors sending ripples through the semi-molten surface.")
    elif temp_c < -50 and planet.atmosphere.total_pressure < 0.1:
        parts.append("An airless graveyard of cosmic collisions spreads before you. The surface is a stark mosaic of impact craters of all sizes, from microscopic pockmarks to colossal basins hundreds of kilometers across. In the absence of atmosphere, the regolith remains undisturbed for eons, preserving the violent history of this world in perfect detail. Sharp-edged rocks and fine dust create a treacherous landscape that has never known wind or weather to smooth its harsh features.")
    elif liquid < 0.01 and ice < 0.01 and temp_c > 0:
        parts.append("Endless dunes of fine particulate matter roll across the planet's surface like frozen waves of an ancient ocean. The landscape is a monochromatic study in beige and ochre, with occasional outcroppings of bare rock breaking through the sandy expanse. No rivers, lakes, or even morning dew grace this world—the atmosphere holds barely enough moisture to form the occasional dust storm rather than rain. The sun beats down mercilessly on this parched realm where water exists only as a distant memory or buried treasure.")

    return " ".join(parts) if parts else ""


def _describe_gravity(planet: Planet) -> str:
    """Describe the effect of gravity on movement and structures."""
    g = planet.surface_gravity

    if g < 0.3:
        return "Gravity is negligible — a near-weightless environment where anchoring is essential and movement is more like flying."
    elif g < 0.6:
        return (
            f"Gravity is light at {g:.1f}g. Movement feels buoyant, each step carrying far "
            "more distance than on Earth. Structures can be lighter and taller, but retaining "
            "an atmosphere is this world's deeper challenge."
        )
    elif g < 0.9:
        return (
            f"Gravity is slightly below Earth-normal at {g:.1f}g. The difference is subtle but "
            "perceptible — a lightness in the limbs that would take adjustment."
        )
    elif g <= 1.3:
        return f"Gravity is Earth-like at {g:.1f}g, one less variable to engineer around."
    elif g <= 2.0:
        return (
            f"Gravity is heavy at {g:.1f}g. Every step carries the weight of an extra burden. "
            "Structural engineering becomes significantly more demanding, and launch costs "
            "increase steeply — escape velocity is correspondingly higher."
        )
    else:
        return (
            f"Gravity is crushing at {g:.1f}g. Movement without mechanical assistance would be "
            "exhausting or impossible. Structures must be over-engineered, and reaching orbit "
            "demands enormous energy expenditure."
        )


def _describe_radiation(planet: Planet) -> str:
    """Describe magnetic field and radiation environment."""
    field = planet.magnetic_field
    star = planet.star
    flux = planet.solar_flux
    parts = []
    if field > 1.0:
        parts.append("Powerful magnetic field lines weave a protective cocoon around the planet, creating spectacular auroral displays at the poles while deflecting harmful cosmic and stellar radiation. The magnetosphere extends far into space, forming a formidable shield against the star's particle emissions.")
    elif field > 0.5:
        parts.append("Moderate magnetic forces shape the planet's interaction with space, creating visible auroras during periods of heightened stellar activity. The protective field extends several planetary radii into space, significantly reducing but not eliminating radiation exposure on the surface.")
    elif field > 0.2:
        parts.append("Weak magnetic ripples barely reach beyond the planet's atmosphere, offering limited protection during normal conditions but leaving the surface vulnerable during stellar flares. Occasional auroral glimmers mark where the feeble field interacts with charged particles from the star.")
    else:
        parts.append("With virtually no magnetic defense, the planet lies exposed to the full fury of space. Stellar winds and cosmic rays bombard the surface unimpeded, stripping away atmosphere over geological time and rendering the surface hostile to complex life.")

    # Stellar flux context
    earth_flux = 1361  # W/m²
    if flux > earth_flux * 3:
        parts.append("The star's fury scours the planet's surface, bathing it in relentless radiation that would strip the atmosphere from lesser worlds. Colonists must live beneath thick radiation shields or in deep subterranean habitats, while specialized materials are required for any surface structures to prevent rapid degradation. The intense stellar wind creates spectacular auroral displays visible even during daylight hours.")
    elif flux > earth_flux * 1.5:
        parts.append("The sun hangs heavy in the sky, its disk noticeably larger than Earth's. Radiation levels require careful management in colony design, with protected corridors connecting buildings and specialized glass that filters harmful wavelengths. Colonists must monitor their exposure time, especially during peak hours when the star's intensity can cause sunburn in minutes rather than hours. The landscape is baked in perpetual summer, with temperatures soaring in unshaded areas.")
    elif flux < earth_flux * 0.3:
        parts.append("The star hangs in the sky like a pale coin, its light barely sufficient to cast shadows. Daytime resembles a perpetual twilight on Earth, with colors washed out and visibility limited. Solar panels struggle to generate meaningful power, forcing colonies to rely on alternative energy sources. Plants must be genetically engineered to photosynthesize efficiently in the dim conditions, and the cold climate requires constant heating to maintain habitable temperatures.")

    return " ".join(parts) if parts else ""


def _describe_geology(planet: Planet) -> str:
    """Describe geological activity and mineral resources."""
    parts = []
    core = planet.iron_core_fraction
    # Tectonic inference from core and age
    if core > 0.35 and planet.star.age_gyr < 6:
        parts.append("Beneath the surface, the planet's heart beats with restless fury. A massive iron core churns with magnetic energy, powering a dynamo that reaches tendrils of force far into space. The crust fractures and reforms in an endless cycle, where tectonic plates grind against each other in slow, inexorable motion, birthing mountain ranges that would dwarf Earth's Himalayas. Volcanic chains punctuate the landscape like wounds, spewing molten rock and precious metals from the planet's fiery depths. This is a world still in its geological youth, its face constantly reshaped by the violent processes of formation.")
    elif core > 0.25:
        parts.append("The planet's geological pulse beats at a measured pace, neither frenetic nor dormant. Deep beneath the surface, convection currents stir the mantle with enough vigor to occasionally remind inhabitants of the planet's living nature. Earthquakes ripple through the crust at predictable intervals, while volcanic regions smolder with contained energy, occasionally releasing pressure in spectacular displays. The landscape bears the scars of ancient geological violence—mountain ranges worn by eons of erosion, vast plains formed by long-cooled lava flows, and mineral-rich regions where the planet's bounty lies exposed for those who know where to look.")
    else:
        parts.append("This ancient world has settled into geological tranquility. The once-fierce processes that shaped its features have largely subsided, leaving behind a landscape of remarkable stability. The iron core, while still present, no longer drives the violent tectonic activity of the planet's youth. Instead, gentle undulations mark the surface, with only occasional tremors disturbing the long peace. Mountains have been worn to gentle hills by billions of years of weather, their mineral wealth exposed through gradual erosion. The planet's geological story is written in its sedimentary layers—a testament to the vast ages that have passed since the last great upheaval reshaped its face.")
    # Resource hint from mass and composition
    if planet.mass_earth > 2.0:
        parts.append("The planet's substantial mass has worked as a natural refinery over billions of years. Heavy elements have sunk deep into the core, creating a treasure trove of metals that would be the envy of any spacefaring civilization. Yet the crust remains richly endowed with accessible deposits—veins of precious metals threading through mountain ranges, rare earth elements concentrated in ancient geological formations, and crystal formations of breathtaking purity and size. The high gravity has compressed these resources into denser configurations than found on smaller worlds, making mining operations uniquely challenging but potentially extraordinarily rewarding.")
    elif planet.mass_earth > 1.0:
        parts.append("The planet's Earth-like mass has produced a geological bounty familiar yet distinct. Continental drift has created diverse mineral provinces—mountain ranges rich in metallic ores, ancient seabeds transformed into fossil fuel deposits, and volcanic regions where the planet's internal processes have concentrated rare elements. The moderate gravity allows for a balanced distribution of resources, neither too compressed nor too dispersed. Prospectors would find a world where the planet's geological history has conveniently sorted and concentrated its wealth, creating natural resource maps that tell the story of tectonic movements across hundreds of millions of years.")

    return " ".join(parts) if parts else ""


def _describe_habitability(planet: Planet) -> str:
    """Summarize habitability assessment."""
    h = planet.habitability_index
    temp_c = planet.surface_temperature_c

    if h >= 75:
        return f"This world is remarkably habitable (index: {h:.0f}/100). With modest engineering, a self-sustaining colony is feasible."
    elif h >= 50:
        return (
            f"This world is marginally habitable (index: {h:.0f}/100). Significant terraforming "
            "would be required, but the fundamentals are present."
        )
    elif h >= 25:
        return (
            f"This world is challenging (index: {h:.0f}/100). Terraforming would be a "
            "multi-generational megaproject, but not impossible."
        )
    else:
        return (
            f"This world is deeply hostile (index: {h:.0f}/100). Colonization would require "
            "fully sealed habitats — terraforming is infeasible with current technology."
        )
