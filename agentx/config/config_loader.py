"""Configuration loader for agent system."""

import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import structlog
from pydantic import BaseModel, Field, validator, field_validator
from typing import List

logger = structlog.get_logger()

class TaskConfig(BaseModel):
    """Task configuration model."""
    
    id: str
    type: str
    priority: Optional[int] = None
    required_capabilities: list[str] = []
    
    @field_validator("priority")
    def validate_priority(cls, v: Optional[int]) -> Optional[int]:
        """Validate task priority.
        
        Args:
            v (Optional[int]): Priority value
            
        Returns:
            Optional[int]: Validated priority value
            
        Raises:
            ValueError: If priority is not between 1 and 10
        """
        if v is not None and not (1 <= v <= 10):
            raise ValueError("Priority must be between 1 and 10")
        return v

class SystemConfig(BaseModel):
    """System configuration model."""
    
    log_level: str = "INFO"
    max_concurrent_tasks: int = 5
    task_timeout_seconds: int = 300
    default_priority: int = 5
    
    @field_validator("default_priority")
    def validate_default_priority(cls, v: int) -> int:
        """Validate default priority.
        
        Args:
            v (int): Default priority value
            
        Returns:
            int: Validated default priority value
            
        Raises:
            ValueError: If default priority is not between 1 and 10
        """
        if not (1 <= v <= 10):
            raise ValueError("Default priority must be between 1 and 10")
        return v

class AgentCapabilities(BaseModel):
    """Agent capabilities configuration."""
    id: str
    type: str
    capabilities: List[str]
    max_tasks: int = Field(default=1, ge=1)
    priority: str

    @validator("priority")
    def validate_priority(cls, v):
        """Validate priority level."""
        valid_priorities = ["critical", "high", "medium", "low"]
        if v.lower() not in valid_priorities:
            raise ValueError(f"Priority must be one of {valid_priorities}")
        return v.lower()

class TaskTypeConfig(BaseModel):
    """Task type configuration."""
    required_capabilities: List[str]
    default_priority: str

    @validator("default_priority")
    def validate_priority(cls, v):
        """Validate priority level."""
        valid_priorities = ["critical", "high", "medium", "low"]
        if v.lower() not in valid_priorities:
            raise ValueError(f"Priority must be one of {valid_priorities}")
        return v.lower()

class TaskQueueConfig(BaseModel):
    """Task queue configuration."""
    max_size: int = Field(default=100, ge=1)
    retry_limit: int = Field(default=3, ge=0)
    retry_delay_seconds: int = Field(default=60, ge=1)

class AgentConfig(BaseModel):
    """Complete agent configuration."""
    system: SystemConfig
    agents: List[AgentCapabilities]
    task_types: Dict[str, TaskTypeConfig]
    priorities: Dict[str, int]
    task_queue: TaskQueueConfig

class ConfigLoader:
    """Configuration loader for agent system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration loader.
        
        Args:
            config_path: Path to configuration file
        """
        self.logger = logger.bind(component="config_loader")
        self.config_path = config_path or str(Path(__file__).parent / "agent_config.yaml")
        self.config = None
    
    def load_config(self) -> AgentConfig:
        """Load and validate configuration.
        
        Returns:
            Validated configuration object
        """
        try:
            # Load YAML file
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Validate configuration
            config = AgentConfig(**config_data)
            self.config = config
            
            self.logger.info("Configuration loaded successfully",
                           config_path=self.config_path)
            
            return config
            
        except Exception as e:
            self.logger.error("Failed to load configuration",
                            config_path=self.config_path,
                            error=str(e))
            raise
    
    def get_agent_config(self, agent_id: str) -> Optional[AgentCapabilities]:
        """Get configuration for a specific agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent configuration if found, None otherwise
        """
        if not self.config:
            self.load_config()
        
        for agent in self.config.agents:
            if agent.id == agent_id:
                return agent
        return None
    
    def get_task_type_config(self, task_type: str) -> Optional[TaskTypeConfig]:
        """Get configuration for a specific task type.
        
        Args:
            task_type: Type of task
            
        Returns:
            Task type configuration if found, None otherwise
        """
        if not self.config:
            self.load_config()
        
        return self.config.task_types.get(task_type)
    
    def get_priority_weight(self, priority: str) -> int:
        """Get weight for a priority level.
        
        Args:
            priority: Priority level
            
        Returns:
            Priority weight
        """
        if not self.config:
            self.load_config()
        
        return self.config.priorities.get(priority.lower(), 0)
    
    def validate_agent_capabilities(self, agent_id: str, task_type: str) -> bool:
        """Validate if an agent has required capabilities for a task type.
        
        Args:
            agent_id: ID of the agent
            task_type: Type of task
            
        Returns:
            True if agent has required capabilities, False otherwise
        """
        if not self.config:
            self.load_config()
        
        agent_config = self.get_agent_config(agent_id)
        task_config = self.get_task_type_config(task_type)
        
        if not agent_config or not task_config:
            return False
        
        return all(cap in agent_config.capabilities 
                  for cap in task_config.required_capabilities)
    
    def get_system_config(self) -> SystemConfig:
        """Get system-wide configuration.
        
        Returns:
            System configuration
        """
        if not self.config:
            self.load_config()
        
        return self.config.system
    
    def get_task_queue_config(self) -> TaskQueueConfig:
        """Get task queue configuration.
        
        Returns:
            Task queue configuration
        """
        if not self.config:
            self.load_config()
        
        return self.config.task_queue 