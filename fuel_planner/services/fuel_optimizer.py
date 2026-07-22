import os
import json
import numpy as np
from scipy.spatial import KDTree
from typing import List, Dict, Any

# Global dataset & KDTree storage initialized at import time
STATIONS_DATA: List[Dict[str, Any]] = []
STATION_COORDS: np.ndarray = np.empty((0, 2))
STATION_TREE: KDTree | None = None

def _initialize_dataset():
    global STATIONS_DATA, STATION_COORDS, STATION_TREE
    dataset_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'geocoded_fuel_prices.json')
    dataset_path = os.path.abspath(dataset_path)

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Geocoded fuel price dataset not found at {dataset_path}")

    with open(dataset_path, 'r', encoding='utf-8') as f:
        STATIONS_DATA = json.load(f)

    if STATIONS_DATA:
        coords_list = [[s['lat'], s['lon']] for s in STATIONS_DATA]
        STATION_COORDS = np.array(coords_list)
        STATION_TREE = KDTree(STATION_COORDS)

# Initialize on module import
_initialize_dataset()

MAX_RANGE_MILES = 500.0
VEHICLE_MPG = 10.0
FULL_TANK_GALLONS = MAX_RANGE_MILES / VEHICLE_MPG # 50 gallons

def compute_cumulative_distances(route_latlon: List[List[float]]) -> np.ndarray:
    """Compute cumulative distance in miles along route waypoints using Haversine approximation."""
    arr = np.array(route_latlon)
    lats = np.radians(arr[:, 0])
    lons = np.radians(arr[:, 1])

    dlats = lats[1:] - lats[:-1]
    dlons = lons[1:] - lons[:-1]

    a = np.sin(dlats / 2.0) ** 2 + np.cos(lats[:-1]) * np.cos(lats[1:]) * np.sin(dlons / 2.0) ** 2
    seg_miles = 2.0 * 3956.0 * np.arcsin(np.sqrt(a))
    cum_miles = np.insert(np.cumsum(seg_miles), 0, 0.0)
    return cum_miles

def optimize_fuel_stops(route_latlon: List[List[float]], total_distance_miles: float) -> Dict[str, Any]:
    """
    Find candidate fuel stations along the route and select optimal refuel stops.
    Vehicle range: 500 miles. Fuel efficiency: 10 MPG. Starts with full tank (50 gallons).
    """
    if not STATIONS_DATA or STATION_TREE is None:
        _initialize_dataset()

    cum_miles = compute_cumulative_distances(route_latlon)
    route_latlon_arr = np.array(route_latlon)
    route_tree = KDTree(route_latlon_arr)

    # Downsample route waypoints for spatial indexing query (~1 point per 2 miles)
    step = max(1, len(route_latlon) // 500)
    sample_indices = np.arange(0, len(route_latlon), step)
    sample_points = route_latlon_arr[sample_indices]

    # Query fuel stations within 0.25 degrees (~15 miles) of route waypoints
    near_indices_list = STATION_TREE.query_ball_point(sample_points, r=0.25)
    candidate_indices = sorted(list(set([idx for sublist in near_indices_list for idx in sublist])))

    candidate_stations = []
    for idx in candidate_indices:
        station = STATIONS_DATA[idx]
        s_lat, s_lon = station['lat'], station['lon']
        dist_deg, wp_idx = route_tree.query([s_lat, s_lon])
        dist_miles = dist_deg * 69.0 # ~69 miles per degree latitude
        if dist_miles <= 15.0:
            s_cum_dist = float(cum_miles[wp_idx])
            candidate_stations.append({
                'id': station['id'],
                'name': station['name'],
                'address': station['address'],
                'city': station['city'],
                'state': station['state'],
                'price': station['price'],
                'lat': s_lat,
                'lon': s_lon,
                'route_dist': s_cum_dist
            })

    candidate_stations.sort(key=lambda s: s['route_dist'])

    current_dist = 0.0
    current_range = MAX_RANGE_MILES # Starts with full tank (500 miles)
    fuel_stops = []
    total_fuel_cost = 0.0
    total_gallons_bought = 0.0

    # Refuel optimization loop
    while current_dist < total_distance_miles:
        dist_remaining = total_distance_miles - current_dist
        if dist_remaining <= current_range:
            # Vehicle can reach destination without further refuel
            break

        # Reachable window for station search (up to current_range miles ahead)
        window_max = current_dist + current_range - 10.0 # 10-mile safety buffer
        reachable = [s for s in candidate_stations if current_dist < s['route_dist'] <= window_max]

        if not reachable:
            # Fallback: any station within remaining range
            reachable = [s for s in candidate_stations if current_dist < s['route_dist'] <= current_dist + current_range]

        if not reachable:
            # If no station reachable in current range, search up to MAX_RANGE_MILES ahead
            reachable = [s for s in candidate_stations if current_dist < s['route_dist'] <= current_dist + MAX_RANGE_MILES]

        if not reachable:
            # No fuel station available along route section
            break

        # Score stations: balance low retail price and maximum forward progress along route
        best_station = min(reachable, key=lambda s: s['price'] - 0.0008 * (s['route_dist'] - current_dist))

        leg_dist = best_station['route_dist'] - current_dist
        current_range -= leg_dist
        current_dist = best_station['route_dist']

        # Refuel to full capacity (500 miles range = 50 gallons)
        gallons_needed = (MAX_RANGE_MILES - current_range) / VEHICLE_MPG
        cost = gallons_needed * best_station['price']

        total_fuel_cost += cost
        total_gallons_bought += gallons_needed
        current_range = MAX_RANGE_MILES

        fuel_stops.append({
            'station_id': best_station['id'],
            'name': best_station['name'],
            'address': best_station['address'],
            'city': best_station['city'],
            'state': best_station['state'],
            'price_per_gallon': best_station['price'],
            'lat': best_station['lat'],
            'lon': best_station['lon'],
            'route_distance_miles': round(best_station['route_dist'], 1),
            'gallons_refueled': round(gallons_needed, 2),
            'fuel_cost_usd': round(cost, 2)
        })

    # Total gallons required for entire trip = total_distance / 10.0
    total_trip_gallons = total_distance_miles / VEHICLE_MPG

    return {
        'total_trip_distance_miles': round(total_distance_miles, 1),
        'total_trip_gallons_required': round(total_trip_gallons, 2),
        'total_fuel_cost_usd': round(total_fuel_cost, 2),
        'total_gallons_bought': round(total_gallons_bought, 2),
        'fuel_stops_count': len(fuel_stops),
        'fuel_stops': fuel_stops
    }
