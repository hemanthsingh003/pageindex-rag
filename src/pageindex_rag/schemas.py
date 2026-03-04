from typing import Optional, List
from pydantic import BaseModel, Field


class IndexPathRequest(BaseModel):
    path: str = Field(..., description="Path to file or directory")
    recursive: bool = Field(default=False, description="Recursively scan directories")


class DocumentResponse(BaseModel):
    doc_id: str
    title: str
    original_path: str
    indexed_at: str


class IndexResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class QueryRequest(BaseModel):
    query: str = Field(..., description="Query string")
    doc_id: Optional[str] = Field(
        default=None, description="Limit to specific document ID"
    )
    top_k: int = Field(default=3, description="Number of top results")


class SourceInfo(BaseModel):
    doc_id: str
    title: str
    section: str
    pages: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]


class HistoryEntry(BaseModel):
    id: str
    timestamp: str
    query: str
    answer: str
    doc_ids: List[str]


class HistoryResponse(BaseModel):
    entries: List[HistoryEntry]
    total: int


class ConfigResponse(BaseModel):
    model: str


class ConfigUpdateRequest(BaseModel):
    model: str


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool


class ErrorResponse(BaseModel):
    detail: str
