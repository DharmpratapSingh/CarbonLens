"""
Location Resolver - Intelligently identifies location types (city, state, country)
and returns the correct database file and column to query.
"""

import os
import json
import sqlite3
import duckdb
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class LocationResolver:
    """Resolves location names to their type and optimal query parameters."""

    def __init__(self, db_path: str = "data/warehouse/climategpt.duckdb"):
        """Initialize the resolver with database connection."""
        self.db_path = Path(db_path)
        self.conn = None
        self._location_cache = {}
        self._connect()

    def _connect(self):
        """Establish database connection."""
        try:
            self.conn = duckdb.connect(str(self.db_path), read_only=True)
        except Exception as e:
            print(f"Warning: Could not connect to DuckDB: {e}")
            self.conn = None

    def resolve(self, location_name: str, sector: str = None) -> Dict:
        """
        Resolve a location name to its type and query parameters.

        Args:
            location_name: Name of the location (e.g., "London", "California", "India")
            sector: Optional sector filter (e.g., "transport", "waste")

        Returns:
            Dict with keys:
            - location_type: "city", "admin1", or "country"
            - column_name: "city_name", "admin1_name", or "country_name"
            - file_suffix: Suffix to append to sector files (e.g., "-city-year")
            - normalized_name: Normalized location name as it appears in DB
            - confidence: Confidence level (HIGH, MEDIUM, LOW)
        """

        # Check cache first
        cache_key = f"{location_name}:{sector or 'any'}"
        if cache_key in self._location_cache:
            return self._location_cache[cache_key]

        if not self.conn:
            return self._default_resolution(location_name)

        result = self._query_location_type(location_name, sector)

        # Cache the result
        self._location_cache[cache_key] = result
        return result

    def _query_location_type(self, location_name: str, sector: Optional[str]) -> Dict:
        """Query the database to determine location type."""

        try:
            # Try to find in each table type with priority: city > admin1 > country

            # 1. Check cities (highest priority - most specific)
            city_result = self._check_table(
                "transport_city_year",
                "city_name",
                location_name
            )
            if city_result:
                return {
                    "location_type": "city",
                    "column_name": "city_name",
                    "file_suffix": "-city-year",
                    "normalized_name": city_result,
                    "confidence": "HIGH",
                    "priority": 1
                }

            # 2. Check admin1/states (medium priority)
            admin1_result = self._check_table(
                "transport_admin1_year",
                "admin1_name",
                location_name
            )
            if admin1_result:
                return {
                    "location_type": "admin1",
                    "column_name": "admin1_name",
                    "file_suffix": "-admin1-year",
                    "normalized_name": admin1_result,
                    "confidence": "HIGH",
                    "priority": 2
                }

            # 3. Check countries (lowest priority - least specific)
            country_result = self._check_table(
                "transport_country_year",
                "country_name",
                location_name
            )
            if country_result:
                return {
                    "location_type": "country",
                    "column_name": "country_name",
                    "file_suffix": "-country-year",
                    "normalized_name": country_result,
                    "confidence": "HIGH",
                    "priority": 3
                }

            # Not found in database - return best guess
            return self._guess_location_type(location_name)

        except Exception as e:
            print(f"Warning: Error querying location type: {e}")
            return self._guess_location_type(location_name)

    def _check_table(self, table_name: str, column_name: str, location_name: str) -> Optional[str]:
        """Check if a location exists in a specific table."""
        try:
            # Case-insensitive search
            query = f"""
                SELECT DISTINCT {column_name}
                FROM {table_name}
                WHERE LOWER({column_name}) = LOWER(?)
                LIMIT 1
            """
            result = self.conn.execute(query, [location_name]).fetchone()
            return result[0] if result else None
        except Exception:
            return None

    def _guess_location_type(self, location_name: str) -> Dict:
        """
        Make an educated guess about location type based on common patterns.
        Used when location is not found in database.
        """

        # List of known major world cities
        major_cities = {
            "london", "paris", "tokyo", "new york", "berlin", "madrid", "rome",
            "barcelona", "moscow", "shanghai", "beijing", "hong kong", "singapore",
            "bangkok", "istanbul", "dubai", "mumbai", "delhi", "los angeles",
            "chicago", "san francisco", "toronto", "sydney", "melbourne",
            "amsterdam", "brussels", "vienna", "prague", "warsaw", "athens",
            "lisbon", "dublin", "stockholm", "oslo", "helsinki", "zurich",
            "geneva", "milan", "venice", "florence", "buenos aires", "sao paulo",
            "mexico city", "cairo", "johannesburg", "cape town", "nairobi",
            "seoul", "bangkok", "manila", "ho chi minh", "hanoi", "kuala lumpur",
            "jakarta", "auckland", "perth", "brisbane", "vancouver", "montreal"
        }

        location_lower = location_name.lower()

        if location_lower in major_cities:
            return {
                "location_type": "city",
                "column_name": "city_name",
                "file_suffix": "-city-year",
                "normalized_name": location_name,
                "confidence": "MEDIUM",
                "priority": 1
            }

        # Known US states
        us_states = {
            "california", "texas", "florida", "new york", "pennsylvania",
            "illinois", "ohio", "georgia", "north carolina", "michigan",
            "new jersey", "virginia", "washington", "arizona", "massachusetts",
            "tennessee", "indiana", "maryland", "missouri", "wisconsin",
            "colorado", "minnesota", "south carolina", "alabama", "louisiana",
            "kentucky", "oregon", "oklahoma", "connecticut", "utah",
            "iowa", "nevada", "arkansas", "kansas", "mississippi"
        }

        if location_lower in us_states:
            return {
                "location_type": "admin1",
                "column_name": "admin1_name",
                "file_suffix": "-admin1-year",
                "normalized_name": location_name,
                "confidence": "MEDIUM",
                "priority": 2
            }

        # Known countries (sample)
        countries = {
            "india", "china", "usa", "united states", "united kingdom", "uk",
            "germany", "france", "italy", "spain", "canada", "australia",
            "japan", "south korea", "mexico", "brazil", "argentina", "russia",
            "netherlands", "belgium", "switzerland", "austria", "sweden",
            "norway", "denmark", "finland", "greece", "portugal"
        }

        if location_lower in countries:
            return {
                "location_type": "country",
                "column_name": "country_name",
                "file_suffix": "-country-year",
                "normalized_name": location_name,
                "confidence": "MEDIUM",
                "priority": 3
            }

        # Default: assume it's a city (most specific)
        return {
            "location_type": "city",
            "column_name": "city_name",
            "file_suffix": "-city-year",
            "normalized_name": location_name,
            "confidence": "LOW",
            "priority": 1
        }

    def _default_resolution(self, location_name: str) -> Dict:
        """Fallback resolution when database is unavailable."""
        return self._guess_location_type(location_name)

    def get_location_info(self, location_name: str) -> Dict:
        """
        Get comprehensive info about a location.

        Returns:
            Dict with location details including type, column, and file info
        """
        resolution = self.resolve(location_name)

        return {
            "input": location_name,
            "resolved_name": resolution["normalized_name"],
            "type": resolution["location_type"],
            "column_name": resolution["column_name"],
            "file_suffix": resolution["file_suffix"],
            "confidence": resolution["confidence"],
            "query_hint": self._generate_query_hint(resolution)
        }

    def _generate_query_hint(self, resolution: Dict) -> str:
        """Generate a query hint for the LLM based on resolution."""
        col = resolution["column_name"]
        name = resolution["normalized_name"]
        suffix = resolution["file_suffix"]
        loc_type = resolution["location_type"]

        return f'For "{name}" ({loc_type}): use "-{suffix.split("-")[1]}-" files with {col}:"{name}"'

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# Global resolver instance (lazy loaded)
_resolver = None

def get_resolver() -> LocationResolver:
    """Get or create the global location resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = LocationResolver()
    return _resolver

def resolve_location(location_name: str, sector: Optional[str] = None) -> Dict:
    """Convenience function to resolve a location."""
    return get_resolver().resolve(location_name, sector)

def shutdown_resolver():
    """Shutdown the global resolver."""
    global _resolver
    if _resolver:
        _resolver.close()
        _resolver = None


if __name__ == "__main__":
    # Test the resolver
    resolver = LocationResolver()

    test_locations = [
        "London",
        "California",
        "Texas",
        "India",
        "China",
        "New York",
        "Paris",
        "Maharashtra",
        "Germany",
    ]

    print("Testing Location Resolver:")
    print("=" * 80)

    for location in test_locations:
        info = resolver.get_location_info(location)
        print(f"\nLocation: {location}")
        print(f"  Resolved as: {info['type']} ({info['confidence']})")
        print(f"  Resolved name: {info['resolved_name']}")
        print(f"  Column: {info['column_name']}")
        print(f"  File pattern: *{info['file_suffix']}.duckdb")
        print(f"  Hint: {info['query_hint']}")

    resolver.close()
