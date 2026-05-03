"""ChromaDB client implementation."""

import chromadb
from chromadb.config import Settings
from pathlib import Path
import structlog

logger = structlog.get_logger()
_client = None

def get_chroma_client(persist_directory: str) -> chromadb.Client:
    """Get or create a ChromaDB client.
    
    Args:
        persist_directory: Directory to persist ChromaDB data
        
    Returns:
        ChromaDB client instance
    """
    global _client
    
    if _client is None:
        # Ensure directory exists
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        try:
            # Create client with persistence
            _client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
            )
            logger.info("ChromaDB client initialized", persist_directory=persist_directory)
        except Exception as e:
            logger.error("Failed to initialize ChromaDB client", error=str(e))
            raise
    
    return _client

def reset_chroma_client() -> None:
    """Reset the ChromaDB client."""
    global _client
    
    if _client is not None:
        try:
            # Get all collections
            collections = _client.list_collections()
            
            # Delete each collection
            for collection in collections:
                try:
                    _client.delete_collection(collection.name)
                    logger.info("Deleted collection", name=collection.name)
                except Exception as e:
                    logger.error("Failed to delete collection", collection=collection.name, error=str(e))
            
            # Reset the client reference
            _client = None
            logger.info("ChromaDB client reset")
            
        except Exception as e:
            logger.error("Failed to reset ChromaDB client", error=str(e))
        finally:
            # Ensure client is reset even if there's an error
            _client = None 