# Personal Knowledge Base Demo

A CLI tool for building a personal knowledge base using [mem0](https://github.com/mem0ai/mem0).

## Features

- Add text files (.txt, .md) to knowledge base
- Semantic search across stored knowledge
- List and manage memories
- Local storage with ChromaDB
- Supports OpenRouter and OpenAI

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure API keys:

```bash
cp .env.example .env
# Edit .env and add your API key
```

**OpenRouter** (recommended):
```
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_EMBED_MODEL=openai/text-embedding-3-small
```

**OpenAI**:
```
OPENAI_API_KEY=your_key_here
```

## Usage

### Using Makefile (recommended)

```bash
make help                              # Show available commands
make install                           # Install dependencies
make add FILE=path/to/file.md          # Add a file
make search Q="your query"             # Search
make list                              # List all memories
make clear                             # Clear all memories
```

### Using Python directly

```bash
python main.py add path/to/file.md
python main.py search "your query"
python main.py search "your query" -n 10  # limit results
python main.py list
python main.py list -n 20                 # limit results
python main.py clear
python main.py clear -f                   # skip confirmation
```

## Architecture

```
knowledge-base/
├── main.py              # CLI entry point
├── config.py            # mem0 configuration
├── knowledge_base.py    # Core operations
├── file_processor.py    # File reading and chunking
├── data/                # Local storage (auto-created)
│   └── chroma/          # ChromaDB data
└── .env                 # API keys (not committed)
```

## How it works

1. **Add**: Files are read, split into paragraphs, and each paragraph is stored as a memory in mem0
2. **Search**: Query is embedded and matched against stored memories using vector similarity
3. **Storage**: ChromaDB stores embeddings locally, no external database needed

## Configuration

See `config.py` for configuration options:

- `DATA_DIR`: Local storage directory
- `DEFAULT_USER_ID`: User ID for memories
- LLM and Embedder settings via environment variables
