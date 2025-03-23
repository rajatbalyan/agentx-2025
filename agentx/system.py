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
from agentx.specialized_agents.performance_monitoring_agent.performance_monitoring_agent import PerformanceMonitoringAgent
from agentx.specialized_agents.seo_optimization_agent.seo_optimization_agent import SEOOptimizationAgent
from agentx.specialized_agents.content_generation_agent.content_generation_agent import ContentGenerationAgent
from agentx.specialized_agents.error_fixing_agent.error_fixing_agent import ErrorFixingAgent
from agentx.github_controller.controller import GitHubController
from agentx.cicd_deployment_agent.cicd_deployment_agent import CICDDeploymentAgent
from datetime import datetime
import subprocess

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
        
        # Initialize GitHub controller
        self.github = GitHubController(
            token=self.config.api_keys.get('github_token', ''),
            repo_owner=self.config.github.repo_owner,
            repo_name=self.config.github.repo_name
        )
    
    async def initialize(self) -> None:
        """Initialize the system and all agents."""
        try:
            # Check for required API keys
            if not self.config.api_keys.get('google_api_key'):
                raise ValueError("Google API key not found in configuration")
            if not self.config.api_keys.get('github_token'):
                raise ValueError("GitHub token not found in configuration")
            
            self.logger.info("Starting system initialization")
            
            # Ensure we're on the sitesentry branch
            result = self.github.ensure_sitesentry_branch()
            if result["status"] != "success":
                raise ValueError(f"Failed to setup sitesentry branch: {result['message']}")
            self.logger.info("Successfully set up sitesentry branch", branch=result["branch"])
            
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
            
            # Initialize specialized agents
            self.logger.info("Initializing specialized agents")
            
            specialized_agents = {
                "performance_monitoring": (PerformanceMonitoringAgent, "Agent for performance optimization"),
                "seo_optimization": (SEOOptimizationAgent, "Agent for SEO improvements"),
                "content_generation": (ContentGenerationAgent, "Agent for content updates"),
                "error_fixing": (ErrorFixingAgent, "Agent for fixing errors"),
                "cicd_deployment": (CICDDeploymentAgent, "Agent for CI/CD deployment")
            }
            
            for agent_type, (agent_class, description) in specialized_agents.items():
                self.logger.info(f"Initializing {agent_type} agent")
                agent_config = AgentConfig(
                    name=f"{agent_type}_agent",
                    description=description,
                    model_name=self.config.model.name,
                    temperature=self.config.model.temperature,
                    max_tokens=self.config.model.max_tokens,
                    top_p=self.config.model.top_p
                )
                
                agent = agent_class(
                    config=agent_config,
                    system_config=self.config
                )
                await agent.initialize()
                
                # Register with system and manager
                self.agents[agent_type] = agent
                manager_agent.register_agent(agent_type, agent)
                self.logger.info(f"{agent_type} agent initialized and registered")
            
            self.logger.info(
                "System initialized successfully",
                registered_agents=list(self.agents.keys())
            )
            
        except Exception as e:
            self.logger.error("Error initializing system", error=str(e))
            raise
    
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
            
            # If this is a read task, also process through manager for subtask creation
            if task_type == "read" and result.get("status") == "success":
                self.logger.info("Processing read result through manager for subtask creation")
                manager_result = await self.agents["manager"].process(result)
                result["manager_actions"] = manager_result
            
            # If changes were made, commit them
            if result.get("changes_made", False):
                commit_message = f"AgentX: {task_type} changes - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                if self.github.commit_changes(commit_message):
                    self.logger.info("Changes committed successfully", commit_message=commit_message)
                    # Try to push changes
                    if self.github.push_changes():
                        self.logger.info("Changes pushed successfully")
                    else:
                        self.logger.warning("Failed to push changes")
                else:
                    self.logger.warning("Failed to commit changes")
            
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
    
    async def cleanup(self):
        """Clean up system resources."""
        try:
            # Clean up agents
            for agent in self.agents.values():
                try:
                    await agent.cleanup()
                except Exception as e:
                    self.logger.error("Error during agent cleanup", agent=agent.config.name, error=str(e))
            
            # Reset ChromaDB client
            try:
                reset_chroma_client()
                self.logger.info("ChromaDB client reset")
            except Exception as e:
                self.logger.error("Error resetting ChromaDB client", error=str(e))
            
            # Reset GitHub controller
            try:
                if hasattr(self, 'github'):
                    # First try to stash any changes
                    subprocess.run(["git", "stash", "save", "Temporary stash before cleanup"], 
                                 cwd=self.config.workspace.path,
                                 capture_output=True,
                                 text=True)
                    
                    # Then checkout main branch
                    subprocess.run(["git", "checkout", "main"],
                                 cwd=self.config.workspace.path,
                                 capture_output=True,
                                 text=True)
                    
                    self.logger.info("GitHub controller reset")
            except Exception as e:
                self.logger.error("Error resetting GitHub controller", error=str(e))
            
            self.logger.info("System cleaned up")
        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))

async def main():
    """Main entry point"""
    # Check required environment variables
    required_env_vars = [
        "GOOGLE_API_KEY",
        "GITHUB_TOKEN",
        "GITHUB_REPO",
        "GITHUB_OWNER"
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