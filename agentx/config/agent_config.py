"""Configuration management for AgentX agents."""

import os
from typing import Dict, Any
from pydantic import BaseModel, validator

# Port range configuration
PORT_RANGE_START = 8000  # Base port for agents
PORT_RANGE_END = 8999   # Maximum port for agents
MONITORING_PORT_RANGE_START = 9000  # Base port for monitoring services
MONITORING_PORT_RANGE_END = 9999   # Maximum port for monitoring services

class PortConfig:
    """Port configuration and validation."""
    
    @staticmethod
    def validate_port(port: int, port_type: str = "agent") -> bool:
        """Validate if a port number is valid and within the correct range."""
        if not 1024 <= port <= 65535:
            return False
            
        if port_type == "agent":
            return PORT_RANGE_START <= port <= PORT_RANGE_END
        elif port_type == "monitoring":
            return MONITORING_PORT_RANGE_START <= port <= MONITORING_PORT_RANGE_END
        return False

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

    @validator('port')
    def validate_agent_port(cls, v):
        if not PortConfig.validate_port(v, "agent"):
            raise ValueError(f"Invalid agent port: {v}. Must be between {PORT_RANGE_START} and {PORT_RANGE_END}")
        return v

class SystemConfig:
    """System-wide configuration"""
    
    def __init__(self):
        """Initialize system configuration with environment-aware port assignments."""
        # Agent ports with environment variable support and validation
        self.READ_AGENT_PORT = self._get_validated_port('READ_AGENT_PORT', 8000)
        self.MANAGER_AGENT_PORT = self._get_validated_port('MANAGER_AGENT_PORT', 8001)
        self.CONTENT_UPDATE_PORT = self._get_validated_port('CONTENT_UPDATE_PORT', 8002)
        self.ERROR_FIXING_PORT = self._get_validated_port('ERROR_FIXING_PORT', 8003)
        self.SEO_OPTIMIZATION_PORT = self._get_validated_port('SEO_OPTIMIZATION_PORT', 8004)
        self.CONTENT_GENERATION_PORT = self._get_validated_port('CONTENT_GENERATION_PORT', 8005)
        self.PERFORMANCE_MONITORING_PORT = self._get_validated_port('PERFORMANCE_MONITORING_PORT', 8006)
        self.CICD_DEPLOYMENT_PORT = self._get_validated_port('CICD_DEPLOYMENT_PORT', 8007)
        
        # Validate no port conflicts
        self._validate_no_port_conflicts()
        
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
            "max_retries": int(os.getenv('WORKFLOW_MAX_RETRIES', '3')),
            "retry_delay": int(os.getenv('WORKFLOW_RETRY_DELAY', '5')),  # seconds
            "timeout": int(os.getenv('WORKFLOW_TIMEOUT', '300'))  # seconds
        }
        
        # Memory configuration
        self.memory_config = {
            "conversation_buffer_size": int(os.getenv('MEMORY_BUFFER_SIZE', '1000')),
            "vector_store_path": os.getenv('VECTOR_STORE_PATH', 'data/memory/vectors'),
            "conversation_store_path": os.getenv('CONVERSATION_STORE_PATH', 'data/memory/conversations')
        }
        
        # Monitoring configuration with validated ports
        self.monitoring_config = {
            "prometheus_port": self._get_validated_port('PROMETHEUS_PORT', 9090, "monitoring"),
            "grafana_port": self._get_validated_port('GRAFANA_PORT', 3000, "monitoring"),
            "log_path": os.getenv('LOG_PATH', 'logs')
        }
    
    def _get_validated_port(self, env_var: str, default: int, port_type: str = "agent") -> int:
        """Get and validate port from environment variable or default."""
        port = int(os.getenv(env_var, str(default)))
        if not PortConfig.validate_port(port, port_type):
            raise ValueError(
                f"Invalid {port_type} port {port} for {env_var}. "
                f"Must be between {PORT_RANGE_START if port_type == 'agent' else MONITORING_PORT_RANGE_START} "
                f"and {PORT_RANGE_END if port_type == 'agent' else MONITORING_PORT_RANGE_END}"
            )
        return port
    
    def _validate_no_port_conflicts(self) -> None:
        """Ensure there are no port conflicts between agents."""
        ports = [
            (self.READ_AGENT_PORT, "READ_AGENT"),
            (self.MANAGER_AGENT_PORT, "MANAGER_AGENT"),
            (self.CONTENT_UPDATE_PORT, "CONTENT_UPDATE"),
            (self.ERROR_FIXING_PORT, "ERROR_FIXING"),
            (self.SEO_OPTIMIZATION_PORT, "SEO_OPTIMIZATION"),
            (self.CONTENT_GENERATION_PORT, "CONTENT_GENERATION"),
            (self.PERFORMANCE_MONITORING_PORT, "PERFORMANCE_MONITORING"),
            (self.CICD_DEPLOYMENT_PORT, "CICD_DEPLOYMENT")
        ]
        
        seen_ports = {}
        for port, agent in ports:
            if port in seen_ports:
                raise ValueError(
                    f"Port conflict detected: {agent} and {seen_ports[port]} "
                    f"both trying to use port {port}"
                )
            seen_ports[port] = agent
    
    def get_agent_config(self, agent_type: str) -> AgentConfig:
        """Get configuration for a specific agent."""
        if agent_type not in self.agent_configs:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return self.agent_configs[agent_type]
    
    def get_all_agent_ports(self) -> Dict[str, int]:
        """Get a mapping of all agent names to their ports."""
        return {name: config.port for name, config in self.agent_configs.items()}
    
    def is_port_available(self, port: int) -> bool:
        """Check if a port is available (not used by any agent)."""
        return port not in [config.port for config in self.agent_configs.values()] 