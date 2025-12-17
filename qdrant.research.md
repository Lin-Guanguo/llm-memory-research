# Qdrant Technical Research Report

Last Updated: 2025-12-18

> **Research Methodology**: Gemini CLI internet search + Qdrant official documentation (chrome-devtools)

## Overview

**Qdrant** is a high-performance, open-source vector database written in Rust. It specializes in storing, indexing, and searching high-dimensional vectors with associated metadata (payloads), making it ideal for AI/ML applications requiring similarity search.

**Key Innovation**: Filtrable HNSW index that extends the graph with payload-based edges, enabling efficient filtered vector search without sacrificing accuracy.

**Funding**: $37.8M total funding

**Source**: [Qdrant GitHub](https://github.com/qdrant/qdrant) | [Qdrant Documentation](https://qdrant.tech/documentation/)

---

## 1. Core Architecture

### Segment-Based Storage

Data within a collection is divided into **segments**, each with independent:
- Vector storage
- Payload storage
- Vector indexes
- Payload indexes
- ID mapper (internal ↔ external ID relationship)

```
Collection
├── Segment 1 (appendable)
│   ├── Vector Storage (In-memory or Memmap)
│   ├── Payload Storage (InMemory or OnDisk/RocksDB)
│   ├── HNSW Index
│   ├── Payload Indexes
│   └── ID Mapper
├── Segment 2 (non-appendable)
│   └── ...
└── Write-Ahead Log (WAL)
```

**Segment Types**:
- **Appendable**: Supports add, delete, and query operations
- **Non-appendable**: Read and delete only (optimized for search)

**Source**: [Storage Documentation](https://qdrant.tech/documentation/concepts/storage/)

---

## 2. Vector Storage Options

| Storage Type | Description | Use Case |
|--------------|-------------|----------|
| **In-memory** | All vectors in RAM, disk for persistence only | Highest speed, sufficient RAM |
| **Memmap** | Virtual address space mapped to disk file | Large datasets, uses page cache |

### Memmap Configuration

```http
PUT /collections/{collection_name}
{
    "vectors": {
      "size": 768,
      "distance": "Cosine",
      "on_disk": true
    },
    "hnsw_config": {
        "on_disk": true
    }
}
```

**Key Parameter**: `memmap_threshold` - segments convert to memmap after reaching this point count.

**Source**: [Storage Documentation](https://qdrant.tech/documentation/concepts/storage/#configuring-memmap-storage)

---

## 3. Indexing System

### 3.1 Vector Index (HNSW)

Qdrant uses **HNSW (Hierarchical Navigable Small World Graph)** exclusively for dense vector indexing.

**Architecture**:
- Multi-layer navigation structure
- Upper layers: sparse, long-distance connections
- Lower layers: dense, short-distance connections
- Search starts from top layer, iteratively descending

**Key Parameters**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `m` | 16 | Max edges per node (higher = more accurate, more memory) |
| `ef_construct` | 100 | Neighbors considered during build (higher = more accurate, slower build) |
| `ef` | = ef_construct | Search range (configurable per query) |
| `full_scan_threshold` | 10000 | Below this, full-scan preferred over HNSW |

```yaml
storage:
  hnsw_index:
    m: 16
    ef_construct: 100
    full_scan_threshold: 10000
```

**Source**: [Indexing Documentation](https://qdrant.tech/documentation/concepts/indexing/#vector-index)

### 3.2 Payload Index

Similar to document database indexes, built for specific fields to accelerate filtering:

| Type | Use Case | Filter Support |
|------|----------|----------------|
| `keyword` | String matching | Match |
| `integer` | Numeric values | Match, Range |
| `float` | Decimal values | Range |
| `bool` | Boolean values | Match |
| `geo` | Geographic coordinates | Geo Bounding Box, Geo Radius |
| `datetime` | Timestamps | Range |
| `text` | Full-text search | Full Text Match |
| `uuid` | UUID optimization | Match |

**Special Index Types**:
- **Tenant Index**: Optimizes multitenancy with `is_tenant: true`
- **Principal Index**: Optimizes time-based filtering with `is_principal: true`
- **On-disk Index**: Reduces memory with `on_disk: true`

**Source**: [Indexing Documentation](https://qdrant.tech/documentation/concepts/indexing/#payload-index)

### 3.3 Sparse Vector Index

For vectors with high proportion of zeros (like BM25 outputs):
- Exact search (no approximation)
- Similar to inverted index
- Supports IDF modifier for relevance ranking

```http
PUT /collections/{collection_name}
{
    "sparse_vectors": {
        "text": {
            "modifier": "idf",
            "index": { "on_disk": false }
        }
    }
}
```

**Source**: [Indexing Documentation](https://qdrant.tech/documentation/concepts/indexing/#sparse-vector-index)

### 3.4 Full-Text Index

For keyword search within string payloads:

**Tokenizers**:
- `word`: Split by spaces and punctuation
- `whitespace`: Split by spaces only
- `prefix`: Creates prefix index (h, he, hel, hell, hello)
- `multilingual`: Language-aware (charabia + vaporetto)

**Features**:
- Lowercasing (default on)
- ASCII folding (é → e)
- Stemming (Snowball algorithm)
- Stopwords filtering
- Phrase matching

```http
PUT /collections/{collection_name}/index
{
    "field_name": "content",
    "field_schema": {
        "type": "text",
        "tokenizer": "word",
        "lowercase": true,
        "phrase_matching": true,
        "stemmer": { "type": "snowball", "language": "english" }
    }
}
```

**Source**: [Indexing Documentation](https://qdrant.tech/documentation/concepts/indexing/#full-text-index)

### 3.5 Filtrable HNSW Index

**Key Innovation**: Extends HNSW graph with payload-based edges for efficient filtered search.

**Problem**: Standard HNSW fails with strict filters (graph becomes disconnected).

**Solution**:
1. Add extra edges based on payload values
2. Use ACORN Search Algorithm for complex filter combinations

**Source**: [Filtrable HNSW Article](https://qdrant.tech/articles/filtrable-hnsw/)

---

## 4. Hybrid Search Capabilities

### 4.1 Query API with Prefetch

Enables multi-stage and hybrid queries through nested `prefetch` operations:

```http
POST /collections/{collection_name}/points/query
{
    "prefetch": [
        { "query": {"indices": [1, 42], "values": [0.22, 0.8]}, "using": "sparse", "limit": 20 },
        { "query": [0.01, 0.45, 0.67, ...], "using": "dense", "limit": 20 }
    ],
    "query": { "fusion": "rrf" },
    "limit": 10
}
```

### 4.2 Fusion Methods

| Method | Description | Formula |
|--------|-------------|---------|
| **RRF** | Reciprocal Rank Fusion | score(d) = Σ 1/(k + rank) |
| **DBSF** | Distribution-Based Score Fusion | Normalizes using mean ± 3σ |

### 4.3 Multi-Stage Queries

Coarse-to-fine search strategies:
1. **Quantized → Full precision**: Use compressed vectors first, refine with full vectors
2. **MRL (Matryoshka)**: Short vector candidates, long vector refinement
3. **Dense → Multi-vector**: Dense pre-fetch, ColBERT re-ranking

```http
POST /collections/{collection_name}/points/query
{
    "prefetch": {
        "query": [1, 23, 45, 67],  // small byte vector
        "using": "mrl_byte",
        "limit": 1000
    },
    "query": [0.01, 0.299, 0.45, 0.67, ...],  // full vector
    "using": "full",
    "limit": 10
}
```

### 4.4 Additional Query Features

| Feature | Description | Version |
|---------|-------------|---------|
| **MMR** | Maximal Marginal Relevance for diversity | v1.15.0+ |
| **Score Boosting** | Custom formulas with payload values | v1.14.0+ |
| **Time Decay** | exp_decay, gauss_decay, lin_decay functions | v1.14.0+ |
| **Grouping** | Group results by payload field | v1.11.0+ |

**Source**: [Hybrid Queries Documentation](https://qdrant.tech/documentation/concepts/hybrid-queries/)

---

## 5. Data Integrity

### Write-Ahead Log (WAL)

All changes written to WAL before segments:
1. Operations assigned sequential numbers
2. Segments store last applied version
3. Per-point version tracking
4. Safe recovery from abnormal shutdown

**Source**: [Storage Documentation](https://qdrant.tech/documentation/concepts/storage/#versioning)

---

## 6. Distributed Architecture

### Raft Consensus

For cluster coordination and consistency:
- Leader election
- Log replication
- Fault tolerance

### Sharding & Replication

| Feature | Description |
|---------|-------------|
| **Sharding** | Horizontal data partitioning |
| **Replication** | Multiple copies for fault tolerance |
| **Consistent Hashing** | Even data distribution |

**Source**: [Distributed Deployment Guide](https://qdrant.tech/documentation/guides/distributed_deployment/)

---

## 7. Vector Quantization

Reduces memory footprint and improves search speed:

| Method | Description | Trade-off |
|--------|-------------|-----------|
| **Scalar Quantization** | Float32 → Int8 | 4x compression, minimal accuracy loss |
| **Product Quantization (PQ)** | Vector → subspace codes | Higher compression, more accuracy loss |
| **Binary Quantization** | Float → 1-bit | Maximum compression |

**Source**: [Vector Quantization Article](https://qdrant.tech/articles/what-is-vector-quantization/)

---

## 8. 2025 Features & Ecosystem

### Recent Updates

| Feature | Version | Description |
|---------|---------|-------------|
| **Sparse Vectors** | v1.7.0+ | Native sparse vector support with IDF |
| **Hybrid Queries** | v1.10.0+ | Prefetch-based multi-stage queries |
| **Tenant Index** | v1.11.0+ | Multitenancy optimization |
| **Score Boosting** | v1.14.0+ | Custom ranking formulas |
| **MMR** | v1.15.0+ | Diversity in results |
| **Parametrized RRF** | v1.16.0+ | Configurable fusion constant |

### Ecosystem

| Component | Description |
|-----------|-------------|
| **FastEmbed** | Lightweight embedding library |
| **Qdrant MCP Server** | Model Context Protocol integration |
| **Qdrant Cloud** | Managed service with free tier |
| **Web UI** | Built-in data exploration interface |

---

## 9. Comparison with Other Vector Databases

| Feature | Qdrant | Chroma | Weaviate | Milvus |
|---------|--------|--------|----------|--------|
| **Language** | Rust | Rust (v1.0) | Go | Go |
| **Index** | HNSW only | HNSW | HNSW + Flat | IVF, HNSW, DiskANN |
| **Sparse Vectors** | Native | No | No | Yes |
| **Hybrid Search** | RRF, DBSF | No | BM25 + Vector | Yes |
| **Filtering** | Pre-filtering (Filtrable HNSW) | Post-filtering | Pre-filtering | Post-filtering |
| **Quantization** | Scalar, PQ, Binary | No | PQ, BQ | Various |
| **Multitenancy** | Native (Tenant Index) | No | Native | Partition-based |

---

## 10. Key Technical Specifications

| Metric | Value |
|--------|-------|
| **Language** | Rust |
| **Vector Index** | HNSW (single algorithm, highly optimized) |
| **Distance Metrics** | Cosine, Dot Product, Euclidean, Manhattan |
| **Max Dimensions** | Unlimited (practical limit by memory) |
| **Persistence** | WAL + Snapshots |
| **Storage Options** | In-memory, Memmap, On-disk |
| **SDKs** | Python, TypeScript, Rust, Go, Java, C# |

---

## 11. Key Takeaways

1. **Filtrable HNSW**: Unique approach to filtered vector search by extending HNSW with payload-based edges

2. **Rust Performance**: Written in Rust for memory safety and performance

3. **Flexible Storage**: In-memory for speed, Memmap for scale, configurable per collection

4. **Hybrid Search**: Native support for combining dense + sparse vectors with RRF/DBSF fusion

5. **Multi-Stage Queries**: Prefetch architecture enables coarse-to-fine search patterns

6. **Production-Ready**: WAL for durability, Raft for distributed consensus, quantization for scale

7. **Multitenancy**: Native tenant index optimization for SaaS applications

8. **Full-Text Search**: Built-in tokenization, stemming, and phrase matching

9. **Score Boosting**: Custom ranking formulas using payload values and decay functions

10. **MCP Integration**: Official MCP server for AI agent integration

---

## References

### Documentation
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Concepts Overview](https://qdrant.tech/documentation/concepts/)
- [Indexing](https://qdrant.tech/documentation/concepts/indexing/)
- [Storage](https://qdrant.tech/documentation/concepts/storage/)
- [Hybrid Queries](https://qdrant.tech/documentation/concepts/hybrid-queries/)

### Technical Articles
- [Filtrable HNSW](https://qdrant.tech/articles/filtrable-hnsw/)
- [Vector Quantization](https://qdrant.tech/articles/what-is-vector-quantization/)

### Market Data
- GitHub Stars: 27.7k+
- Funding: $37.8M
- Recognition: 2025 AI TechAward
