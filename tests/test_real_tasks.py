"""Test real tasks with the landing page codebase."""

import pytest
import asyncio
from agentx.agents.specialized_agent import SpecializedAgent
import os

WORKSPACE_PATH = "d:/Programming/Projects/landing-page"

@pytest.fixture
def web_agent():
    """Create a web agent for testing."""
    return SpecializedAgent(
        agent_type="web",
        capabilities=["html", "css", "js"],
        agent_id="web_agent_1",
        workspace_path=WORKSPACE_PATH
    )

@pytest.fixture
def security_agent():
    """Create a security agent for testing."""
    return SpecializedAgent(
        agent_type="security",
        capabilities=["audit", "scan", "vulnerability"],
        agent_id="security_agent_1",
        workspace_path=WORKSPACE_PATH
    )

def progress_callback(progress_data):
    """Print progress updates."""
    print(f"Progress Update: {progress_data}")

@pytest.mark.asyncio
async def test_analyze_metacatalyst_homepage():
    # Initialize web agent
    agent = SpecializedAgent(
        agent_type='web',
        capabilities=['html', 'css', 'js'],
        agent_id='web_agent_1',
        workspace_path='web_analysis'  # Use a local directory for analysis
    )
    
    # Define task
    task = {
        'id': 'test1',
        'type': 'web_task',
        'action': 'analyze_page',
        'target': 'http://metacatalyst.in',
        'requirements': {
            'check_accessibility': True,
            'validate_html': True,
            'check_performance': True
        }
    }
    
    # Execute task
    result = await agent.execute_task(task)
    
    # Assertions
    assert result is not None
    assert result.get('status') == 'completed'
    assert 'analysis' in result
    assert 'tracked_files' in result
    
    # Print results for inspection
    print("\nTask Results:")
    print(f"Status: {result.get('status')}")
    print(f"Analysis: {result.get('analysis')}")
    print(f"Tracked Files: {result.get('tracked_files')}")

@pytest.mark.asyncio
async def test_security_scan_codebase(security_agent):
    """Test scanning the landing page codebase for security issues."""
    task = {
        "id": "security_task_1",
        "type": "security_task",
        "action": "vulnerability_scan",
        "target": WORKSPACE_PATH,
        "required_capabilities": ["scan", "vulnerability"],
        "scan_config": {
            "scan_depth": "deep",
            "check_ssl": True,
            "port_scan": True,
            "check_secrets": True
        }
    }
    
    result = await security_agent.execute_task_async(task, progress_callback=progress_callback)
    print("\nSecurity Task Result:", result)
    
    assert result["status"] == "completed"
    assert "analysis" in result
    assert "vulnerabilities" in result["analysis"]
    assert result["ci_cd_notification"]["status"] == "sent"

if __name__ == "__main__":
    asyncio.run(test_analyze_metacatalyst_homepage())
    asyncio.run(test_security_scan_codebase(security_agent())) 