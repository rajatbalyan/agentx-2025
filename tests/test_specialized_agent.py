"""Test suite for Specialized Agent functionality."""

import pytest
from agentx.agents.specialized_agent import SpecializedAgent
from unittest.mock import Mock, patch
import asyncio

@pytest.fixture
def web_agent():
    """Create a web agent for testing."""
    return SpecializedAgent(
        agent_type="web",
        capabilities=["html", "css", "js"],
        agent_id="web_agent_1"
    )

@pytest.fixture
def security_agent():
    """Create a security agent for testing."""
    return SpecializedAgent(
        agent_type="security",
        capabilities=["audit", "scan", "vulnerability"],
        agent_id="security_agent_1"
    )

def test_agent_initialization(web_agent):
    """Test agent initialization."""
    assert web_agent.agent_type == "web"
    assert web_agent.capabilities == ["html", "css", "js"]
    assert web_agent.agent_id == "web_agent_1"

def test_can_handle_task(web_agent):
    """Test task handling capability check."""
    # Task that agent can handle
    task = {
        "id": "task1",
        "type": "web_task",
        "required_capabilities": ["html", "css"]
    }
    assert web_agent.can_handle_task(task)

    # Task that agent cannot handle
    task = {
        "id": "task2",
        "type": "web_task",
        "required_capabilities": ["html", "python"]
    }
    assert not web_agent.can_handle_task(task)

def test_execute_web_task(web_agent):
    """Test web task execution."""
    task = {
        "id": "task1",
        "type": "web_task",
        "action": "analyze_page",
        "url": "https://example.com",
        "required_capabilities": ["html"]
    }
    
    result = web_agent.execute_task(task)
    assert result["status"] == "completed"
    assert "analysis" in result
    assert "results" in result
    assert "validation" in result
    assert result["validation"]["valid"]

def test_execute_security_task(security_agent):
    """Test security task execution."""
    task = {
        "id": "task1",
        "type": "security_task",
        "action": "vulnerability_scan",
        "target": "https://example.com",
        "required_capabilities": ["scan", "vulnerability"]
    }
    
    result = security_agent.execute_task(task)
    assert result["status"] == "completed"
    assert "analysis" in result
    assert "results" in result
    assert "validation" in result
    assert result["validation"]["valid"]

def test_execute_invalid_task(web_agent):
    """Test execution of invalid task."""
    task = {
        "id": "task1",
        "type": "invalid_task",
        "action": "unknown_action"
    }
    
    result = web_agent.execute_task(task)
    assert result["status"] == "failed"
    assert "error" in result
    assert "Invalid task type" in result["error"]

def test_task_execution_error_handling(web_agent):
    """Test error handling during task execution."""
    task = {
        "id": "task1",
        "type": "web_task",
        "action": "analyze_page",
        # Missing required URL
    }
    
    result = web_agent.execute_task(task)
    assert result["status"] == "failed"
    assert "error" in result
    assert "Missing required field: url" in result["error"]

@pytest.mark.asyncio
async def test_web_task_actual_execution(web_agent):
    """Test actual web task execution with page analysis."""
    task = {
        "id": "task1",
        "type": "web_task",
        "action": "analyze_page",
        "url": "https://example.com",
        "required_capabilities": ["html"],
        "analysis_requirements": {
            "check_accessibility": True,
            "validate_html": True,
            "check_performance": True
        }
    }
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.text = Mock(return_value="""
        <!DOCTYPE html>
        <html>
            <head><title>Test Page</title></head>
            <body>
                <header><nav>Menu</nav></header>
                <main><h1>Content</h1></main>
                <footer>Footer</footer>
            </body>
        </html>
        """)
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await web_agent.execute_task_async(task)
        
        assert result["status"] == "completed"
        assert result["analysis"]["url"] == "https://example.com"
        assert len(result["analysis"]["components"]) > 0
        assert "header" in result["analysis"]["components"]
        assert "main" in result["analysis"]["components"]
        assert "footer" in result["analysis"]["components"]
        assert "accessibility_score" in result["results"]
        assert "html_validation" in result["results"]
        assert "performance_metrics" in result["results"]
        
        # Verify CI/CD notification was sent
        assert result["ci_cd_notification"]["status"] == "sent"
        assert result["ci_cd_notification"]["task_id"] == "task1"

@pytest.mark.asyncio
async def test_security_task_actual_execution(security_agent):
    """Test actual security task execution with vulnerability scan."""
    task = {
        "id": "task2",
        "type": "security_task",
        "action": "vulnerability_scan",
        "target": "https://example.com",
        "required_capabilities": ["scan", "vulnerability"],
        "scan_config": {
            "scan_depth": "deep",
            "check_ssl": True,
            "port_scan": True
        }
    }
    
    with patch('agentx.agents.security.scanner.SecurityScanner.scan') as mock_scan:
        # Mock the security scan results
        mock_scan.return_value = {
            "vulnerabilities": [
                {
                    "type": "SSL",
                    "severity": "medium",
                    "description": "Outdated SSL version"
                }
            ],
            "open_ports": [80, 443],
            "ssl_info": {
                "version": "TLS 1.2",
                "expires": "2024-12-31"
            }
        }
        
        result = await security_agent.execute_task_async(task)
        
        assert result["status"] == "completed"
        assert result["analysis"]["target"] == "https://example.com"
        assert "vulnerabilities" in result["analysis"]
        assert len(result["analysis"]["vulnerabilities"]) > 0
        assert "ssl_analysis" in result["results"]
        assert "port_scan_results" in result["results"]
        
        # Verify CI/CD notification was sent
        assert result["ci_cd_notification"]["status"] == "sent"
        assert result["ci_cd_notification"]["task_id"] == "task2"

@pytest.mark.asyncio
async def test_task_progress_reporting(web_agent):
    """Test task progress reporting during execution."""
    task = {
        "id": "task3",
        "type": "web_task",
        "action": "analyze_page",
        "url": "https://example.com",
        "required_capabilities": ["html"],
        "report_progress": True
    }
    
    progress_updates = []
    
    def progress_callback(update):
        progress_updates.append(update)
    
    result = await web_agent.execute_task_async(task, progress_callback=progress_callback)
    
    assert result["status"] == "completed"
    assert len(progress_updates) > 0
    assert any(update["stage"] == "initialization" for update in progress_updates)
    assert any(update["stage"] == "analysis" for update in progress_updates)
    assert any(update["stage"] == "completion" for update in progress_updates)

@pytest.mark.asyncio
async def test_task_cancellation(web_agent):
    """Test task cancellation during execution."""
    task = {
        "id": "task4",
        "type": "web_task",
        "action": "analyze_page",
        "url": "https://example.com",
        "required_capabilities": ["html"],
        "analysis_requirements": {
            "check_accessibility": True,
            "validate_html": True,
            "check_performance": True
        }
    }
    
    # Create a future to control task cancellation
    cancel_event = asyncio.Event()
    
    async def cancel_task():
        await asyncio.sleep(0.1)  # Wait a bit before cancelling
        cancel_event.set()
    
    # Start cancellation task
    asyncio.create_task(cancel_task())
    
    result = await web_agent.execute_task_async(task, cancel_event=cancel_event)
    
    assert result["status"] == "cancelled"
    assert "partial_results" in result
    assert result["ci_cd_notification"]["status"] == "sent"
    assert result["ci_cd_notification"]["result"] == "cancelled" 