"""Test suite for configuration loader."""

import pytest
from pathlib import Path
import yaml
from agentx.config.config_loader import ConfigLoader, AgentConfig

@pytest.fixture
def test_config_path(tmp_path):
    """Create a temporary test configuration file."""
    config_data = {
        "system": {
            "log_level": "INFO",
            "max_concurrent_tasks": 5,
            "task_timeout_seconds": 300
        },
        "agents": [
            {
                "id": "test_agent",
                "type": "test",
                "capabilities": ["test1", "test2"],
                "max_tasks": 2,
                "priority": "high"
            }
        ],
        "task_types": {
            "test_task": {
                "required_capabilities": ["test1"],
                "default_priority": "medium"
            }
        },
        "priorities": {
            "critical": 100,
            "high": 75,
            "medium": 50,
            "low": 25
        },
        "task_queue": {
            "max_size": 100,
            "retry_limit": 3,
            "retry_delay_seconds": 60
        }
    }
    
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    return str(config_file)

@pytest.fixture
def config_loader(test_config_path):
    """Create a configuration loader instance."""
    return ConfigLoader(test_config_path)

def test_load_config(config_loader):
    """Test loading configuration."""
    config = config_loader.load_config()
    assert isinstance(config, AgentConfig)
    assert config.system.log_level == "INFO"
    assert config.system.max_concurrent_tasks == 5
    assert len(config.agents) == 1
    assert config.agents[0].id == "test_agent"

def test_get_agent_config(config_loader):
    """Test getting agent configuration."""
    agent_config = config_loader.get_agent_config("test_agent")
    assert agent_config is not None
    assert agent_config.type == "test"
    assert agent_config.capabilities == ["test1", "test2"]
    assert agent_config.max_tasks == 2
    assert agent_config.priority == "high"

def test_get_nonexistent_agent_config(config_loader):
    """Test getting configuration for non-existent agent."""
    agent_config = config_loader.get_agent_config("nonexistent")
    assert agent_config is None

def test_get_task_type_config(config_loader):
    """Test getting task type configuration."""
    task_config = config_loader.get_task_type_config("test_task")
    assert task_config is not None
    assert task_config.required_capabilities == ["test1"]
    assert task_config.default_priority == "medium"

def test_get_nonexistent_task_type_config(config_loader):
    """Test getting configuration for non-existent task type."""
    task_config = config_loader.get_task_type_config("nonexistent")
    assert task_config is None

def test_get_priority_weight(config_loader):
    """Test getting priority weight."""
    assert config_loader.get_priority_weight("critical") == 100
    assert config_loader.get_priority_weight("high") == 75
    assert config_loader.get_priority_weight("medium") == 50
    assert config_loader.get_priority_weight("low") == 25
    assert config_loader.get_priority_weight("nonexistent") == 0

def test_validate_agent_capabilities(config_loader):
    """Test validating agent capabilities."""
    assert config_loader.validate_agent_capabilities("test_agent", "test_task")
    assert not config_loader.validate_agent_capabilities("nonexistent", "test_task")
    assert not config_loader.validate_agent_capabilities("test_agent", "nonexistent")

def test_get_system_config(config_loader):
    """Test getting system configuration."""
    system_config = config_loader.get_system_config()
    assert system_config.log_level == "INFO"
    assert system_config.max_concurrent_tasks == 5
    assert system_config.task_timeout_seconds == 300

def test_get_task_queue_config(config_loader):
    """Test getting task queue configuration."""
    queue_config = config_loader.get_task_queue_config()
    assert queue_config.max_size == 100
    assert queue_config.retry_limit == 3
    assert queue_config.retry_delay_seconds == 60

def test_invalid_config_file():
    """Test loading invalid configuration file."""
    with pytest.raises(Exception):
        ConfigLoader("nonexistent_file.yaml").load_config()

def test_invalid_config_data(tmp_path):
    """Test loading configuration with invalid data."""
    config_data = {
        "system": {
            "log_level": "INFO",
            "max_concurrent_tasks": -1  # Invalid value
        }
    }
    
    config_file = tmp_path / "invalid_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    with pytest.raises(Exception):
        ConfigLoader(str(config_file)).load_config()

def test_invalid_priority(tmp_path):
    """Test configuration with invalid priority."""
    config_data = {
        "system": {
            "log_level": "INFO",
            "max_concurrent_tasks": 5,
            "task_timeout_seconds": 300
        },
        "agents": [
            {
                "id": "test_agent",
                "type": "test",
                "capabilities": ["test1"],
                "max_tasks": 2,
                "priority": "invalid"  # Invalid priority
            }
        ],
        "task_types": {},
        "priorities": {
            "high": 75,
            "medium": 50,
            "low": 25
        },
        "task_queue": {
            "max_size": 100,
            "retry_limit": 3,
            "retry_delay_seconds": 60
        }
    }
    
    config_file = tmp_path / "invalid_priority.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    with pytest.raises(ValueError, match="Priority must be one of"):
        ConfigLoader(str(config_file)).load_config()

def test_missing_required_fields(tmp_path):
    """Test configuration with missing required fields."""
    config_data = {
        "system": {
            "log_level": "INFO"
        }
    }
    
    config_file = tmp_path / "missing_fields.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    with pytest.raises(Exception):
        ConfigLoader(str(config_file)).load_config() 