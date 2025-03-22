"""Manager Agent module for coordinating specialized agents."""

from typing import Dict, Any, List
from agentx.agents.specialized_agent import SpecializedAgent
from agentx.config.config_loader import SystemConfig
import structlog

logger = structlog.get_logger()

class ManagerAgent:
    """Manager Agent class responsible for coordinating specialized agents."""

    def __init__(self, config: Dict[str, Any], system_config: SystemConfig):
        """Initialize Manager Agent.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
            system_config (SystemConfig): System configuration
        """
        self.config = config
        self.system_config = system_config
        self.specialized_agents: Dict[str, SpecializedAgent] = {}
        self.task_queue: List[Dict[str, Any]] = []
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.initialize_agents()

    def initialize_agents(self):
        """Initialize specialized agents based on configuration."""
        for agent_config in self.config.get("agents", []):
            agent_id = agent_config.get("id")
            if not agent_id:
                continue
                
            agent = SpecializedAgent(
                agent_type=agent_config.get("type", ""),
                capabilities=agent_config.get("capabilities", []),
                agent_id=agent_id
            )
            self.specialized_agents[agent_id] = agent

    def add_task(self, task: Dict[str, Any]) -> str:
        """Add a new task to the system.
        
        Args:
            task (Dict[str, Any]): Task configuration
            
        Returns:
            str: Task ID
            
        Raises:
            ValueError: If task doesn't have an ID
        """
        if "id" not in task:
            raise ValueError("Task must have an ID")
            
        task_id = task["id"]
        
        # Find suitable agent
        suitable_agent = None
        required_capabilities = task.get("required_capabilities", [])
        
        for agent in self.specialized_agents.values():
            if all(cap in agent.capabilities for cap in required_capabilities):
                suitable_agent = agent
                break
        
        if suitable_agent:
            # Assign task to agent
            self.active_tasks[task_id] = {
                "task": task,
                "agent": suitable_agent,
                "status": "assigned"
            }
        else:
            # Queue task if no suitable agent found
            self.task_queue.append(task)
            self.active_tasks[task_id] = {
                "task": task,
                "status": "queued"
            }
            
        return task_id

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a task.
        
        Args:
            task_id (str): Task ID
            
        Returns:
            Dict[str, Any]: Task status information
            
        Raises:
            ValueError: If task not found
        """
        if task_id not in self.active_tasks:
            raise ValueError(f"No task found with ID: {task_id}")
            
        return self.active_tasks[task_id]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.
        
        Args:
            task_id (str): Task ID
            
        Returns:
            bool: True if task was cancelled, False if task not found
        """
        if task_id not in self.active_tasks:
            # Check task queue
            for task in self.task_queue:
                if task["id"] == task_id:
                    self.task_queue.remove(task)
                    return True
            return False
            
        task_info = self.active_tasks[task_id]
        if task_info["status"] in ["queued", "assigned"]:
            if task_info["status"] == "queued":
                # Remove from queue
                self.task_queue = [t for t in self.task_queue if t["id"] != task_id]
                del self.active_tasks[task_id]
            else:
                # Mark as cancelled
                task_info["status"] = "cancelled"
            return True
            
        return False

    def execute_task(self, task_id: str) -> None:
        """Execute a task.
        
        Args:
            task_id (str): Task ID
            
        Raises:
            ValueError: If task not found or not in assigned state
        """
        if task_id not in self.active_tasks:
            raise ValueError(f"No task found with ID: {task_id}")
            
        task_info = self.active_tasks[task_id]
        if task_info["status"] != "assigned":
            raise ValueError(f"Task {task_id} is not in assigned state")
            
        try:
            # Execute task
            result = task_info["agent"].execute_task(task_info["task"])
            task_info["status"] = result["status"]
            task_info["result"] = result
        except Exception as e:
            # Handle execution failure
            task_info["status"] = "failed"
            task_info["error"] = str(e)

    async def initialize(self):
        """Initialize the manager agent."""
        pass

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data.
        
        Args:
            input_data (Dict[str, Any]): Input data to process
            
        Returns:
            Dict[str, Any]: Processing result
        """
        if "analysis" not in input_data:
            return {
                "status": "error",
                "error": "No analysis data found in input"
            }
            
        return {
            "status": "success",
            "result": {}
        } 