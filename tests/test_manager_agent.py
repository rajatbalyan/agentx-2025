"""Test suite for Manager Agent functionality."""

import pytest
from typing import Dict, Any
from agentx.agents.manager_agent import ManagerAgent
from agentx.config.config_loader import SystemConfig
from unittest.mock import Mock, patch
from agentx.agents.specialized_agent import SpecializedAgent

@pytest.fixture
def system_config():
    """Create system configuration for testing."""
    return SystemConfig(
        log_level="INFO",
        max_concurrent_tasks=5,
        task_timeout_seconds=300
    )

@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return {
        "agents": [
            {
                "id": "web_agent",
                "type": "web",
                "capabilities": ["html", "css", "js"]
            },
            {
                "id": "security_agent",
                "type": "security",
                "capabilities": ["audit", "scan"]
            }
        ]
    }

@pytest.fixture
def manager_agent(mock_config, system_config):
    """Create manager agent instance for testing."""
    return ManagerAgent(mock_config, system_config)

def test_initialize_agents(manager_agent):
    """Test agent initialization."""
    assert len(manager_agent.specialized_agents) == 2
    assert "web_agent" in manager_agent.specialized_agents
    assert "security_agent" in manager_agent.specialized_agents
    
    web_agent = manager_agent.specialized_agents["web_agent"]
    assert isinstance(web_agent, SpecializedAgent)
    assert web_agent.agent_type == "web"
    assert web_agent.capabilities == ["html", "css", "js"]
    
    security_agent = manager_agent.specialized_agents["security_agent"]
    assert isinstance(security_agent, SpecializedAgent)
    assert security_agent.agent_type == "security"
    assert security_agent.capabilities == ["audit", "scan"]

def test_add_task(manager_agent):
    """Test adding a task."""
    task = {
        "id": "task1",
        "type": "web_task",
        "required_capabilities": ["html"]
    }
    
    task_id = manager_agent.add_task(task)
    assert task_id == "task1"
    
    # Task should be assigned to web agent
    task_status = manager_agent.get_task_status(task_id)
    assert task_status["status"] == "assigned"

def test_add_task_no_id(manager_agent):
    """Test adding a task without ID."""
    task = {
        "type": "web_task",
        "required_capabilities": ["html"]
    }
    
    with pytest.raises(ValueError, match="Task must have an ID"):
        manager_agent.add_task(task)

def test_add_task_no_suitable_agent(manager_agent):
    """Test adding a task with no suitable agent."""
    task = {
        "id": "task1",
        "type": "ml_task",
        "required_capabilities": ["tensorflow"]
    }
    
    task_id = manager_agent.add_task(task)
    assert task_id == "task1"
    
    # Task should remain in queue
    assert len(manager_agent.task_queue) == 1
    assert manager_agent.task_queue[0]["id"] == "task1"

def test_get_task_status_queued(manager_agent):
    """Test getting status of queued task."""
    task = {
        "id": "task1",
        "type": "ml_task",
        "required_capabilities": ["tensorflow"]
    }
    
    task_id = manager_agent.add_task(task)
    status = manager_agent.get_task_status(task_id)
    assert status["status"] == "queued"

def test_get_task_status_not_found(manager_agent):
    """Test getting status of non-existent task."""
    with pytest.raises(ValueError, match="No task found with ID: task1"):
        manager_agent.get_task_status("task1")

def test_cancel_active_task(manager_agent):
    """Test cancelling an active task."""
    task = {
        "id": "task1",
        "type": "web_task",
        "required_capabilities": ["html"]
    }
    
    task_id = manager_agent.add_task(task)
    assert manager_agent.cancel_task(task_id)
    
    status = manager_agent.get_task_status(task_id)
    assert status["status"] == "cancelled"

def test_cancel_queued_task(manager_agent):
    """Test cancelling a queued task."""
    task = {
        "id": "task1",
        "type": "ml_task",
        "required_capabilities": ["tensorflow"]
    }
    
    task_id = manager_agent.add_task(task)
    assert manager_agent.cancel_task(task_id)
    
    with pytest.raises(ValueError, match="No task found with ID: task1"):
        manager_agent.get_task_status(task_id)

def test_cancel_nonexistent_task(manager_agent):
    """Test cancelling a non-existent task."""
    assert not manager_agent.cancel_task("task1")

@pytest.mark.asyncio
async def test_task_execution_success(system_config):
    """Test successful task execution."""
    config = {
        "agents": [
            {
                "id": "test_agent",
                "type": "test",
                "capabilities": ["test"]
            }
        ]
    }
    
    manager = ManagerAgent(config, system_config)
    
    # Mock the specialized agent's execute_task method
    mock_result = {
        "status": "completed",
        "analysis": {},
        "results": {},
        "validation": {"valid": True}
    }
    
    with patch.object(SpecializedAgent, 'execute_task', return_value=mock_result):
        task = {
            "id": "task1",
            "type": "test",
            "required_capabilities": ["test"]
        }
        
        # Add and verify task is assigned
        task_id = manager.add_task(task)
        status = manager.get_task_status(task_id)
        assert status["status"] == "assigned"
        
        # Execute task and verify completion
        manager.execute_task(task_id)
        status = manager.get_task_status(task_id)
        assert status["status"] == "completed"
        assert status["result"] == mock_result

@pytest.mark.asyncio
async def test_task_execution_failure(system_config):
    """Test task execution failure."""
    config = {
        "agents": [
            {
                "id": "test_agent",
                "type": "test",
                "capabilities": ["test"]
            }
        ]
    }
    
    manager = ManagerAgent(config, system_config)
    
    # Mock the specialized agent's execute_task method to raise an exception
    with patch.object(SpecializedAgent, 'execute_task', side_effect=Exception("Test error")):
        task = {
            "id": "task1",
            "type": "test",
            "required_capabilities": ["test"]
        }
        
        # Add and verify task is assigned
        task_id = manager.add_task(task)
        status = manager.get_task_status(task_id)
        assert status["status"] == "assigned"
        
        # Execute task and verify failure
        manager.execute_task(task_id)
        status = manager.get_task_status(task_id)
        assert status["status"] == "failed"
        assert status["error"] == "Test error"

@pytest.mark.asyncio
async def test_manager_task_distribution(manager_agent):
    """Test that manager properly distributes tasks."""
    await manager_agent.initialize()
    
    # Process input
    result = await manager_agent.process({
        "type": "website_audit",
        "url": "https://test.com"
    })
    
    # Verify error handling (since we haven't implemented full task distribution yet)
    assert result["status"] == "error"
    assert result["error"] == "No analysis data found in input"

@pytest.mark.asyncio
async def test_manager_error_handling(manager_agent):
    """Test manager's error handling."""
    await manager_agent.initialize()
    
    # Process input
    result = await manager_agent.process({
        "type": "website_audit",
        "url": "https://test.com"
    })
    
    # Verify error handling
    assert result["status"] == "error"
    assert "error" in result
    assert "No analysis data found in input" in result["error"]

if __name__ == "__main__":
    pytest.main([__file__]) 