"""
mem0 configuration for personal knowledge base.
"""

import os
from pathlib import Path

# Data directory for local storage
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Default user ID for the knowledge base
DEFAULT_USER_ID = "knowledge_base_user"


def get_mem0_config() -> dict:
    """
    Get mem0 configuration.

    Supports OpenRouter via OPENROUTER_API_KEY environment variable.
    Falls back to OpenAI if OPENAI_API_KEY is set.
    Uses HuggingFace local embeddings by default.
    """
    config = {
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "knowledge_base",
                "path": str(DATA_DIR / "chroma"),
            }
        },
        "history_db_path": str(DATA_DIR / "history.db"),
    }

    # Configure LLM and Embedder based on available API keys
    # mem0 auto-detects OPENROUTER_API_KEY and uses OpenRouter for LLM
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        config["llm"] = {
            "provider": "openai",
            "config": {
                "model": os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
                "temperature": 0.1,
                "max_tokens": 2000,
            }
        }
        config["embedder"] = {
            "provider": "openai",
            "config": {
                "model": os.environ.get("OPENROUTER_EMBED_MODEL", "openai/text-embedding-3-small"),
                "api_key": openrouter_key,
                "openai_base_url": "https://openrouter.ai/api/v1",
            }
        }
    elif os.environ.get("OPENAI_API_KEY"):
        config["llm"] = {
            "provider": "openai",
            "config": {
                "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                "temperature": 0.1,
                "max_tokens": 2000,
            }
        }
        # OpenAI embedder uses OPENAI_API_KEY from env by default

    return config
