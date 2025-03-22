"""Manager agent for AgentX framework."""

from typing import Dict, Any, List, Optional, Annotated
from typing_extensions import TypedDict
import structlog
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig
from agentx.common_libraries.system_config import SystemConfig

logger = structlog.get_logger()

class TaskPriority:
    """Task priority levels for agent tasks."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ManagerState(TypedDict):
    """State definition for the manager agent workflow."""
    input: Dict[str, Any]
    read_result: Optional[Dict[str, Any]]
    tasks: Annotated[List[Dict[str, Any]], add_messages]
    task_results: Dict[str, Any]
    error: Optional[str]

class ManagerAgent(BaseAgent):
    """Agent responsible for managing and coordinating other agents."""
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig):
        """Initialize the manager agent.
        
        Args:
            config: Agent configuration
            system_config: System configuration
        """
        super().__init__(config, system_config)
        self.logger = logger.bind(agent="manager_agent")
        self.workflow_graph = None
        self.agents = {}  # Dictionary to store agent references
        
        # Score thresholds for determining task priority
        self.CRITICAL_THRESHOLD = 70
        self.WARNING_THRESHOLD = 85
    
    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """Register an agent with the manager.
        
        Args:
            name: Name of the agent
            agent: Agent instance
        """
        self.agents[name] = agent
    
    def _determine_priority(self, score: float) -> str:
        """Determine task priority based on score."""
        if score < self.CRITICAL_THRESHOLD:
            return TaskPriority.HIGH
        elif score < self.WARNING_THRESHOLD:
            return TaskPriority.MEDIUM
        return TaskPriority.LOW
    
    def _analyze_performance_issues(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze performance data and create task if needed."""
        performance_data = data.get('normalized_data', {}).get('performance', {})
        score = performance_data.get('score', 100)
        
        if score >= self.WARNING_THRESHOLD:
            return None
            
        return {
            "type": "performance_optimization",
            "priority": self._determine_priority(score),
            "score": score,
            "issues": performance_data.get('hints', []),
            "metrics": data.get('audit', {}).get('audit', {}).get('performance', {}).get('metrics', {}),
            "prompt": self._generate_performance_prompt(score, performance_data.get('hints', []))
        }
    
    def _analyze_seo_issues(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze SEO data and create task if needed."""
        seo_data = data.get('normalized_data', {}).get('seo', {})
        score = seo_data.get('score', 100)
        
        if score >= self.WARNING_THRESHOLD:
            return None
            
        return {
            "type": "seo_optimization",
            "priority": self._determine_priority(score),
            "score": score,
            "issues": seo_data.get('hints', []),
            "metrics": data.get('audit', {}).get('audit', {}).get('seo', {}).get('metrics', {}),
            "prompt": self._generate_seo_prompt(score, seo_data.get('hints', []))
        }
    
    def _generate_performance_prompt(self, score: float, issues: List[Dict[str, Any]]) -> str:
        """Generate a detailed prompt for performance optimization tasks."""
        prompt = (
            f"Performance Optimization Task\n"
            f"Current Performance Score: {score}/100\n\n"
            f"Priority: {self._determine_priority(score).upper()}\n\n"
            "Issues Requiring Attention:\n"
        )
        
        for issue in issues:
            severity = issue.get('severity', 'medium').upper()
            prompt += (
                f"\n🔍 Issue ({severity}):\n"
                f"- Problem: {issue.get('message', 'No description')}\n"
                f"- Technical Context: {issue.get('details', 'No additional details')}\n"
            )
        
        prompt += "\nRequired Actions:\n"
        prompt += "1. Analyze each issue in detail\n"
        prompt += "2. Implement optimizations for identified problems\n"
        prompt += "3. Verify improvements with metrics\n"
        prompt += "4. Document changes and their impact\n"
        
        return prompt
    
    def _generate_seo_prompt(self, score: float, issues: List[Dict[str, Any]]) -> str:
        """Generate a detailed prompt for SEO optimization tasks."""
        prompt = (
            f"SEO Optimization Task\n"
            f"Current SEO Score: {score}/100\n\n"
            f"Priority: {self._determine_priority(score).upper()}\n\n"
            "Issues Requiring Attention:\n"
        )
        
        for issue in issues:
            severity = issue.get('severity', 'medium').upper()
            prompt += (
                f"\n🔍 Issue ({severity}):\n"
                f"- Problem: {issue.get('message', 'No description')}\n"
                f"- Impact: {issue.get('details', 'No additional details')}\n"
            )
        
        prompt += "\nRequired Actions:\n"
        prompt += "1. Review each SEO issue\n"
        prompt += "2. Implement necessary SEO improvements\n"
        prompt += "3. Verify changes meet SEO best practices\n"
        prompt += "4. Document optimizations made\n"
        
        return prompt
    
    async def _distribute_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Distribute tasks to appropriate specialized agents."""
        results = {}
        
        for task in tasks:
            task_type = task['type']
            agent_name = None
            
            if task_type == 'performance_optimization':
                agent_name = 'performance_monitoring'
            elif task_type == 'seo_optimization':
                agent_name = 'seo_optimization'
            
            if agent_name and agent_name in self.agents:
                try:
                    # Send task to specialized agent
                    agent_result = await self.agents[agent_name].process({
                        "type": task_type,
                        "priority": task['priority'],
                        "data": task
                    })
                    results[agent_name] = {
                        "status": "assigned",
                        "task": task,
                        "result": agent_result
                    }
                except Exception as e:
                    self.logger.error(f"Error assigning task to {agent_name}", error=str(e))
                    results[agent_name] = {
                        "status": "error",
                        "error": str(e)
                    }
            else:
                self.logger.warning(f"Agent not found for task type: {task_type}")
                results[task_type] = {
                    "status": "unassigned",
                    "reason": f"No agent available for {task_type}"
                }
        
        return results
    
    def _route_to_read(self, state: ManagerState) -> List[str]:
        """Route from start to read."""
        return ["read"]
    
    def _route_next(self, state: ManagerState) -> List[str]:
        """Route to next nodes based on state."""
        if state.get("error") or state.get("task_results"):
            return []  # End the workflow
        return ["read"]  # Continue with read node
    
    async def initialize(self) -> None:
        """Initialize the workflow graph."""
        await super().initialize()
        
        # Create workflow graph with state type
        self.workflow_graph = StateGraph(ManagerState)
        
        # Add nodes for each agent
        self.workflow_graph.add_node("start", self._initialize_state)
        self.workflow_graph.add_node("read", self._process_read)
        
        # Add edges with class methods
        self.workflow_graph.add_edge("start", self._route_to_read)
        self.workflow_graph.add_edge("read", self._route_next)
        
        # Set entry point
        self.workflow_graph.set_entry_point("start")
        
    def _initialize_state(self, input_data: Dict[str, Any]) -> ManagerState:
        """Initialize workflow state from input data.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Initial state for the workflow
        """
        if not isinstance(input_data, dict):
            input_data = {"data": input_data}
            
        return {
            "input": input_data,
            "read_result": None,
            "tasks": [],
            "task_results": {},
            "error": None
        }
        
    async def _process_read(self, state: ManagerState) -> ManagerState:
        """Process read node and distribute tasks based on analysis."""
        try:
            # Get the read result from the state
            read_result = state.get("read_result")
            if not read_result:
                return {
                    **state,
                    "error": "No read result available"
                }
            
            # Analyze results and create tasks
            tasks = []
            
            # Check for performance issues
            performance_task = self._analyze_performance_issues(read_result)
            if performance_task:
                tasks.append(performance_task)
            
            # Check for SEO issues
            seo_task = self._analyze_seo_issues(read_result)
            if seo_task:
                tasks.append(seo_task)
            
            # Update state with new tasks
            return {
                **state,
                "tasks": tasks
            }
            
        except Exception as e:
            self.logger.error("Error processing read result", error=str(e))
            return {
                **state,
                "error": str(e)
            }
    
    async def _process_content_update(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process content update node."""
        return {"content_update": "Not implemented yet"}
    
    async def _process_seo(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process SEO optimization node."""
        return {"seo_optimization": "Not implemented yet"}
    
    async def _process_errors(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process error fixing node."""
        return {"error_fixing": "Not implemented yet"}
    
    async def _process_generation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process content generation node."""
        return {"content_generation": "Not implemented yet"}
    
    async def _process_performance(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process performance monitoring node."""
        return {"performance_monitoring": "Not implemented yet"}
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and create tasks as needed.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Processing results
        """
        try:
            self.logger.info("Processing input data", input=input_data)
            
            # Extract analysis results
            analysis = input_data.get('results', {}).get('analysis', {})
            if not analysis:
                return {
                    "status": "error",
                    "error": "No analysis data found in input"
                }
            
            tasks = []
            
            # Check for performance issues
            performance_task = self._analyze_performance_issues(analysis)
            if performance_task:
                self.logger.info(
                    "Created performance optimization task",
                    score=performance_task['score'],
                    priority=performance_task['priority']
                )
                tasks.append(performance_task)
            
            # Check for SEO issues
            seo_task = self._analyze_seo_issues(analysis)
            if seo_task:
                self.logger.info(
                    "Created SEO optimization task",
                    score=seo_task['score'],
                    priority=seo_task['priority']
                )
                tasks.append(seo_task)
            
            # Distribute tasks to specialized agents
            task_results = {}
            if tasks:
                task_results = await self._distribute_tasks(tasks)
            
            return {
                "status": "success",
                "tasks_created": len(tasks),
                "tasks": tasks,
                "task_results": task_results
            }
            
        except Exception as e:
            self.logger.error("Error processing input", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        # Cleanup all registered agents
        for agent in self.agents.values():
            await agent.cleanup()
        await super().cleanup() 