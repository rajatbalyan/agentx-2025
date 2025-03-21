"""Global database management for AgentX."""

import os
from typing import Optional
import chromadb
from chromadb.config import Settings

class DBManager:
    """Global database manager for AgentX."""
    
    _instance: Optional['DBManager'] = None
    _chroma_client: Optional[chromadb.Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._chroma_client is None:
            # Initialize with default settings
            self._chroma_client = None
    
    def initialize(self, persist_directory: str) -> chromadb.Client:
        """Initialize the ChromaDB client.
        
        Args:
            persist_directory: Directory to persist the database
            
        Returns:
            ChromaDB client instance
        """
        if self._chroma_client is None:
            # Ensure the persist directory exists
            os.makedirs(persist_directory, exist_ok=True)
            
            # Create the client with consistent settings
            self._chroma_client = chromadb.Client(Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False
            ))
        
        return self._chroma_client
    
    def get_client(self) -> Optional[chromadb.Client]:
        """Get the current ChromaDB client.
        
        Returns:
            Current ChromaDB client instance or None if not initialized
        """
        return self._chroma_client
    
    def reset(self):
        """Reset the ChromaDB client."""
        self._chroma_client = None

# Create a global instance
db_manager = DBManager() 