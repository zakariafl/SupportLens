# SupportLens — Analyse d'incidents et assistant RAG

**MVP de portfolio** : ingestion de tickets de support, embeddings multilingues, recherche sémantique dans PostgreSQL/pgvector et réponses générées **localement** avec Ollama, références à l'appui.

> Les 12 incidents fournis sont **entièrement fictifs**, destinés uniquement à la démonstration.

## 1. Pré-requis

- Docker Desktop récent et Docker Compose V2 (sur Windows, activer le moteur Linux/WSL2).
- Connexion Internet au premier démarrage pour télécharger les images et le modèle d'embeddings.
- Pour la génération RAG locale : prévoir plusieurs Go de RAM supplémentaires et de l'espace disque pour `qwen2.5:3b`.
- Python n'est **pas nécessaire** sur la machine hôte : tout fonctionne dans les conteneurs.

## 2. Démarrer la base et l'API

Placez-vous dans le dossier `SupportLens` (PowerShell ou terminal) :

```bash
docker compose up --build -d
```

Lancez ensuite l'import de 12 incidents d'exemple :

```bash
docker compose exec api python scripts/seed.py
```

Cela peut prendre du temps au premier import : `Sentence Transformers` télécharge son modèle multilingue, le charge en mémoire et calcule les embeddings (384 dimensions). La commande est **idempotente** grâce aux références `INC-001`…`INC-012` : les doublons sont ignorés.

Ouvrez :

- **Interface web** : http://localhost:8000
- **Documentation API (Swagger)** : http://localhost:8000/docs
- **Santé de l'API** : http://localhost:8000/health

Sans Ollama, la recherche sémantique fonctionne déjà. Décochez **Générer une réponse RAG** dans l'interface pour éviter le message d'indisponibilité.

## 3. Activer la vraie génération RAG avec Ollama

Démarrez Ollama en plus de l'API et de PostgreSQL :

```bash
docker compose --profile rag up --build -d
```

Téléchargez le modèle de génération dans le conteneur Ollama :

```bash
docker compose exec ollama ollama pull qwen2.5:3b
```

Le modèle est conservé dans le volume `ollama_data`. Une fois le téléchargement terminé, laissez cochée l'option **Générer une réponse RAG (Ollama)** dans l'interface.

Si la machine manque de RAM, vous pouvez utiliser uniquement la recherche sémantique et ajouter le LLM ensuite.

## 4. Test rapide

Dans l'interface web, posez cette question :

> Pourquoi les utilisateurs reçoivent-ils une erreur 401 après une période d'inactivité ?

