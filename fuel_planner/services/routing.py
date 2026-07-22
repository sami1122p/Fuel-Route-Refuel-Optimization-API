import requests
from typing import Dict, Any, List, Tuple

OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving"

def fetch_osrm_route(start_lat: float, start_lon: float, finish_lat: float, finish_lon: float) -> Dict[str, Any]:
    """
    Fetch driving route from OSRM public API (1 HTTP call).
    Returns total distance in miles, duration in seconds, and list of [lat, lon] waypoints.
    """
    # OSRM expects coordinates in {longitude},{latitude} format
    coordinates_str = f"{start_lon},{start_lat};{finish_lon},{finish_lat}"
    url = f"{OSRM_BASE_URL}/{coordinates_str}?overview=full&geometries=geojson"
    
    headers = {
        'User-Agent': 'FuelUpRoutePlanner/1.0 (Django App)'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != 'Ok' or not data.get('routes'):
            raise ValueError("No driving route could be calculated between the specified locations.")

        route = data['routes'][0]
        distance_meters = route['distance']
        duration_seconds = route['duration']
        geojson_geometry = route['geometry']
        
        # GeoJSON coordinates are [lon, lat]. Convert to [lat, lon] for internal spatial processing
        coords_lonlat = geojson_geometry['coordinates']
        route_latlon = [[lat, lon] for lon, lat in coords_lonlat]

        # Convert meters to miles (1 meter = 0.000621371 miles)
        distance_miles = distance_meters * 0.000621371

        return {
            'distance_miles': distance_miles,
            'duration_seconds': duration_seconds,
            'duration_hours': duration_seconds / 3600.0,
            'route_latlon': route_latlon,
            'geojson_geometry': geojson_geometry
        }
    except requests.RequestException as e:
        raise RuntimeError(f"Routing API service error: {str(e)}")
