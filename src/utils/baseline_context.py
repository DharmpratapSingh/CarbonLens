#!/usr/bin/env python3
"""
Baseline Context Provider - Leverages ClimateGPT's base knowledge

This module provides curated baseline knowledge to enrich MCP data responses,
creating more informative and actionable answers.

Usage:
    from src.utils.baseline_context import BaselineContextProvider

    provider = BaselineContextProvider()

    # Add context to MCP response
    mcp_data = {"rows": [...], "meta": {...}}
    enriched = provider.enrich_response(
        mcp_data=mcp_data,
        question="Germany's power emissions change 2022-2023",
        persona="Climate Analyst"
    )
"""

from typing import Dict, List, Any, Optional
import re


class BaselineContextProvider:
    """
    Provides baseline climate knowledge to enrich MCP data responses.

    This leverages ClimateGPT's built-in knowledge (from training) to add
    context, explanations, and interpretations to raw MCP data.
    """

    def __init__(self):
        """Initialize baseline context knowledge base."""
        self._sector_context = self._load_sector_context()
        self._country_context = self._load_country_context()
        self._policy_context = self._load_policy_context()
        self._persona_frameworks = self._load_persona_frameworks()

    # =========================================================================
    # Public API
    # =========================================================================

    def enrich_response(
        self,
        mcp_data: Dict[str, Any],
        question: str,
        persona: str = "Climate Analyst"
    ) -> Dict[str, Any]:
        """
        Enrich MCP data with baseline context appropriate for persona.

        Args:
            mcp_data: Response from MCP tool call
            question: User's original question
            persona: Target persona (Climate Analyst, Research Scientist, etc.)

        Returns:
            Enriched response with data + context
        """
        # Extract key elements from question
        elements = self._extract_question_elements(question)

        # Build context based on question elements
        context = self._build_context(elements, persona)

        # Combine MCP data with baseline context
        enriched = {
            "mcp_data": mcp_data,
            "baseline_context": context,
            "combined_narrative": self._create_narrative(mcp_data, context, persona)
        }

        return enriched

    def get_sector_explanation(self, sector: str) -> str:
        """Get baseline explanation for a sector."""
        return self._sector_context.get(
            sector.lower(),
            f"The {sector} sector contributes to greenhouse gas emissions."
        )

    def get_policy_context(self, country: str, topic: str) -> Optional[str]:
        """Get policy context for country and topic."""
        country_key = country.lower().replace(" ", "_")
        country_policies = self._policy_context.get(country_key, {})
        return country_policies.get(topic)

    def get_interpretation_framework(self, persona: str) -> Dict[str, str]:
        """Get interpretation framework for persona."""
        return self._persona_frameworks.get(persona, {})

    # =========================================================================
    # Baseline Knowledge Base (Curated from ClimateGPT's training)
    # =========================================================================

    def _load_sector_context(self) -> Dict[str, str]:
        """
        Sector-specific baseline knowledge.

        This is SAFE to use - it's conceptual knowledge, not quantitative.
        Leverages ClimateGPT's training on climate science.
        """
        return {
            "transport": (
                "The transport sector includes road vehicles, aviation, shipping, and rail. "
                "It's primarily powered by fossil fuels (gasoline, diesel, jet fuel), making it "
                "a major source of CO₂ emissions. Decarbonization strategies include electric "
                "vehicles, hydrogen fuel, sustainable aviation fuels, and modal shifts to public transit."
            ),
            "power": (
                "The power sector generates electricity through various energy sources. "
                "Historically dominated by fossil fuels (coal, natural gas), it's transitioning to "
                "renewables (solar, wind, hydro). The power sector often decarbonizes fastest due to "
                "mature renewable technologies and policy incentives like carbon pricing and renewable mandates."
            ),
            "waste": (
                "The waste sector includes landfills, incineration, and waste treatment. "
                "Landfills produce methane (a potent greenhouse gas) from organic decomposition. "
                "Mitigation strategies include waste reduction, recycling, composting, and methane capture "
                "for energy generation."
            ),
            "agriculture": (
                "Agriculture emits greenhouse gases through livestock (methane from enteric fermentation), "
                "rice cultivation (methane from flooded paddies), and soil management (nitrous oxide from "
                "fertilizers). Climate-smart agriculture includes improved livestock feed, precision "
                "fertilization, and agroforestry."
            ),
            "buildings": (
                "Buildings emit through heating, cooling, lighting, and appliances. Both residential and "
                "commercial buildings consume significant energy, often from fossil fuel-powered grids. "
                "Efficiency improvements (insulation, LED lighting, heat pumps) and renewable energy "
                "integration are key mitigation strategies."
            ),
            "ind-combustion": (
                "Industrial combustion refers to fuel burning in manufacturing processes (steel, chemicals, "
                "cement, etc.). These industries require high-temperature heat, traditionally from coal and "
                "natural gas. Decarbonization involves electrification, hydrogen, and carbon capture."
            ),
            "ind-processes": (
                "Industrial process emissions come from chemical reactions in manufacturing (e.g., CO₂ from "
                "cement clinker production, limestone calcination). These are harder to abate than combustion "
                "emissions and may require carbon capture or alternative chemistry."
            ),
            "fuel-exploitation": (
                "Fuel exploitation includes extraction, processing, and transport of fossil fuels "
                "(oil, gas, coal). Emissions arise from methane leaks, flaring, and energy use in extraction. "
                "Reducing these requires leak detection, flaring reduction, and ultimately transitioning "
                "away from fossil fuels."
            )
        }

    def _load_country_context(self) -> Dict[str, Dict[str, str]]:
        """
        Country-specific baseline context.

        General information about countries' climate contexts - NOT quantitative data.
        """
        return {
            "germany": {
                "energy_context": (
                    "Germany has been a leader in renewable energy transition (Energiewende), "
                    "phasing out nuclear power and coal while expanding wind and solar."
                ),
                "policy": (
                    "Germany committed to carbon neutrality by 2045 (earlier than EU's 2050 target) "
                    "and coal phaseout by 2038 (recently accelerated)."
                )
            },
            "china": {
                "energy_context": (
                    "China is the world's largest emitter but also largest renewable energy investor. "
                    "It has massive coal capacity but rapidly expanding solar and wind."
                ),
                "policy": (
                    "China committed to peak emissions before 2030 and carbon neutrality by 2060. "
                    "It has the world's largest carbon trading market (launched 2021)."
                )
            },
            "united_states_of_america": {
                "energy_context": (
                    "The US is transitioning from coal to natural gas and renewables. "
                    "State-level policies (California, NY) often lead federal action."
                ),
                "policy": (
                    "US rejoined Paris Agreement in 2021, targeting 50-52% emission reduction by 2030. "
                    "Inflation Reduction Act (2022) provides major clean energy incentives."
                )
            },
            "india": {
                "energy_context": (
                    "India relies heavily on coal for electricity but has ambitious renewable targets. "
                    "Balancing development needs with climate action is a key challenge."
                ),
                "policy": (
                    "India targets 50% renewable electricity by 2030 and net zero by 2070. "
                    "Emphasizes equity and common but differentiated responsibilities."
                )
            },
            "france": {
                "energy_context": (
                    "France has low-carbon electricity due to nuclear power (70%+), with growing "
                    "renewable integration. Transport and buildings are key decarbonization challenges."
                ),
                "policy": (
                    "France targets carbon neutrality by 2050, with interim targets including "
                    "40% emission reduction by 2030 relative to 1990."
                )
            },
            "japan": {
                "energy_context": (
                    "Japan increased coal use after Fukushima nuclear shutdown, but is now "
                    "restarting nuclear and expanding renewables, especially offshore wind."
                ),
                "policy": (
                    "Japan targets carbon neutrality by 2050 and 46% emission reduction by 2030. "
                    "Emphasis on hydrogen and ammonia for hard-to-abate sectors."
                )
            }
        }

    def _load_policy_context(self) -> Dict[str, str]:
        """
        General policy framework knowledge.

        Safe baseline knowledge about climate policy frameworks.
        """
        return {
            "paris_agreement": (
                "The Paris Agreement (2015) aims to limit global warming to well below 2°C, "
                "pursuing 1.5°C. Countries submit Nationally Determined Contributions (NDCs) "
                "updated every 5 years."
            ),
            "net_zero": (
                "Net zero means balancing greenhouse gas emissions with removals, achieving no "
                "net increase in atmospheric GHG concentration. Over 70 countries have committed "
                "to net zero by mid-century."
            ),
            "carbon_pricing": (
                "Carbon pricing mechanisms (carbon tax or cap-and-trade) put a price on emissions, "
                "incentivizing reduction. The EU Emissions Trading System (ETS) is the largest, "
                "with over 30 carbon pricing systems globally."
            ),
            "ipcc": (
                "The Intergovernmental Panel on Climate Change (IPCC) provides scientific assessments "
                "on climate change. Its reports (latest: AR6, 2021-2023) inform international policy "
                "including the Paris Agreement."
            )
        }

    def _load_persona_frameworks(self) -> Dict[str, Dict[str, Any]]:
        """
        Persona-specific interpretation frameworks.

        These define HOW each persona should interpret and contextualize data.
        """
        return {
            "Climate Analyst": {
                "focus": ["mitigation priorities", "policy implications", "actionable insights"],
                "language_style": "strategic, action-oriented",
                "key_questions": [
                    "What does this mean for policy?",
                    "Which entities should be prioritized?",
                    "What mitigation strategies apply?"
                ],
                "context_elements": [
                    "policy_alignment",
                    "sector_strategies",
                    "geographic_targeting"
                ]
            },
            "Research Scientist": {
                "focus": ["methodology", "data quality", "uncertainty", "scientific rigor"],
                "language_style": "precise, evidence-based, methodological",
                "key_questions": [
                    "What are the data limitations?",
                    "What methodology was used?",
                    "What's the uncertainty range?"
                ],
                "context_elements": [
                    "edgar_methodology",
                    "temporal_resolution",
                    "spatial_uncertainty",
                    "validation_sources"
                ]
            },
            "Financial Analyst": {
                "focus": ["risk signals", "concentration", "momentum", "material changes"],
                "language_style": "concise, directional, risk-aware",
                "key_questions": [
                    "Where is the concentration risk?",
                    "What's the momentum (rising/falling)?",
                    "What's material for investors?"
                ],
                "context_elements": [
                    "regulatory_risk",
                    "stranded_assets",
                    "portfolio_exposure",
                    "comparative_benchmarks"
                ]
            },
            "Student": {
                "focus": ["understanding", "definitions", "real-world meaning", "simplicity"],
                "language_style": "friendly, clear, educational",
                "key_questions": [
                    "What does this mean?",
                    "Why does it matter?",
                    "How does it work?"
                ],
                "context_elements": [
                    "definitions",
                    "analogies",
                    "why_it_matters",
                    "simple_comparisons"
                ]
            }
        }

    # =========================================================================
    # Context Building
    # =========================================================================

    def _extract_question_elements(self, question: str) -> Dict[str, Any]:
        """Extract key elements from user question."""
        elements = {
            "sectors": [],
            "countries": [],
            "years": [],
            "comparison": False,
            "trend": False,
            "seasonal": False
        }

        # Extract sectors
        for sector in self._sector_context.keys():
            if sector.replace("-", " ") in question.lower():
                elements["sectors"].append(sector)

        # Extract countries
        for country in ["germany", "china", "united states", "usa", "india", "france", "japan", "uk"]:
            if country in question.lower():
                elements["countries"].append(country.replace(" ", "_"))

        # Extract years
        years = re.findall(r'\b(20\d{2})\b', question)
        elements["years"] = [int(y) for y in years]

        # Detect question types
        elements["comparison"] = any(word in question.lower() for word in ["compare", "vs", "versus", "difference"])
        elements["trend"] = any(word in question.lower() for word in ["change", "trend", "increase", "decrease"])
        elements["seasonal"] = any(word in question.lower() for word in ["seasonal", "monthly", "month"])

        return elements

    def _build_context(self, elements: Dict[str, Any], persona: str) -> Dict[str, str]:
        """Build contextual information based on question elements and persona."""
        context = {}

        # Add sector context
        if elements["sectors"]:
            context["sector_explanation"] = " ".join([
                self._sector_context.get(sector, "") for sector in elements["sectors"]
            ])

        # Add country context
        if elements["countries"]:
            country_contexts = []
            for country in elements["countries"]:
                country_info = self._country_context.get(country, {})
                if country_info:
                    country_contexts.append(
                        f"{country.replace('_', ' ').title()}: {country_info.get('energy_context', '')}"
                    )
            if country_contexts:
                context["country_context"] = " ".join(country_contexts)

        # Add persona-specific framing
        framework = self._persona_frameworks.get(persona, {})
        context["interpretation_focus"] = ", ".join(framework.get("focus", []))

        # Add change context for trends
        if elements["trend"] and elements["years"]:
            context["trend_context"] = self._get_trend_context(elements["years"])

        # Add seasonal context
        if elements["seasonal"]:
            context["seasonal_context"] = (
                "Seasonal patterns in emissions often reflect temperature variations "
                "(higher heating/cooling demand), economic cycles, and cultural factors "
                "(holidays, tourism). Understanding these patterns helps target interventions "
                "and manage seasonal capacity."
            )

        return context

    def _get_trend_context(self, years: List[int]) -> str:
        """Provide context for time period."""
        if not years:
            return ""

        min_year, max_year = min(years), max(years)

        # Add specific historical context for key periods
        context_snippets = []

        if 2020 in years or 2021 in years:
            context_snippets.append(
                "2020-2021 saw COVID-19 pandemic impacts with temporary emission reductions "
                "followed by rebounds."
            )

        if 2022 in years:
            context_snippets.append(
                "2022 experienced energy market disruptions from Russia-Ukraine conflict, "
                "affecting especially Europe's energy mix."
            )

        if 2023 in years:
            context_snippets.append(
                "2023 marked accelerated renewable deployment globally and record clean energy investment."
            )

        if max_year - min_year >= 5:
            context_snippets.append(
                f"The {min_year}-{max_year} period spans {max_year - min_year} years, "
                "sufficient to identify structural trends beyond year-to-year volatility."
            )

        return " ".join(context_snippets)

    def _create_narrative(
        self,
        mcp_data: Dict[str, Any],
        context: Dict[str, str],
        persona: str
    ) -> str:
        """
        Create combined narrative from MCP data and baseline context.

        This is a template - actual narrative generation would call LLM
        with structured prompt combining data + context.
        """
        narrative_parts = []

        # Start with data summary
        if "rows" in mcp_data and mcp_data["rows"]:
            row_count = len(mcp_data["rows"])
            narrative_parts.append(f"[MCP DATA: {row_count} data points retrieved]")

        # Add baseline context
        for key, value in context.items():
            if value:
                narrative_parts.append(f"[CONTEXT - {key}]: {value}")

        # Add persona-specific interpretation guide
        framework = self._persona_frameworks.get(persona, {})
        if framework:
            narrative_parts.append(
                f"[INTERPRETATION FOCUS]: {framework.get('interpretation_focus', '')}"
            )

        return "\n\n".join(narrative_parts)


