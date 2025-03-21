import asyncio
import os
from typing import Dict, Any
from agentx.config.agent_config import SystemConfig
from agentx.read_agent.read_agent import ReadAgent
from agentx.manager_agent.manager_agent import ManagerAgent
from agentx.specialized_agents.content_update_agent.content_update_agent import ContentUpdateAgent
from agentx.specialized_agents.error_fixing_agent.error_fixing_agent import ErrorFixingAgent
from agentx.specialized_agents.seo_optimization_agent.seo_optimization_agent import SEOOptimizationAgent
from agentx.specialized_agents.content_generation_agent.content_generation_agent import ContentGenerationAgent
from agentx.specialized_agents.performance_monitoring_agent.performance_monitoring_agent import PerformanceMonitoringAgent
from agentx.cicd_deployment_agent.cicd_deployment_agent import CICDDeploymentAgent

class AgentXSystem:
    """Main system class that initializes and manages all agents"""
    
    def __init__(self):
        self.config = SystemConfig()
        self.agents = {}
        self._setup_directories()
    
    def _setup_directories(self) -> None:
        """Create necessary directories"""
        directories = [
            "data/memory/vectors",
            "data/memory/conversations",
            "logs",
            "temp"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    async def initialize_agents(self) -> None:
        """Initialize all agents"""
        # Create agents
        self.agents["read"] = ReadAgent(
            self.config.get_agent_config("read")
        )
        
        self.agents["manager"] = ManagerAgent(
            self.config.get_agent_config("manager")
        )
        
        self.agents["content_update"] = ContentUpdateAgent(
            self.config.get_agent_config("content_update")
        )
        
        self.agents["error_fixing"] = ErrorFixingAgent(
            self.config.get_agent_config("error_fixing")
        )
        
        self.agents["seo_optimization"] = SEOOptimizationAgent(
            self.config.get_agent_config("seo_optimization")
        )
        
        self.agents["content_generation"] = ContentGenerationAgent(
            self.config.get_agent_config("content_generation")
        )
        
        self.agents["performance_monitoring"] = PerformanceMonitoringAgent(
            self.config.get_agent_config("performance_monitoring")
        )
        
        self.agents["cicd_deployment"] = CICDDeploymentAgent(
            self.config.get_agent_config("cicd_deployment")
        )
        
        # Initialize each agent
        for agent in self.agents.values():
            await agent.initialize()
        
        # Register specialized agents with manager
        manager = self.agents["manager"]
        for agent_type, agent in self.agents.items():
            if agent_type != "manager":
                await manager.register_agent(agent_type, agent)
    
    async def start_monitoring(self, url: str) -> Dict[str, Any]:
        """Start monitoring a website"""
        # Start with READ agent analysis
        read_result = await self.agents["read"].process({
            "url": url
        })
        
        if read_result["status"] == "error":
            return read_result
        
        # Execute complete workflow through manager
        return await self.agents["manager"].process({
            "task_type": "workflow",
            "data": read_result
        })
    
    async def cleanup(self) -> None:
        """Cleanup all agents"""
        for agent in self.agents.values():
            await agent.cleanup()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all agents"""
        health_status = {}
        for agent_type, agent in self.agents.items():
            health_status[agent_type] = await agent.health_check()
        return health_status

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
        await system.initialize_agents()
        
        # Example: Start monitoring a website
        url = "https://example.com"  # Replace with actual URL
        result = await system.start_monitoring(url)
        print(f"Monitoring result: {result}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        
    finally:
        await system.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 