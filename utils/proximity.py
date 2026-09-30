import csv
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path

def load_location_coords():
    root = Path(__file__).resolve().parent.parent

    candidates = [
        root / "uk_towns_cities.csv",
        root / "uk_town_cities.csv",
        root / "location_coords.csv",
    ]

    csv_path = next((p for p in candidates if p.exists()), None)

    if csv_path is None:
        return {}

    coords = {}

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if not row:
                continue

            name = (
                row.get("city_town_village")
                or row.get("city")
                or row.get("town")
                or row.get("name")
                or ""
            ).strip()

            if not name:
                continue

            try:
                lat = float(row.get("latitude") or row.get("lat") or 0)
                lon = float(row.get("longitude") or row.get("lon") or row.get("lng") or 0)
            except (TypeError, ValueError):
                continue

            if lat and lon:
                coords[name.lower()] = (lat, lon)

    return coords


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c


def post_is_within_distance(post_location, user_location, max_km):
    if max_km in (None, "Any"):
        return True

    if not post_location or not user_location:
        return True

    coords = load_location_coords()
    post_key = (post_location or "").strip().lower()
    user_key = (user_location or "").strip().lower()

    if not coords:
        return True

    if post_key not in coords or user_key not in coords:
        return True

    lat1, lon1 = coords[user_key]
    lat2, lon2 = coords[post_key]

    distance_km = haversine_km(lat1, lon1, lat2, lon2)
    return distance_km <= float(max_km)