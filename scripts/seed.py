"""Insert synthetic demonstration tickets through the public API.

Run inside API container: docker compose exec api python scripts/seed.py
"""
import json
import os
from pathlib import Path

import requests

API = os.getenv("SUPPORTLENS_API", "http://127.0.0.1:8000")
DATA = Path(__file__).resolve().parents[1] / "data" / "incidents.json"


def main():
    incidents = json.loads(DATA.read_text(encoding="utf-8"))
    created = 0
    skipped = 0
    for incident in incidents:
        response = requests.post(f"{API}/api/incidents", json=incident, timeout=300)
        if response.status_code == 409:
            skipped += 1
            continue
        response.raise_for_status()
        created += 1
        print(f"Créé : {incident['source_ref']} — {incident['title']}")
    print(f"Terminé : {created} créés, {skipped} déjà présents")


if __name__ == "__main__":
    main()
