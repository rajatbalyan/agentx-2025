"""Read agent for AgentX framework."""

from typing import Dict, Any, List
import asyncio
import json
import subprocess
from datetime import datetime
import structlog
from pathlib import Path
from langchain.schema import HumanMessage, SystemMessage
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig
from agentx.common_libraries.system_config import SystemConfig
from agentx.common_libraries.code_indexer import CodeIndexer

logger = structlog.get_logger()

class ReadAgent(BaseAgent):
    """Agent responsible for reading and analyzing website content"""
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig):
        super().__init__(config, system_config)
        self.logger = logger.bind(agent="read_agent")
        
        # Get workspace path from configuration
        workspace_path = system_config.workspace.path
        
        # Convert relative path to absolute
        if workspace_path == '.':
            workspace_path = Path.cwd().absolute()
        else:
            workspace_path = Path(workspace_path).absolute()
            
        self.logger.info("Initializing code indexer", workspace_path=str(workspace_path))
        
        # Initialize code indexer
        self.code_indexer = CodeIndexer(
            workspace_path=str(workspace_path),
            db_path="data/memory/vectors"
        )
    
    async def initialize(self) -> None:
        """Initialize the agent"""
        await super().initialize()
        # Index the codebase
        await self.code_indexer.index_codebase()
        self.logger.info("Read agent initialized")
    
    async def run_audit_tools(self, url: str) -> Dict[str, Any]:
        """Run website audit tools"""
        try:
            # Run WebHint analysis using CLI
            result = subprocess.run(
                ["hint", url, "--format", "json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error("webhint_error", error=result.stderr)
                return {}
            
            # Parse WebHint results
            webhint_results = json.loads(result.stdout)
            
            # Process results
            audit_data = {
                "accessibility": self._process_accessibility_hints(webhint_results),
                "performance": self._process_performance_hints(webhint_results),
                "best_practices": self._process_best_practices_hints(webhint_results),
                "seo": self._process_seo_hints(webhint_results),
                "security": self._process_security_hints(webhint_results)
            }
            
            return audit_data
            
        except Exception as e:
            self.logger.error("audit_error", url=url, error=str(e))
            return {}
    
    def _process_accessibility_hints(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process accessibility hints"""
        return [
            {
                "message": hint["message"],
                "severity": hint["severity"],
                "category": "accessibility"
            }
            for hint in results
            if hint.get("category", "").lower() == "accessibility"
        ]
    
    def _process_performance_hints(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process performance hints"""
        return [
            {
                "message": hint["message"],
                "severity": hint["severity"],
                "category": "performance"
            }
            for hint in results
            if hint.get("category", "").lower() == "performance"
        ]
    
    def _process_best_practices_hints(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process best practices hints"""
        return [
            {
                "message": hint["message"],
                "severity": hint["severity"],
                "category": "best_practices"
            }
            for hint in results
            if hint.get("category", "").lower() == "best_practices"
        ]
    
    def _process_seo_hints(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process SEO hints"""
        return [
            {
                "message": hint["message"],
                "severity": hint["severity"],
                "category": "seo"
            }
            for hint in results
            if hint.get("category", "").lower() == "seo"
        ]
    
    def _process_security_hints(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process security hints"""
        return [
            {
                "message": hint["message"],
                "severity": hint["severity"],
                "category": "security"
            }
            for hint in results
            if hint.get("category", "").lower() == "security"
        ]
    
    def normalize_data(self, audit_results: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize audit results"""
        normalized = {
            "accessibility_score": self._calculate_score(audit_results.get("accessibility", [])),
            "performance_score": self._calculate_score(audit_results.get("performance", [])),
            "best_practices_score": self._calculate_score(audit_results.get("best_practices", [])),
            "seo_score": self._calculate_score(audit_results.get("seo", [])),
            "security_score": self._calculate_score(audit_results.get("security", [])),
            "hints": []
        }
        
        # Combine all hints
        for category in ["accessibility", "performance", "best_practices", "seo", "security"]:
            hints = audit_results.get(category, [])
            normalized["hints"].extend(hints)
        
        return normalized
    
    def _calculate_score(self, hints: List[Dict[str, Any]]) -> float:
        """Calculate score based on hint severity"""
        if not hints:
            return 100.0
            
        severity_weights = {
            "error": 0.0,
            "warning": 0.5,
            "hint": 0.8
        }
        
        total_weight = 0
        weighted_sum = 0
        
        for hint in hints:
            weight = severity_weights.get(hint["severity"], 0.5)
            total_weight += weight
            weighted_sum += weight * 100
            
        return weighted_sum / total_weight if total_weight > 0 else 100.0
    
    def generate_prompt(self, normalized_data: Dict[str, Any]) -> str:
        """Generate prompt for LLM"""
        prompt = f"""Analyze the following website audit results:

Accessibility Score: {normalized_data['accessibility_score']:.1f}/100
Performance Score: {normalized_data['performance_score']:.1f}/100
Best Practices Score: {normalized_data['best_practices_score']:.1f}/100
SEO Score: {normalized_data['seo_score']:.1f}/100
Security Score: {normalized_data['security_score']:.1f}/100

Issues Found:
"""
        
        for hint in normalized_data["hints"]:
            prompt += f"- [{hint['severity'].upper()}] {hint['message']}\n"
            
        prompt += "\nPlease provide a detailed analysis of the website's health and recommendations for improvement."
        
        return prompt
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a website URL and generate analysis"""
        url = data.get("url")
        if not url:
            raise ValueError("URL is required")
        
        try:
            # Run audit tools
            audit_results = await self.run_audit_tools(url)
            
            # Normalize data
            normalized_data = self.normalize_data(audit_results)
            
            # Generate prompt
            prompt = self.generate_prompt(normalized_data)
            
            # Store results in memory
            await self.memory_manager.add_document({
                "url": url,
                "normalized_data": normalized_data,
                "prompt": prompt,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "status": "success",
                "normalized_data": normalized_data,
                "prompt": prompt
            }
            
        except Exception as e:
            self.logger.error("processing_error", url=url, error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """Cleanup agent resources"""
        await super().cleanup()
        self.logger.info("Read agent cleaned up") 