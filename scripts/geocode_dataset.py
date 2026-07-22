import os
import json
import pandas as pd
import numpy as np

def geocode_and_save():
    csv_path = 'fuel-prices-for-be-assessment.csv'
    output_path = os.path.join('fuel_planner', 'data', 'geocoded_fuel_prices.json')

    print(f"Reading {csv_path}...")
    fuel_df = pd.read_csv(csv_path)

    us_cities_url = 'https://raw.githubusercontent.com/kelvins/US-Cities-Database/main/csv/us_cities.csv'
    print(f"Fetching US cities database from {us_cities_url}...")
    cities_df = pd.read_csv(us_cities_url)

    fuel_df['City_Clean'] = fuel_df['City'].astype(str).str.strip().str.upper()
    fuel_df['State_Clean'] = fuel_df['State'].astype(str).str.strip().str.upper()
    cities_df['CITY_Clean'] = cities_df['CITY'].astype(str).str.strip().str.upper()
    cities_df['STATE_Clean'] = cities_df['STATE_CODE'].astype(str).str.strip().str.upper()

    cities_dedup = cities_df.groupby(['CITY_Clean', 'STATE_Clean']).agg({
        'LATITUDE': 'first',
        'LONGITUDE': 'first'
    }).reset_index()

    merged = pd.merge(
        fuel_df,
        cities_dedup,
        left_on=['City_Clean', 'State_Clean'],
        right_on=['CITY_Clean', 'STATE_Clean'],
        how='left'
    )

    manual_coords = {
        ('PORT WENTWORTH', 'GA'): (32.149092, -81.163168),
        ('ELIZABETHPORT', 'NJ'): (40.650103, -74.187088),
        ('BROOKPARK', 'OH'): (41.419791, -81.823818),
        ('EVERGREEN', 'AL'): (31.433499, -86.956917),
        ('HENRICO', 'VA'): (37.513119, -77.346508),
        ('UNIVERSITY PARK', 'IL'): (41.440034, -87.683377)
    }

    for (city, state), (lat, lon) in manual_coords.items():
        mask = (merged['City_Clean'] == city) & (merged['State_Clean'] == state)
        merged.loc[mask, 'LATITUDE'] = lat
        merged.loc[mask, 'LONGITUDE'] = lon

    valid_us = merged[merged['LATITUDE'].notna()].copy()

    stations = []
    for idx, row in valid_us.iterrows():
        stations.append({
            'id': int(row['OPIS Truckstop ID']),
            'name': str(row['Truckstop Name']).strip(),
            'address': str(row['Address']).strip(),
            'city': str(row['City']).strip(),
            'state': str(row['State']).strip(),
            'price': float(row['Retail Price']),
            'lat': float(row['LATITUDE']),
            'lon': float(row['LONGITUDE'])
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stations, f, indent=2)

    print(f"Successfully saved {len(stations)} geocoded US fuel stations to {output_path}")

if __name__ == '__main__':
    geocode_and_save()
