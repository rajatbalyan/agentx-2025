from typing import Dict, Any, List, Optional
from langmem import Memory, VectorMemory, ConversationMemory
from langmem.store import ChromaStore
from langmem.embeddings import GeminiEmbeddings
import google.generativeai as genai
from datetime import datetime
import os
import json

class MemoryManager:
    """Manages different types of memory for agents using LangMem"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        
        # Initialize Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.embeddings = GeminiEmbeddings()
        
        # Create memory storage directory
        self.storage_path = f"data/memory/{agent_name}"
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Initialize vector memory with ChromaDB
        self.vector_store = ChromaStore(
            collection_name=f"{agent_name}_vectors",
            persist_directory=self.storage_path
        )
        
        # Initialize different types of memory
        self.conversation_memory = ConversationMemory(
            buffer_size=1000,  # Store last 1000 interactions
            storage_path=os.path.join(self.storage_path, "conversations")
        )
        
        self.vector_memory = VectorMemory(
            store=self.vector_store,
            embeddings=self.embeddings
        )
        
        # Combined memory manager
        self.memory = Memory(
            conversation=self.conversation_memory,
            vector=self.vector_memory
        )
    
    async def add_interaction(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any]
    ) -> None:
        """Store an interaction in both conversation and vector memory"""
        timestamp = datetime.now().isoformat()
        
        # Create memory entry
        memory_entry = {
            "timestamp": timestamp,
            "input": input_data,
            "output": output_data,
            "type": "interaction"
        }
        
        # Add to conversation memory
        await self.conversation_memory.add(memory_entry)
        
        # Add to vector memory with metadata
        await self.vector_memory.add(
            text=json.dumps(memory_entry),
            metadata={
                "timestamp": timestamp,
                "type": "interaction",
                "agent": self.agent_name
            }
        )
    
    async def add_document(
        self,
        document: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store a document in vector memory"""
        metadata = metadata or {}
        metadata.update({
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_name
        })
        
        await self.vector_memory.add(
            text=json.dumps(document),
            metadata=metadata
        )
    
    async def search_similar_interactions(
        self,
        query: str,
        k: int = 5,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar past interactions"""
        results = await self.vector_memory.search(
            query=query,
            k=k,
            filter_criteria=filter_criteria
        )
        
        return [
            {
                "content": json.loads(result.text),
                "score": result.score,
                "metadata": result.metadata
            }
            for result in results
        ]
    
    async def get_recent_interactions(
        self,
        k: int = 5,
        filter_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get the most recent interactions"""
        interactions = await self.conversation_memory.get_recent(k)
        
        if filter_type:
            interactions = [
                i for i in interactions
                if i.get("type") == filter_type
            ]
        
        return interactions
    
    async def get_conversation_context(
        self,
        window_size: int = 5
    ) -> str:
        """Get recent conversation context for LLM prompts"""
        recent = await self.get_recent_interactions(window_size)
        context = []
        
        for interaction in recent:
            context.append(f"User: {json.dumps(interaction['input'])}")
            context.append(f"Assistant: {json.dumps(interaction['output'])}")
        
        return "\n".join(context)
    
    async def save(self) -> None:
        """Save all memory to disk"""
        await self.conversation_memory.save()
        await self.vector_memory.save()
    
    async def load(self) -> None:
        """Load all memory from disk"""
        try:
            await self.conversation_memory.load()
            await self.vector_memory.load()
        except Exception as e:
            print(f"Error loading memory: {str(e)}")
    
    async def clear(self) -> None:
        """Clear all memory"""
        await self.conversation_memory.clear()
        await self.vector_memory.clear()
        
        # Remove persistent storage
        import shutil
        shutil.rmtree(self.storage_path, ignore_errors=True)
        os.makedirs(self.storage_path, exist_ok=True) 