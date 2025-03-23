"""Test file for CI/CD Deployment Agent."""

import os
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from agentx.common_libraries.base_agent import AgentConfig
from agentx.common_libraries.system_config import SystemConfig
from agentx.cicd_deployment_agent.cicd_deployment_agent import CICDDeploymentAgent

@pytest.fixture
def mock_system_config():
    """Create a mock system configuration."""
    config = MagicMock(spec=SystemConfig)
    config.api_keys = {"github_token": "test_token"}
    config.github = MagicMock()
    config.github.repo_owner = "metacatalysthq"
    config.github.repo_name = "landing-page"
    config.model = MagicMock()
    config.model.name = "test-model"
    config.model.temperature = 0.7
    config.model.max_tokens = 1000
    config.model.top_p = 0.95
    return config

@pytest.fixture
def mock_agent_config():
    """Create a mock agent configuration."""
    return AgentConfig(
        name="test_cicd_agent",
        description="Test CI/CD Agent",
        model_name="test-model",
        temperature=0.7,
        max_tokens=1000,
        top_p=0.95
    )

@pytest.fixture
def mock_github_controller():
    """Create a mock GitHub controller."""
    controller = MagicMock()
    controller.checkout_branch.return_value = True
    controller.create_pull_request.return_value = {"url": "https://github.com/test/pr/1"}
    return controller

@pytest.mark.asyncio
async def test_task_completion_tracking():
    """Test task completion tracking functionality."""
    with patch("agentx.cicd_deployment_agent.cicd_deployment_agent.GitHubController") as mock_github:
        # Setup
        system_config = mock_system_config()
        agent_config = mock_agent_config()
        agent = CICDDeploymentAgent(agent_config, system_config)
        
        # Test initial state
        assert not any(agent.completed_tasks.values())
        
        # Test task completion
        await agent.process({"task_type": "performance_monitoring"})
        assert agent.completed_tasks["performance_monitoring"]
        assert not agent.completed_tasks["seo_optimization"]

@pytest.mark.asyncio
async def test_audit_comparison():
    """Test audit results comparison."""
    with patch("agentx.cicd_deployment_agent.cicd_deployment_agent.GitHubController") as mock_github:
        # Setup
        system_config = mock_system_config()
        agent_config = mock_agent_config()
        agent = CICDDeploymentAgent(agent_config, system_config)
        
        # Test cases
        old_results = {
            "performance": 0.8,
            "accessibility": 0.7,
            "best_practices": 0.9,
            "seo": 0.85
        }
        
        better_results = {
            "performance": 0.85,
            "accessibility": 0.75,
            "best_practices": 0.95,
            "seo": 0.9
        }
        
        worse_results = {
            "performance": 0.75,
            "accessibility": 0.65,
            "best_practices": 0.85,
            "seo": 0.8
        }
        
        # Test comparisons
        assert agent.compare_audit_results(old_results, better_results)
        assert not agent.compare_audit_results(old_results, worse_results)

@pytest.mark.asyncio
async def test_deployment_workflow():
    """Test the complete deployment workflow."""
    with patch("agentx.cicd_deployment_agent.cicd_deployment_agent.GitHubController") as mock_github, \
         patch("subprocess.Popen") as mock_popen, \
         patch("subprocess.check_output") as mock_check_output, \
         patch("subprocess.run") as mock_run:
        
        # Setup mocks
        mock_popen.return_value = MagicMock()
        mock_check_output.return_value = b"Server is running"
        mock_run.return_value = MagicMock(returncode=0)
        
        # Setup agent
        system_config = mock_system_config()
        agent_config = mock_agent_config()
        agent = CICDDeploymentAgent(agent_config, system_config)
        
        # Mock audit results
        async def mock_run_auditor(url):
            if "3000" in url:  # Old version
                return {
                    "performance": 0.8,
                    "accessibility": 0.7,
                    "best_practices": 0.9,
                    "seo": 0.85
                }
            else:  # New version
                return {
                    "performance": 0.85,
                    "accessibility": 0.75,
                    "best_practices": 0.95,
                    "seo": 0.9
                }
        
        agent.run_auditor = mock_run_auditor
        
        # Complete all tasks
        for task_type in agent.completed_tasks:
            await agent.process({"task_type": task_type})
        
        # Verify all tasks are marked as completed
        assert all(agent.completed_tasks.values())

async def main():
    """Run the tests."""
    # Run the tests
    await test_task_completion_tracking()
    await test_audit_comparison()
    await test_deployment_workflow()
    print("All tests passed!")

if __name__ == "__main__":
    asyncio.run(main()) 