"""SupportLens REST API + lightweight web interface."""
from contextlib import asynccontextmanager
from pathlib import Path

import requests
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db, init_db
from app.embeddings import embed, incident_text
from app.models import Incident
from app.rag import answer_with_ollama
from app.retrieval import find_similar
from app.schemas import (
    AskRequest,
    AskResponse,
    IncidentCreate,
    IncidentRead,
    SearchRequest,
    SearchResponse,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SupportLens API",
    description="Analyse sémantique d'incidents de support et assistant RAG",
    version="0.1.0",
    lifespan=lifespan,
)
STATIC = Path(__file__).parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(Incident)) or 0
    resolved = db.scalar(
        select(func.count()).select_from(Incident).where(Incident.status == "résolu")
    ) or 0
    return {"total": total, "resolved": resolved, "open": total - resolved}


@app.get("/api/incidents", response_model=list[IncidentRead])
def list_incidents(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(Incident).order_by(Incident.created_at.desc(), Incident.id.desc()).limit(limit)
    return db.scalars(stmt).all()


@app.get("/api/incidents/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident introuvable")
    return incident


@app.post("/api/incidents", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    if payload.source_ref:
        existing = db.scalar(select(Incident.id).where(Incident.source_ref == payload.source_ref))
        if existing:
            raise HTTPException(status_code=409, detail="Référence déjà utilisée")

    incident = Incident(
        **payload.model_dump(),
        embedding=embed(
            incident_text(
                title=payload.title,
                description=payload.description,
                resolution=payload.resolution,
            )
        ),
    )
    db.add(incident)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Incident déjà présent") from exc
    db.refresh(incident)
    return incident


@app.post("/api/search", response_model=SearchResponse)
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    return SearchResponse(
        question=payload.question,
        sources=find_similar(db, payload.question, payload.top_k),
    )


@app.post("/api/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)):
    sources = find_similar(db, payload.question, payload.top_k)
    if not sources:
        return AskResponse(
            question=payload.question,
            answer="Aucun incident n'est encore disponible. Ajoutez des incidents avant de poser une question.",
            sources=[],
            generated=False,
        )
    if not payload.generate:
        return AskResponse(
            question=payload.question,
            answer="Voici les incidents proches de votre question. La génération RAG est désactivée.",
            sources=sources,
            generated=False,
        )
    try:
        answer = answer_with_ollama(payload.question, sources)
    except (requests.RequestException, ValueError) as exc:
        return AskResponse(
            question=payload.question,
            answer="La génération RAG est indisponible, mais les incidents similaires sont affichés ci-dessous.",
            sources=sources,
            generated=False,
            notice=(
                "Vérifiez que le service Ollama est démarré et que le modèle est téléchargé "
                "(voir le README). " + type(exc).__name__
            ),
        )
    return AskResponse(
        question=payload.question,
        answer=answer,
        sources=sources,
        generated=True,
    )
