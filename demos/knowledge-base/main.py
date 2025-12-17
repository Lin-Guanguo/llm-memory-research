#!/usr/bin/env python3
"""
Personal Knowledge Base CLI - powered by mem0.

Usage:
    python main.py add <path>          Add a file or directory to the knowledge base
    python main.py search <query>      Search the knowledge base
    python main.py list                List all memories
    python main.py clear               Clear all memories
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from knowledge_base import KnowledgeBase


def cmd_add(args):
    """Add a file or directory to the knowledge base."""
    target_path = Path(args.path).resolve()

    if not target_path.exists():
        print(f"Error: Path not found: {target_path}")
        sys.exit(1)

    if target_path.is_dir():
        print(f"Adding directory: {target_path}")
    else:
        print(f"Adding file: {target_path}")

    kb = KnowledgeBase()

    try:
        stats = kb.add_path(str(target_path), update=True, verbose=args.verbose)

        # Print summary
        print("\n--- Summary ---")
        if stats["files_added"] > 0:
            print(f"  Added: {stats['files_added']} file(s)")
        if stats["files_updated"] > 0:
            print(f"  Updated: {stats['files_updated']} file(s)")
        print(f"  Total chunks: {stats['chunks_added']}")

        if stats["errors"]:
            print(f"\nErrors ({len(stats['errors'])}):")
            for err in stats["errors"]:
                print(f"  - {err}")

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_search(args):
    """Search the knowledge base."""
    query = args.query
    limit = args.limit

    print(f"Searching for: {query}\n")
    kb = KnowledgeBase()

    results = kb.search(query, limit=limit)

    if not results:
        print("No results found.")
        return

    print(f"Found {len(results)} result(s):\n")
    for i, result in enumerate(results, 1):
        print(f"--- Result {i} ---")
        print(f"Memory: {result.get('memory', 'N/A')}")
        if "score" in result:
            print(f"Score: {result['score']:.4f}")
        metadata = result.get("metadata", {})
        if metadata:
            source = metadata.get("filename", metadata.get("source", "Unknown"))
            print(f"Source: {source}")
        print()


def cmd_list(args):
    """List all memories."""
    kb = KnowledgeBase()
    memories = kb.list_all(limit=args.limit)

    if not memories:
        print("Knowledge base is empty.")
        return

    print(f"Total memories: {len(memories)}\n")
    for i, mem in enumerate(memories, 1):
        print(f"[{i}] ID: {mem.get('id', 'N/A')}")
        memory_text = mem.get("memory", "N/A")
        # Truncate long memories
        if len(memory_text) > 100:
            memory_text = memory_text[:100] + "..."
        print(f"    Memory: {memory_text}")
        metadata = mem.get("metadata", {})
        if metadata.get("filename"):
            print(f"    Source: {metadata['filename']}")
        print()


def cmd_clear(args):
    """Clear all memories."""
    if not args.force:
        confirm = input("Are you sure you want to delete all memories? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return

    kb = KnowledgeBase()
    deleted, failed = kb.clear()
    print(f"Deleted {deleted} memories.")
    if failed:
        print(f"Warning: Failed to delete {failed} memories.")


def main():
    parser = argparse.ArgumentParser(
        description="Personal Knowledge Base CLI - powered by mem0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # add command
    add_parser = subparsers.add_parser("add", help="Add a file or directory to the knowledge base")
    add_parser.add_argument("path", help="Path to file or directory (.txt, .md files)")
    add_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed progress")
    add_parser.set_defaults(func=cmd_add)

    # search command
    search_parser = subparsers.add_parser("search", help="Search the knowledge base")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-n", "--limit", type=int, default=5, help="Max results (default: 5)")
    search_parser.set_defaults(func=cmd_search)

    # list command
    list_parser = subparsers.add_parser("list", help="List all memories")
    list_parser.add_argument("-n", "--limit", type=int, default=100, help="Max results (default: 100)")
    list_parser.set_defaults(func=cmd_list)

    # clear command
    clear_parser = subparsers.add_parser("clear", help="Clear all memories")
    clear_parser.add_argument("-f", "--force", action="store_true", help="Skip confirmation")
    clear_parser.set_defaults(func=cmd_clear)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
