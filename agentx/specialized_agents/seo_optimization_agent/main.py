"""SEO Optimization Agent for AgentX framework."""

from typing import Dict, Any, List
from bs4 import BeautifulSoup
import structlog
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig

logger = structlog.get_logger()

class SEOOptimizationAgent(BaseAgent):
    """Agent responsible for SEO optimization tasks."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.logger = logger.bind(agent="seo_optimization")

    async def analyze_meta_tags(self, html_content: str) -> Dict[str, Any]:
        """Analyze meta tags in HTML content.
        
        Args:
            html_content: HTML content to analyze
            
        Returns:
            Analysis results and suggestions
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get meta tags
        title = soup.find('title')
        meta_description = soup.find('meta', attrs={'name': 'description'})
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        
        # Analyze meta tags
        issues = []
        suggestions = []
        
        if not title:
            issues.append("Missing title tag")
            suggestions.append("Add a title tag with relevant keywords")
        elif len(title.text) < 30 or len(title.text) > 60:
            issues.append("Title length not optimal")
            suggestions.append("Adjust title length to be between 30-60 characters")
            
        if not meta_description:
            issues.append("Missing meta description")
            suggestions.append("Add a meta description with relevant keywords")
        elif meta_description.get('content', '') and (len(meta_description['content']) < 120 or len(meta_description['content']) > 160):
            issues.append("Meta description length not optimal")
            suggestions.append("Adjust meta description length to be between 120-160 characters")
            
        if not meta_keywords:
            issues.append("Missing meta keywords")
            suggestions.append("Add meta keywords based on page content")
            
        return {
            'issues': issues,
            'suggestions': suggestions,
            'current_meta': {
                'title': title.text if title else None,
                'description': meta_description['content'] if meta_description else None,
                'keywords': meta_keywords['content'] if meta_keywords else None
            }
        }

    async def analyze_content_structure(self, html_content: str) -> Dict[str, Any]:
        """Analyze content structure for SEO optimization.
        
        Args:
            html_content: HTML content to analyze
            
        Returns:
            Analysis results and suggestions
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Analyze headings
        headings = {f'h{i}': len(soup.find_all(f'h{i}')) for i in range(1, 7)}
        
        # Analyze images
        images = soup.find_all('img')
        images_without_alt = [img for img in images if not img.get('alt')]
        
        # Analyze links
        links = soup.find_all('a')
        internal_links = [link for link in links if not link.get('href', '').startswith(('http', 'https', '//'))]
        external_links = [link for link in links if link.get('href', '').startswith(('http', 'https', '//'))]
        
        issues = []
        suggestions = []
        
        # Check heading structure
        if headings['h1'] == 0:
            issues.append("Missing H1 heading")
            suggestions.append("Add an H1 heading that includes your main keyword")
        elif headings['h1'] > 1:
            issues.append("Multiple H1 headings found")
            suggestions.append("Use only one H1 heading per page")
            
        if images_without_alt:
            issues.append(f"Found {len(images_without_alt)} images without alt text")
            suggestions.append("Add descriptive alt text to all images")
            
        if len(internal_links) < 2:
            issues.append("Few internal links")
            suggestions.append("Add more internal links to improve site structure")
            
        return {
            'structure_analysis': {
                'headings': headings,
                'images': {
                    'total': len(images),
                    'missing_alt': len(images_without_alt)
                },
                'links': {
                    'internal': len(internal_links),
                    'external': len(external_links)
                }
            },
            'issues': issues,
            'suggestions': suggestions
        }

    async def generate_seo_improvements(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate SEO improvement suggestions using LLM.
        
        Args:
            content: Content analysis results
            
        Returns:
            List of improvement suggestions
        """
        # Get similar successful optimizations from memory
        similar_interactions = await self.get_similar_interactions(content)
        
        # Prepare context for LLM
        context = {
            'current_analysis': content,
            'similar_optimizations': similar_interactions,
            'seo_best_practices': {
                'title_length': '30-60 characters',
                'meta_description_length': '120-160 characters',
                'heading_structure': 'One H1, proper hierarchy',
                'image_optimization': 'Alt text for all images',
                'internal_linking': 'Relevant internal links'
            }
        }
        
        # Generate suggestions using LLM
        response = await self.llm.agenerate([
            f"""As an SEO expert, analyze this content and provide specific improvements:
            Current Analysis: {content}
            Similar Successful Optimizations: {similar_interactions}
            
            Provide detailed, actionable suggestions for:
            1. Meta tags optimization
            2. Content structure improvements
            3. Keyword placement and density
            4. Internal linking strategy
            5. Image optimization
            
            Format each suggestion with:
            - Issue description
            - Specific action to take
            - Expected impact
            """
        ])
        
        # Process and structure LLM response
        suggestions = []
        for suggestion in response.generations[0].text.split('\n'):
            if suggestion.strip():
                suggestions.append({
                    'suggestion': suggestion,
                    'category': 'seo_improvement',
                    'priority': 'high' if 'critical' in suggestion.lower() else 'medium'
                })
                
        return suggestions

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process SEO optimization task.
        
        Args:
            task: Task containing HTML content to analyze
            
        Returns:
            SEO analysis and suggestions
        """
        try:
            html_content = task.get('html_content', '')
            if not html_content:
                raise ValueError("No HTML content provided")
                
            # Analyze meta tags
            meta_analysis = await self.analyze_meta_tags(html_content)
            
            # Analyze content structure
            structure_analysis = await self.analyze_content_structure(html_content)
            
            # Generate improvements
            improvements = await self.generate_seo_improvements({
                'meta_analysis': meta_analysis,
                'structure_analysis': structure_analysis
            })
            
            result = {
                'meta_analysis': meta_analysis,
                'structure_analysis': structure_analysis,
                'suggested_improvements': improvements,
                'status': 'success'
            }
            
            # Store successful interaction
            await self.store_interaction(task, result)
            
            return result
            
        except Exception as e:
            self.logger.error("Error processing SEO task", error=str(e))
            return {
                'status': 'error',
                'error': str(e)
            }

if __name__ == "__main__":
    config = AgentConfig(
        name="seo_optimization_agent",
        port=8003
    )
    
    agent = SEOOptimizationAgent(config)
    agent.start() 