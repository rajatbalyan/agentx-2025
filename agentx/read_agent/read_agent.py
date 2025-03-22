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
import os

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
        """Run website audit tools using the auditor module."""
        try:
            self.logger.info("Starting website audit", url=url)
            
            # Import and run the auditor
            from agentx.auditor.auditor import audit
            audit(url)
            
            # Read all audit results from temp/lighthouse
            audit_results = {}
            lighthouse_dir = Path("temp/lighthouse")
            
            if not lighthouse_dir.exists():
                self.logger.error("Lighthouse directory not found", path=str(lighthouse_dir))
                raise FileNotFoundError(f"Lighthouse directory not found at {lighthouse_dir}")
            
            # List all JSON files in the directory
            json_files = list(lighthouse_dir.glob("*.json"))
            self.logger.info(f"Found {len(json_files)} audit files", files=[f.name for f in json_files])
            
            for audit_file in json_files:
                page_name = audit_file.stem
                try:
                    with open(audit_file, 'r') as f:
                        audit_results[page_name] = json.load(f)
                    self.logger.info(f"Successfully loaded audit results for {page_name}")
                except Exception as e:
                    self.logger.error(f"Error loading audit file {audit_file}", error=str(e))
                    continue
            
            if not audit_results:
                raise FileNotFoundError("No valid audit results found")
            
            self.logger.info("Successfully loaded audit results", pages=len(audit_results))
            return audit_results
            
        except Exception as e:
            self.logger.error("Error running audit tools", error=str(e))
            raise
    
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
    
    def _process_performance_hints(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process performance audit results."""
        performance_hints = []
        metrics = results.get('performance', {}).get('metrics', {})
        
        # First Contentful Paint
        fcp = metrics.get('first-contentful-paint', 0)
        if fcp > 1.8:  # 1.8s threshold
            performance_hints.append({
                'type': 'performance',
                'severity': 'medium',
                'message': f"First Contentful Paint is {fcp}s (should be < 1.8s)",
                'details': "First Contentful Paint (FCP) measures how long it takes for the first content to appear on screen."
            })
        
        # Largest Contentful Paint
        lcp = metrics.get('largest-contentful-paint', 0)
        if lcp > 2.5:  # 2.5s threshold
            performance_hints.append({
                'type': 'performance',
                'severity': 'high',
                'message': f"Largest Contentful Paint is {lcp}s (should be < 2.5s)",
                'details': "Largest Contentful Paint (LCP) measures when the largest content element becomes visible."
            })
        
        # Speed Index
        si = metrics.get('speed-index', 0)
        if si > 3.4:  # 3.4s threshold
            performance_hints.append({
                'type': 'performance',
                'severity': 'medium',
                'message': f"Speed Index is {si}s (should be < 3.4s)",
                'details': "Speed Index measures how quickly content is visually displayed during page load."
            })
        
        # Total Blocking Time
        tbt = metrics.get('total-blocking-time', 0)
        if tbt > 0.3:  # 300ms threshold
            performance_hints.append({
                'type': 'performance',
                'severity': 'high',
                'message': f"Total Blocking Time is {tbt}s (should be < 0.3s)",
                'details': "Total Blocking Time (TBT) measures the total time when the main thread was blocked."
            })
        
        return performance_hints
    
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
    
    def _process_seo_hints(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process SEO audit results."""
        seo_hints = []
        metrics = results.get('seo', {}).get('metrics', {})
        
        # Meta Description
        if not metrics.get('meta-description', True):
            seo_hints.append({
                'type': 'seo',
                'severity': 'high',
                'message': "Missing meta description",
                'details': "Meta descriptions are important for SEO and click-through rates from search results."
            })
        
        # Robots.txt
        if not metrics.get('robots-txt', True):
            seo_hints.append({
                'type': 'seo',
                'severity': 'high',
                'message': "Missing or invalid robots.txt",
                'details': "robots.txt helps search engines understand which pages to crawl and index."
            })
        
        # Viewport
        if not metrics.get('viewport', True):
            seo_hints.append({
                'type': 'seo',
                'severity': 'medium',
                'message': "Missing viewport meta tag",
                'details': "Viewport meta tag is required for proper mobile rendering and responsive design."
            })
        
        return seo_hints
    
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
        """Normalize audit results into scores and categories."""
        # Extract the actual audit data from the nested structure
        audit_data = audit_results.get('audit', audit_results)
        
        normalized_data = {
            'performance': {
                'score': audit_data.get('performance', {}).get('score', 0) * 100,
                'hints': []
            },
            'seo': {
                'score': audit_data.get('seo', {}).get('score', 0) * 100,
                'hints': []
            }
        }
        
        # Process performance hints
        perf_hints = self._process_performance_hints(audit_data)
        normalized_data['performance']['hints'].extend(perf_hints)
        
        # Process SEO hints
        seo_hints = self._process_seo_hints(audit_data)
        normalized_data['seo']['hints'].extend(seo_hints)
        
        return normalized_data
    
    def generate_prompt(self, normalized_data: Dict[str, Any]) -> str:
        """Generate a detailed analysis prompt optimized for manager AI consumption."""
        prompt = (
            "You are analyzing a website audit report to make strategic decisions about performance and SEO improvements. "
            "Below is a comprehensive analysis of the audit results.\n\n"
            
            "CONTEXT:\n"
            "- This analysis is based on Lighthouse performance metrics and SEO best practices\n"
            "- Scores are rated out of 100, where higher is better\n"
            "- Issues are prioritized using severity indicators: 🔴 (Critical), 🟡 (High), 🟢 (Medium)\n\n"
            
            "CURRENT STATUS:\n"
            f"Performance Score: {normalized_data['performance']['score']:.1f}/100\n"
            f"SEO Score: {normalized_data['seo']['score']:.1f}/100\n\n"
        )

        # Critical Issues Section
        prompt += "CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:\n"
        high_severity_issues = [
            hint for hint in normalized_data['performance']['hints'] + normalized_data['seo']['hints']
            if hint['severity'] == 'high'
        ]
        
        if high_severity_issues:
            for issue in high_severity_issues:
                prompt += (
                    f"🔴 Issue: {issue['message']}\n"
                    f"   Impact: {issue.get('details', 'No additional details available')}\n"
                    "   Required Action: Immediate resolution needed\n"
                )
        else:
            prompt += "✅ No critical issues detected\n"

        # Performance Analysis
        prompt += "\nPERFORMANCE ANALYSIS:\n"
        if normalized_data['performance']['hints']:
            for hint in sorted(normalized_data['performance']['hints'], 
                            key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['severity']]):
                severity_icon = '🔴' if hint['severity'] == 'high' else '🟡' if hint['severity'] == 'medium' else '🟢'
                prompt += (
                    f"{severity_icon} Metric: {hint['message']}\n"
                    f"   Technical Context: {hint.get('details', 'No additional details available')}\n"
                )
        else:
            prompt += "✅ All performance metrics within acceptable ranges\n"

        # SEO Analysis
        prompt += "\nSEO ANALYSIS:\n"
        if normalized_data['seo']['hints']:
            for hint in sorted(normalized_data['seo']['hints'],
                           key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['severity']]):
                severity_icon = '🔴' if hint['severity'] == 'high' else '🟡' if hint['severity'] == 'medium' else '🟢'
                prompt += (
                    f"{severity_icon} Finding: {hint['message']}\n"
                    f"   Impact: {hint.get('details', 'No additional details available')}\n"
                )
        else:
            prompt += "✅ All SEO requirements met\n"

        # Strategic Recommendations
        prompt += "\nSTRATEGIC RECOMMENDATIONS:\n"
        
        if normalized_data['performance']['score'] < 90:
            prompt += "\nPerformance Strategy:\n"
            priority = (
                "CRITICAL - Immediate action required"
                if normalized_data['performance']['score'] < 70
                else "HIGH - Action required within next sprint"
                if normalized_data['performance']['score'] < 85
                else "MEDIUM - Plan for upcoming sprints"
            )
            prompt += f"Priority Level: {priority}\n"
            
            recommendations = [
                ("Image Optimization", "Implement WebP format and responsive images"),
                ("Resource Loading", "Add lazy loading for below-the-fold content"),
                ("Asset Optimization", "Minimize and compress JS/CSS, remove unused code"),
                ("Caching Strategy", "Implement optimal browser caching policies"),
                ("Infrastructure", "Deploy CDN for static assets"),
                ("Resource Management", "Eliminate render-blocking resources"),
                ("Server Performance", "Optimize server response time and time to first byte")
            ]
            for category, action in recommendations:
                prompt += f"- {category}: {action}\n"

        if normalized_data['seo']['score'] < 90:
            prompt += "\nSEO Strategy:\n"
            priority = (
                "CRITICAL - Immediate action required"
                if normalized_data['seo']['score'] < 70
                else "HIGH - Action required within next sprint"
                if normalized_data['seo']['score'] < 85
                else "MEDIUM - Plan for upcoming sprints"
            )
            prompt += f"Priority Level: {priority}\n"
            
            recommendations = [
                ("Meta Information", "Implement comprehensive meta descriptions"),
                ("Search Engine Access", "Configure robots.txt properly"),
                ("Mobile Optimization", "Add viewport meta tags, ensure responsive design"),
                ("Structured Data", "Implement JSON-LD markup for rich snippets"),
                ("Site Architecture", "Create and submit XML sitemap"),
                ("Content Optimization", "Enhance title tags and meta descriptions"),
                ("User Experience", "Ensure mobile-first design principles")
            ]
            for category, action in recommendations:
                prompt += f"- {category}: {action}\n"

        # Implementation Guide
        prompt += "\nIMPLEMENTATION GUIDE:\n"
        prompt += "1. IMMEDIATE (24-48 hours):\n"
        prompt += "   - Address all 🔴 critical issues\n"
        prompt += "   - Begin implementation of high-priority performance fixes\n"
        prompt += "2. SHORT-TERM (1-2 weeks):\n"
        prompt += "   - Resolve 🟡 high-priority issues\n"
        prompt += "   - Implement critical SEO improvements\n"
        prompt += "3. MEDIUM-TERM (2-4 weeks):\n"
        prompt += "   - Address 🟢 medium-priority items\n"
        prompt += "   - Monitor impact of implemented changes\n"
        
        # Expected Outcomes
        prompt += "\nEXPECTED OUTCOMES:\n"
        prompt += "- Improved user experience through faster page loads\n"
        prompt += "- Better search engine visibility and rankings\n"
        prompt += "- Increased conversion rates and user engagement\n"
        prompt += "- Enhanced mobile user experience\n"
        
        return prompt
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data through the agent.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Processing results
        """
        try:
            # Extract URL from input data
            url = input_data.get('url')
            if not url:
                raise ValueError("URL not provided in input data")
            
            # Run audit tools
            audit_results = await self.run_audit_tools(url)
            
            # Normalize and analyze the data
            normalized_data = self.normalize_data(audit_results)
            
            # Generate analysis prompt
            analysis_prompt = self.generate_prompt(normalized_data)
            
            # Store the interaction
            await self.store_interaction({
                'type': 'website_audit',
                'url': url,
                'normalized_data': normalized_data,
                'analysis': analysis_prompt,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                'status': 'success',
                'results': {
                    'audit': audit_results,
                    'analysis': {
                        'normalized_data': normalized_data,
                        'prompt': analysis_prompt
                    }
                }
            }
            
        except Exception as e:
            self.logger.error("processing_error", error=str(e), url=url)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def cleanup(self) -> None:
        """Cleanup agent resources"""
        await super().cleanup()
        self.logger.info("Read agent cleaned up") 