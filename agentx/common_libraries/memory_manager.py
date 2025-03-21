"""Memory management system for AgentX."""

import os
from typing import Any, Dict, List, Optional
import structlog
from datetime import datetime

from agentx.common_libraries.db_manager import db_manager

logger = structlog.get_logger()

class MemoryManager:
    """Manages memory operations for agents."""
    
    def __init__(self, persist_directory: str = "data/memory/vectors"):
        """Initialize the memory manager.
        
        Args:
            persist_directory: Directory to persist the database
        """
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB client using the global database manager
        self.client = db_manager.initialize(
            os.path.join(persist_directory, "chroma")
        )
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="agent_memory",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.logger = logger.bind(component="memory_manager")
        
    async def add_interaction(self, interaction: Dict[str, Any]) -> None:
        """Add an interaction to memory.
        
        Args:
            interaction: Interaction data to store
        """
        try:
            # Add to vector memory for semantic search
            self.collection.add(
                documents=[str(interaction)],
                metadatas=[{
                    "type": "interaction",
                    "timestamp": str(datetime.now())
                }],
                ids=[f"interaction_{len(self.collection.get()['ids'])}"]
            )
            
            self.logger.info("Added interaction to memory")
            
        except Exception as e:
            self.logger.error("Error adding interaction to memory", error=str(e))
    
    async def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar interactions.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List of similar interactions
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            return [
                {
                    "content": doc,
                    "metadata": meta,
                    "id": id
                }
                for doc, meta, id in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["ids"][0]
                )
            ]
            
        except Exception as e:
            self.logger.error("Error searching memory", error=str(e))
            return []
    
    async def get_recent_interactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent interactions.
        
        Args:
            limit: Maximum number of interactions to return
            
        Returns:
            List of recent interactions
        """
        try:
            results = self.collection.get(
                limit=limit,
                order_by=["timestamp"],
                order=["desc"]
            )
            
            return [
                {
                    "content": doc,
                    "metadata": meta,
                    "id": id
                }
                for doc, meta, id in zip(
                    results["documents"],
                    results["metadatas"],
                    results["ids"]
                )
            ]
            
        except Exception as e:
            self.logger.error("Error getting recent interactions", error=str(e))
            return []
    
    async def get_conversation_context(self, limit: int = 5) -> str:
        """Get conversation context.
        
        Args:
            limit: Maximum number of interactions to include
            
        Returns:
            Formatted conversation context
        """
        try:
            interactions = await self.get_recent_interactions(limit)
            
            context = []
            for interaction in interactions:
                context.append(f"{interaction['metadata']['timestamp']}: {interaction['content']}")
            
            return "\n".join(context)
            
        except Exception as e:
            self.logger.error("Error getting conversation context", error=str(e))
            return ""
    
    async def cleanup(self) -> None:
        """Clean up memory resources."""
        try:
            self.client.persist()
        except Exception as e:
            self.logger.error("Error during memory cleanup", error=str(e)) 