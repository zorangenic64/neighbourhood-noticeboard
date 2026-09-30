import csv
from pathlib import Path

def load_location_choices():
    root = Path(__file__).resolve().parent.parent

    candidates = [
        root / "uk_towns_cities.csv",
        root / "uk_town_cities.csv",
    ]

    csv_path = next((p for p in candidates if p.exists()), None)

    if csv_path is None:
        return ["Unknown"]

    choices = []

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue

            value = (
                row.get("city_town_village")
                or row.get("city")
                or row.get("town")
                or row.get("name")
                or ""
            ).strip()

            if value:
                choices.append(value)

    seen = set()
    unique = []
    for item in choices:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique or ["Unknown"]