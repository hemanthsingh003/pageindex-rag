import json
import os
import sys
import uuid
from pathlib import Path
from typing import Optional, List

from . import models
from .config import get_index_dir, ensure_directories
from .storage import generate_doc_id, register_document


TREE_SYSTEM_PROMPT = """You are a document indexing assistant. Your task is to analyze a document and create a hierarchical tree structure (like a table of contents) that represents its content structure.

For each section of the document, provide:
- title: A clear, descriptive title for the section
- summary: A brief 1-2 sentence summary of what this section contains
- start_page: The page number where this section begins
- end_page: The page number where this section ends
- subsections: Any subsections within this section (recursive structure)

Output ONLY valid JSON in this exact format:
{
  "title": "Document Title",
  "sections": [
    {
      "title": "Section Title",
      "summary": "Brief summary of section content",
      "start_page": 1,
      "end_page": 5,
      "subsections": [
        {
          "title": "Subsection Title",
          "summary": "Brief summary",
          "start_page": 2,
          "end_page": 3,
          "subsections": []
        }
      ]
    }
  ]
}

Do NOT include any explanation, only output the JSON."""


def extract_text_from_pdf(pdf_path: str, max_pages: int = 50) -> str:
    try:
        import PyPDF2
    except ImportError:
        print("Installing PyPDF2...", file=sys.stderr)
        os.system(f"{sys.executable} -m pip install PyPDF2 -q")
        import PyPDF2

    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        num_pages = min(len(reader.pages), max_pages)
        for i in range(num_pages):
            page = reader.pages[i]
            text += f"\n--- Page {i+1} ---\n"
            text += page.extract_text() or ""
    return text


def extract_text_from_markdown(md_path: str) -> str:
    with open(md_path, "r") as f:
        return f.read()


def build_tree_index(document_text: str, doc_title: str = "Document") -> dict:
    prompt = f"""{TREE_SYSTEM_PROMPT}

Document Title: {doc_title}

Document Content (first part):
{document_text[:15000]}

Now create the hierarchical tree structure:"""

    response = models.generate(
        prompt=prompt,
        max_tokens=4000,
    )

    try:
        tree = json.loads(response)
        return tree
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"title": doc_title, "sections": [], "error": "Failed to parse tree"}


def get_document_content(file_path: str) -> tuple[str, str]:
    path = Path(file_path)
    ext = path.suffix.lower()
    
    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif ext in [".md", ".markdown", ".txt"]:
        text = extract_text_from_markdown(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    
    title = path.stem
    return text, title


def index_document(
    file_path: str,
    doc_id: Optional[str] = None,
) -> dict:
    ensure_directories()
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if doc_id is None:
        doc_id = generate_doc_id()
    
    print(f"Reading document: {file_path}", file=sys.stderr)
    text, title = get_document_content(file_path)
    
    print(f"Building tree index for: {title}", file=sys.stderr)
    tree = build_tree_index(text, title)
    
    tree["doc_id"] = doc_id
    tree["original_path"] = os.path.abspath(file_path)
    tree["indexed_at"] = str(Path(file_path).stat().st_mtime)
    
    index_dir = get_index_dir()
    tree_path = index_dir / f"{doc_id}_tree.json"
    
    with open(tree_path, "w") as f:
        json.dump(tree, f, indent=2)
    
    register_document(
        doc_id=doc_id,
        original_path=os.path.abspath(file_path),
        tree_path=str(tree_path),
        title=title,
    )
    
    print(f"Indexed document: {doc_id}", file=sys.stderr)
    return {"doc_id": doc_id, "title": title, "tree_path": str(tree_path)}


def index_multiple_files(file_paths: List[str]) -> List[dict]:
    results = []
    for path in file_paths:
        try:
            result = index_document(path)
            results.append(result)
        except Exception as e:
            print(f"Error indexing {path}: {e}", file=sys.stderr)
    return results


def index_directory(dir_path: str, recursive: bool = False) -> List[dict]:
    path = Path(dir_path)
    if not path.is_dir():
        raise ValueError(f"Not a directory: {dir_path}")
    
    patterns = ["*.pdf", "*.md", "*.markdown", "*.txt"]
    files = []
    
    for pattern in patterns:
        if recursive:
            files.extend(path.rglob(pattern))
        else:
            files.extend(path.glob(pattern))
    
    file_paths = [str(f) for f in files]
    return index_multiple_files(file_paths)
