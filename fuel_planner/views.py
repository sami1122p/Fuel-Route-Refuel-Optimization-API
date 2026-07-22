from django.http import JsonResponse, HttpRequest
from django.shortcuts import render
from django.views.decorators.http import require_GET
from typing import Dict, Any

from .services.geocoding import geocode_location
from .services.routing import fetch_osrm_route
from .services.fuel_optimizer import optimize_fuel_stops

@require_GET
def route_fuel_api_view(request: HttpRequest) -> JsonResponse:
    """
    API Endpoint: /api/route/
    Query parameters:
      - start: Start location string or lat,lon (e.g. 'New York, NY' or '40.7128,-74.0060')
      - finish: Finish location string or lat,lon (e.g. 'Los Angeles, CA' or '34.0522,-118.2437')
    """
    start_query = request.GET.get('start', '').strip()
    finish_query = request.GET.get('finish', '').strip()

    if not start_query or not finish_query:
        return JsonResponse({
            'status': 'error',
            'error': "Both 'start' and 'finish' location parameters are required. Example: /api/route/?start=New+York,+NY&finish=Los+Angeles,+CA"
        }, status=400)

    try:
        # Step 1: Geocode start and finish locations (1-2 external calls max)
        start_lat, start_lon, start_address = geocode_location(start_query)
        finish_lat, finish_lon, finish_address = geocode_location(finish_query)

        # Step 2: Fetch OSRM driving route (1 external call)
        route_data = fetch_osrm_route(start_lat, start_lon, finish_lat, finish_lon)
        total_distance = route_data['distance_miles']
        duration_hours = route_data['duration_hours']
        route_latlon = route_data['route_latlon']
        geojson_geometry = route_data['geojson_geometry']

        # Step 3: Compute optimal fuel stops and total fuel cost (0 external calls)
        opt_results = optimize_fuel_stops(route_latlon, total_distance)

        # Step 4: Construct GeoJSON FeatureCollection for Map rendering
        features = [
            # Route LineString
            {
                'type': 'Feature',
                'geometry': geojson_geometry,
                'properties': {
                    'type': 'route',
                    'title': f"Route from {start_address} to {finish_address}",
                    'distance_miles': round(total_distance, 1),
                    'duration_hours': round(duration_hours, 1)
                }
            },
            # Start Location Marker
            {
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [start_lon, start_lat]},
                'properties': {
                    'type': 'start',
                    'title': 'Start Location',
                    'address': start_address
                }
            },
            # Finish Location Marker
            {
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [finish_lon, finish_lat]},
                'properties': {
                    'type': 'finish',
                    'title': 'Finish Location',
                    'address': finish_address
                }
            }
        ]

        # Fuel Stops Markers
        for stop in opt_results['fuel_stops']:
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [stop['lon'], stop['lat']]},
                'properties': {
                    'type': 'fuel_stop',
                    'station_id': stop['station_id'],
                    'name': stop['name'],
                    'address': stop['address'],
                    'city': stop['city'],
                    'state': stop['state'],
                    'price_per_gallon': stop['price_per_gallon'],
                    'route_distance_miles': stop['route_distance_miles'],
                    'gallons_refueled': stop['gallons_refueled'],
                    'fuel_cost_usd': stop['fuel_cost_usd']
                }
            })

        geojson_feature_collection = {
            'type': 'FeatureCollection',
            'features': features
        }

        # Response payload
        response_payload: Dict[str, Any] = {
            'status': 'success',
            'start': {
                'lat': start_lat,
                'lon': start_lon,
                'address': start_address
            },
            'finish': {
                'lat': finish_lat,
                'lon': finish_lon,
                'address': finish_address
            },
            'summary': {
                'total_distance_miles': opt_results['total_trip_distance_miles'],
                'total_duration_hours': round(duration_hours, 1),
                'total_fuel_gallons_required': opt_results['total_trip_gallons_required'],
                'total_fuel_cost_usd': opt_results['total_fuel_cost_usd'],
                'fuel_stops_count': opt_results['fuel_stops_count'],
                'vehicle_specs': {
                    'max_range_miles': 500,
                    'fuel_efficiency_mpg': 10,
                    'tank_capacity_gallons': 50
                }
            },
            'fuel_stops': opt_results['fuel_stops'],
            'geojson': geojson_feature_collection
        }

        return JsonResponse(response_payload, status=200)

    except ValueError as ve:
        return JsonResponse({'status': 'error', 'error': str(ve)}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': f"Internal server error: {str(e)}"}, status=500)

@require_GET
def map_interface_view(request: HttpRequest):
    """Render interactive dark-mode web application interface."""
    return render(request, 'map.html')
