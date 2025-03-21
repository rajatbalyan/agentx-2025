"""Base agent class for AgentX framework."""

import asyncio
from typing import Any, Dict, List, Optional
import structlog
from pydantic import BaseModel
from langchain.chat_models import ChatGoogleGenerativeAI
from langmem import Memory
from .code_indexer import CodeIndexer

logger = structlog.get_logger()

class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str
    port: int
    model_path: Optional[str] = None
    memory_path: Optional[str] = None
    api_key: Optional[str] = None
    workspace_path: Optional[str] = None

class BaseAgent:
    """Base class for all agents in the AgentX framework."""

    def __init__(self, config: AgentConfig):
        """Initialize the base agent.
        
        Args:
            config: Agent configuration
        """
        self.config = config
        self.name = config.name
        self.port = config.port
        self.logger = logger.bind(agent=self.name)
        
        # Initialize LLM
        if config.api_key:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=config.api_key,
                temperature=0.7
            )
        
        # Initialize memory
        if config.memory_path:
            self.memory = Memory(
                storage_path=config.memory_path,
                agent_name=self.name
            )
        
        # Initialize code indexer
        if config.workspace_path:
            self.code_indexer = CodeIndexer(
                workspace_path=config.workspace_path,
                db_path=f"{config.memory_path}/code_index"
            )
        
        self.logger.info("Agent initialized", port=self.port)

    async def initialize(self) -> None:
        """Initialize the agent and index codebase."""
        if hasattr(self, 'code_indexer'):
            await self.code_indexer.index_codebase()

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task.
        
        Args:
            task: Task to process
            
        Returns:
            Processing results
        """
        raise NotImplementedError("Subclasses must implement process()")

    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        if hasattr(self, 'memory'):
            await self.memory.cleanup()
        self.logger.info("Agent cleaned up")

    def health_check(self) -> bool:
        """Check if the agent is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return True

    async def store_interaction(self, task: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Store an interaction in memory.
        
        Args:
            task: Input task
            result: Processing result
        """
        if hasattr(self, 'memory'):
            await self.memory.add_interaction({
                'input': task,
                'output': result,
                'timestamp': asyncio.get_event_loop().time()
            })

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