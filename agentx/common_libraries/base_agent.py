"""Base agent class for all specialized agents."""

import asyncio
import os
from typing import Any, Dict, List, Optional
import structlog
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime

from agentx.common_libraries.memory_manager import MemoryManager
from agentx.common_libraries.system_config import SystemConfig
from agentx.common_libraries.db_manager import db_manager
from .code_indexer import CodeIndexer

logger = structlog.get_logger()

class AgentResponse(BaseModel):
    """Response model for agent outputs."""
    status: str
    result: str
    error: Optional[str] = None

class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str
    description: str
    enabled: bool = True
    max_retries: int = 3
    timeout: int = 300
    temperature: float = 0.7
    max_tokens: int = 1000

class BaseAgent:
    """Base class for all specialized agents."""
    
    def __init__(
        self,
        config: AgentConfig,
        system_config: SystemConfig,
        memory_manager: Optional[MemoryManager] = None
    ):
        """Initialize the agent."""
        self.config = config
        self.system_config = system_config
        self.memory_manager = memory_manager or MemoryManager()
        
        # Initialize ChromaDB client using the global database manager
        self.chroma_client = db_manager.initialize(
            os.path.join(system_config.memory.vector_store_path, "vectors", "chroma")
        )
        
        # Initialize the collection for this agent
        self.collection = self.chroma_client.get_or_create_collection(
            name=f"{self.config.name}_memory"
        )
        
        # Get API key from system config
        api_key = self.system_config.api_keys.get('google_api_key')
        if not api_key:
            raise ValueError("Google API key not found in system configuration")
        
        # Initialize the LLM with API key from system config
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=api_key,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens,
            convert_system_message_to_human=True
        )
        
        # Initialize output parser
        self.output_parser = PydanticOutputParser(pydantic_object=AgentResponse)
        
        # Initialize prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant."),
            ("human", "{input}")
        ])
        
        self.logger = logger.bind(agent=self.config.name)
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the input data."""
        try:
            # Add to memory
            self.collection.add(
                documents=[str(input_data)],
                metadatas=[{"type": "input", "timestamp": str(datetime.now())}],
                ids=[f"input_{len(self.collection.get()['ids'])}"]
            )
            
            # Process the input
            messages = self.prompt.format_messages(
                task_description=self.config.description,
                input=str(input_data)
            )
            
            response = await self.llm.ainvoke(messages)
            
            # Add response to memory
            self.collection.add(
                documents=[response.content],
                metadatas=[{"type": "response", "timestamp": str(datetime.now())}],
                ids=[f"response_{len(self.collection.get()['ids'])}"]
            )
            
            return {"status": "success", "result": response.content}
            
        except Exception as e:
            logger.error("Error processing input", error=str(e))
            return {"status": "error", "error": str(e)}
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            # Persist memory
            self.chroma_client.persist()
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

    async def initialize(self) -> None:
        """Initialize the agent and index codebase."""
        if hasattr(self, 'code_indexer'):
            await self.code_indexer.index_codebase()

    def health_check(self) -> bool:
        """Check if the agent is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return True

    async def store_interaction(self, interaction: Dict[str, Any]) -> None:
        """Store an interaction in memory.
        
        Args:
            interaction: Interaction data to store
        """
        try:
            await self.memory_manager.add_interaction(interaction)
            self.logger.info("Interaction stored in memory")
        except Exception as e:
            self.logger.error("Error storing interaction", error=str(e))
            raise

    async def get_similar_interactions(self, task: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """Get similar past interactions.
        
        Args:
            task: Current task
            limit: Maximum number of interactions to return
            
        Returns:
            List of similar interactions
        """
        if hasattr(self, 'memory'):
            return await self.memory.search_similar(task, limit=limit)
        return []

    async def analyze_code_changes(self, task_description: str) -> Dict[str, Any]:
        """Analyze potential code changes for a task.
        
        Args:
            task_description: Description of the task
            
        Returns:
            Analysis results including suggested changes
        """
        if not hasattr(self, 'code_indexer'):
            return {"error": "Code indexer not initialized"}
            
        try:
            # Get modification suggestions
            suggestions = await self.code_indexer.suggest_modification_points(
                task_description
            )
            
            # Get similar past changes from memory
            similar_changes = await self.get_similar_interactions({
                "type": "code_change",
                "description": task_description
            })
            
            # Analyze impact and risk
            analysis = {
                "suggestions": suggestions,
                "similar_changes": similar_changes,
                "impact_analysis": {
                    "high_impact_changes": [
                        s for s in suggestions
                        if s["impact_score"] > 5
                    ],
                    "low_risk_changes": [
                        s for s in suggestions
                        if s["impact_score"] <= 2
                    ]
                },
                "recommended_approach": self._recommend_change_approach(
                    suggestions,
                    similar_changes
                )
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error("Error analyzing code changes", error=str(e))
            return {"error": str(e)}

    def _recommend_change_approach(
        self,
        suggestions: List[Dict[str, Any]],
        similar_changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Recommend an approach for implementing changes.
        
        Args:
            suggestions: List of change suggestions
            similar_changes: List of similar past changes
            
        Returns:
            Recommended approach
        """
        # Sort changes by risk and impact
        high_risk = [s for s in suggestions if s["impact_score"] > 5]
        low_risk = [s for s in suggestions if s["impact_score"] <= 2]
        medium_risk = [s for s in suggestions if 2 < s["impact_score"] <= 5]
        
        # Analyze similar changes for success patterns
        success_patterns = self._analyze_success_patterns(similar_changes)
        
        return {
            "order_of_changes": [
                "low_risk_first",
                "test_critical_components",
                "gradual_rollout"
            ],
            "suggested_steps": [
                {
                    "phase": "preparation",
                    "actions": [
                        "backup_code",
                        "setup_test_environment",
                        "create_feature_branch"
                    ]
                },
                {
                    "phase": "implementation",
                    "actions": [
                        f"modify_{s['entity'].name}"
                        for s in low_risk + medium_risk + high_risk
                    ]
                },
                {
                    "phase": "validation",
                    "actions": [
                        "run_tests",
                        "check_dependencies",
                        "validate_functionality"
                    ]
                }
            ],
            "success_patterns": success_patterns
        }

    def _analyze_success_patterns(
        self,
        similar_changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze patterns in successful changes.
        
        Args:
            similar_changes: List of similar past changes
            
        Returns:
            Analysis of success patterns
        """
        successful_changes = [
            c for c in similar_changes
            if c.get("status") == "success"
        ]
        
        patterns = {
            "common_approaches": [],
            "testing_strategies": [],
            "validation_steps": []
        }
        
        for change in successful_changes:
            if "approach" in change:
                patterns["common_approaches"].append(change["approach"])
            if "testing" in change:
                patterns["testing_strategies"].append(change["testing"])
            if "validation" in change:
                patterns["validation_steps"].append(change["validation"])
        
        return patterns 