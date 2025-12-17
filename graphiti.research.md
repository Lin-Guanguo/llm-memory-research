# Graphiti (Zep) Technical Research Report

Last Updated: 2025-12-18

> **Research Methodology**: Code repository analysis (graphiti submodule) + Claude Code exploration + Gemini CLI internet search

## Overview

**Graphiti** is an open-source framework for building temporally-aware knowledge graphs designed for AI agents. Unlike traditional RAG which relies on batch processing and static summaries, Graphiti continuously integrates user interactions, structured and unstructured data into a coherent, queryable graph with real-time incremental updates.

**Key Innovation**: Bi-temporal data model with explicit tracking of event occurrence and ingestion times, enabling accurate point-in-time queries.

**Paper**: [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956)

**Source**: [Graphiti GitHub](https://github.com/getzep/graphiti) | [Zep Documentation](https://help.getzep.com/graphiti)

---

## 1. Core Architecture: Knowledge Graph Structure

### Graph Elements

Graphiti uses a knowledge graph where facts are represented as "triplets":

| Element | Description | Example |
|---------|-------------|---------|
| **EntityNode** | Entities (people, places, things) | "Kendra", "Adidas shoes" |
| **EntityEdge** | Relationships between entities | "loves" |
| **EpisodicNode** | Source events/interactions | Conversation message, JSON data |
| **EpisodicEdge** | Links episodes to entities they mention | MENTIONS relationship |
| **CommunityNode** | Clusters of related entities | "Fashion preferences" |

**Source**: `graphiti_core/nodes.py`, `graphiti_core/edges.py`

### Node Types

```python
# graphiti_core/nodes.py (line 51-84)
class EpisodeType(Enum):
    message = 'message'  # Format: "actor: content"
    json = 'json'        # Structured JSON data
    text = 'text'        # Plain text
```

**Key Classes**:

| Class | Location | Key Fields |
|-------|----------|------------|
| `EpisodicNode` | nodes.py:295-432 | `source`, `content`, `valid_at`, `entity_edges` |
| `EntityNode` | nodes.py:435-544 | `name`, `name_embedding`, `summary`, `attributes`, `labels` |
| `CommunityNode` | nodes.py | Generated via label propagation algorithm |

### Edge Types

| Class | Location | Relationship Type | Purpose |
|-------|----------|-------------------|---------|
| `EpisodicEdge` | edges.py:131-218 | `MENTIONS` | Links episodes to entities |
| `EntityEdge` | edges.py:221-249 | `RELATES_TO` | Relationships between entities |
| `CommunityEdge` | edges.py | `HAS_MEMBER` | Connects entities to communities |

**EntityEdge Temporal Fields**: `valid_at`, `invalid_at`, `expired_at` - for handling contradictions

---

## 2. Bi-Temporal Data Model (Key Differentiator)

### What is Bi-Temporal?

Graphiti tracks **two time dimensions** for every fact:

| Dimension | Description | Use Case |
|-----------|-------------|----------|
| **Valid Time** | When the fact was true in the real world | "Kendra lived in NY from 2020-2023" |
| **Transaction Time** | When the fact was recorded in the system | When we learned this information |

**Source**: README.md (line 104)

### Temporal Edge Invalidation

When relationships change, Graphiti doesn't delete old facts - it **invalidates** them with timestamps:

```
Old: Kendra --[loves, valid_until: 2024-01-01]--> Running
New: Kendra --[loves, valid_from: 2024-01-01]--> Cycling
```

This enables historical queries like "What did Kendra love in 2023?"

---

## 3. Hybrid Retrieval System

### Search Methods

Graphiti combines **three search approaches** for optimal retrieval:

| Method | Implementation | Best For |
|--------|----------------|----------|
| **Semantic (Cosine Similarity)** | Vector embeddings | Conceptual similarity |
| **Keyword (BM25)** | Full-text search | Exact term matching |
| **Graph Traversal (BFS)** | Breadth-first search | Related entities |

**Source**: `graphiti_core/search/search.py`, `graphiti_core/search/search_config_recipes.py`

### Search Configuration Recipes

```python
# graphiti_core/search/search_config_recipes.py

# Combined hybrid search with RRF reranking
COMBINED_HYBRID_SEARCH_RRF = SearchConfig(
    edge_config=EdgeSearchConfig(
        search_methods=[EdgeSearchMethod.bm25, EdgeSearchMethod.cosine_similarity],
        reranker=EdgeReranker.rrf,
    ),
    node_config=NodeSearchConfig(
        search_methods=[NodeSearchMethod.bm25, NodeSearchMethod.cosine_similarity],
        reranker=NodeReranker.rrf,
    ),
    community_config=CommunitySearchConfig(
        search_methods=[CommunitySearchMethod.bm25, CommunitySearchMethod.cosine_similarity],
        reranker=CommunityReranker.rrf,
    ),
)
```

### Reranking Strategies

| Reranker | Description |
|----------|-------------|
| **RRF (Reciprocal Rank Fusion)** | Combines rankings from multiple search methods |
| **MMR (Maximal Marginal Relevance)** | Diversity-aware reranking |
| **Cross-Encoder** | LLM-based relevance scoring |
| **Node Distance** | Proximity in graph structure |
| **Episode Mentions** | Frequency in source data |

### Search Parameters

| Parameter | Default Value | Location |
|-----------|---------------|----------|
| `DEFAULT_MIN_SCORE` | 0.6 | search_utils.py:64 |
| `MAX_SEARCH_DEPTH` | 3 | search_utils.py:66 |
| `DEFAULT_SEARCH_LIMIT` | 10 | search_config.py |
| `MMR_LAMBDA` | 0.5 | search_config.py |

### Database Indices

| Index Name | Purpose |
|------------|---------|
| `entities` | EntityNode fulltext search |
| `episodes` | EpisodicNode fulltext search |
| `communities` | CommunityNode fulltext search |
| `entity_edges` | EntityEdge fulltext search |

**Source**: `graphiti_core/driver/driver.py` (lines 36-39)

---

## 4. Incremental Updates (vs Batch Processing)

### Traditional RAG Problem

- Requires complete graph recomputation for new data
- Static summaries become stale
- High latency for updates

### Graphiti Solution

```python
# graphiti_core/graphiti.py (line 105-121)
class AddEpisodeResults(BaseModel):
    episode: EpisodicNode
    episodic_edges: list[EpisodicEdge]
    nodes: list[EntityNode]
    edges: list[EntityEdge]
    communities: list[CommunityNode]
    community_edges: list[CommunityEdge]
```

**Real-time ingestion pipeline**:
1. Parse episode (message, JSON, or text)
2. Extract entities and relationships using LLM
3. Deduplicate against existing nodes/edges
4. Create embeddings
5. Update graph incrementally
6. Update affected communities

**No batch recomputation required.**

### Ingestion Pipeline Details

**Location**: `graphiti_core/graphiti.py` (lines 615-825)

The `add_episode()` method performs:

1. **Episode creation**: Stores raw content with temporal metadata
2. **Node extraction**: LLM extracts entities from episode body
3. **Node resolution**: Deduplicates extracted nodes, resolves against existing graph
4. **Edge extraction**: Extracts relationships between entities, generates fact embeddings
5. **Edge resolution**: Detects contradictions with existing edges, invalidates contradicted edges
6. **Attribute extraction**: Enriches nodes with contextual summaries
7. **Database persistence**: Bulk saves to graph database

**Key Utility Files**:
- Node extraction: `utils/maintenance/node_operations.py`
- Edge extraction: `utils/maintenance/edge_operations.py`
- Temporal handling: `utils/maintenance/temporal_operations.py`
- Bulk operations: `utils/bulk_utils.py`

---

## 5. Graphiti vs GraphRAG Comparison

| Aspect | GraphRAG | Graphiti |
|--------|----------|----------|
| **Primary Use** | Static document summarization | Dynamic data management |
| **Data Handling** | Batch-oriented processing | Continuous, incremental updates |
| **Knowledge Structure** | Entity clusters & community summaries | Episodic data, semantic entities, communities |
| **Retrieval Method** | Sequential LLM summarization | Hybrid semantic, keyword, and graph-based search |
| **Temporal Handling** | Basic timestamp tracking | Explicit bi-temporal tracking |
| **Contradiction Handling** | LLM-driven summarization judgments | Temporal edge invalidation |
| **Query Latency** | Seconds to tens of seconds | Typically sub-second latency |
| **Custom Entity Types** | No | Yes, customizable via Pydantic |

**Source**: README.md (lines 117-129)

---

## 6. Database Backends

### Supported Graph Databases

| Database | Type | Notes |
|----------|------|-------|
| **Neo4j** | Primary | Default, most tested |
| **FalkorDB** | Alternative | Redis-compatible, fast |
| **Kuzu** | Embedded | Local/embedded use cases |
| **Amazon Neptune** | Cloud | Enterprise, requires OpenSearch |

**Source**: `graphiti_core/driver/` directory

### Driver Architecture

```python
# graphiti_core/driver/driver.py
class GraphProvider(Enum):
    NEO4J = 'neo4j'
    FALKORDB = 'falkordb'
    KUZU = 'kuzu'
    NEPTUNE = 'neptune'
```

---

## 7. LLM Integration

### Supported Providers

| Provider | Models |
|----------|--------|
| **OpenAI** | GPT-4o, GPT-4o-mini (default) |
| **Anthropic** | Claude 3.5 Sonnet |
| **Google** | Gemini 2.0 Flash |
| **Groq** | Fast inference |
| **Ollama** | Local models |
| **Azure OpenAI** | Enterprise |

**Source**: `graphiti_core/llm_client/` directory, CLAUDE.md (lines 136-173)

### LLM Usage in Pipeline

1. **Entity Extraction**: Extract entities from text
2. **Relationship Extraction**: Identify relationships between entities
3. **Deduplication**: Determine if extracted entities match existing ones
4. **Summarization**: Generate community summaries
5. **Cross-Encoder Reranking**: Score relevance of search results

---

## 8. MCP Server Integration

Graphiti provides an **MCP (Model Context Protocol) server** for integration with AI assistants like Claude and Cursor.

**Location**: `mcp_server/` directory

### MCP Capabilities

- Episode management (add, retrieve, delete)
- Entity and relationship handling
- Semantic and hybrid search
- Group management for multi-tenant data
- Graph maintenance operations

**Source**: README.md (lines 275-291)

---

## 9. Key Technical Specifications

| Metric | Value |
|--------|-------|
| **Query Latency** | Sub-second (typical) |
| **Supported Languages** | Python 3.10+ |
| **Default Embedding** | OpenAI text-embedding-3-small |
| **Concurrency Control** | SEMAPHORE_LIMIT env var (default: 10) |
| **Graph Databases** | Neo4j 5.26+, FalkorDB 1.1.2+, Kuzu 0.11.2+ |

---

## 10. Comparison with Other Memory Systems

| Feature | Graphiti | Mem0 | Letta |
|---------|----------|------|-------|
| **Memory Model** | Temporal knowledge graph | Vector + Graph dual storage | Three-tier (Core/Recall/Archival) |
| **Temporal Awareness** | Bi-temporal tracking | Basic timestamps | No explicit temporal model |
| **Update Strategy** | Incremental, real-time | Stateless extraction | Self-editing prompts |
| **Search Methods** | Hybrid (BM25 + Vector + BFS) | Vector similarity | Tool-based retrieval |
| **Contradiction Handling** | Edge invalidation | LLM resolution | Manual updates |
| **Best For** | Historical queries, evolving data | User profiles | Infinite context agents |

---

## 11. Key Takeaways

1. **Bi-Temporal Model**: Explicit tracking of both "when it happened" and "when we learned it" enables historical queries and contradiction handling

2. **Hybrid Retrieval**: Combines semantic search, keyword search (BM25), and graph traversal for optimal results

3. **Incremental Updates**: No batch recomputation - new data integrates in real-time

4. **Sub-Second Latency**: Designed for interactive AI applications

5. **Graph-Native**: Knowledge represented as entities and relationships, not just vector chunks

6. **Multiple Backends**: Supports Neo4j, FalkorDB, Kuzu, and Amazon Neptune

7. **MCP Integration**: Ready for use with Claude, Cursor, and other AI assistants

8. **LLM-Powered**: Uses LLMs for extraction, deduplication, summarization, and reranking

---

## References

### Documentation
- [Graphiti GitHub](https://github.com/getzep/graphiti)
- [Graphiti Documentation](https://help.getzep.com/graphiti)
- [Quick Start Guide](https://help.getzep.com/graphiti/graphiti/quick-start)

### Research
- [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956) - arXiv Paper

### Code References
- Main entry point: `graphiti_core/graphiti.py`
- Node definitions: `graphiti_core/nodes.py`
- Edge definitions: `graphiti_core/edges.py`
- Search system: `graphiti_core/search/`
- Database drivers: `graphiti_core/driver/`
- LLM clients: `graphiti_core/llm_client/`
