#!/usr/bin/env bash
# Copy relevant md files into docs/ for mkdocs build.
# Submodules and non-doc files are excluded.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS="$REPO_ROOT/docs"

rm -rf "$DOCS"
mkdir -p "$DOCS/reverse-engineer" "$DOCS/agent-cli" "$DOCS/plan"

# Root-level md files (exclude CLAUDE.md)
for f in "$REPO_ROOT"/*.md; do
  name="$(basename "$f")"
  [ "$name" = "CLAUDE.md" ] && continue
  cp "$f" "$DOCS/$name"
done

# Subdirectories with research docs
cp "$REPO_ROOT"/reverse-engineer/*.md "$DOCS/reverse-engineer/"
cp "$REPO_ROOT"/agent-cli/*.md "$DOCS/agent-cli/"
cp "$REPO_ROOT"/plan/*.md "$DOCS/plan/"

echo "docs/ ready ($(find "$DOCS" -name '*.md' | wc -l | tr -d ' ') files)"
