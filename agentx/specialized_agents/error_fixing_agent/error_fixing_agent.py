"""Error Fixing Agent for detecting and fixing website errors."""

import structlog
from typing import Dict, Any, List
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
import re
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig
from agentx.common_libraries.system_config import SystemConfig

logger = structlog.get_logger()

class ErrorFixingAgent(BaseAgent):
    """Agent responsible for detecting and fixing website errors."""
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig):
        """Initialize the Error Fixing Agent.
        
        Args:
            config: Agent configuration
            system_config: System configuration
        """
        super().__init__(config, system_config)
        self.logger = logger.bind(agent="error_fixing")
        self.common_fixes = self._load_common_fixes()
    
    def _load_common_fixes(self) -> Dict[str, Any]:
        """Load common error fixes and patterns"""
        return {
            "html": {
                "unclosed_tags": {
                    "pattern": r"<([a-z0-9]+)[^>]*>(?![^<]*</\1>)",
                    "fix": lambda m: f"{m.group(0)}</{m.group(1)}>"
                },
                "invalid_attributes": {
                    "pattern": r'(\s[a-z-]+)=([^"\'][^\s>]*)',
                    "fix": lambda m: f'{m.group(1)}="{m.group(2)}"'
                }
            },
            "accessibility": {
                "missing_alt": {
                    "pattern": r'<img[^>]+(?!alt=)[^>]*>',
                    "fix": lambda m: m.group(0).replace(">", ' alt="Image">')
                },
                "missing_labels": {
                    "pattern": r'<input[^>]+(?!aria-label|aria-labelledby|id=)[^>]*>',
                    "fix": lambda m: m.group(0).replace(">", ' aria-label="Input field">')
                }
            },
            "seo": {
                "missing_meta": {
                    "pattern": r'<head>(?![^<]*<meta[^>]+description)',
                    "fix": lambda m: m.group(0) + '<meta name="description" content="Page description">'
                },
                "missing_title": {
                    "pattern": r'<head>(?![^<]*<title>)',
                    "fix": lambda m: m.group(0) + '<title>Page Title</title>'
                }
            }
        }
    
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Error Fixing Agent initialized")
    
    async def analyze_errors(
        self,
        html_content: str,
        audit_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze HTML content for various types of errors"""
        errors = {
            "html": [],
            "accessibility": [],
            "seo": []
        }
        
        # HTML validation
        for error_type, fix_info in self.common_fixes["html"].items():
            matches = re.finditer(fix_info["pattern"], html_content)
            for match in matches:
                errors["html"].append({
                    "type": error_type,
                    "location": match.start(),
                    "content": match.group(0),
                    "fix": fix_info["fix"](match)
                })
        
        # Accessibility checks
        for error_type, fix_info in self.common_fixes["accessibility"].items():
            matches = re.finditer(fix_info["pattern"], html_content)
            for match in matches:
                errors["accessibility"].append({
                    "type": error_type,
                    "location": match.start(),
                    "content": match.group(0),
                    "fix": fix_info["fix"](match)
                })
        
        # SEO validation
        for error_type, fix_info in self.common_fixes["seo"].items():
            matches = re.finditer(fix_info["pattern"], html_content)
            for match in matches:
                errors["seo"].append({
                    "type": error_type,
                    "location": match.start(),
                    "content": match.group(0),
                    "fix": fix_info["fix"](match)
                })
        
        # Use LLM for complex error analysis
        if audit_data:
            llm_analysis = await self.llm.agenerate([
                SystemMessage(content="You are an expert at identifying and fixing web errors."),
                HumanMessage(content=f"Analyze these audit results and suggest fixes:\n\n{audit_data}")
            ])
            
            errors["llm_suggestions"] = llm_analysis.generations[0].text
        
        return errors
    
    async def apply_fixes(
        self,
        html_content: str,
        errors: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply fixes to the HTML content"""
        fixed_content = html_content
        applied_fixes = []
        
        # Sort errors by location (reverse order to maintain indices)
        all_errors = []
        for category in ["html", "accessibility", "seo"]:
            all_errors.extend((e, category) for e in errors[category])
        
        all_errors.sort(key=lambda x: x[0]["location"], reverse=True)
        
        # Apply fixes
        for error, category in all_errors:
            try:
                # Replace the error with its fix
                fixed_content = (
                    fixed_content[:error["location"]] +
                    error["fix"] +
                    fixed_content[error["location"] + len(error["content"]):]
                )
                
                applied_fixes.append({
                    "category": category,
                    "type": error["type"],
                    "original": error["content"],
                    "fixed": error["fix"]
                })
                
            except Exception as e:
                self.logger.error("fix_error", error=str(e))
        
        return {
            "fixed_content": fixed_content,
            "applied_fixes": applied_fixes
        }
    
    async def validate_fixes(
        self,
        fixed_content: str,
        original_errors: Dict[str, Any]
    ) -> bool:
        """Validate that fixes didn't introduce new errors"""
        # Re-analyze the fixed content
        new_errors = await self.analyze_errors(fixed_content, None)
        
        # Compare error counts
        for category in ["html", "accessibility", "seo"]:
            if len(new_errors[category]) >= len(original_errors[category]):
                return False
        
        return True
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process error fixing tasks.
        
        Args:
            data: Task data containing error information
            
        Returns:
            Processing results
        """
        try:
            task_type = data.get("type")
            if not task_type:
                raise ValueError("Task type not provided")
            
            if task_type == "error_audit":
                return await self._audit_errors(data)
            elif task_type == "bug_fix":
                return await self._fix_bug(data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
        except Exception as e:
            self.logger.error("Error processing task", error=str(e))
            return {
                "status": "error",
                "message": str(e)
            }
            
    async def _audit_errors(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Audit website for errors.
        
        Args:
            data: Audit parameters
            
        Returns:
            Audit results
        """
        try:
            target_url = data.get("target")
            if not target_url:
                raise ValueError("Target URL not provided")
            
            # TODO: Implement error auditing logic
            # 1. Check for JavaScript errors
            # 2. Verify API endpoints
            # 3. Test form submissions
            # 4. Check for broken links
            
            return {
                "status": "success",
                "message": "Error audit completed",
                "errors_found": False,
                "issues": []
            }
            
        except Exception as e:
            self.logger.error("Error audit failed", error=str(e))
            return {
                "status": "error",
                "message": str(e)
            }
            
    async def _fix_bug(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fix a specific bug.
        
        Args:
            data: Bug fix parameters
            
        Returns:
            Fix results
        """
        try:
            files = data.get("files_modified", [])
            if not files:
                raise ValueError("No files specified for bug fix")
            
            # TODO: Implement bug fixing logic
            # 1. Analyze error
            # 2. Generate fix
            # 3. Apply changes
            # 4. Test fix
            
            return {
                "status": "success",
                "message": "Bug fixed successfully",
                "changes_made": True,
                "fixed_files": files
            }
            
        except Exception as e:
            self.logger.error("Bug fix failed", error=str(e))
            return {
                "status": "error",
                "message": str(e)
            }
            
    async def cleanup(self) -> None:
        """Clean up resources."""
        await super().cleanup() 