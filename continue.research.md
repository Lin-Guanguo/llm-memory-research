# Continue Technical Research Report

Last Updated: 2025-12-18

> **Research Methodology**: Code repository analysis (continue submodule) + Gemini CLI internet search

## Overview

**Continue** is an open-source AI coding assistant that integrates with VS Code and JetBrains IDEs. It focuses on flexibility through a "Bring Your Own Model" (BYOM) approach, allowing developers to use any LLM provider including local models via Ollama.

**Key Innovation**: Highly customizable context providers and rules system, with Model Context Protocol (MCP) support for standardized tool integration.

**Funding**: $65M Series A (September 2024), $500M valuation

**Source**: [Continue GitHub](https://github.com/continuedev/continue) | [Continue Documentation](https://docs.continue.dev)

---

## 1. Core Architecture

### System Components

| Component | Description | Interface |
|-----------|-------------|-----------|
| **IDE Agents** | Integrated directly into VS Code/JetBrains | IDE extension |
| **CLI Agents** | Terminal-based TUI mode | `npm i -g @continuedev/cli` |
| **Cloud Agents** | Automated workflows on events | Mission Control dashboard |
| **Core** | TypeScript-based processing engine | `core/` directory |

**Source**: README.md, `core/` directory structure

### Directory Structure

```
continue/
├── core/                    # Main processing engine
│   ├── indexing/           # Codebase indexing system
│   ├── context/            # Context providers
│   ├── llm/                # LLM integrations
│   ├── tools/              # Agent tools
│   └── config/             # Configuration handling
├── extensions/             # IDE extensions (VS Code, JetBrains)
├── gui/                    # Web-based UI
├── packages/               # Shared packages
└── binary/                 # Compiled binaries
```

---

## 2. Indexing System

### Tagging & Content Addressing

Continue uses a sophisticated tagging system to avoid redundant indexing:

> "When you change branches, Continue will only re-index the files that are newly modified and that we don't already have a copy of."

**Source**: `core/indexing/README.md`

### Indexing Pipeline

**Location**: `core/indexing/CodebaseIndexer.ts`

1. **Check timestamps**: Compare file modification times (faster than reading files)
2. **Catalog comparison**: SQLite-based catalog of indexed files
3. **Branch awareness**: Check if file was indexed on another branch
4. **Cache key**: Hash of file contents for deduplication
5. **Tag management**: Add/remove tags per branch

### Index Types

| Index | File | Purpose |
|-------|------|---------|
| **CodeSnippetsIndex** | `CodeSnippetsIndex.ts` | Tree-sitter queries for functions, classes, top-level objects |
| **FullTextSearchIndex** | `FullTextSearchCodebaseIndex.ts` | SQLite FTS5 for keyword search |
| **ChunkCodebaseIndex** | `chunk/ChunkCodebaseIndex.ts` | Recursive code structure chunking |
| **LanceDbIndex** | `LanceDbIndex.ts` | Vector embeddings for semantic search |

**Source**: `core/indexing/README.md` (lines 19-26)

### LanceDB Vector Storage

**Location**: `core/indexing/LanceDbIndex.ts`

- Uses LanceDB for vector embeddings
- Creates separate tables per branch/repo tag
- SQLite cache for metadata (`lance_db_cache` table)
- Batch processing: 200 files per batch by default

```typescript
// core/indexing/LanceDbIndex.ts (lines 88-98)
await db.exec(`CREATE TABLE IF NOT EXISTS lance_db_cache (
    uuid TEXT PRIMARY KEY,
    cacheKey TEXT NOT NULL,
    path TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    vector TEXT NOT NULL,
    startLine INTEGER NOT NULL,
    endLine INTEGER NOT NULL,
    contents TEXT NOT NULL
)`);
```

---

## 3. Context Providers System

### Architecture

**Location**: `core/context/`

Context providers inject relevant information into LLM prompts:

```typescript
// core/context/index.ts
abstract class BaseContextProvider implements IContextProvider {
  abstract getContextItems(
    query: string,
    extras: ContextProviderExtras,
  ): Promise<ContextItem[]>;
}
```

### Available Providers

| Provider | File | Description |
|----------|------|-------------|
| `@codebase` | `CodebaseContextProvider.ts` | Semantic codebase search (deprecated, now agent-based) |
| `@file` | `FileContextProvider.ts` | Specific file contents |
| `@folder` | `FolderContextProvider.ts` | Folder contents |
| `@docs` | `DocsContextProvider.ts` | Documentation search |
| `@web` | `WebContextProvider.ts` | Web search results |
| `@terminal` | `TerminalContextProvider.ts` | Terminal output |
| `@diff` | `DiffContextProvider.ts` | Git diff content |
| `@git` | `GitCommitContextProvider.ts` | Git commit history |
| `@problems` | `ProblemsContextProvider.ts` | IDE problems/diagnostics |
| `@clipboard` | `ClipboardContextProvider.ts` | Clipboard contents |
| `@rules` | `RulesContextProvider.ts` | Project rules |
| `@mcp` | `MCPContextProvider.ts` | Model Context Protocol integration |

**Source**: `core/context/providers/` directory

### MCP Integration

**Location**: `core/context/mcp/`

Model Context Protocol (MCP) enables standardized tool and context integration:

- Prompts handling
- Tool usage
- Context retrieval

---

## 4. Rules System

### Configuration Locations

| Location | Scope |
|----------|-------|
| `.continue/rules/` | Project-specific rules |
| `~/.continue/rules/` | User-global rules |

### Rule Format

Rules are markdown files that provide persistent context:

```markdown
# Example rule (.continue/rules/coding-style.md)

- Use TypeScript for all new code
- Follow ESLint configuration
- Write tests for new features
```

**Source**: `core/context/providers/RulesContextProvider.ts`

---

## 5. Chunking System

### Chunk Structure

**Location**: `core/index.d.ts` (lines 33-45)

```typescript
interface ChunkWithoutID {
  content: string;
  startLine: number;
  endLine: number;
  signature?: string;
  otherMetadata?: { [key: string]: any };
}

interface Chunk extends ChunkWithoutID {
  digest: string;
  filepath: string;
  index: number;
}
```

### Chunking Strategies

**Location**: `core/indexing/chunk/`

- **Code structure chunking**: Uses tree-sitter for language-aware splitting
- **Basic chunking**: Fallback for unsupported languages
- **Recursive chunking**: Splits large chunks further

---

## 6. LLM Integration

### Supported Providers

**Location**: `core/llm/`

| Provider | Description |
|----------|-------------|
| OpenAI | GPT-4, GPT-3.5 |
| Anthropic | Claude models |
| Google | Gemini models |
| Mistral | Mistral models |
| Ollama | Local models |
| LM Studio | Local models |
| Azure OpenAI | Enterprise |
| AWS Bedrock | Enterprise |
| Together AI | Open source models |

### BYOM (Bring Your Own Model)

Continue's key differentiator - no vendor lock-in:

```yaml
# config.yaml example
models:
  - name: "Local Llama"
    provider: ollama
    model: llama3
```

---

## 7. Agent Mode

### Tool-Based Exploration

Instead of the deprecated `@codebase` context provider, Continue now uses agent mode with tools:

- **File exploration**: Navigate and read files
- **Code search**: Grep and semantic search
- **Git integration**: Branch, diff, history
- **Terminal**: Execute commands

**Source**: Gemini CLI search results

### 2025 Features

| Feature | Description |
|---------|-------------|
| **Next Edit** | Predictive multi-line code suggestions |
| **Plan Mode** | Read-only mode for strategizing changes |
| **Parallel Tool Calling** | Concurrent tool execution for speed |
| **Cloud Agents** | Automated workflows on PR opens, schedules, events |

---

## 8. Data Storage

### Local Storage

| Data | Location | Format |
|------|----------|--------|
| Index database | `~/.continue/index.sqlite` | SQLite |
| Vector embeddings | `~/.continue/lancedb/` | LanceDB |
| Configuration | `~/.continue/config.yaml` | YAML |
| Dev data | `.continue/dev_data/` | JSON/Binary |

### Privacy-First Design

- All data stored locally by default
- No code sent to Continue servers (unless using Continue Hub)
- Full control over which LLM provider receives code

---

## 9. Comparison with Other Tools

| Feature | Continue | GitHub Copilot | Cursor |
|---------|----------|----------------|--------|
| **Model Control** | High (BYOM) | Low (fixed) | Medium |
| **Open Source** | Yes | No | No |
| **Local Models** | Yes (Ollama) | No | Limited |
| **IDE Support** | VS Code, JetBrains | VS Code, JetBrains | Custom IDE |
| **Codebase Indexing** | LanceDB + SQLite | Proprietary | Proprietary |
| **MCP Support** | Yes | No | Yes |
| **Price** | Free (OSS) | $10-19/mo | $20/mo |

---

## 10. Key Technical Specifications

| Metric | Value |
|--------|-------|
| **Files per batch** | 200 (indexing) |
| **Index storage** | SQLite + LanceDB |
| **Chunking** | Tree-sitter based |
| **Search methods** | FTS5 + Vector similarity |
| **IDE extensions** | VS Code, JetBrains |
| **CLI** | `@continuedev/cli` (npm) |

---

## 11. Key Takeaways

1. **BYOM Architecture**: No vendor lock-in, supports any LLM provider including local models

2. **Branch-Aware Indexing**: Content-addressed caching avoids re-indexing when switching branches

3. **Hybrid Search**: Combines FTS5 (keyword) and LanceDB (vector) for optimal retrieval

4. **Tree-Sitter Chunking**: Language-aware code splitting for better context

5. **Context Providers**: Extensible system for injecting context (@file, @docs, @web, etc.)

6. **Rules System**: Persistent project-specific instructions in `.continue/rules/`

7. **MCP Integration**: Model Context Protocol for standardized tool integration

8. **Privacy-First**: All data stored locally, full control over code exposure

9. **Agent Mode**: Tool-based exploration replacing static codebase indexing

---

## References

### Documentation
- [Continue Documentation](https://docs.continue.dev)
- [Continue CLI Quick Start](https://docs.continue.dev/cli/quick-start)
- [Mission Control](https://hub.continue.dev)

### Code References
- Main indexer: `core/indexing/CodebaseIndexer.ts`
- Index types: `core/indexing/README.md`
- Vector storage: `core/indexing/LanceDbIndex.ts`
- Context providers: `core/context/providers/`
- Configuration: `core/config/`

### Market Data
- Funding: $65M Series A (September 2024)
- Valuation: $500M
- Lead Investor: Insight Partners
- GitHub Stars: 30.4k+
