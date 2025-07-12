import streamlit as st
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pages import alerts, rca_dashboard, rca_details
from utils.api_client import APIClient

# Configure Streamlit page
st.set_page_config(
    page_title="Alert RCA Management System",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize API client
@st.cache_resource
def get_api_client():
    return APIClient()

api_client = get_api_client()

def main():
    """Main application entry point"""
    
    # Custom CSS for better styling
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
        }
        .status-open {
            color: #ff4b4b;
            font-weight: bold;
        }
        .status-in-progress {
            color: #ffa500;
            font-weight: bold;
        }
        .status-closed {
            color: #00ff00;
            font-weight: bold;
        }
        .severity-critical {
            color: #ff0000;
            font-weight: bold;
        }
        .severity-high {
            color: #ff4500;
            font-weight: bold;
        }
        .severity-medium {
            color: #ffa500;
            font-weight: bold;
        }
        .severity-low {
            color: #32cd32;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Main header
    st.markdown('<h1 class="main-header">🚨 Alert RCA Management System</h1>', unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.title("Navigation")
        
        # Check system health
        health_status = api_client.get_health_status()
        if health_status and health_status.get("success"):
            status_data = health_status.get("data", {})
            overall_status = status_data.get("status", "unknown")
            
            if overall_status == "healthy":
                st.success("🟢 System Healthy")
            elif overall_status == "degraded":
                st.warning("🟡 System Degraded")
            else:
                st.error("🔴 System Issues")
                
            with st.expander("Service Status"):
                st.write(f"**Database:** {status_data.get('database', 'unknown')}")
                st.write(f"**LLM Service:** {status_data.get('llm_service', 'unknown')}")
                st.write(f"**RAG Service:** {status_data.get('rag_service', 'unknown')}")
        else:
            st.error("🔴 Cannot reach backend")
        
        st.markdown("---")
        
        # Navigation options
        page = st.selectbox(
            "Select Page",
            ["Dashboard", "Alerts", "RCA Details"],
            key="page_selector"
        )
        
        st.markdown("---")
        
        # Quick stats
        st.subheader("Quick Stats")
        try:
            alert_stats = api_client.get_alert_stats()
            if alert_stats and alert_stats.get("success"):
                stats_data = alert_stats.get("data", {})
                st.metric("Total Alerts", stats_data.get("total_alerts", 0))
                st.metric("Alert Groups", stats_data.get("total_groups", 0))
                
                # Status distribution
                status_dist = stats_data.get("status_distribution", {})
                st.metric("Active Alerts", status_dist.get("active", 0))
                st.metric("Resolved Alerts", status_dist.get("resolved", 0))
            
            rca_stats = api_client.get_rca_stats()
            if rca_stats and rca_stats.get("success"):
                rca_data = rca_stats.get("data", {})
                st.metric("Total RCAs", rca_data.get("total_rcas", 0))
                
                # RCA status distribution
                rca_status_dist = rca_data.get("status_distribution", {})
                st.metric("Open RCAs", rca_status_dist.get("open", 0))
                st.metric("Closed RCAs", rca_status_dist.get("closed", 0))
                
        except Exception as e:
            st.error(f"Error loading stats: {e}")
    
    # Main content area
    if page == "Dashboard":
        show_dashboard()
    elif page == "Alerts":
        alerts.show_alerts_page(api_client)
    elif page == "RCA Details":
        rca_details.show_rca_details_page(api_client)


def show_dashboard():
    """Show the main dashboard"""
    
    st.header("📊 System Dashboard")
    
    # Get system info
    system_info = api_client.get_system_info()
    if system_info and system_info.get("success"):
        info_data = system_info.get("data", {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("System Information")
            st.write(f"**Version:** {info_data.get('version', 'Unknown')}")
            st.write(f"**Backend:** {info_data.get('backend', 'Unknown')}")
            st.write(f"**Database:** {info_data.get('database', 'Unknown')}")
            st.write(f"**LLM:** {info_data.get('llm', 'Unknown')}")
            st.write(f"**Vector DB:** {info_data.get('vector_db', 'Unknown')}")
        
        with col2:
            st.subheader("Configuration")
            settings = info_data.get("settings", {})
            st.write(f"**Grouping Window:** {settings.get('alert_grouping_window', 'Unknown')} min")
            st.write(f"**Similarity Threshold:** {settings.get('similarity_threshold', 'Unknown')}")
            st.write(f"**LLM Model:** {settings.get('ollama_model', 'Unknown')}")
        
        with col3:
            st.subheader("Vector Database")
            vector_stats = info_data.get("vector_stats", {})
            if vector_stats.get("status") == "available":
                stats = vector_stats.get("stats", {})
                st.write(f"**Status:** Available ✅")
                st.write(f"**Documents:** {stats.get('total_documents', 0)}")
                st.write(f"**Model:** {stats.get('embedding_model', 'Unknown')}")
            else:
                st.write("**Status:** Unavailable ❌")
    
    st.markdown("---")
    
    # Show RCA dashboard
    rca_dashboard.show_rca_dashboard(api_client)
    
    st.markdown("---")
    
    # Recent activity
    st.header("📈 Recent Activity")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recent Alerts")
        try:
            recent_alerts = api_client.get_alerts(page=1, size=5)
            if recent_alerts and recent_alerts.get("success"):
                alerts_data = recent_alerts.get("data", {}).get("items", [])
                
                if alerts_data:
                    for alert in alerts_data:
                        severity_class = f"severity-{alert.get('severity', 'low')}"
                        st.markdown(f"""
                        <div class="metric-card">
                            <strong>{alert.get('title', 'Unknown')}</strong><br>
                            <span class="{severity_class}">Severity: {alert.get('severity', 'Unknown').upper()}</span><br>
                            <small>Source: {alert.get('source_system', 'Unknown')}</small><br>
                            <small>Created: {alert.get('created_at', 'Unknown')[:19]}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                else:
                    st.info("No recent alerts found")
            else:
                st.error("Failed to load recent alerts")
        except Exception as e:
            st.error(f"Error loading recent alerts: {e}")
    
    with col2:
        st.subheader("Recent RCAs")
        try:
            recent_rcas = api_client.get_rcas(page=1, size=5)
            if recent_rcas and recent_rcas.get("success"):
                rcas_data = recent_rcas.get("data", {}).get("items", [])
                
                if rcas_data:
                    for rca in rcas_data:
                        status_class = f"status-{rca.get('status', 'open').replace('_', '-')}"
                        severity_class = f"severity-{rca.get('severity', 'low')}"
                        
                        st.markdown(f"""
                        <div class="metric-card">
                            <strong>{rca.get('title', 'Unknown')}</strong><br>
                            <span class="{status_class}">Status: {rca.get('status', 'Unknown').upper()}</span><br>
                            <span class="{severity_class}">Severity: {rca.get('severity', 'Unknown').upper()}</span><br>
                            <small>Created: {rca.get('created_at', 'Unknown')[:19]}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                else:
                    st.info("No recent RCAs found")
            else:
                st.error("Failed to load recent RCAs")
        except Exception as e:
            st.error(f"Error loading recent RCAs: {e}")


if __name__ == "__main__":
    main()
