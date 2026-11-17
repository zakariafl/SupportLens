"""API request/response schemas."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IncidentCreate(BaseModel):
    source_ref: str | None = Field(default=None, min_length=2, max_length=80)
    title: str = Field(min_length=5, max_length=220)
    description: str = Field(min_length=10, max_length=5000)
    resolution: str | None = Field(default=None, max_length=5000)
    category: str = Field(default="Autre", max_length=80)
    priority: Literal["faible", "moyenne", "haute", "critique"] = "moyenne"
    status: Literal["ouvert", "en cours", "résolu"] = "résolu"


class IncidentRead(IncidentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class SearchRequest(BaseModel):
    question: str = Field(min_length=4, max_length=1200)
    top_k: int = Field(default=3, ge=1, le=10)


class AskRequest(SearchRequest):
    generate: bool = True


class Source(BaseModel):
    id: int
    source_ref: str | None
    title: str
    category: str
    status: str
    description: str
    resolution: str | None
    score: float


class SearchResponse(BaseModel):
    question: str
    sources: list[Source]


class AskResponse(SearchResponse):
    answer: str
    generated: bool
    notice: str | None = None
