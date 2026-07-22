import re
import requests
from typing import Tuple, Dict

# In-memory cache for geocoding queries
_GEOCODE_CACHE: Dict[str, Tuple[float, float, str]] = {}

# Pre-populated common US locations for instant lookup
_PRESET_LOCATIONS = {
    "NEW YORK, NY": (40.712776, -74.005974, "New York, NY, USA"),
    "LOS ANGELES, CA": (34.052234, -118.243685, "Los Angeles, CA, USA"),
    "CHICAGO, IL": (41.878114, -87.629798, "Chicago, IL, USA"),
    "HOUSTON, TX": (29.760427, -95.369803, "Houston, TX, USA"),
    "MIAMI, FL": (25.761680, -80.191790, "Miami, FL, USA"),
    "SAN FRANCISCO, CA": (37.774929, -122.419416, "San Francisco, CA, USA"),
    "SEATTLE, WA": (47.606209, -122.332071, "Seattle, WA, USA"),
    "BOSTON, MA": (42.360082, -71.058880, "Boston, MA, USA"),
    "DALLAS, TX": (32.776664, -96.796988, "Dallas, TX, USA"),
    "ATLANTA, GA": (33.748995, -84.387982, "Atlanta, GA, USA"),
    "DENVER, CO": (39.739236, -104.990251, "Denver, CO, USA"),
    "LAS VEGAS, NV": (36.169941, -115.139830, "Las Vegas, NV, USA"),
}

def parse_lat_lon(query: str) -> Tuple[float, float, str] | None:
    """Check if query is already lat,lon format e.g. '40.7128,-74.0060'"""
    pattern = r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$"
    match = re.match(pattern, query)
    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        return (lat, lon, f"{lat:.4f}, {lon:.4f}")
    return None

def geocode_location(location_query: str) -> Tuple[float, float, str]:
    """
    Geocode location string to (latitude, longitude, formatted_address).
    First checks coordinate format, preset lookup, in-memory cache, and finally Nominatim API.
    """
    query_clean = location_query.strip()
    if not query_clean:
        raise ValueError("Location query cannot be empty.")

    # 1. Direct coordinate format check
    parsed_coords = parse_lat_lon(query_clean)
    if parsed_coords:
        return parsed_coords

    # 2. Key check in uppercase
    query_upper = query_clean.upper()
    if query_upper in _PRESET_LOCATIONS:
        return _PRESET_LOCATIONS[query_upper]

    # 3. In-memory cache check
    if query_upper in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[query_upper]

    # 4. Fallback to Nominatim API (1 HTTP call)
    headers = {
        'User-Agent': 'FuelUpRoutePlanner/1.0 (Django App)'
    }
    params = {
        'q': query_clean,
        'format': 'json',
        'countrycodes': 'us',
        'limit': 1
    }
    url = "https://nominatim.openstreetmap.org/search"
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise ValueError(f"Could not resolve location: '{location_query}' within the USA.")

        first_result = data[0]
        lat = float(first_result['lat'])
        lon = float(first_result['lon'])
        display_name = first_result.get('display_name', query_clean)

        res = (lat, lon, display_name)
        _GEOCODE_CACHE[query_upper] = res
        return res
    except requests.RequestException as e:
        raise RuntimeError(f"Geocoding service unavailable for location '{location_query}': {str(e)}")
