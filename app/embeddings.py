"""Multilingual semantic representations for French support tickets."""
import os
from functools import lru_cache

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
VECTOR_SIZE = 384


@lru_cache(maxsize=1)
def _load_model():
    # Lazy import and load: /health works before the model is downloaded.
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    size = model.get_sentence_embedding_dimension()
    if size != VECTOR_SIZE:
        raise ValueError(
            f"Le modèle {MODEL_NAME} produit {size} dimensions ; "
            f"la base attend {VECTOR_SIZE}."
        )
    return model


def embed(text: str) -> list[float]:
    vector = _load_model().encode(text, normalize_embeddings=True)
    return vector.tolist()


def incident_text(*, title: str, description: str, resolution: str | None) -> str:
    # La recherche se base sur le problème ET sur sa solution éventuelle.
    blocks = [f"Incident : {title}", f"Symptômes : {description}"]
    if resolution:
        blocks.append(f"Solution : {resolution}")
    return "\n".join(blocks)
