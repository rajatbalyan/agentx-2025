from typing import Dict, Any, List
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
import aiohttp
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig

class ContentUpdateAgent(BaseAgent):
    """Agent responsible for updating outdated content using external APIs"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.session = None
    
    async def initialize(self) -> None:
        """Initialize aiohttp session and other resources"""
        await super().initialize()
        self.session = aiohttp.ClientSession()
    
    async def verify_content_freshness(
        self,
        content: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify if content is up to date using external APIs"""
        # Use the LLM to identify potentially outdated information
        response = await self.llm.agenerate([
            SystemMessage(content="You are an expert at identifying outdated information."),
            HumanMessage(content=f"Analyze this content and identify any information that might be outdated:\n\n{content}")
        ])
        
        potential_outdated = response.generations[0].text
        updates_needed = []
        
        # For each potentially outdated piece, verify against external APIs
        soup = BeautifulSoup(content, 'html.parser')
        for element in soup.find_all(['p', 'span', 'div']):
            text = element.get_text()
            if any(outdated in text.lower() for outdated in potential_outdated.lower().split('\n')):
                # Check external APIs for updated information
                updated_info = await self.check_external_apis(text)
                if updated_info:
                    updates_needed.append({
                        "original": text,
                        "updated": updated_info,
                        "element_path": self.get_element_path(element)
                    })
        
        return {
            "updates_needed": updates_needed,
            "analysis": potential_outdated
        }
    
    async def check_external_apis(self, text: str) -> str:
        """Check external APIs for updated information"""
        # Example: Check Wikipedia API for latest information
        try:
            async with self.session.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "format": "json",
                    "prop": "extracts",
                    "exintro": True,
                    "titles": text
                }
            ) as response:
                data = await response.json()
                # Process and return updated information
                pages = data.get("query", {}).get("pages", {})
                if pages:
                    page = next(iter(pages.values()))
                    return page.get("extract", "")
        except Exception as e:
            self.logger.error("api_error", error=str(e))
        
        return ""
    
    def get_element_path(self, element) -> str:
        """Get CSS selector path to the element"""
        path = []
        while element and element.name:
            siblings = element.find_previous_siblings(element.name)
            path.append(f"{element.name}:nth-of-type({len(siblings) + 1})")
            element = element.parent
        return " > ".join(reversed(path))
    
    async def update_content(
        self,
        updates: List[Dict[str, Any]],
        html_content: str
    ) -> str:
        """Apply content updates to HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for update in updates:
            try:
                # Find element using the stored path
                element = soup.select_one(update["element_path"])
                if element:
                    # Update content while preserving HTML structure
                    element.string = update["updated"]
            except Exception as e:
                self.logger.error("update_error", error=str(e))
        
        return str(soup)
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process content update request"""
        content = data.get("content")
        if not content:
            raise ValueError("Content is required")
        
        try:
            # Check content freshness
            freshness_check = await self.verify_content_freshness(
                content,
                data.get("context", {})
            )
            
            if freshness_check["updates_needed"]:
                # Apply updates
                updated_content = await self.update_content(
                    freshness_check["updates_needed"],
                    content
                )
                
                # Store update in memory
                await self.memory_manager.add_document({
                    "original_content": content,
                    "updates": freshness_check["updates_needed"],
                    "updated_content": updated_content,
                    "timestamp": datetime.now().isoformat()
                })
                
                return {
                    "status": "updated",
                    "updates": freshness_check["updates_needed"],
                    "updated_content": updated_content
                }
            
            return {
                "status": "current",
                "message": "Content is up to date"
            }
            
        except Exception as e:
            self.logger.error("processing_error", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        await super().cleanup() 