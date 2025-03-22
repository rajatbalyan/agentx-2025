"""Performance monitoring agent for optimizing website performance."""

from typing import Dict, Any
import structlog
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig
from agentx.common_libraries.system_config import SystemConfig

logger = structlog.get_logger()

class PerformanceMonitoringAgent(BaseAgent):
    """Agent responsible for monitoring and optimizing website performance."""
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig):
        """Initialize the performance monitoring agent.
        
        Args:
            config: Agent configuration
            system_config: System configuration
        """
        super().__init__(config, system_config)
        self.logger = logger.bind(agent="performance_monitoring_agent")
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process performance optimization tasks.
        
        Args:
            input_data: Task data containing performance issues
            
        Returns:
            Processing results with optimization recommendations
        """
        try:
            self.logger.info("Processing performance task", task=input_data)
            
            task_data = input_data.get('data', {})
            metrics = task_data.get('metrics', {})
            issues = task_data.get('issues', [])
            
            # Generate optimization recommendations
            recommendations = []
            
            # Check Largest Contentful Paint (LCP)
            lcp = metrics.get('largest-contentful-paint')
            if lcp and lcp > 2.5:
                recommendations.append({
                    "issue": "High Largest Contentful Paint",
                    "metric": f"{lcp}s",
                    "target": "< 2.5s",
                    "recommendations": [
                        "Optimize and compress images",
                        "Implement lazy loading for below-the-fold content",
                        "Use a CDN for faster content delivery",
                        "Optimize server response time"
                    ]
                })
            
            # Check First Contentful Paint (FCP)
            fcp = metrics.get('first-contentful-paint')
            if fcp and fcp > 1.8:
                recommendations.append({
                    "issue": "High First Contentful Paint",
                    "metric": f"{fcp}s",
                    "target": "< 1.8s",
                    "recommendations": [
                        "Minimize render-blocking resources",
                        "Optimize critical rendering path",
                        "Implement resource hints (preload, prefetch)",
                        "Optimize CSS delivery"
                    ]
                })
            
            # Check Speed Index
            speed_index = metrics.get('speed-index')
            if speed_index and speed_index > 3.4:
                recommendations.append({
                    "issue": "High Speed Index",
                    "metric": f"{speed_index}s",
                    "target": "< 3.4s",
                    "recommendations": [
                        "Optimize page load sequence",
                        "Minimize main thread work",
                        "Reduce JavaScript execution time",
                        "Implement progressive rendering"
                    ]
                })
            
            # Check Total Blocking Time
            tbt = metrics.get('total-blocking-time')
            if tbt and tbt > 0.3:
                recommendations.append({
                    "issue": "High Total Blocking Time",
                    "metric": f"{tbt}s",
                    "target": "< 0.3s",
                    "recommendations": [
                        "Break up long tasks",
                        "Optimize JavaScript execution",
                        "Remove unused JavaScript",
                        "Implement code splitting"
                    ]
                })
            
            # Generate action plan
            action_plan = {
                "priority": task_data.get('priority', 'medium'),
                "current_score": task_data.get('score', 0),
                "target_score": 90,
                "recommendations": recommendations,
                "implementation_steps": [
                    {
                        "phase": "Immediate (24-48 hours)",
                        "actions": [
                            "Implement critical performance fixes",
                            "Optimize largest contentful paint",
                            "Minimize render-blocking resources"
                        ]
                    },
                    {
                        "phase": "Short-term (1 week)",
                        "actions": [
                            "Implement CDN integration",
                            "Optimize image delivery",
                            "Implement caching strategy"
                        ]
                    },
                    {
                        "phase": "Medium-term (2-4 weeks)",
                        "actions": [
                            "Refactor JavaScript code",
                            "Implement advanced optimization techniques",
                            "Set up performance monitoring"
                        ]
                    }
                ]
            }
            
            return {
                "status": "success",
                "action_plan": action_plan,
                "metrics_analyzed": list(metrics.keys()),
                "issues_found": len(recommendations)
            }
            
        except Exception as e:
            self.logger.error("Error processing performance task", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        pass 