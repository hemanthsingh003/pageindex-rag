import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query
from fastapi.responses import JSONResponse

from . import indexer, query_engine, storage
from .config import (
    ensure_directories,
    load_config,
    save_config,
    get_model,
    get_default_model,
)
from .models import load_model
from .schemas import (
    IndexPathRequest,
    IndexResponse,
    DocumentResponse,
    QueryRequest,
    QueryResponse,
    SourceInfo,
    HistoryResponse,
    HistoryEntry,
    ConfigResponse,
    ConfigUpdateRequest,
    HealthResponse,
)


app = FastAPI(
    title="pageindex-rag",
    description="Local RAG API using PageIndex + MLX for Apple Silicon",
    version="0.1.0",
)

_model_loaded = False


def ensure_model_loaded():
    global _model_loaded
    if not _model_loaded:
        load_model()
        _model_loaded = True


@app.on_event("startup")
async def startup_event():
    ensure_directories()


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        model_loaded=_model_loaded,
    )


@app.post("/api/documents", response_model=IndexResponse)
async def index_document(file: UploadFile = File(...)):
    ensure_directories()
    ensure_model_loaded()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    allowed_extensions = {".pdf", ".md", ".markdown", ".txt"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {allowed_extensions}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = indexer.index_document(tmp_path)
        documents = [
            DocumentResponse(
                doc_id=result["doc_id"],
                title=result["title"],
                original_path=result.get("original_path", tmp_path),
                indexed_at=result.get("indexed_at", ""),
            )
        ]
        return IndexResponse(documents=documents, total=len(documents))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/api/documents/from-path", response_model=IndexResponse)
async def index_from_path(request: IndexPathRequest):
    ensure_directories()
    ensure_model_loaded()

    path = Path(request.path)

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {request.path}")

    try:
        if path.is_file():
            result = indexer.index_document(str(path))
            documents = [
                DocumentResponse(
                    doc_id=result["doc_id"],
                    title=result["title"],
                    original_path=result.get("original_path", str(path)),
                    indexed_at=result.get("indexed_at", ""),
                )
            ]
        elif path.is_dir():
            results = indexer.index_directory(str(path), recursive=request.recursive)
            documents = [
                DocumentResponse(
                    doc_id=r["doc_id"],
                    title=r["title"],
                    original_path=r.get("original_path", ""),
                    indexed_at=r.get("indexed_at", ""),
                )
                for r in results
            ]
        else:
            raise HTTPException(status_code=400, detail="Invalid path")

        return IndexResponse(documents=documents, total=len(documents))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents", response_model=IndexResponse)
async def list_documents():
    ensure_directories()
    docs = storage.get_indexed_documents()
    documents = [
        DocumentResponse(
            doc_id=doc["id"],
            title=doc.get("title", "Unknown"),
            original_path=doc.get("original_path", ""),
            indexed_at=doc.get("indexed_at", ""),
        )
        for doc in docs
    ]
    return IndexResponse(documents=documents, total=len(documents))


@app.get("/api/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    ensure_directories()
    doc = storage.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")
    return DocumentResponse(
        doc_id=doc["id"],
        title=doc.get("title", "Unknown"),
        original_path=doc.get("original_path", ""),
        indexed_at=doc.get("indexed_at", ""),
    )


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    ensure_directories()
    success = storage.unregister_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")
    return {"message": f"Document {doc_id} removed successfully"}


@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    ensure_directories()
    ensure_model_loaded()

    result = query_engine.query_documents(
        query=request.query,
        doc_id=request.doc_id,
        top_k=request.top_k,
    )

    sources = [
        SourceInfo(
            doc_id=s["doc_id"],
            title=s["title"],
            section=s.get("section", ""),
            pages=s.get("pages", ""),
        )
        for s in result.get("sources", [])
    ]

    return QueryResponse(
        answer=result["answer"],
        sources=sources,
    )


@app.get("/api/history", response_model=HistoryResponse)
async def get_history(limit: int = Query(default=20, ge=1, le=100)):
    ensure_directories()
    history = storage.load_history()
    entries = [
        HistoryEntry(
            id=entry["id"],
            timestamp=entry["timestamp"],
            query=entry["query"],
            answer=entry["answer"],
            doc_ids=entry.get("doc_ids", []),
        )
        for entry in history[-limit:]
    ]
    return HistoryResponse(entries=entries, total=len(history))


@app.delete("/api/history")
async def clear_history():
    ensure_directories()
    storage.clear_history()
    return {"message": "History cleared successfully"}


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    config = load_config()
    return ConfigResponse(model=config.get("model", get_default_model()))


@app.put("/api/config", response_model=ConfigResponse)
async def update_config(request: ConfigUpdateRequest):
    global _model_loaded
    config = load_config()
    old_model = config.get("model", get_default_model())

    config["model"] = request.model
    save_config(config)

    if old_model != request.model:
        _model_loaded = False
        ensure_model_loaded()

    return ConfigResponse(model=request.model)


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
