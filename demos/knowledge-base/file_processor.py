"""
File processor for reading and chunking text files.
"""

import re
from pathlib import Path
from typing import List

SUPPORTED_EXTENSIONS = {".txt", ".md"}


def is_supported_file(file_path: Path) -> bool:
    """Check if file type is supported."""
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def read_file(file_path: Path) -> str:
    """Read file content with encoding fallback."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()


def split_into_paragraphs(content: str) -> List[str]:
    """
    Split content into paragraphs.

    Rules:
    - Split by double newlines (blank lines)
    - Merge very short paragraphs (< 50 chars) with previous
    - Filter out empty paragraphs
    """
    # Split by blank lines (one or more empty lines)
    raw_paragraphs = re.split(r"\n\s*\n", content)

    paragraphs = []
    for p in raw_paragraphs:
        p = p.strip()
        if not p:
            continue

        # Merge short paragraphs with previous
        if paragraphs and len(p) < 50:
            paragraphs[-1] = paragraphs[-1] + "\n\n" + p
        else:
            paragraphs.append(p)

    return paragraphs


def process_file(file_path: Path) -> List[dict]:
    """
    Process a file and return chunks with metadata.

    Returns:
        List of dicts with 'content' and 'metadata' keys.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not is_supported_file(file_path):
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}. "
            f"Supported: {SUPPORTED_EXTENSIONS}"
        )

    content = read_file(file_path)
    paragraphs = split_into_paragraphs(content)

    chunks = []
    for i, paragraph in enumerate(paragraphs):
        chunks.append({
            "content": paragraph,
            "metadata": {
                "source": str(file_path),
                "filename": file_path.name,
                "chunk_index": i,
                "total_chunks": len(paragraphs),
            }
        })

    return chunks


def scan_directory(dir_path: Path) -> List[Path]:
    """
    Recursively scan directory for supported files.

    Returns:
        List of file paths.
    """
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {dir_path}")

    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(dir_path.rglob(f"*{ext}"))

    return sorted(files)
