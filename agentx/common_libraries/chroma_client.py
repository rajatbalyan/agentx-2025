"""Shared ChromaDB client for AgentX."""

import os
from typing import Optional
import chromadb
from chromadb.config import Settings

# Global ChromaDB client instance
_chroma_client: Optional[chromadb.Client] = None
_persist_directory: Optional[str] = None

def get_chroma_client(persist_directory: str) -> chromadb.Client:
    """Get or create a ChromaDB client instance.
    
    Args:
        persist_directory: Directory to persist the database
        
    Returns:
        ChromaDB client instance
    """
    global _chroma_client, _persist_directory
    
    # If we already have a client with a different directory, reset it
    if _chroma_client is not None and _persist_directory != persist_directory:
        reset_chroma_client()
    
    if _chroma_client is None:
        # Ensure the persist directory exists
        os.makedirs(persist_directory, exist_ok=True)
        _persist_directory = persist_directory
        
        # Create the client with consistent settings
        _chroma_client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
    
    return _chroma_client

def reset_chroma_client():
    """Reset the ChromaDB client. Use this for testing or when you need to change settings."""
    global _chroma_client, _persist_directory
    
    # If we have an existing client, try to close it
    if _chroma_client is not None:
        try:
            _chroma_client._settings.allow_reset = True
            _chroma_client.reset()
        except Exception:
            pass
    
    _chroma_client = None
    _persist_directory = None 