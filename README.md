# LLM Memory Research

A personal research project for studying and experimenting with LLM memory implementations.

## Overview

This repository explores how large language models can maintain long-term memory, enabling more personalized and context-aware AI interactions.

**[summary.md](./summary.md)** - Key findings from reverse-engineering ChatGPT, Claude, and AI coding CLI memory systems, And letta, mem0 this two open source memeory system.

## Directory Structure

### Submodules

#### [mem0](https://github.com/mem0ai/mem0)

The memory layer for personalized AI. Mem0 provides intelligent memory capabilities that help AI systems remember user preferences, past interactions, and contextual information.

- Long-term memory for AI agents
- Semantic memory extraction and retrieval
- Multi-level memory (user, session, agent)

#### [letta](https://github.com/letta-ai/letta)

Letta (formerly MemGPT) is a framework for creating LLM agents with long-term memory and the ability to manage their own context.

- Self-editing memory for extended context
- Stateful agents with persistent memory
- Tool use and function calling

### agent-cli/

Research documentation on how AI coding assistants (Claude Code, Codex CLI, Gemini CLI) manage session files and memory.

- Session file schemas and structures
- Cross-agent analysis and comparison
- Integration guides

### demos/

Experimental implementations and proof-of-concept demos.

- **knowledge-base/**: Vector-based knowledge base using ChromaDB for semantic search

### reverse-engineer/

Collected articles and resources on reverse engineering LLM memory systems.

- ChatGPT memory system analysis
- Claude memory system analysis

## Setup

```bash
# Clone with submodules
git clone --recursive <repo-url>

# Or initialize submodules after clone
git submodule update --init --recursive
```

## License

This is a personal research project. The included submodules retain their original licenses.
