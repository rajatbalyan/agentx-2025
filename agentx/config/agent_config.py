from typing import Dict, Any
from pydantic import BaseModel

class AgentConfig(BaseModel):
    """Base configuration for all agents"""
    name: str
    host: str = "0.0.0.0"
    port: int
    log_level: str = "INFO"
    redis_url: str = "redis://redis:6379/0"
    model_name: str = "gemini-pro"
    temperature: float = 0.7
    memory_path: str = "data/memory"

class SystemConfig:
    """System-wide configuration"""
    
    def __init__(self):
        # Agent ports
        self.READ_AGENT_PORT = 8000
        self.MANAGER_AGENT_PORT = 8001
        self.CONTENT_UPDATE_PORT = 8002
        self.ERROR_FIXING_PORT = 8003
        self.SEO_OPTIMIZATION_PORT = 8004
        self.CONTENT_GENERATION_PORT = 8005
        self.PERFORMANCE_MONITORING_PORT = 8006
        self.CICD_DEPLOYMENT_PORT = 8007
        
        # Agent configurations
        self.agent_configs = {
            "read": AgentConfig(
                name="read_agent",
                port=self.READ_AGENT_PORT
            ),
            "manager": AgentConfig(
                name="manager_agent",
                port=self.MANAGER_AGENT_PORT
            ),
            "content_update": AgentConfig(
                name="content_update_agent",
                port=self.CONTENT_UPDATE_PORT
            ),
            "error_fixing": AgentConfig(
                name="error_fixing_agent",
                port=self.ERROR_FIXING_PORT
            ),
            "seo_optimization": AgentConfig(
                name="seo_optimization_agent",
                port=self.SEO_OPTIMIZATION_PORT
            ),
            "content_generation": AgentConfig(
                name="content_generation_agent",
                port=self.CONTENT_GENERATION_PORT
            ),
            "performance_monitoring": AgentConfig(
                name="performance_monitoring_agent",
                port=self.PERFORMANCE_MONITORING_PORT
            ),
            "cicd_deployment": AgentConfig(
                name="cicd_deployment_agent",
                port=self.CICD_DEPLOYMENT_PORT
            )
        }
        
        # Workflow configuration
        self.workflow_config = {
            "max_retries": 3,
            "retry_delay": 5,  # seconds
            "timeout": 300  # seconds
        }
        
        # Memory configuration
        self.memory_config = {
            "conversation_buffer_size": 1000,
            "vector_store_path": "data/memory/vectors",
            "conversation_store_path": "data/memory/conversations"
        }
        
        # Monitoring configuration
        self.monitoring_config = {
            "prometheus_port": 9090,
            "grafana_port": 3000,
            "log_path": "logs"
        }
    
    def get_agent_config(self, agent_type: str) -> AgentConfig:
        """Get configuration for a specific agent"""
        if agent_type not in self.agent_configs:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return self.agent_configs[agent_type] 