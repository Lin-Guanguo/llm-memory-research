"""
Knowledge base operations using mem0.
"""

from pathlib import Path
from typing import List, Optional

from mem0 import Memory

from config import DEFAULT_USER_ID, get_mem0_config
from file_processor import is_supported_file, process_file, scan_directory


class KnowledgeBase:
    """Personal knowledge base powered by mem0."""

    def __init__(self, user_id: str = DEFAULT_USER_ID):
        self.user_id = user_id
        try:
            self.memory = Memory.from_config(get_mem0_config())
        except Exception as e:
            raise RuntimeError(
                "Failed to initialize memory. Please check that OPENAI_API_KEY or "
                "OPENROUTER_API_KEY is set in your .env file.\n"
                f"Original error: {e}"
            ) from e

    def _delete_by_source(self, source: str) -> int:
        """Delete all memories from a specific source file."""
        memories = self.list_all(limit=1000)
        deleted = 0
        for mem in memories:
            metadata = mem.get("metadata", {})
            if metadata.get("source") == source:
                mem_id = mem.get("id")
                if mem_id:
                    try:
                        self.memory.delete(mem_id)
                        deleted += 1
                    except Exception:
                        pass
        return deleted

    def add_file(self, file_path: str, update: bool = True, verbose: bool = False) -> tuple[int, bool]:
        """
        Add a file to the knowledge base.

        Args:
            file_path: Path to the file to add.
            update: If True, delete existing memories from this file before adding.
            verbose: If True, print progress for each chunk.

        Returns:
            Tuple of (chunks_added, was_updated).
        """
        path = Path(file_path).resolve()
        source = str(path)

        # Check if file was already added
        was_updated = False
        if update:
            deleted = self._delete_by_source(source)
            if deleted > 0:
                was_updated = True
                if verbose:
                    print(f"    Deleted {deleted} old memories")

        chunks = process_file(path)

        for i, chunk in enumerate(chunks, 1):
            if verbose:
                print(f"    Processing chunk {i}/{len(chunks)}...", end=" ", flush=True)
            messages = [
                {
                    "role": "user",
                    "content": f"Please remember this information from {chunk['metadata']['filename']}:\n\n{chunk['content']}"
                }
            ]
            self.memory.add(
                messages,
                user_id=self.user_id,
                metadata=chunk["metadata"]
            )
            if verbose:
                print("done")

        return len(chunks), was_updated

    def add_path(self, path: str, update: bool = True, verbose: bool = False) -> dict:
        """
        Add a file or directory to the knowledge base.

        Args:
            path: Path to file or directory.
            update: If True, update existing files instead of skipping.
            verbose: If True, print progress.

        Returns:
            Dict with stats: files_added, files_updated, chunks_added, errors.
        """
        p = Path(path).resolve()

        if p.is_file():
            if not is_supported_file(p):
                return {"files_added": 0, "files_updated": 0, "chunks_added": 0, "errors": [str(p)]}
            if verbose:
                print(f"  Processing: {p.name}")
            chunks, was_updated = self.add_file(str(p), update=update, verbose=verbose)
            return {
                "files_added": 0 if was_updated else 1,
                "files_updated": 1 if was_updated else 0,
                "chunks_added": chunks,
                "errors": []
            }

        if p.is_dir():
            files = scan_directory(p)
            stats = {"files_added": 0, "files_updated": 0, "chunks_added": 0, "errors": []}

            if verbose:
                print(f"  Found {len(files)} file(s) to process\n")

            for idx, file_path in enumerate(files, 1):
                if verbose:
                    print(f"  [{idx}/{len(files)}] {file_path.name}")
                try:
                    chunks, was_updated = self.add_file(str(file_path), update=update, verbose=verbose)
                    stats["chunks_added"] += chunks
                    if was_updated:
                        stats["files_updated"] += 1
                    else:
                        stats["files_added"] += 1
                    if verbose:
                        status = "updated" if was_updated else "added"
                        print(f"         {status}, {chunks} chunks\n")
                except Exception as e:
                    stats["errors"].append(f"{file_path}: {e}")
                    if verbose:
                        print(f"         ERROR: {e}\n")

            return stats

        raise FileNotFoundError(f"Path not found: {path}")

    def search(self, query: str, limit: int = 5) -> List[dict]:
        """
        Search the knowledge base.

        Args:
            query: Search query.
            limit: Maximum number of results.

        Returns:
            List of matching memories.
        """
        results = self.memory.search(
            query,
            user_id=self.user_id,
            limit=limit
        )
        return results.get("results", []) if isinstance(results, dict) else results

    def list_all(self, limit: int = 100) -> List[dict]:
        """
        List all memories in the knowledge base.

        Args:
            limit: Maximum number of results.

        Returns:
            List of all memories.
        """
        results = self.memory.get_all(user_id=self.user_id, limit=limit)
        return results.get("results", []) if isinstance(results, dict) else results

    def clear(self) -> tuple[int, int]:
        """
        Clear all memories for the user.

        Returns:
            Tuple of (deleted_count, failed_count).
        """
        memories = self.list_all()
        deleted = 0
        failed = 0
        for mem in memories:
            mem_id = mem.get("id")
            if not mem_id:
                continue
            try:
                self.memory.delete(mem_id)
                deleted += 1
            except Exception:
                failed += 1
        return deleted, failed

    def delete(self, memory_id: str) -> bool:
        """
        Delete a specific memory by ID.

        Args:
            memory_id: ID of the memory to delete.

        Returns:
            True if deleted successfully.
        """
        try:
            self.memory.delete(memory_id)
            return True
        except Exception:
            return False
