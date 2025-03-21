from typing import Dict, Any, List
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig

class ContentGenerationAgent(BaseAgent):
    """Agent responsible for generating and refining web content"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.content_types = {
            "article": self._generate_article,
            "product_description": self._generate_product_description,
            "meta_description": self._generate_meta_description,
            "social_media": self._generate_social_media_content
        }
    
    async def _generate_article(
        self,
        topic: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a full article"""
        # Create article outline
        outline_response = await self.llm.agenerate([
            SystemMessage(content="You are an expert content strategist."),
            HumanMessage(content=f"Create a detailed outline for an article about: {topic}\nContext: {context}")
        ])
        
        outline = outline_response.generations[0].text
        
        # Generate article sections
        sections = []
        for section in outline.split("\n"):
            if section.strip():
                section_response = await self.llm.agenerate([
                    SystemMessage(content="You are an expert content writer."),
                    HumanMessage(content=f"Write a detailed section about: {section}\nTopic: {topic}\nContext: {context}")
                ])
                sections.append({
                    "heading": section.strip(),
                    "content": section_response.generations[0].text
                })
        
        return {
            "type": "article",
            "topic": topic,
            "outline": outline,
            "sections": sections
        }
    
    async def _generate_product_description(
        self,
        product_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate product description"""
        response = await self.llm.agenerate([
            SystemMessage(content="You are an expert product copywriter."),
            HumanMessage(content=f"Write a compelling product description for:\n{product_data}\nContext: {context}")
        ])
        
        return {
            "type": "product_description",
            "product_data": product_data,
            "description": response.generations[0].text
        }
    
    async def _generate_meta_description(
        self,
        content: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate SEO meta description"""
        response = await self.llm.agenerate([
            SystemMessage(content="You are an expert SEO copywriter."),
            HumanMessage(content=f"Write a compelling meta description (max 160 characters) for:\n{content}\nContext: {context}")
        ])
        
        return {
            "type": "meta_description",
            "content": content,
            "meta_description": response.generations[0].text[:160]
        }
    
    async def _generate_social_media_content(
        self,
        topic: str,
        platform: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate social media content"""
        response = await self.llm.agenerate([
            SystemMessage(content=f"You are an expert {platform} content creator."),
            HumanMessage(content=f"Create engaging {platform} content about:\n{topic}\nContext: {context}")
        ])
        
        return {
            "type": "social_media",
            "platform": platform,
            "topic": topic,
            "content": response.generations[0].text
        }
    
    async def refine_content(
        self,
        content: str,
        style_guide: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Refine existing content based on style guide"""
        # Analyze current content
        analysis_response = await self.llm.agenerate([
            SystemMessage(content="You are an expert content analyst."),
            HumanMessage(content=f"Analyze this content and identify areas for improvement based on the style guide:\nContent: {content}\nStyle Guide: {style_guide}")
        ])
        
        analysis = analysis_response.generations[0].text
        
        # Refine content
        refinement_response = await self.llm.agenerate([
            SystemMessage(content="You are an expert content editor."),
            HumanMessage(content=f"Refine this content based on the analysis and style guide:\nContent: {content}\nAnalysis: {analysis}\nStyle Guide: {style_guide}\nContext: {context}")
        ])
        
        return {
            "original_content": content,
            "analysis": analysis,
            "refined_content": refinement_response.generations[0].text
        }
    
    async def optimize_for_target(
        self,
        content: Dict[str, Any],
        target: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize content for specific target audience/platform"""
        response = await self.llm.agenerate([
            SystemMessage(content="You are an expert content optimizer."),
            HumanMessage(content=f"Optimize this content for the target:\nContent: {content}\nTarget: {target}")
        ])
        
        return {
            "original_content": content,
            "target": target,
            "optimized_content": response.generations[0].text
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process content generation request"""
        content_type = data.get("type")
        if not content_type:
            raise ValueError("Content type is required")
        
        try:
            # Generate new content
            if content_type in self.content_types:
                result = await self.content_types[content_type](**data)
            
            # Refine existing content
            elif content_type == "refine":
                result = await self.refine_content(
                    data["content"],
                    data.get("style_guide", {}),
                    data.get("context", {})
                )
            
            # Optimize for target
            elif content_type == "optimize":
                result = await self.optimize_for_target(
                    data["content"],
                    data.get("target", {})
                )
            
            else:
                raise ValueError(f"Unknown content type: {content_type}")
            
            # Store in memory
            await self.memory_manager.add_document({
                "request": data,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            self.logger.error("processing_error", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        await super().cleanup() 