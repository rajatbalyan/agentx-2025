"""
Smoke tests for Site-Sentry.
Tests config loading, LLM provider factory, and pipeline initialization.
These tests do NOT make real API calls or run Lighthouse.
"""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


def make_test_config(tmp_path: Path) -> Path:
    """Create a minimal valid config for testing."""
    config = {
        "website_url": "https://example.com",
        "workspace_path": str(tmp_path),
        "llm": {
            "provider": "nvidia_nim",
            "manager_model": "deepseek-ai/deepseek-v3-2",
            "agent_model": "deepseek-ai/deepseek-v4-flash",
        },
        "memory": {"enabled": False},
        "github": {"repo_owner": "", "repo_name": ""},
    }
    config_path = tmp_path / "sentry.config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f)
    return config_path


class TestConfig:
    def test_load_valid_config(self, tmp_path):
        from site_sentry.config.schema import SentryConfig

        config_path = make_test_config(tmp_path)
        config = SentryConfig.load(str(config_path))
        assert config.website_url == "https://example.com"
        assert config.llm.provider == "nvidia_nim"

    def test_url_validation(self, tmp_path):
        from site_sentry.config.schema import SentryConfig
        from pydantic import ValidationError

        with pytest.raises((ValidationError, ValueError)):
            SentryConfig(website_url="not-a-url")

    def test_missing_config_file(self):
        from site_sentry.config.schema import SentryConfig

        with pytest.raises(FileNotFoundError):
            SentryConfig.load("nonexistent.yaml")


class TestLighthouseNormalize:
    def test_normalize_scores(self):
        """Test that we correctly extract scores from Lighthouse JSON."""
        from site_sentry.auditor.lighthouse import _normalize

        fake_raw = {
            "fetchTime": "2025-01-01",
            "lighthouseVersion": "12.0",
            "userAgent": "test",
            "categories": {
                "performance": {"score": 0.72, "auditRefs": []},
                "seo": {"score": 0.95, "auditRefs": []},
                "best-practices": {"score": 0.83, "auditRefs": []},
                "accessibility": {"score": 0.88, "auditRefs": []},
            },
            "audits": {},
        }
        result = _normalize(fake_raw, "https://example.com")
        assert result["scores"]["performance"] == 72.0
        assert result["scores"]["seo"] == 95.0
        assert result["url"] == "https://example.com"


class TestGitHubController:
    def test_branch_name_generation(self):
        from site_sentry.github.controller import GitHubController

        name = GitHubController.generate_branch_name("sentry/fix")
        assert name.startswith("sentry/fix-")
        assert len(name) > 15

    def test_missing_token_raises(self):
        from site_sentry.github.controller import GitHubController

        with pytest.raises(ValueError, match="token"):
            GitHubController(token="", repo_owner="test", repo_name="repo")


class TestPipelineInit:
    def test_pipeline_no_github(self, tmp_path):
        """Pipeline should init without GitHub credentials (dry-run mode)."""
        from site_sentry.config.schema import SentryConfig
        from site_sentry.pipeline import SentryPipeline

        config_path = make_test_config(tmp_path)
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-test"}):
            config = SentryConfig.load(str(config_path))
            with patch("site_sentry.core.llm_provider.get_llm") as mock_llm:
                mock_llm.return_value = MagicMock()
                pipeline = SentryPipeline(config)
                assert pipeline.github is None  # No credentials configured


class TestAccessibilityAgent:
    def test_accessibility_agent_no_issues(self, tmp_path):
        """Agent returns empty changes when no issues are passed."""
        import asyncio

        from site_sentry.agents.accessibility_agent import AccessibilityAgent
        from site_sentry.config.schema import SentryConfig

        config_path = make_test_config(tmp_path)
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-test"}):
            config = SentryConfig.load(str(config_path))
            with patch("site_sentry.core.llm_provider.get_llm") as mock_llm:
                mock_llm.return_value = MagicMock()
                agent = AccessibilityAgent(config)
                result = asyncio.run(
                    agent.process({"issues": [], "url": "https://example.com"})
                )
                assert result["status"] == "success"
                assert result["changes"] == []

    def test_accessibility_agent_in_agents_init(self):
        """AccessibilityAgent is exported from the agents package."""
        from site_sentry.agents import AccessibilityAgent

        assert AccessibilityAgent is not None

    def test_accessibility_toggle_in_config(self, tmp_path):
        """accessibility toggle exists in AgentToggleConfig and defaults to True."""
        from site_sentry.config.schema import AgentToggleConfig

        toggle = AgentToggleConfig()
        assert hasattr(toggle, "accessibility")
        assert toggle.accessibility is True

    def test_accessibility_wired_in_manager(self):
        """AccessibilityAgent is registered in ManagerAgent.agents dict."""
        import inspect

        from site_sentry.agents.manager_agent import ManagerAgent

        src = inspect.getsource(ManagerAgent.__init__)
        assert '"accessibility"' in src or "'accessibility'" in src
