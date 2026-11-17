"""Small demonstration retrieval evaluation: Hit@3, with expected synthetic references."""
import os

import requests

API = os.getenv("SUPPORTLENS_API", "http://127.0.0.1:8000")
EXAMPLES = [
    ("Pourquoi une erreur 401 survient après une inactivité ?", "INC-001"),
    ("L'application ne se connecte plus à PostgreSQL quand il y a du trafic", "INC-003"),
    ("Notre conteneur redémarre en boucle après déploiement", "INC-006"),
    ("Le serveur n'a plus d'espace disque à cause des journaux", "INC-008"),
    ("Le SSO ne marche plus depuis le renouvellement du certificat", "INC-011"),
]


def main():
    hits = 0
    for question, expected in EXAMPLES:
        response = requests.post(
            f"{API}/api/search", json={"question": question, "top_k": 3}, timeout=300
        )
        response.raise_for_status()
        sources = response.json()["sources"]
        retrieved = [item["source_ref"] for item in sources]
        hit = expected in retrieved
        hits += int(hit)
        print(f"{'OK' if hit else 'NON'} | attendu={expected} | obtenus={retrieved}")
    print(f"Hit@3 : {hits}/{len(EXAMPLES)} = {100*hits/len(EXAMPLES):.1f}%")
    print("Attention : ce mini-test illustratif n'est pas une évaluation de production.")


if __name__ == "__main__":
    main()
