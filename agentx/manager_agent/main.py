import asyncio
from typing import Dict, Any, List
import aiohttp
from pydantic import BaseModel
import json
from langchain.agents import Tool, AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
import redis.asyncio as redis

from agentx.common_libraries.base_agent import BaseAgent, AgentConfig

class Task(BaseModel):
    """Model for tasks assigned to specialized agents"""
    task_id: str
    agent_type: str
    priority: int
    data: Dict[str, Any]
    status: str = "pending"

class ManagerAgent(BaseAgent):
    """Agent responsible for orchestrating all other agents"""
    
    def _setup_tools(self) -> List[Tool]:
        """Setup tools for the manager agent"""
        return [
            Tool(
                name="analyze_website",
                func=self._analyze_website_tool,
                description="Analyze a website's content, SEO, and performance metrics"
            ),
            Tool(
                name="delegate_task",
                func=self._delegate_task_tool,
                description="Delegate a task to a specialized agent"
            ),
            Tool(
                name="check_task_status",
                func=self._check_task_status_tool,
                description="Check the status of a delegated task"
            )
        ]
    
    def _setup_agent_executor(self) -> AgentExecutor:
        """Setup the LangChain agent executor with custom prompt"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the manager agent responsible for orchestrating website optimization tasks.
            You analyze website data and delegate tasks to specialized agents.
            Use the available tools to process requests and manage tasks effectively.
            Consider past interactions when making decisions."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        agent = create_openai_functions_agent(
            llm=self.llm,
            prompt=prompt,
            tools=self.tools
        )
        
        return AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=self.tools,
            memory=self.memory_manager.conversation_memory,
            verbose=True
        )
    
    async def initialize(self) -> None:
        """Initialize connections and resources"""
        await super().initialize()
        self.redis_client = redis.from_url(self.config.redis_url)
        self.session = aiohttp.ClientSession()
        
        self.agent_endpoints = {
            "read": "http://read_agent:8001",
            "content_update": "http://content_update_agent:8002",
            "seo_optimization": "http://seo_optimization_agent:8003",
            "error_fixing": "http://error_fixing_agent:8004",
            "content_generation": "http://content_generation_agent:8005",
            "performance_monitor": "http://performance_monitor_agent:8006"
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        await super().cleanup()
        await self.session.close()
        await self.redis_client.close()
    
    async def _analyze_website_tool(self, url: str) -> Dict[str, Any]:
        """Tool for analyzing website data"""
        async with self.session.post(
            f"{self.agent_endpoints['read']}/process",
            json={"url": url}
        ) as response:
            website_data = await response.json()
            
            # Store website data in memory for future reference
            await self.memory_manager.add_document(
                website_data,
                metadata={"type": "website_analysis", "url": url}
            )
            
            return website_data
    
    async def _delegate_task_tool(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tool for delegating tasks to specialized agents"""
        task = Task(**task_data)
        endpoint = self.agent_endpoints.get(task.agent_type)
        
        if not endpoint:
            raise ValueError(f"Unknown agent type: {task.agent_type}")
        
        async with self.session.post(
            f"{endpoint}/process",
            json=task.dict()
        ) as response:
            result = await response.json()
            
            # Store task result in memory
            await self.memory_manager.add_document(
                result,
                metadata={
                    "type": "task_result",
                    "task_id": task.task_id,
                    "agent_type": task.agent_type
                }
            )
            
            return result
    
    async def _check_task_status_tool(self, task_id: str) -> Dict[str, Any]:
        """Tool for checking task status"""
        # Search memory for task results
        similar = await self.memory_manager.search_similar_interactions(
            f"task_id:{task_id}",
            k=1
        )
        
        if similar:
            return similar[0]["content"]
        return {"status": "not_found", "task_id": task_id}
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests using LangChain agent"""
        # Use the agent executor to process the request
        result = await self.agent_executor.arun(
            input=json.dumps(data)
        )
        
        return {
            "result": result,
            "status": "completed"
        }

if __name__ == "__main__":
    config = AgentConfig(
        name="manager_agent",
        port=8000,
        model_name="gpt-4",  # Use GPT-4 for better orchestration
        temperature=0.7
    )
    
    agent = ManagerAgent(config)
    agent.start() 