import json
import re
from typing import Optional, List

from . import models
from .storage import get_all_trees, get_document_by_id, add_to_history

def clean_json_string(json_str):
    # Replace unquoted keys with double quotes
    json_str = re.sub(r'([{,]\s*)(\\w+?)\s*:', r'\1"\2":', json_str)
    # Replace single quoted strings with double quotes (keys and values)
    json_str = re.sub(r"'([^\\']*?)'", r'"\1"', json_str)
    return json_str


TREE_SEARCH_PROMPT = """You are a document search assistant. Given a query and a document tree structure, identify which sections of the document are most relevant to answer the query.

Document Tree:
{doc_tree}

Query: {query}

Analyze the tree structure above and identify the relevant sections. For each relevant section, provide:
- The section title
- The page range (start_page - end_page)
- A brief reason why it's relevant

Output ONLY valid JSON in this format:
{{
  "relevant_sections": [
    {{
      "title": "Section Title",
      "start_page": 1,
      "end_page": 5,
      "reason": "Why this section is relevant"
    }}
  ]
}}

If no relevant sections found, output: {{"relevant_sections": []}}

Output ONLY the JSON, no explanation."""


ANSWER_GENERATION_PROMPT = """You are a helpful assistant. Based on the provided document sections, answer the user's query.

Query: {query}

Relevant Document Sections:
{context}

Based ONLY on the provided context, answer the query. If the context doesn't contain enough information to answer the query, say so clearly. Do not make up information.

Answer:"""


def search_tree(tree: dict, query: str) -> List[dict]:
    doc_tree_json = json.dumps(tree.get("sections", []), indent=2)
    
    prompt = TREE_SEARCH_PROMPT.format(
        doc_tree=doc_tree_json[:8000],
        query=query,
    )
    
    try:
        response = models.generate(
            prompt=prompt,
            max_tokens=1000,
        )        

        cleaned_response = clean_json_string(response)
        result = json.loads(cleaned_response)
        return result.get("relevant_sections", [])
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            cleaned_match = clean_json_string(json_match.group())
            result = json.loads(cleaned_match)
            return result.get("relevant_sections", [])
        return []


def extract_text_from_pdf_pages(pdf_path: str, pages: List[int]) -> str:
    try:
        import PyPDF2
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "PyPDF2", "-q"])
        import PyPDF2
    
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page_num in pages:
            if page_num <= len(reader.pages):
                page = reader.pages[page_num - 1]
                text += f"\n--- Page {page_num} ---\n"
                text += page.extract_text() or ""
    return text


def extract_section_content(tree: dict, pdf_path: str) -> str:
    sections = tree.get("sections", [])
    if not sections:
        return ""
    
    all_pages = set()
    
    def collect_pages(section_list):
        for sec in section_list:
            sp = sec.get("start_page", 0)
            ep = sec.get("end_page", 0)
            if sp and ep:
                all_pages.update(range(sp, ep + 1))
            if sec.get("subsections"):
                collect_pages(sec["subsections"])
    
    collect_pages(sections)
    
    if all_pages:
        return extract_text_from_pdf_pages(pdf_path, sorted(all_pages))
    return ""


def query_documents(
    query: str,
    doc_id: Optional[str] = None,
    top_k: int = 3,
) -> dict:
    trees = get_all_trees()
    
    if not trees:
        return {
            "answer": "No documents indexed. Please index some documents first.",
            "sources": [],
        }
    
    if doc_id:
        trees = [t for t in trees if t["doc_id"] == doc_id]
        if not trees:
            return {
                "answer": f"Document {doc_id} not found.",
                "sources": [],
            }
    
    all_relevant = []
    
    for tree_data in trees:
        tree = tree_data["tree"]
        doc = tree_data["doc"]
        
        relevant_sections = search_tree(tree, query)
        
        for sec in relevant_sections[:top_k]:
            all_relevant.append({
                "doc_id": tree_data["doc_id"],
                "title": doc.get("title", "Unknown"),
                "section": sec.get("title", ""),
                "pages": f"{sec.get('start_page', '?')} - {sec.get('end_page', '?')}",
                "reason": sec.get("reason", ""),
            })
    
    context_parts = []
    sources = []
    
    for rel in all_relevant[:top_k * 2]:
        doc = get_document_by_id(rel["doc_id"])
        if doc:
            pdf_path = doc["original_path"]
            content = extract_section_content(
                {"sections": [{"start_page": 1, "end_page": 50}]},
                pdf_path
            )
            if content:
                context_parts.append(
                    f"Document: {rel['title']}\n"
                    f"Section: {rel['section']}\n"
                    f"Content: {content[:3000]}"
                )
                sources.append({
                    "doc_id": rel["doc_id"],
                    "title": rel["title"],
                    "section": rel["section"],
                    "pages": rel["pages"],
                })
    
    if not context_parts:
        answer = "Could not find relevant information in the indexed documents."
    else:
        context = "\n\n".join(context_parts[:3])
        
        prompt = ANSWER_GENERATION_PROMPT.format(
            query=query,
            context=context,
        )
        
        answer = models.generate(
            prompt=prompt,
            max_tokens=1000,
        )
    
    doc_ids = list(set([s["doc_id"] for s in sources]))
    add_to_history(query, answer, doc_ids)
    
    return {
        "answer": answer,
        "sources": sources,
    }
