from typing import Dict, Any, List
import asyncio
from datetime import datetime
from langgraph.graph import Graph, StateType
from langgraph.prebuilt import ToolExecutor
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig

class ManagerAgent(BaseAgent):
    """Agent responsible for orchestrating specialized agents"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.workflow = self._setup_workflow()
        self.specialized_agents = {}
    
    def _setup_workflow(self) -> Graph:
        """Setup LangGraph workflow for agent orchestration"""
        # Define workflow nodes
        workflow = Graph()
        
        # Add nodes for each specialized agent type
        workflow.add_node("content_update", self._handle_content_update)
        workflow.add_node("error_fixing", self._handle_error_fixing)
        workflow.add_node("seo_optimization", self._handle_seo_optimization)
        workflow.add_node("content_generation", self._handle_content_generation)
        workflow.add_node("performance_monitoring", self._handle_performance_monitoring)
        
        # Define workflow edges based on dependencies
        workflow.add_edge("content_update", "error_fixing")
        workflow.add_edge("error_fixing", "seo_optimization")
        workflow.add_edge("seo_optimization", "content_generation")
        workflow.add_edge("content_generation", "performance_monitoring")
        
        return workflow
    
    async def register_agent(
        self,
        agent_type: str,
        agent: BaseAgent
    ) -> None:
        """Register a specialized agent"""
        self.specialized_agents[agent_type] = agent
    
    async def _handle_content_update(
        self,
        state: StateType
    ) -> StateType:
        """Handle content update tasks"""
        if "content_update" not in self.specialized_agents:
            return state
        
        agent = self.specialized_agents["content_update"]
        result = await agent.process(state["data"])
        
        state["results"]["content_update"] = result
        return state
    
    async def _handle_error_fixing(
        self,
        state: StateType
    ) -> StateType:
        """Handle error fixing tasks"""
        if "error_fixing" not in self.specialized_agents:
            return state
        
        agent = self.specialized_agents["error_fixing"]
        result = await agent.process(state["data"])
        
        state["results"]["error_fixing"] = result
        return state
    
    async def _handle_seo_optimization(
        self,
        state: StateType
    ) -> StateType:
        """Handle SEO optimization tasks"""
        if "seo_optimization" not in self.specialized_agents:
            return state
        
        agent = self.specialized_agents["seo_optimization"]
        result = await agent.process(state["data"])
        
        state["results"]["seo_optimization"] = result
        return state
    
    async def _handle_content_generation(
        self,
        state: StateType
    ) -> StateType:
        """Handle content generation tasks"""
        if "content_generation" not in self.specialized_agents:
            return state
        
        agent = self.specialized_agents["content_generation"]
        result = await agent.process(state["data"])
        
        state["results"]["content_generation"] = result
        return state
    
    async def _handle_performance_monitoring(
        self,
        state: StateType
    ) -> StateType:
        """Handle performance monitoring tasks"""
        if "performance_monitoring" not in self.specialized_agents:
            return state
        
        agent = self.specialized_agents["performance_monitoring"]
        result = await agent.process(state["data"])
        
        state["results"]["performance_monitoring"] = result
        return state
    
    async def delegate_task(
        self,
        task_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delegate task to appropriate specialized agent"""
        if task_type not in self.specialized_agents:
            raise ValueError(f"Unknown task type: {task_type}")
        
        agent = self.specialized_agents[task_type]
        return await agent.process(data)
    
    async def execute_workflow(
        self,
        initial_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the complete workflow"""
        state = {
            "data": initial_state,
            "results": {},
            "errors": []
        }
        
        try:
            # Execute workflow using LangGraph
            final_state = await self.workflow.arun(state)
            
            # Store workflow results in memory
            await self.memory_manager.add_document({
                "initial_state": initial_state,
                "final_state": final_state,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "status": "success",
                "results": final_state["results"]
            }
            
        except Exception as e:
            self.logger.error("workflow_error", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests and coordinate specialized agents"""
        task_type = data.get("task_type")
        
        try:
            if task_type == "workflow":
                # Execute complete workflow
                return await self.execute_workflow(data)
            
            elif task_type in self.specialized_agents:
                # Delegate to specific agent
                return await self.delegate_task(task_type, data)
            
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
        except Exception as e:
            self.logger.error("processing_error", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        # Cleanup all registered agents
        for agent in self.specialized_agents.values():
            await agent.cleanup()
        await super().cleanup() 