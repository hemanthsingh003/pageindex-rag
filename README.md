# pageindex-rag

[![Platform: macOS](https://img.shields.io/badge/Platform-macOS%20Apple%20Silicon-blue.svg)](https://apple.com/mac)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)

A local RAG (Retrieval Augmented Generation) system using [PageIndex](https://github.com/vectify-ai/pageindex) + [MLX](https://github.com/ml-explore/mlx) for Apple Silicon Macs.

Ask questions about your PDF documents using local LLMs - no data leaves your machine.

## Requirements

- **Apple Silicon Mac** (M1, M2, M3, or M4)
- **macOS 13.0+** (Ventura or later)
- **Python 3.10+**

> **Note**: This project uses MLX, which is exclusively designed for Apple Silicon. It will NOT work on Intel Macs, Linux, or Windows.

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/hemanthsingh003/pageindex-rag.git
cd pageindex-rag

# Install in development mode
pip install -e .
```

### Verify Installation

```bash
pageindex-rag --help
```

## Usage

### Indexing Documents

Index a single PDF:

```bash
pageindex-rag index path/to/document.pdf
```

Index multiple files:

```bash
pageindex-rag index doc1.pdf doc2.pdf
```

Index all PDFs in a directory:

```bash
pageindex-rag index ./documents/
```

Recursively index subdirectories:

```bash
pageindex-rag index ./documents/ --recursive
```

### Querying Documents

Ask a question about your indexed documents:

```bash
pageindex-rag query "What is this document about?"
```

Query a specific document by ID:

```bash
pageindex-rag query "Summarize the key points" --doc <doc_id>
```

### Managing Indexed Documents

List all indexed documents:

```bash
pageindex-rag list
```

Remove a document from the index:

```bash
pageindex-rag remove <doc_id>
```

Rebuild index for a document:

```bash
pageindex-rag rebuild <doc_id>
```

### Query History

View query history:

```bash
pageindex-rag history
```

Clear query history:

```bash
pageindex-rag history --clear
```

### Configuration

Show current configuration:

```bash
pageindex-rag config --show
```

Set a different model (any MLX-compatible model from HuggingFace):

```bash
pageindex-rag config --model mlx-community/Llama-3.2-1B-Instruct-4bit
```

## API Server

You can also run a REST API server for programmatic access or web UIs.

### Starting the Server

```bash
# Start server on default port (8000)
pageindex-rag serve

# Start on custom port
pageindex-rag serve --port 9000

# Start on specific host
pageindex-rag serve --host 127.0.0.1 --port 8000
```

The server will start and the model will be loaded on first request. The model stays loaded in memory for faster subsequent queries.

### API Endpoints

| Method | Endpoint                   | Description                      |
| ------ | -------------------------- | -------------------------------- |
| GET    | `/api/health`              | Health check                     |
| POST   | `/api/documents`           | Index a file (multipart upload)  |
| POST   | `/api/documents/from-path` | Index from server directory path |
| GET    | `/api/documents`           | List all indexed documents       |
| GET    | `/api/documents/{doc_id}`  | Get document details             |
| DELETE | `/api/documents/{doc_id}`  | Remove a document                |
| POST   | `/api/query`               | Query indexed documents          |
| GET    | `/api/history`             | View query history               |
| DELETE | `/api/history`             | Clear query history              |
| GET    | `/api/config`              | Get current configuration        |
| PUT    | `/api/config`              | Update configuration             |

### API Examples

#### Index a File (using curl)

```bash
curl -X POST http://localhost:8000/api/documents \
  -F "file=@path/to/document.pdf"
```

#### Index from Directory Path

```bash
curl -X POST http://localhost:8000/api/documents/from-path \
  -H "Content-Type: application/json" \
  -d '{"path": "/Users/hemanth/Documents/pdfs/", "recursive": true}'
```

#### Query Documents

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the methodology used in this study?"}'
```

#### Query a Specific Document

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize this document", "doc_id": "a1b2c3d4"}'
```

#### List All Indexed Documents

```bash
curl http://localhost:8000/api/documents
```

#### Get Document by ID

```bash
curl http://localhost:8000/api/documents/a1b2c3d4
```

#### Remove a Document

```bash
curl -X DELETE http://localhost:8000/api/documents/a1b2c3d4
```

#### View Query History

```bash
curl http://localhost:8000/api/history
```

#### Clear Query History

```bash
curl -X DELETE http://localhost:8000/api/history
```

#### Get/Update Configuration

```bash
# Get current config
curl http://localhost:8000/api/config

# Update model
curl -X PUT http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{"model": "mlx-community/Llama-3.2-1B-Instruct-4bit"}'
```

### Using with Postman

1. Start the server: `pageindex-rag serve`
2. Open Postman
3. Make requests to `http://localhost:8000/api/...`

**Indexing**: Use POST to `/api/documents`, select Body > form-data, add a key named `file` with type File, and select your PDF.

### Using with Python

```python
import requests

# Index a document
with open("doc.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/documents",
        files={"file": f}
    )
    doc_id = response.json()["documents"][0]["doc_id"]

# Query
response = requests.post(
    "http://localhost:8000/api/query",
    json={"query": "What is this about?", "doc_id": doc_id}
)
print(response.json()["answer"])
```

## Configuration

### Default Model

The default model is `mlx-community/Llama-3.2-3B-Instruct-4bit`.

### Available Models

You can use any MLX-compatible model from HuggingFace. Popular options:

| Model                                      | Size | Description               |
| ------------------------------------------ | ---- | ------------------------- |
| `mlx-community/Llama-3.2-1B-Instruct-4bit` | ~1GB | Fast, lower memory        |
| `mlx-community/Llama-3.2-3B-Instruct-4bit` | ~3GB | Balanced performance      |
| `mlx-community/Qwen2.5-3B-Instruct-4bit`   | ~3GB | Good multilingual support |
| `mlx-community/Phi-3.5-mini-instruct-4bit` | ~3GB | Microsoft model           |

### Data Storage

Configuration and index data are stored in:

- **macOS**: `~/Library/Application Support/pageindex-rag/`

This includes:

- `config.json` - Your configuration
- `index/` - Indexed document data
- `history.json` - Query history

## Example Workflow

```bash
# 1. Index your documents
pageindex-rag index ~/Documents/research/*.pdf

# 2. List indexed documents to see their IDs
pageindex-rag list

# 3. Ask questions
pageindex-rag query "What methodology was used in this study?"

# 4. View your query history
pageindex-rag history
```

## License

MIT License
