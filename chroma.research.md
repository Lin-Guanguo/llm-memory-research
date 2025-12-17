# Chroma Technical Research Report

Last Updated: 2025-12-18

> **Research Methodology**: Chroma official documentation (chrome-devtools) + Gemini CLI internet search

## Overview

**Chroma** is an open-source AI application database designed to make building LLM applications easy by providing pluggable knowledge, facts, and skills for LLMs. It emphasizes developer experience with zero-config setup and seamless scaling from local development to production.

**Key Innovation**: Modular architecture with pluggable embedding functions and write-ahead log design that scales from embedded library to distributed system.

**Funding**: $36M (Series A, 2023)

**Source**: [Chroma Documentation](https://docs.trychroma.com) | [Chroma GitHub](https://github.com/chroma-core/chroma)

---

## 1. Core Architecture

### Five Core Components

Chroma is composed of five core components that operate over a shared data model:

```
┌─────────────────────────────────────────────────────────┐
│                       Gateway                           │
│  (API, Auth, Rate Limiting, Quota, Request Validation)  │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │   Log    │    │  Query   │    │ System   │
    │  (WAL)   │    │ Executor │    │ Database │
    └──────────┘    └──────────┘    └──────────┘
          │               │
          └───────┬───────┘
                  ▼
           ┌──────────┐
           │Compactor │
           │(Indexing)│
           └──────────┘
```

| Component | Description |
|-----------|-------------|
| **Gateway** | API entrypoint, handles auth, rate-limiting, quota management, request validation |
| **Log** | Write-ahead log for durability, ensures atomicity across multi-record writes |
| **Query Executor** | Handles all read operations (vector, full-text, metadata search) |
| **Compactor** | Periodically builds and maintains indexes from the Log |
| **System Database** | Internal catalog tracking tenants, collections, cluster state |

**Source**: [Architecture Documentation](https://docs.trychroma.com/docs/overview/architecture)

---

## 2. Deployment Modes

| Mode | Description | Scale |
|------|-------------|-------|
| **Local** | Embedded library in Python | Prototyping, < 1M records |
| **Single Node** | Standalone server | Small-medium, < 10M records |
| **Distributed** | Scalable cluster (Chroma Cloud) | Millions of collections |

### Storage by Mode

| Mode | Storage | Runtime |
|------|---------|---------|
| Local/Single Node | Local filesystem | Single process |
| Distributed | Cloud object storage + SSD cache | Independent services |

**Source**: [Architecture Documentation](https://docs.trychroma.com/docs/overview/architecture#deployment-modes)

---

## 3. Rust v1.0 Rewrite (2025)

### Performance Improvements

The migration to a pure Rust core was completed in early 2025:

| Metric | Improvement |
|--------|-------------|
| Query throughput | 3-5x faster |
| Write latency | 3-5x faster |
| Concurrency | True multithreading (no Python GIL) |

### Segment-Based Architecture

Data is organized into specialized segments:

| Segment | Contents |
|---------|----------|
| **Vector Segment** | HNSW graph + raw vectors |
| **Metadata Segment** | Key-value metadata (SQLite/DuckDB) |

### Data Tiering

- **Hot segments**: Cached in memory/NVMe for active queries
- **Cold segments**: Offloaded to object storage (S3/GCS)
- Enables infinite scaling of dormant data

### Language Bindings

The Rust core (`chroma-core`) provides native bindings for:
- Python
- JavaScript/TypeScript
- Go
- Ruby

**Source**: Gemini CLI internet search (Dec 2025)

---

## 4. Vector Indexing (HNSW)

Chroma uses **HNSW (Hierarchical Navigable Small World)** for approximate nearest neighbor search. The Rust v1.0 implementation is lock-free and multithreaded.

### HNSW Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `space` | `l2` | Distance function: `l2`, `cosine`, `ip` |
| `ef_construction` | 100 | Candidate list size during index build |
| `ef_search` | 100 | Dynamic candidate list during search (modifiable) |
| `max_neighbors` | 16 | Max connections per node (like `m` in Qdrant) |
| `num_threads` | CPU count | Threads for index operations (modifiable) |
| `batch_size` | 100 | Vectors per batch (modifiable) |
| `sync_threshold` | 1000 | When to sync with storage (modifiable) |
| `resize_factor` | 1.2 | Index growth multiplier (modifiable) |

### Distance Functions

| Distance | Parameter | Use Case |
|----------|-----------|----------|
| Squared L2 | `l2` | Spatial proximity |
| Inner Product | `ip` | Recommendation systems |
| Cosine Similarity | `cosine` | Text embeddings (direction-focused) |

### Configuration Example

```python
collection = client.create_collection(
    name="my-collection",
    embedding_function=OpenAIEmbeddingFunction(model_name="text-embedding-3-small"),
    configuration={
        "hnsw": {
            "space": "cosine",
            "ef_construction": 200
        }
    }
)
```

**Source**: [Configure Documentation](https://docs.trychroma.com/docs/collections/configure)

---

## 4. Search Capabilities

### 4.1 Vector Similarity Search

```python
results = collection.query(
    query_embeddings=[[0.1, 0.2, ...]],
    n_results=10
)
```

### 4.2 Full-Text Search

Operators for document content filtering:

| Operator | Description |
|----------|-------------|
| `$contains` | Document contains string |
| `$not_contains` | Document doesn't contain string |
| `$regex` | Regex pattern match |
| `$not_regex` | Regex pattern doesn't match |

```python
collection.get(
    where_document={"$contains": "search string"}
)

# Regex example
collection.get(
    where_document={
        "$regex": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    }
)
```

**Note**: Full-text search is case-sensitive.

### 4.3 Metadata Filtering

Filter by arbitrary metadata fields:

```python
collection.query(
    query_texts=["query"],
    n_results=10,
    where={"metadata_field": "value"},
    where_document={"$contains": "search_string"}
)
```

### 4.4 Logical Operators

```python
# AND - all conditions must match
where_document={
    "$and": [
        {"$contains": "string_1"},
        {"$regex": "[a-z]+"}
    ]
}

# OR - any condition matches
where_document={
    "$or": [
        {"$contains": "string_1"},
        {"$not_contains": "string_2"}
    ]
}
```

**Source**: [Full Text Search Documentation](https://docs.trychroma.com/docs/querying-collections/full-text-search)

---

## 5. Embedding Functions

Chroma supports pluggable embedding functions that persist in collection configuration.

### Built-in Providers

| Provider | Package | Environment Variable |
|----------|---------|----------------------|
| OpenAI | `chromadb` | `OPENAI_API_KEY` |
| Cohere | `cohere` | `COHERE_API_KEY` |
| HuggingFace | `sentence-transformers` | - |
| Google | `google-generativeai` | `GOOGLE_API_KEY` |
| Ollama | - | - (local) |

### Configuration

```python
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

collection = client.create_collection(
    name="my_collection",
    embedding_function=OpenAIEmbeddingFunction(
        model_name="text-embedding-3-small"
    )
)
```

### Custom Environment Variables

```python
cohere_ef = CohereEmbeddingFunction(
    api_key_env_var="MY_CUSTOM_COHERE_API_KEY",
    model_name="embed-english-light-v2.0"
)
```

**Source**: [Embedding Functions Documentation](https://docs.trychroma.com/docs/embeddings/embedding-functions)

---

## 6. Data Model

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Collection** | Named container for embeddings and documents |
| **Document** | Raw text stored alongside embedding |
| **Embedding** | Vector representation of document |
| **Metadata** | Arbitrary key-value pairs for filtering |
| **ID** | Unique identifier for each record |

### Record Structure

```python
collection.add(
    ids=["id1", "id2"],
    documents=["doc1", "doc2"],
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    metadatas=[{"key": "value1"}, {"key": "value2"}]
)
```

---

## 7. Write Path & Read Path

### Write Path

1. Request arrives at Gateway (auth, validation)
2. Operations forwarded to Write-Ahead Log (WAL)
3. Gateway acknowledges after WAL persistence
4. Compactor periodically builds indexes from WAL
5. New indexes written to storage, registered in System Database

### Read Path

1. Request arrives at Gateway
2. Routed to Query Executor (via rendezvous hash in distributed mode)
3. Query Executor transforms logical plan to physical plan
4. Pulls data from Log for consistent read
5. Results returned through Gateway

**Source**: [Architecture Documentation](https://docs.trychroma.com/docs/overview/architecture#request-sequences)

---

## 8. Client SDKs

### Official Clients

| Language | Package | Maintained By |
|----------|---------|---------------|
| Python | `chromadb` | Chroma |
| JavaScript/TypeScript | `chromadb` | Chroma |
| Rust | `chroma` | Chroma |

### Community Clients

Ruby, Java, Go, C#/.NET, Elixir, Dart, PHP, Clojure, R, C++

**Source**: [Introduction Documentation](https://docs.trychroma.com/docs/overview/introduction#language-clients)

---

## 9. Comparison with Other Vector Databases

| Feature | Chroma | Qdrant | Pinecone |
|---------|--------|--------|----------|
| **Open Source** | Yes (Apache 2.0) | Yes (Apache 2.0) | No |
| **Language** | Python + Rust | Rust | Managed |
| **Vector Index** | HNSW | HNSW | Proprietary |
| **Embedding Functions** | Built-in pluggable | External | External |
| **Full-Text Search** | $contains, $regex | Built-in tokenizers | No |
| **Hybrid Search** | Vector + FTS + Metadata | RRF/DBSF fusion | Metadata filtering |
| **Sparse Vectors** | No | Yes | Yes |
| **Local Mode** | Yes (embedded) | Yes (Docker) | No |
| **Managed Cloud** | Chroma Cloud | Qdrant Cloud | Pinecone |

### Key Differentiators

| Aspect | Chroma | Qdrant |
|--------|--------|--------|
| **Philosophy** | Developer Experience (DX) first | Scale/Performance first |
| **Filtering** | Pre-filtering (metadata lookup → vector search) | Filterable HNSW (integrated into graph traversal) |
| **Architecture** | Segment-based, serverless-native | Service-based, cluster-native (Raft) |
| **Embedding** | Built-in pluggable functions | External embedding required |
| **Best For** | Rapid prototyping, RAG apps | High-QPS production, strict latency SLAs |

---

## 10. Key Technical Specifications

| Metric | Value |
|--------|-------|
| **Primary Language** | Python + Rust (core) |
| **Vector Index** | HNSW |
| **Distance Metrics** | L2, Cosine, Inner Product |
| **Storage** | SQLite (local), Object Storage (distributed) |
| **WAL** | Built-in for durability |
| **SDKs** | Python, TypeScript, Rust (official) |
| **License** | Apache 2.0 |

---

## 11. Key Takeaways

1. **Developer Experience First**: Zero-config setup, embedded library mode for rapid prototyping

2. **Pluggable Embedding Functions**: Built-in support for OpenAI, Cohere, HuggingFace with configuration persistence

3. **Modular Architecture**: Five components (Gateway, Log, Query Executor, Compactor, System Database) scale independently

4. **Write-Ahead Log**: All writes recorded before acknowledgment, ensures durability and atomicity

5. **HNSW Indexing**: Standard approximate nearest neighbor with configurable parameters

6. **Full-Text Search**: Simple operators ($contains, $regex) for document filtering

7. **Distributed Mode**: Scales to millions of collections with object storage backend and SSD caching

8. **Multi-Language Support**: Official Python, TypeScript, Rust clients plus extensive community clients

9. **Seamless Scaling**: Same API from local development to distributed production

10. **No Sparse Vectors**: Unlike Qdrant, Chroma doesn't support sparse vector search (as of 2025)

---

## References

### Documentation
- [Chroma Introduction](https://docs.trychroma.com/docs/overview/introduction)
- [Architecture](https://docs.trychroma.com/docs/overview/architecture)
- [Configure Collections](https://docs.trychroma.com/docs/collections/configure)
- [Full Text Search](https://docs.trychroma.com/docs/querying-collections/full-text-search)
- [Embedding Functions](https://docs.trychroma.com/docs/embeddings/embedding-functions)

### Market Data
- GitHub Stars: ~25k
- Funding: $36M Series A
- Twitter: 22.7k followers
