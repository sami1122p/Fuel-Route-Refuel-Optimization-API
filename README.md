# 🚚 Fuel Route & Refuel Optimization API

[![Python Version](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-6.0%2B-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

A high-performance Django REST API and interactive web application that calculates optimal driving routes within the USA, determines cost-effective fuel stops based on retail fuel prices from `fuel-prices-for-be-assessment.csv`, accounts for vehicle constraints (500-mile max range, 10 MPG fuel efficiency), and returns both structured JSON metrics and an interactive Leaflet map.

---

## ✨ Features

- **Strictly Minimized External API Calls (1–3 calls max per request)**:
  - **Geocoding**: Nominatim API for start and finish locations (1–2 calls, skipped if coordinates are provided directly).
  - **Routing**: OpenStreetMap / OSRM Driving Route API (`http://router.project-osrm.org/route/v1/driving/...`) for geometry and distance (1 call).
  - **Zero external calls for fuel stations**: Pre-geocoded 7,531 valid US fuel stations from `fuel-prices-for-be-assessment.csv` using KD-Tree spatial indexing (**< 5 ms execution time**).

- **Vehicle & Fuel Optimization**:
  - Maximum Range: **500 miles**.
  - Fuel Efficiency: **10 MPG** (50-gallon tank capacity).
  - Starts with a **full tank** (500 miles range).
  - Greedy gas station algorithm selects optimal fuel stops along the route to minimize overall fuel expenses while guaranteeing zero range depletion.

- **Interactive Dark-Mode Map Interface**:
  - Integrated Leaflet.js dashboard at `http://127.0.0.1:8000/`.
  - Visual polyline route, custom markers for Start, Finish, and Refuel Stops with detailed popups (price per gallon, gallons refueled, cost, cumulative distance).

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Pip package manager

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/sami1122p/Fuel-Route-Refuel-Optimization-API.git
cd Fuel-Route-Refuel-Optimization-API
pip install django numpy pandas scipy geopy requests
```

### 3. Run the Application
Start the Django development server:
```bash
python manage.py runserver 8000
```

- **Web Map Dashboard**: Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.
- **REST API Endpoint**: `http://127.0.0.1:8000/api/route/?start=New+York,+NY&finish=Los+Angeles,+CA`

---

## 📡 API Documentation

### Request Format
`GET /api/route/?start={START_LOCATION}&finish={FINISH_LOCATION}`

**Parameters**:
- `start` (string, required): City, State name (e.g. `"New York, NY"`) or coordinates (`"40.7128,-74.0060"`).
- `finish` (string, required): City, State name (e.g. `"Los Angeles, CA"`) or coordinates (`"34.0522,-118.2437"`).

### Example cURL
```bash
curl "http://127.0.0.1:8000/api/route/?start=New+York,+NY&finish=Los+Angeles,+CA"
```

### Example Response
```json
{
  "status": "success",
  "start": {
    "lat": 40.712776,
    "lon": -74.005974,
    "address": "New York, NY, USA"
  },
  "finish": {
    "lat": 34.052234,
    "lon": -118.243685,
    "address": "Los Angeles, CA, USA"
  },
  "summary": {
    "total_distance_miles": 2798.4,
    "total_duration_hours": 49.8,
    "total_fuel_gallons_required": 279.84,
    "total_fuel_cost_usd": 765.2,
    "fuel_stops_count": 7,
    "vehicle_specs": {
      "max_range_miles": 500,
      "fuel_efficiency_mpg": 10,
      "tank_capacity_gallons": 50
    }
  },
  "fuel_stops": [
    {
      "station_id": 72782,
      "name": "SHEETZ #791",
      "address": "I-76, Exit 57",
      "city": "North Jackson",
      "state": "OH",
      "price_per_gallon": 3.06566666,
      "lat": 41.088044,
      "lon": -80.86225,
      "route_distance_miles": 403.4,
      "gallons_refueled": 40.34,
      "fuel_cost_usd": 123.68
    }
  ],
  "geojson": {
    "type": "FeatureCollection",
    "features": [ ... ]
  }
}
```

---

## 🧪 Running Automated Tests

Run the Django test suite covering geocoding, routing, optimization logic, and views:
```bash
python manage.py test
```

Expected output:
```text
Found 9 test(s).
Creating test database for alias 'default'...
.........
----------------------------------------------------------------------
Ran 9 tests in ~3.2s

OK
```

---

## 📄 License
This project is open-source under the MIT License.
