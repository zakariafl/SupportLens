"""Top-k vector search using PostgreSQL pgvector cosine distance."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings import embed
from app.models import Incident
from app.schemas import Source


def find_similar(db: Session, question: str, top_k: int) -> list[Source]:
    query_vector = embed(question)
    distance = Incident.embedding.cosine_distance(query_vector)
    stmt = (
        select(Incident, (1 - distance).label("score"))
        .order_by(distance)
        .limit(top_k)
    )
    results = db.execute(stmt).all()
    return [
        Source(
            id=incident.id,
            source_ref=incident.source_ref,
            title=incident.title,
            category=incident.category,
            status=incident.status,
            description=incident.description,
            resolution=incident.resolution,
            score=round(float(score), 3),
        )
        for incident, score in results
    ]
