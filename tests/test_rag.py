"""Fast tests that do not need Docker, a model download, or a database."""
from app.embeddings import incident_text
from app.rag import make_prompt
from app.schemas import IncidentCreate, Source


def test_incident_text_contains_problem_and_fix():
    content = incident_text(title="API 401", description="Jeton expiré", resolution="Renouveler")
    assert "API 401" in content
    assert "Jeton expiré" in content
    assert "Renouveler" in content


def test_rag_prompt_references_documents():
    source = Source(
        id=4,
        source_ref="INC-004",
        title="API lente",
        category="API",
        status="résolu",
        description="Erreur 502 après import",
        resolution="Déplacer l'import en tâche asynchrone",
        score=0.86,
    )
    prompt = make_prompt("Que faire avec une erreur 502 ?", [source])
    assert "[Incident 4]" in prompt
    assert "Déplacer l'import en tâche asynchrone" in prompt
    assert "EXCLUSIVEMENT" in prompt


def test_incident_validates_priority():
    from pydantic import ValidationError
    try:
        IncidentCreate(title="Un incident", description="Description complète", priority="urgent")
    except ValidationError:
        return
    raise AssertionError("Priority must be restricted to accepted values")
