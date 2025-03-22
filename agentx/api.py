"""API endpoints for AgentX."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import structlog
from agentx.system import AgentXSystem
from pathlib import Path

logger = structlog.get_logger()
app = FastAPI(title="AgentX API")

# Initialize system
config_path = Path("config/agentx.config.yaml")
system = AgentXSystem(str(config_path))

# Store for task history
task_history: List[Dict[str, Any]] = []

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup."""
    try:
        await system.initialize()
        logger.info("System initialized successfully")
    except Exception as e:
        logger.error("Error initializing system", error=str(e))
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up system on shutdown."""
    try:
        await system.cleanup()
        logger.info("System cleaned up")
    except Exception as e:
        logger.error("Error during cleanup", error=str(e))

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
        
        # Store task in history
        task_record = {
            "task_type": request.task_type,
            "priority": request.priority,
            "data": request.data,
            "result": result,
            "subtasks": result.get("manager_actions", {}).get("tasks", [])
        }
        task_history.append(task_record)
        
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        logger.error("task_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks")
async def list_tasks() -> Dict[str, Any]:
    """List all tasks and their results."""
    return {
        "status": "success",
        "tasks": task_history
    }

@app.get("/api/tasks/summary")
async def get_task_summary() -> Dict[str, Any]:
    """Get a summary of all tasks."""
    try:
        total_tasks = len(task_history)
        tasks_by_type = {}
        tasks_by_priority = {1: 0, 2: 0, 3: 0}
        subtasks_created = 0
        
        for task in task_history:
            # Count by type
            task_type = task["task_type"]
            tasks_by_type[task_type] = tasks_by_type.get(task_type, 0) + 1
            
            # Count by priority
            priority = task.get("priority", 1)
            tasks_by_priority[priority] = tasks_by_priority.get(priority, 0) + 1
            
            # Count subtasks
            subtasks = task.get("subtasks", [])
            subtasks_created += len(subtasks)
        
        return {
            "status": "success",
            "summary": {
                "total_tasks": total_tasks,
                "tasks_by_type": tasks_by_type,
                "tasks_by_priority": tasks_by_priority,
                "subtasks_created": subtasks_created
            }
        }
    except Exception as e:
        logger.error("Error generating task summary", error=str(e))
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
    try:
        status_info = {
            "status": "running",
            "active_agents": list(system.agents.keys()),
            "agent_details": {}
        }
        
        # Get detailed agent information
        for name, agent in system.agents.items():
            agent_info = {
                "status": "active",
                "type": agent.__class__.__name__
            }
            # Add any agent-specific metrics if available
            if hasattr(agent, "get_metrics"):
                try:
                    agent_info["metrics"] = agent.get_metrics()
                except:
                    agent_info["metrics"] = {}
            
            status_info["agent_details"][name] = agent_info
        
        # Add task statistics
        status_info["task_stats"] = {
            "total_tasks": len(task_history),
            "recent_tasks": task_history[-5:] if task_history else []
        }
        
        return status_info
    except Exception as e:
        logger.error("status_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) 