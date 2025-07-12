import requests
import logging
from typing import Dict, Any, Optional, List
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class APIClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("BACKEND_URL", "http://localhost:8000")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request to the API"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}")
            return None

    # Health and System endpoints
    def get_health_status(self) -> Optional[Dict[str, Any]]:
        """Get system health status"""
        return self._make_request("GET", "/health")

    def get_system_info(self) -> Optional[Dict[str, Any]]:
        """Get system information"""
        return self._make_request("GET", "/api/system/info")

    # Alert endpoints
    def create_alert(self, alert_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new alert"""
        return self._make_request("POST", "/api/alerts/", json=alert_data)

    def get_alerts(self, page: int = 1, size: int = 20, **filters) -> Optional[Dict[str, Any]]:
        """Get alerts with filtering and pagination"""
        params = {"page": page, "size": size}
        params.update({k: v for k, v in filters.items() if v is not None})
        return self._make_request("GET", "/api/alerts/", params=params)

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific alert"""
        return self._make_request("GET", f"/api/alerts/{alert_id}")

    def update_alert(self, alert_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an alert"""
        return self._make_request("PUT", f"/api/alerts/{alert_id}", json=update_data)

    def delete_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Delete an alert"""
        return self._make_request("DELETE", f"/api/alerts/{alert_id}")

    def get_alert_groups(self, page: int = 1, size: int = 20, **filters) -> Optional[Dict[str, Any]]:
        """Get alert groups"""
        params = {"page": page, "size": size}
        params.update({k: v for k, v in filters.items() if v is not None})
        return self._make_request("GET", "/api/alerts/groups/", params=params)

    def get_alert_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific alert group"""
        return self._make_request("GET", f"/api/alerts/groups/{group_id}")

    def regroup_alerts(self, hours_back: int = 24) -> Optional[Dict[str, Any]]:
        """Regroup alerts"""
        return self._make_request("POST", "/api/alerts/regroup", params={"hours_back": hours_back})

    def create_bulk_alerts(self, alerts_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Create multiple alerts at once"""
        return self._make_request("POST", "/api/alerts/bulk", json=alerts_data)

    def get_alert_stats(self, hours_back: int = 24) -> Optional[Dict[str, Any]]:
        """Get alert statistics"""
        return self._make_request("GET", "/api/alerts/stats/summary", params={"hours_back": hours_back})

    # RCA endpoints
    def generate_rca(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Generate RCA for an alert group"""
        return self._make_request("POST", "/api/rca/generate", params={"group_id": group_id})

    def get_rcas(self, page: int = 1, size: int = 20, **filters) -> Optional[Dict[str, Any]]:
        """Get RCAs with filtering and pagination"""
        params = {"page": page, "size": size}
        params.update({k: v for k, v in filters.items() if v is not None})
        return self._make_request("GET", "/api/rca/", params=params)

    def get_rca(self, rca_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific RCA"""
        return self._make_request("GET", f"/api/rca/{rca_id}")

    def update_rca(self, rca_id: str, update_data: Dict[str, Any], 
                   changed_by: str = None, change_reason: str = None) -> Optional[Dict[str, Any]]:
        """Update an RCA"""
        params = {}
        if changed_by:
            params["changed_by"] = changed_by
        if change_reason:
            params["change_reason"] = change_reason
        
        return self._make_request("PUT", f"/api/rca/{rca_id}", json=update_data, params=params)

    def get_rca_alerts(self, rca_id: str) -> Optional[Dict[str, Any]]:
        """Get alerts related to an RCA"""
        return self._make_request("GET", f"/api/rca/{rca_id}/alerts")

    def get_rca_history(self, rca_id: str) -> Optional[Dict[str, Any]]:
        """Get RCA status history"""
        return self._make_request("GET", f"/api/rca/{rca_id}/history")

    def delete_rca(self, rca_id: str) -> Optional[Dict[str, Any]]:
        """Delete an RCA"""
        return self._make_request("DELETE", f"/api/rca/{rca_id}")

    def bulk_vectorize_rcas(self, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Bulk vectorize closed RCAs"""
        return self._make_request("POST", "/api/rca/bulk-vectorize", params={"limit": limit})

    def search_historical_incidents(self, query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
        """Search historical incidents"""
        return self._make_request("GET", "/api/rca/search/historical", 
                                params={"query": query, "limit": limit})

    def get_rca_stats(self) -> Optional[Dict[str, Any]]:
        """Get RCA statistics"""
        return self._make_request("GET", "/api/rca/stats/summary")

    # Utility methods
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            response = self._make_request("GET", "/")
            return response is not None and response.get("success", False)
        except Exception:
            return False

    def format_datetime(self, dt_string: str) -> str:
        """Format datetime string for display"""
        try:
            if not dt_string:
                return "N/A"
            # Parse ISO format datetime
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return dt_string

    def get_severity_color(self, severity: str) -> str:
        """Get color for severity level"""
        colors = {
            "critical": "#ff0000",
            "high": "#ff4500", 
            "medium": "#ffa500",
            "low": "#32cd32"
        }
        return colors.get(severity.lower(), "#808080")

    def get_status_color(self, status: str) -> str:
        """Get color for status"""
        colors = {
            "open": "#ff4b4b",
            "in_progress": "#ffa500",
            "closed": "#00ff00",
            "active": "#ff4b4b",
            "acknowledged": "#ffa500",
            "resolved": "#00ff00"
        }
        return colors.get(status.lower(), "#808080")
