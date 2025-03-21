from typing import Dict, Any, List
import asyncio
from playwright.async_api import async_playwright
import json
import subprocess
from pathlib import Path
import structlog
from langchain.schema import HumanMessage, SystemMessage
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig

class ReadAgent(BaseAgent):
    """Agent responsible for reading and analyzing website content"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.browser = None
        self.context = None
        self.page = None
    
    async def initialize(self) -> None:
        """Initialize Playwright and other resources"""
        await super().initialize()
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch()
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
    
    async def run_audit_tools(self, url: str) -> Dict[str, Any]:
        """Run various audit tools on the webpage"""
        results = {}
        
        # HTMLHint analysis
        try:
            html_content = await self.page.content()
            with open("temp.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            htmlhint_result = subprocess.run(
                ["htmlhint", "temp.html", "--format", "json"],
                capture_output=True,
                text=True
            )
            results["htmlhint"] = json.loads(htmlhint_result.stdout)
        except Exception as e:
            self.logger.error("htmlhint_error", error=str(e))
            results["htmlhint"] = {"error": str(e)}
        
        # Lighthouse analysis
        try:
            lighthouse_result = subprocess.run(
                ["lighthouse", url, "--output", "json", "--quiet"],
                capture_output=True,
                text=True
            )
            results["lighthouse"] = json.loads(lighthouse_result.stdout)
        except Exception as e:
            self.logger.error("lighthouse_error", error=str(e))
            results["lighthouse"] = {"error": str(e)}
        
        # WebHint analysis
        try:
            webhint_result = subprocess.run(
                ["hint", url, "--format", "json"],
                capture_output=True,
                text=True
            )
            results["webhint"] = json.loads(webhint_result.stdout)
        except Exception as e:
            self.logger.error("webhint_error", error=str(e))
            results["webhint"] = {"error": str(e)}
        
        return results
    
    def normalize_data(self, audit_results: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize audit data into a unified format"""
        normalized = {
            "html_quality": {
                "errors": [],
                "warnings": []
            },
            "accessibility": {
                "score": None,
                "issues": []
            },
            "performance": {
                "score": None,
                "metrics": {}
            },
            "seo": {
                "score": None,
                "issues": []
            }
        }
        
        # Process HTMLHint results
        if "htmlhint" in audit_results:
            for issue in audit_results["htmlhint"].get("messages", []):
                normalized["html_quality"]["errors"].append({
                    "message": issue.get("message"),
                    "line": issue.get("line"),
                    "rule": issue.get("rule")
                })
        
        # Process Lighthouse results
        if "lighthouse" in audit_results:
            lh = audit_results["lighthouse"]
            categories = lh.get("categories", {})
            
            if "accessibility" in categories:
                normalized["accessibility"]["score"] = categories["accessibility"].get("score")
                
            if "performance" in categories:
                normalized["performance"]["score"] = categories["performance"].get("score")
                normalized["performance"]["metrics"] = lh.get("audits", {}).get("metrics", {})
                
            if "seo" in categories:
                normalized["seo"]["score"] = categories["seo"].get("score")
        
        # Process WebHint results
        if "webhint" in audit_results:
            for hint in audit_results["webhint"]:
                category = hint.get("category", "").lower()
                if category in normalized:
                    normalized[category]["issues"].append({
                        "message": hint.get("message"),
                        "severity": hint.get("severity")
                    })
        
        return normalized
    
    def generate_prompt(self, normalized_data: Dict[str, Any]) -> str:
        """Generate a prompt for the Manager Agent based on normalized data"""
        prompt = "Website Analysis Summary:\n\n"
        
        # HTML Quality
        errors = normalized_data["html_quality"]["errors"]
        prompt += f"HTML Quality Issues: {len(errors)} found\n"
        if errors:
            prompt += "Top issues:\n"
            for error in errors[:3]:
                prompt += f"- {error['message']} (Line {error['line']})\n"
        
        # Accessibility
        acc_score = normalized_data["accessibility"]["score"]
        prompt += f"\nAccessibility Score: {acc_score*100 if acc_score else 'N/A'}%\n"
        acc_issues = normalized_data["accessibility"]["issues"]
        if acc_issues:
            prompt += "Key accessibility issues:\n"
            for issue in acc_issues[:3]:
                prompt += f"- {issue['message']}\n"
        
        # Performance
        perf_score = normalized_data["performance"]["score"]
        prompt += f"\nPerformance Score: {perf_score*100 if perf_score else 'N/A'}%\n"
        metrics = normalized_data["performance"]["metrics"]
        if metrics:
            prompt += "Key metrics:\n"
            for metric, value in list(metrics.items())[:3]:
                prompt += f"- {metric}: {value}\n"
        
        # SEO
        seo_score = normalized_data["seo"]["score"]
        prompt += f"\nSEO Score: {seo_score*100 if seo_score else 'N/A'}%\n"
        seo_issues = normalized_data["seo"]["issues"]
        if seo_issues:
            prompt += "Key SEO issues:\n"
            for issue in seo_issues[:3]:
                prompt += f"- {issue['message']}\n"
        
        prompt += "\nRequired Actions:\n"
        prompt += "1. Address critical HTML errors\n"
        if acc_score and acc_score < 0.9:
            prompt += "2. Improve accessibility\n"
        if perf_score and perf_score < 0.9:
            prompt += "3. Optimize performance\n"
        if seo_score and seo_score < 0.9:
            prompt += "4. Enhance SEO\n"
        
        return prompt
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a website URL and generate analysis"""
        url = data.get("url")
        if not url:
            raise ValueError("URL is required")
        
        try:
            # Navigate to the page
            await self.page.goto(url)
            await self.page.wait_for_load_state("networkidle")
            
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
        """Cleanup Playwright resources"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        await super().cleanup() 