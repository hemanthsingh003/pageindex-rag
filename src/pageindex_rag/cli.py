import argparse
import sys
from pathlib import Path

from . import indexer, query_engine, storage
from .config import ensure_directories, load_config, save_config, get_model


def cmd_index(args):
    ensure_directories()

    paths = []
    for path_arg in args.path:
        p = Path(path_arg)
        if p.is_file():
            paths.append(str(p))
        elif p.is_dir():
            results = indexer.index_directory(str(p), recursive=args.recursive)
            print(f"Indexed {len(results)} documents from directory: {p}")
            return
        else:
            print(f"Error: Path not found: {path_arg}", file=sys.stderr)
            sys.exit(1)

    if not paths:
        print("Error: No files to index", file=sys.stderr)
        sys.exit(1)

    results = indexer.index_multiple_files(paths)

    for result in results:
        print(f"Indexed: {result['title']} (ID: {result['doc_id']})")

    print(f"\nTotal: {len(results)} document(s) indexed")


def cmd_query(args):
    ensure_directories()

    result = query_engine.query_documents(
        query=args.query,
        doc_id=args.doc,
    )

    print("\n" + "=" * 50)
    print("ANSWER:")
    print("=" * 50)
    print(result["answer"])

    if result["sources"]:
        print("\n" + "=" * 50)
        print("SOURCES:")
        print("=" * 50)
        for src in result["sources"]:
            print(f"  - {src['title']}")
            print(f"    Section: {src['section']}")
            print(f"    Pages: {src['pages']}")
            print()


def cmd_list(args):
    ensure_directories()

    docs = storage.get_indexed_documents()

    if not docs:
        print("No documents indexed.")
        return

    print(f"\nIndexed Documents ({len(docs)}):")
    print("-" * 50)
    for doc in docs:
        print(f"ID:      {doc['id']}")
        print(f"Title:   {doc['original_path'].split('/')[-1]}")
        print(f"Path:    {doc['original_path']}")
        print(f"Indexed: {doc['indexed_at'][:19]}")
        print()


def cmd_history(args):
    ensure_directories()

    history = storage.load_history()

    if not history:
        print("No query history.")
        return

    if args.clear:
        storage.clear_history()
        print("History cleared.")
        return

    print(f"\nQuery History ({len(history)} entries):")
    print("-" * 50)
    for entry in reversed(history[-20:]):
        print(f"Query: {entry['query']}")
        print(f"Time:  {entry['timestamp'][:19]}")
        print(f"Docs:  {', '.join(entry['doc_ids'])}")
        print()


def cmd_remove(args):
    ensure_directories()

    success = storage.unregister_document(args.doc_id)

    if success:
        print(f"Removed document: {args.doc_id}")
    else:
        print(f"Document not found: {args.doc_id}")
        sys.exit(1)


def cmd_rebuild(args):
    ensure_directories()

    doc = storage.get_document_by_id(args.doc_id)

    if not doc:
        print(f"Document not found: {args.doc_id}")
        sys.exit(1)

    storage.unregister_document(args.doc_id)

    result = indexer.index_document(doc["original_path"], doc_id=args.doc_id)
    print(f"Rebuilt index for: {result['title']}")


def cmd_serve(args):
    import uvicorn
    from .api import app

    print(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_config(args):
    ensure_directories()

    if args.show:
        config = load_config()
        print(f"\nCurrent Configuration:")
        print(f"  Model: {config.get('model', get_model())}")
        return

    if args.model:
        config = load_config()
        config["model"] = args.model
        save_config(config)
        print(f"Model set to: {args.model}")


def main():
    parser = argparse.ArgumentParser(
        description="pageindex-rag: Local RAG with PageIndex + MLX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index a document or directory")
    index_parser.add_argument("path", nargs="+", help="File(s) or directory to index")
    index_parser.add_argument(
        "-r", "--recursive", action="store_true", help="Recursively scan directories"
    )
    index_parser.set_defaults(func=cmd_index)

    query_parser = subparsers.add_parser("query", help="Query indexed documents")
    query_parser.add_argument("query", help="Query string")
    query_parser.add_argument("--doc", help="Limit to specific document ID")
    query_parser.set_defaults(func=cmd_query)

    list_parser = subparsers.add_parser("list", help="List indexed documents")
    list_parser.set_defaults(func=cmd_list)

    history_parser = subparsers.add_parser("history", help="Query history")
    history_parser.add_argument("--clear", action="store_true", help="Clear history")
    history_parser.set_defaults(func=cmd_history)

    remove_parser = subparsers.add_parser("remove", help="Remove a document")
    remove_parser.add_argument("doc_id", help="Document ID to remove")
    remove_parser.set_defaults(func=cmd_remove)

    rebuild_parser = subparsers.add_parser(
        "rebuild", help="Rebuild index for a document"
    )
    rebuild_parser.add_argument("doc_id", help="Document ID to rebuild")
    rebuild_parser.set_defaults(func=cmd_rebuild)

    config_parser = subparsers.add_parser("config", help="Configuration")
    config_parser.add_argument(
        "--show", action="store_true", help="Show current config"
    )
    config_parser.add_argument("--model", help="Set model")
    config_parser.set_defaults(func=cmd_config)

    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    serve_parser.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