Le résultat devrait retrouver notamment `INC-001` (jeton expiré). Avec Ollama actif, une réponse fondée sur le ticket sera générée et devra citer `[Incident 1]` (l'ID exact dépend de l'ordre d'insertion).

### Exemple via API

Sous PowerShell :

```powershell
$body = @{ question = "Comment résoudre un timeout PostgreSQL ?"; top_k = 3; generate = $false } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/api/ask -Method Post -ContentType 'application/json' -Body $body
```

Pour ajouter un incident, utilisez le formulaire **Nouvel incident** ou l'endpoint `POST /api/incidents` de Swagger.

## 5. Évaluer la recherche

Exécutez un mini-benchmark :

```bash
docker compose exec api python scripts/evaluate.py
```

Il vérifie `Hit@3` sur cinq questions synthétiques avec une référence attendue. **Ce n'est pas une évaluation scientifique** : pour un projet de fin d'études, construire ultérieurement un jeu de questions annotées et mesurer Hit@k, MRR, précision des sources et fidélité des réponses.

## Architecture

```text
Navigateur (HTML/CSS/JS)
       |
       v
   FastAPI (Python)
       |
       +-- Ingestion --> Sentence Transformers --> embeddings 384D
       |                                      |
       |                                      v
       |                                PostgreSQL + pgvector
       |
       +-- Recherche --> question -> embedding -> top-k incidents
       |                                      |
       |                                      v
       +-- RAG (optionnel) ------------> Ollama qwen2.5:3b
                                             |
                                             v
                                  Réponse + références
```

## Structure

```text
SupportLens/
├── app/
│   ├── main.py            # API FastAPI, endpoints, interface
│   ├── db.py              # Connexion PostgreSQL et init pgvector
│   ├── models.py          # Table incidents (avec vecteur)
│   ├── schemas.py         # Validation Pydantic
│   ├── embeddings.py      # Modèle de sentence embeddings
│   ├── retrieval.py       # Recherche par similarité cosinus
│   ├── rag.py             # Construction du contexte + Ollama
│   └── static/index.html  # Interface web responsive
├── data/incidents.json    # 12 incidents fictifs
├── scripts/seed.py        # Import des exemples
├── scripts/evaluate.py    # Test Hit@3
├── tests/test_rag.py      # Tests unitaires sans base
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Configuration

Le projet utilise des valeurs de développement et peut démarrer sans `.env`. Pour personnaliser la configuration, copiez `.env.example` vers `.env` puis modifiez ses valeurs avant le lancement.

- `POSTGRES_PASSWORD` : mot de passe PostgreSQL (**dev uniquement** par défaut)
- `EMBEDDING_MODEL` : `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (vecteur de 384 dimensions)
- `OLLAMA_MODEL` : `qwen2.5:3b`
- `OLLAMA_TIMEOUT` : délai maximal de génération en secondes

⚠️ Si vous changez de modèle d'embeddings, il faut vérifier la dimension des vecteurs et **réindexer** les tickets ; le schéma actuel attend exactement 384 dimensions. Ne modifiez pas simplement le nom du modèle sur une base déjà indexée.

## Endpoints principaux

| Méthode | Endpoint | Fonction |
|---|---|---|
| `GET` | `/api/incidents` | Lister les incidents |
| `POST` | `/api/incidents` | Ajouter et vectoriser un ticket |
| `GET` | `/api/incidents/{id}` | Lire un ticket |
| `POST` | `/api/search` | Recherche vectorielle top-k |
| `POST` | `/api/ask` | Réponse RAG et sources |
| `GET` | `/api/stats` | Indicateurs simples |
| `GET` | `/docs` | Documentation interactive |

## Limites volontaires de cette première version

- Pas d'authentification, de gestion des rôles, d'audit ou de chiffrement applicatif : **ne pas déployer publiquement tel quel**.
- Pas de traitement de pièces jointes, de nettoyage automatique des données personnelles, de découpage long-document ou de détection des doublons sémantiques.
- Les solutions proposées par un modèle génératif doivent être **validées par un humain**. Même avec un prompt fondé sur des sources, une hallucination reste possible.
- La recherche renvoie les incidents les plus proches, même si les similitudes sont faibles. Ajouter un seuil calibré, un reranker et des tests de pertinence avant un usage professionnel.
- L'embedding est calculé à la création du ticket, pas lors de sa modification (pas d'endpoint PUT dans ce MVP).

## Arrêter / réinitialiser

```bash
docker compose --profile rag down
```

Pour **supprimer définitivement les données, le cache et les modèles téléchargés**, utiliser `docker compose --profile rag down -v` (destructif).

## Documentation externe

- [pgvector (GitHub)](https://github.com/pgvector/pgvector)
- [Sentence Transformers](https://sbert.net/docs/sentence_transformer/usage/usage.html)
- [Ollama API](https://docs.ollama.com/api)
- [FastAPI](https://fastapi.tiangolo.com/)

## Prochaines étapes pour faire évoluer le projet

1. **Qualité des données** : nettoyage, suppression des informations personnelles, catégories normalisées et import CSV/JSON avec validation.
2. **Recherche améliorée** : comparaison TF-IDF/BM25 vs embeddings, recherche hybride, réordonnancement avec un reranker et filtres de catégorie.
3. **Qualité du RAG** : découpage des textes longs, vérification des citations, seuil de confiance et réponse « information insuffisante ».
4. **Évaluation** : constituer au moins 50 questions annotées, mesurer Hit@k/MRR et évaluer la fidélité factuelle des réponses.
5. **Industrialisation** : authentification, rôles, migrations Alembic, journalisation, tests d'intégration PostgreSQL et CI/CD GitHub Actions.

**Conseil CV** : décrivez les performances (Hit@3, latence, qualité RAG) seulement après les avoir réellement mesurées, sur un jeu d'évaluation documenté.