# =============================================================================
# Pre-built Context Augmenters
# =============================================================================

class PolicyContextAugmenter:
    """Add policy context to emissions data responses."""

    @staticmethod
    def add_paris_alignment_context(country: str, sector: str, reduction_pct: float) -> str:
        """
        Add Paris Agreement alignment context.

        Args:
            country: Country name
            sector: Emissions sector
            reduction_pct: Percentage reduction observed

        Returns:
            Policy alignment context
        """
        if reduction_pct > 20:
            return (
                f"This {reduction_pct:.1f}% reduction in {country}'s {sector} sector "
                f"represents significant progress toward Paris Agreement targets. "
                f"Sustaining this pace would contribute meaningfully to the <2°C goal."
            )
        elif reduction_pct > 5:
            return (
                f"The {reduction_pct:.1f}% reduction shows positive movement but "
                f"may need acceleration to meet Paris Agreement timelines (50% by 2030 for many countries)."
            )
        else:
            return (
                f"The modest {reduction_pct:.1f}% reduction indicates policy implementation "
                f"gaps. Paris-aligned pathways typically require 7-10% annual reductions in key sectors."
            )


class SectorStrategyAugmenter:
    """Add sector-specific mitigation strategy context."""

    @staticmethod
    def get_decarbonization_strategies(sector: str, data_pattern: str = "declining") -> str:
        """
        Get relevant decarbonization strategies for sector based on data pattern.

        Args:
            sector: Emissions sector
            data_pattern: "declining", "increasing", or "stable"

        Returns:
            Strategy context
        """
        strategies = {
            "power": {
                "declining": "Renewable expansion (wind, solar) and coal retirement are likely driving reductions.",
                "increasing": "Consider accelerating renewable deployment, implementing carbon pricing, or retiring aging fossil plants.",
                "stable": "Power sector requires policy push (renewable mandates, grid modernization) to unlock potential."
            },
            "transport": {
                "declining": "Electric vehicle adoption and efficiency improvements may be contributing.",
                "increasing": "Priority strategies: EV incentives, public transit investment, carbon pricing on fuels.",
                "stable": "Transport decarbonization needs systemic change: electrification, modal shifts, urban planning."
            },
            "buildings": {
                "declining": "Energy efficiency retrofits and heat pump deployment likely contributing.",
                "increasing": "Focus on building codes, retrofit programs, and clean heating/cooling incentives.",
                "stable": "Buildings require policy attention: efficiency standards, appliance regulations, retrofit financing."
            }
        }

        return strategies.get(sector, {}).get(
            data_pattern,
            f"The {sector} sector shows a {data_pattern} emissions pattern."
        )


