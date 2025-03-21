"""API endpoints for AgentX."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import structlog
from agentx.system import AgentXSystem
from pathlib import Path

logger = structlog.get_logger()
app = FastAPI(title="AgentX API")

# Initialize system
config_path = Path("config/agentx.config.yaml")
system = AgentXSystem(str(config_path))

class TaskRequest(BaseModel):
    """Request model for tasks."""
    task_type: str
    data: Dict[str, Any]
    priority: Optional[int] = 1

@app.post("/api/tasks")
async def create_task(request: TaskRequest) -> Dict[str, Any]:
    """Create a new task."""
    try:
        # Process the task through the system
        result = await system.process_task(request.task_type, request.data)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        logger.error("task_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Check system health."""
    return {
        "status": "healthy",
        "agents": {
            name: agent.health_check()
            for name, agent in system.agents.items()
        }
    }

@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    """Get system status."""
    return {
        "status": "running",
        "active_agents": list(system.agents.keys()),
        "memory_stats": {
            "vector_store_size": len(system.chroma_client.get_collection("code_entities").get()["ids"])
        }
    } 