import logging
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = 120  # 2 minutes timeout for LLM requests

    def is_available(self) -> bool:
        """Check if OLLAMA service is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"OLLAMA service not available: {e}")
            return False

    def generate_rca(self, alerts: List[Dict[str, Any]], context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate Root Cause Analysis for a group of alerts
        
        Args:
            alerts: List of alert dictionaries
            context: Optional context from RAG system
            
        Returns:
            Dict containing RCA analysis
        """
        try:
            # Prepare prompt
            prompt = self._create_rca_prompt(alerts, context)
            
            # Call OLLAMA
            response = self._call_ollama(prompt)
            
            if response:
                # Parse the response
                rca_data = self._parse_rca_response(response)
                return rca_data
            else:
                return self._create_fallback_rca(alerts)
                
        except Exception as e:
            logger.error(f"Error generating RCA: {e}")
            return self._create_fallback_rca(alerts)

    def _create_rca_prompt(self, alerts: List[Dict[str, Any]], context: Optional[str] = None) -> str:
        """Create a comprehensive prompt for RCA generation"""
        
        # Alert summary
        alert_summary = self._create_alert_summary(alerts)
        
        # Context section
        context_section = ""
        if context:
            context_section = f"\n\n**Historical Context:**\n{context}\n"

        prompt = f"""
You are an expert Site Reliability Engineer (SRE) and system analyst specializing in Root Cause Analysis (RCA). 
Analyze the following alert group and provide a comprehensive RCA.

**Alert Group Information:**
{alert_summary}
{context_section}

**Instructions:**
1. Analyze the alerts to identify patterns and relationships
2. Determine the most likely root cause
3. Assess the impact on systems and users
4. Provide specific, actionable recommendations
5. Rate your confidence in the analysis

**Please provide your analysis in the following JSON format:**
{{
    "title": "Brief, descriptive title for the RCA",
    "root_cause": "Detailed explanation of the root cause",
    "impact_analysis": "Analysis of impact on systems, users, and business",
    "recommended_actions": "Specific, prioritized list of actions to resolve and prevent recurrence",
    "affected_systems": ["list", "of", "affected", "systems"],
    "timeline": {{
        "incident_start": "estimated start time",
        "detection_time": "when alerts were triggered",
        "key_events": ["list of key events in chronological order"]
    }},
    "confidence_score": "high/medium/low",
    "severity": "critical/high/medium/low",
    "additional_investigation": "Areas that need further investigation"
}}

Focus on being specific, actionable, and technically accurate. Consider both immediate fixes and long-term preventive measures.
"""
        return prompt

    def _create_alert_summary(self, alerts: List[Dict[str, Any]]) -> str:
        """Create a summary of alerts for the prompt"""
        
        summary_parts = []
        
        # Group statistics
        summary_parts.append(f"**Alert Count:** {len(alerts)}")
        
        # Severity distribution
        severities = [alert.get('severity', 'unknown') for alert in alerts]
        severity_counts = {sev: severities.count(sev) for sev in set(severities)}
        summary_parts.append(f"**Severity Distribution:** {severity_counts}")
        
        # Source systems
        sources = list(set([alert.get('source_system', 'unknown') for alert in alerts]))
        summary_parts.append(f"**Source Systems:** {', '.join(sources)}")
        
        # Time range
        if alerts:
            timestamps = [alert.get('created_at') for alert in alerts if alert.get('created_at')]
            if timestamps:
                timestamps.sort()
                summary_parts.append(f"**Time Range:** {timestamps[0]} to {timestamps[-1]}")
        
        # Individual alerts
        summary_parts.append("\n**Individual Alerts:**")
        for i, alert in enumerate(alerts[:10], 1):  # Limit to first 10 alerts
            alert_info = [
                f"Alert {i}:",
                f"  Title: {alert.get('title', 'N/A')}",
                f"  Severity: {alert.get('severity', 'N/A')}",
                f"  Source: {alert.get('source_system', 'N/A')}",
                f"  Time: {alert.get('created_at', 'N/A')}"
            ]
            
            if alert.get('description'):
                alert_info.append(f"  Description: {alert.get('description')[:200]}...")
            
            if alert.get('metric_name'):
                alert_info.append(f"  Metric: {alert.get('metric_name')} = {alert.get('metric_value')}")
            
            summary_parts.append("\n".join(alert_info))
        
        if len(alerts) > 10:
            summary_parts.append(f"... and {len(alerts) - 10} more similar alerts")
        
        return "\n\n".join(summary_parts)

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call OLLAMA API to generate response"""
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for more consistent analysis
                    "top_p": 0.9,
                    "num_predict": 2048  # Max tokens for response
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                logger.error(f"OLLAMA API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("OLLAMA request timed out")
            return None
        except Exception as e:
            logger.error(f"Error calling OLLAMA: {e}")
            return None

    def _parse_rca_response(self, response: str) -> Dict[str, Any]:
        """Parse the RCA response from LLM"""
        
        try:
            # Try to extract JSON from the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                rca_data = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['title', 'root_cause', 'confidence_score', 'severity']
                for field in required_fields:
                    if field not in rca_data:
                        rca_data[field] = 'Not specified'
                
                # Ensure lists are lists
                if 'affected_systems' not in rca_data:
                    rca_data['affected_systems'] = []
                elif isinstance(rca_data['affected_systems'], str):
                    rca_data['affected_systems'] = [rca_data['affected_systems']]
                
                return rca_data
            else:
                # Fallback: parse unstructured response
                return self._parse_unstructured_response(response)
                
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response, attempting unstructured parsing")
            return self._parse_unstructured_response(response)
        except Exception as e:
            logger.error(f"Error parsing RCA response: {e}")
            return self._create_basic_rca_from_text(response)

    def _parse_unstructured_response(self, response: str) -> Dict[str, Any]:
        """Parse unstructured response into RCA format"""
        
        lines = response.split('\n')
        rca_data = {
            'title': 'System Alert Analysis',
            'root_cause': '',
            'impact_analysis': '',
            'recommended_actions': '',
            'confidence_score': 'medium',
            'severity': 'medium',
            'affected_systems': []
        }
        
        current_section = 'root_cause'
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to identify sections
            line_lower = line.lower()
            if 'root cause' in line_lower:
                current_section = 'root_cause'
                continue
            elif 'impact' in line_lower:
                current_section = 'impact_analysis'
                continue
            elif 'recommend' in line_lower or 'action' in line_lower:
                current_section = 'recommended_actions'
                continue
            elif 'title' in line_lower and ':' in line:
                rca_data['title'] = line.split(':', 1)[1].strip()
                continue
            
            # Add content to current section
            if current_section in rca_data:
                if rca_data[current_section]:
                    rca_data[current_section] += '\n' + line
                else:
                    rca_data[current_section] = line
        
        return rca_data

    def _create_basic_rca_from_text(self, response: str) -> Dict[str, Any]:
        """Create basic RCA structure from any text response"""
        
        return {
            'title': 'Alert Group Analysis',
            'root_cause': response[:500] + '...' if len(response) > 500 else response,
            'impact_analysis': 'Impact analysis needs manual review',
            'recommended_actions': 'Please review alerts manually for specific actions',
            'confidence_score': 'low',
            'severity': 'medium',
            'affected_systems': [],
            'timeline': {},
            'additional_investigation': 'LLM response parsing failed, manual review required'
        }

    def _create_fallback_rca(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create fallback RCA when LLM is not available"""
        
        # Basic analysis based on alert data
        severities = [alert.get('severity', 'unknown') for alert in alerts]
        max_severity = 'critical' if 'critical' in severities else 'high' if 'high' in severities else 'medium'
        
        sources = list(set([alert.get('source_system', 'unknown') for alert in alerts]))
        
        return {
            'title': f'Alert Group - {len(alerts)} alerts from {", ".join(sources[:3])}',
            'root_cause': f'Multiple alerts detected from {", ".join(sources)}. Root cause analysis requires investigation of system metrics and logs.',
            'impact_analysis': f'Impact severity: {max_severity}. {len(alerts)} alerts generated.',
            'recommended_actions': 'Investigate system logs, check resource utilization, verify service health',
            'confidence_score': 'low',
            'severity': max_severity,
            'affected_systems': sources,
            'timeline': {
                'incident_start': 'Unknown',
                'detection_time': alerts[0].get('created_at', 'Unknown') if alerts else 'Unknown'
            },
            'additional_investigation': 'LLM service unavailable - manual analysis required'
        }

    def summarize_alerts(self, alerts: List[Dict[str, Any]]) -> str:
        """Generate a brief summary of alerts"""
        
        try:
            prompt = f"""
Provide a brief summary of the following alerts in 2-3 sentences:

{self._create_alert_summary(alerts)}

Focus on the key patterns and most important information.
"""
            
            response = self._call_ollama(prompt)
            if response:
                return response.strip()
            else:
                return f"Alert group with {len(alerts)} alerts from multiple systems"
                
        except Exception as e:
            logger.error(f"Error summarizing alerts: {e}")
            return f"Alert group with {len(alerts)} alerts - summary generation failed"