class EducationalContextAugmenter:
    """Add educational context for Student persona."""

    @staticmethod
    def create_analogy(emissions_mtco2: float, context_type: str = "cars") -> str:
        """
        Create relatable analogy for emissions magnitude.

        Args:
            emissions_mtco2: Emissions in MtCO₂
            context_type: Type of analogy ("cars", "trees", "homes")

        Returns:
            Analogy string
        """
        if context_type == "cars":
            # Average car emits ~4.6 tonnes CO₂/year
            cars_equivalent = int((emissions_mtco2 * 1_000_000) / 4.6)
            return f"That's like the emissions from {cars_equivalent:,} cars driving for a year!"

        elif context_type == "trees":
            # Average tree absorbs ~20 kg CO₂/year
            trees_needed = int((emissions_mtco2 * 1_000_000_000) / 20)
            return f"It would take {trees_needed:,} trees a year to absorb that much CO₂!"

        elif context_type == "homes":
            # Average home emits ~7.5 tonnes CO₂/year
            homes_equivalent = int((emissions_mtco2 * 1_000_000) / 7.5)
            return f"That's equivalent to the annual emissions of {homes_equivalent:,} homes!"

        return ""

    @staticmethod
    def explain_significance(change_pct: float) -> str:
        """
        Explain what a percentage change means in simple terms.

        Args:
            change_pct: Percentage change (positive = increase, negative = decrease)

        Returns:
            Simple explanation
        """
        abs_pct = abs(change_pct)
        direction = "increase" if change_pct > 0 else "decrease"

        if abs_pct > 20:
            magnitude = "huge"
            implication = "really significant for fighting climate change" if change_pct < 0 else "concerning for our climate goals"
        elif abs_pct > 10:
            magnitude = "big"
            implication = "important progress" if change_pct < 0 else "moving in the wrong direction"
        elif abs_pct > 5:
            magnitude = "noticeable"
            implication = "a good start" if change_pct < 0 else "needs attention"
        else:
            magnitude = "small"
            implication = "not changing much yet"

        return (
            f"A {abs_pct:.1f}% {direction} is a {magnitude} change. "
            f"This means emissions are {implication}."
        )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Example: Enrich a response with baseline context
    provider = BaselineContextProvider()

    # Simulated MCP response
    mcp_data = {
        "rows": [
            {"country_name": "Germany", "year": 2022, "MtCO2": 227.68},
            {"country_name": "Germany", "year": 2023, "MtCO2": 175.97}
        ],
        "meta": {"file_id": "power-country-year", "row_count": 2}
    }

    # Enrich with context
    enriched = provider.enrich_response(
        mcp_data=mcp_data,
        question="How did Germany's power emissions change from 2022 to 2023?",
        persona="Climate Analyst"
    )

    print("=" * 80)
    print("ENRICHED RESPONSE EXAMPLE")
    print("=" * 80)
    print("\nMCP DATA:")
    print(f"  2022: {mcp_data['rows'][0]['MtCO2']} MtCO₂")
    print(f"  2023: {mcp_data['rows'][1]['MtCO2']} MtCO₂")
    print(f"  Change: {((175.97 - 227.68) / 227.68 * 100):.1f}%")

    print("\nBASELINE CONTEXT ADDED:")
    for key, value in enriched["baseline_context"].items():
        print(f"\n  {key.upper()}:")
        print(f"  {value}")

    print("\n" + "=" * 80)

    # Example: Policy context
    print("\nPOLICY CONTEXT EXAMPLE:")
    policy_context = PolicyContextAugmenter.add_paris_alignment_context(
        country="Germany",
        sector="power",
        reduction_pct=22.7
    )
    print(f"  {policy_context}")

    # Example: Educational analogy
    print("\nEDUCATIONAL CONTEXT EXAMPLE:")
    analogy = EducationalContextAugmenter.create_analogy(51.71, "cars")
    print(f"  {analogy}")

    significance = EducationalContextAugmenter.explain_significance(-22.7)
    print(f"  {significance}")
