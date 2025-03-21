"""Main system class for AgentX framework."""

import os
import asyncio
import yaml
from typing import Dict, Any, Optional
import structlog
from pathlib import Path
from agentx.common_libraries.system_config import SystemConfig
from agentx.common_libraries.chroma_client import get_chroma_client, reset_chroma_client
from agentx.common_libraries.base_agent import AgentConfig
from agentx.read_agent.read_agent import ReadAgent
from agentx.manager_agent.manager_agent import ManagerAgent
from datetime import datetime

logger = structlog.get_logger()

class AgentXSystem:
    """Main system class that manages all agents."""
    
    def __init__(self, config_path: str = "agentx.config.yaml"):
        """Initialize the system.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = SystemConfig.load(config_path)
        self.agents: Dict[str, Any] = {}
        self.logger = logger.bind(system="agentx")
        
        # Reset any existing ChromaDB client to ensure consistent settings
        reset_chroma_client()
        
        # Initialize a single ChromaDB client for the entire system
        self.chroma_client = get_chroma_client(
            os.path.join(self.config.memory.vector_store_path, "vectors", "chroma")
        )
    
    async def initialize(self) -> None:
        """Initialize the system and all agents."""
        try:
            # Check for required API keys
            if not self.config.api_keys.get('google_api_key'):
                raise ValueError("Google API key not found in configuration")
            
            self.logger.info("Starting system initialization")
            
            # Initialize ReadAgent
            self.logger.info("Initializing ReadAgent")
            read_agent_config = AgentConfig(
                name="read_agent",
                description="Agent responsible for reading and analyzing code",
                model_name=self.config.model.name,
                temperature=self.config.model.temperature,
                max_tokens=self.config.model.max_tokens,
                top_p=self.config.model.top_p
            )
            
            read_agent = ReadAgent(
                config=read_agent_config,
                system_config=self.config
            )
            await read_agent.initialize()
            
            # Register the read agent with the correct task type
            self.agents["read"] = read_agent
            self.logger.info("ReadAgent initialized and registered", agent_type="read")
            
            # Initialize ManagerAgent
            self.logger.info("Initializing ManagerAgent")
            manager_agent_config = AgentConfig(
                name="manager_agent",
                description="Agent responsible for managing and coordinating other agents",
                model_name=self.config.model.name,
                temperature=self.config.model.temperature,
                max_tokens=self.config.model.max_tokens,
                top_p=self.config.model.top_p
            )
            
            manager_agent = ManagerAgent(
                config=manager_agent_config,
                system_config=self.config
            )
            await manager_agent.initialize()
            
            # Register the manager agent
            self.agents["manager"] = manager_agent
            self.logger.info("ManagerAgent initialized and registered", agent_type="manager")
            
            self.logger.info(
                "System initialized successfully",
                registered_agents=list(self.agents.keys())
            )
            
        except Exception as e:
            self.logger.error("Error initializing system", error=str(e))
            raise
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data through the system.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Processing results
        """
        try:
            # Process through read agent
            read_result = await self.agents["read"].process(input_data)
            
            # Process through manager agent
            manager_result = await self.agents["manager"].process(read_result)
            
            return {
                "status": "success",
                "read_result": read_result,
                "manager_result": manager_result
            }
            
        except Exception as e:
            self.logger.error("Error processing input", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self):
        """Clean up system resources."""
        try:
            for agent in self.agents.values():
                await agent.cleanup()
            self.logger.info("System cleaned up")
        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))

    async def process_task(self, task_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task through the appropriate agent.
        
        Args:
            task_type: Type of task to process
            data: Task data
            
        Returns:
            Processing results
        """
        try:
            # Log available agents
            self.logger.info(
                "Available agents",
                agents=list(self.agents.keys()),
                requested_task=task_type
            )
            
            # Get the appropriate agent
            agent = self.agents.get(task_type)
            if not agent:
                raise ValueError(
                    f"No agent found for task type: {task_type}. "
                    f"Available agents: {list(self.agents.keys())}"
                )
            
            # Process the task
            result = await agent.process(data)
            
            # Log the task result
            self.logger.info(
                "Task processed successfully",
                task_type=task_type,
                result=result
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Error processing task",
                error=str(e),
                task_type=task_type,
                available_agents=list(self.agents.keys())
            )
            raise

async def main():
    """Main entry point"""
    # Check required environment variables
    required_env_vars = [
        "GOOGLE_API_KEY",
        "GITHUB_TOKEN",
        "GITHUB_REPO"
    ]
    
    missing_vars = [
        var for var in required_env_vars
        if not os.getenv(var)
    ]
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
    
    try:
        # Initialize system
        system = AgentXSystem()
        await system.initialize()
        
        # Example: Start monitoring a website
        url = "https://example.com"  # Replace with actual URL
        result = await system.process({"url": url})
        print(f"Monitoring result: {result}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        
    finally:
        await system.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 