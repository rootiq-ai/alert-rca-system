import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta


def show_rca_dashboard(api_client):
    """Show RCA dashboard with filtering and management"""
    
    st.header("🔍 RCA Dashboard")
    
    # Quick stats
    show_rca_stats(api_client)
    
    st.markdown("---")
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["RCA List", "Search Historical", "Bulk Operations"])
    
    with tab1:
        show_rca_list(api_client)
    
    with tab2:
        show_historical_search(api_client)
    
    with tab3:
        show_bulk_operations(api_client)


def show_rca_stats(api_client):
    """Show RCA statistics"""
    
    try:
        response = api_client.get_rca_stats()
        
        if response and response.get("success"):
            stats = response.get("data", {})
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total RCAs", stats.get("total_rcas", 0))
            
            with col2:
                status_dist = stats.get("status_distribution", {})
                st.metric("Open RCAs", status_dist.get("open", 0))
            
            with col3:
                st.metric("In Progress", status_dist.get("in_progress", 0))
            
            with col4:
                st.metric("Closed RCAs", status_dist.get("closed", 0))
            
            # Charts in columns
            col1, col2 = st.columns(2)
            
            with col1:
                # Status distribution
                if status_dist:
                    fig_status = px.pie(
                        values=list(status_dist.values()),
                        names=list(status_dist.keys()),
                        title="RCA Status Distribution",
                        color_discrete_map={
                            "open": "#ff4b4b",
                            "in_progress": "#ffa500",
                            "closed": "#00ff00"
                        }
                    )
                    st.plotly_chart(fig_status, use_container_width=True)
            
            with col2:
                # Severity distribution
                severity_dist = stats.get("severity_distribution", {})
                if severity_dist:
                    fig_severity = px.bar(
                        x=list(severity_dist.keys()),
                        y=list(severity_dist.values()),
                        title="RCA Severity Distribution",
                        labels={"x": "Severity", "y": "Count"},
                        color=list(severity_dist.keys()),
                        color_discrete_map={
                            "critical": "#ff0000",
                            "high": "#ff4500",
                            "medium": "#ffa500",
                            "low": "#32cd32"
                        }
                    )
                    st.plotly_chart(fig_severity, use_container_width=True)
        else:
            st.error("Failed to fetch RCA statistics")
            
    except Exception as e:
        st.error(f"Error loading RCA stats: {e}")


def show_rca_list(api_client):
    """Show list of RCAs with filtering options"""
    
    st.subheader("📋 RCA Management")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.multiselect(
            "Status",
            ["open", "in_progress", "closed"],
            default=["open", "in_progress"]
        )
    
    with col2:
        severity_filter = st.multiselect(
            "Severity",
            ["critical", "high", "medium", "low"],
            default=None
        )
    
    with col3:
        assigned_to_filter = st.text_input("Assigned To")
    
    with col4:
        search_query = st.text_input("Search in title/content")
    
    # Date range
    col5, col6 = st.columns(2)
    with col5:
        start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
    with col6:
        end_date = st.date_input("End Date", value=datetime.now())
    
    # Pagination
    col7, col8 = st.columns(2)
    with col7:
        page_size = st.selectbox("Items per page", [10, 20, 50], index=1)
    with col8:
        if "rca_page" not in st.session_state:
            st.session_state.rca_page = 1
        current_page = st.number_input("Page", min_value=1, value=st.session_state.rca_page)
    
    # Fetch RCAs
    filters = {
        "status": status_filter if status_filter else None,
        "severity": severity_filter if severity_filter else None,
        "assigned_to": assigned_to_filter if assigned_to_filter else None,
        "search_query": search_query if search_query else None,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None
    }
    
    try:
        response = api_client.get_rcas(page=current_page, size=page_size, **filters)
        
        if response and response.get("success"):
            rcas_data = response.get("data", {})
            rcas = rcas_data.get("items", [])
            total = rcas_data.get("total", 0)
            total_pages = rcas_data.get("pages", 1)
            
            st.write(f"**Total RCAs:** {total} (Page {current_page} of {total_pages})")
            
            if rcas:
                for rca in rcas:
                    show_rca_card(api_client, rca)
                
                # Pagination
                col_prev, col_next = st.columns([1, 1])
                with col_prev:
                    if current_page > 1:
                        if st.button("⬅️ Previous"):
                            st.session_state.rca_page = current_page - 1
                            st.rerun()
                
                with col_next:
                    if current_page < total_pages:
                        if st.button("Next ➡️"):
                            st.session_state.rca_page = current_page + 1
                            st.rerun()
            else:
                st.info("No RCAs found matching the filters")
        else:
            st.error("Failed to fetch RCAs")
            
    except Exception as e:
        st.error(f"Error fetching RCAs: {e}")


def show_rca_card(api_client, rca):
    """Display an RCA card with details and actions"""
    
    rca_id = rca.get("rca_id", "unknown")
    status = rca.get("status", "unknown")
    severity = rca.get("severity", "unknown")
    
    # Status and severity styling
    status_color = api_client.get_status_color(status)
    severity_color = api_client.get_severity_color(severity)
    
    with st.expander(f"🔍 {rca.get('title', 'Unknown RCA')} - {status.upper()}"):
        # Header info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"**RCA ID:** `{rca_id}`")
            st.markdown(f"**Status:** <span style='color: {status_color}'>**{status.upper()}**</span>", unsafe_allow_html=True)
            st.markdown(f"**Severity:** <span style='color: {severity_color}'>**{severity.upper()}**</span>", unsafe_allow_html=True)
        
        with col2:
            st.write(f"**Group ID:** {rca.get('group_id', 'N/A')}")
            st.write(f"**Confidence:** {rca.get('confidence_score', 'N/A')}")
            st.write(f"**Method:** {rca.get('analysis_method', 'N/A')}")
        
        with col3:
            st.write(f"**Created:** {api_client.format_datetime(rca.get('created_at', ''))}")
            st.write(f"**Updated:** {api_client.format_datetime(rca.get('updated_at', ''))}")
            if rca.get('assigned_to'):
                st.write(f"**Assigned To:** {rca.get('assigned_to')}")
        
        # Root cause and actions
        if rca.get('root_cause'):
            st.write("**Root Cause:**")
            st.write(rca.get('root_cause', '')[:300] + "..." if len(rca.get('root_cause', '')) > 300 else rca.get('root_cause', ''))
        
        # Action buttons
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("View Full Details", key=f"view_{rca_id}"):
                st.session_state.selected_rca_id = rca_id
                st.switch_page("pages/rca_details.py")
        
        with col2:
            if st.button("View Related Alerts", key=f"alerts_{rca_id}"):
                show_rca_alerts(api_client, rca_id)
        
        with col3:
            if status == "open":
                if st.button("Start Progress", key=f"progress_{rca_id}"):
                    update_rca_status(api_client, rca_id, "in_progress", "Started working on RCA")
        
        with col4:
            if status in ["open", "in_progress"]:
                if st.button("Close RCA", key=f"close_{rca_id}"):
                    update_rca_status(api_client, rca_id, "closed", "RCA completed")
        
        with col5:
            if st.button("View History", key=f"history_{rca_id}"):
                show_rca_history(api_client, rca_id)
        
        # Show impact analysis and recommendations if available
        if rca.get('impact_analysis'):
            with st.expander("Impact Analysis"):
                st.write(rca.get('impact_analysis'))
        
        if rca.get('recommended_actions'):
            with st.expander("Recommended Actions"):
                st.write(rca.get('recommended_actions'))


def show_rca_alerts(api_client, rca_id):
    """Show alerts related to an RCA"""
    try:
        response = api_client.get_rca_alerts(rca_id)
        if response and response.get("success"):
            alerts = response.get("data", {}).get("alerts", [])
            
            if alerts:
                st.subheader(f"Related Alerts ({len(alerts)})")
                for alert in alerts:
                    st.write(f"- **{alert.get('title')}** ({alert.get('severity')}) - {alert.get('source_system')}")
            else:
                st.info("No related alerts found")
        else:
            st.error("Failed to fetch related alerts")
    except Exception as e:
        st.error(f"Error fetching related alerts: {e}")


def show_rca_history(api_client, rca_id):
    """Show RCA status change history"""
    try:
        response = api_client.get_rca_history(rca_id)
        if response and response.get("success"):
            history = response.get("data", {}).get("history", [])
            
            if history:
                st.subheader("Status History")
                for entry in history:
                    st.write(f"**{entry.get('changed_at', '')}** - {entry.get('previous_status', 'N/A')} → {entry.get('new_status', 'N/A')}")
                    if entry.get('changed_by'):
                        st.write(f"  Changed by: {entry.get('changed_by')}")
                    if entry.get('change_reason'):
                        st.write(f"  Reason: {entry.get('change_reason')}")
                    st.write("---")
            else:
                st.info("No status history found")
        else:
            st.error("Failed to fetch RCA history")
    except Exception as e:
        st.error(f"Error fetching RCA history: {e}")


def update_rca_status(api_client, rca_id, new_status, reason):
    """Update RCA status"""
    try:
        response = api_client.update_rca(
            rca_id,
            {"status": new_status},
            changed_by="user",
            change_reason=reason
        )
        if response and response.get("success"):
            st.success(f"RCA status updated to {new_status}")
            st.rerun()
        else:
            st.error("Failed to update RCA status")
    except Exception as e:
        st.error(f"Error updating RCA: {e}")


def show_historical_search(api_client):
    """Show historical incident search"""
    
    st.subheader("🔍 Search Historical Incidents")
    
    # Search form
    with st.form("historical_search"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input(
                "Search Query",
                placeholder="Enter keywords to search historical incidents..."
            )
        
        with col2:
            limit = st.number_input("Max Results", min_value=1, max_value=50, value=10)
        
        submitted = st.form_submit_button("Search")
        
        if submitted and search_query:
            try:
                response = api_client.search_historical_incidents(search_query, limit)
                
                if response and response.get("success"):
                    incidents = response.get("data", {}).get("incidents", [])
                    
                    if incidents:
                        st.write(f"Found {len(incidents)} similar incidents:")
                        
                        for i, incident in enumerate(incidents, 1):
                            with st.expander(f"Incident {i} - Similarity: {incident.get('similarity_score', 0):.2f}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write(f"**RCA ID:** {incident.get('rca_id', 'N/A')}")
                                    st.write(f"**Severity:** {incident.get('severity', 'N/A')}")
                                    st.write(f"**Alert Count:** {incident.get('alert_count', 0)}")
                                
                                with col2:
                                    st.write(f"**Source Systems:** {', '.join(incident.get('source_systems', []))}")
                                    st.write(f"**Confidence:** {incident.get('confidence_score', 'N/A')}")
                                    st.write(f"**Created:** {incident.get('created_at', 'N/A')}")
                                
                                if incident.get('summary'):
                                    st.write("**Summary:**")
                                    st.write(incident.get('summary'))
                    else:
                        st.info("No similar incidents found")
                else:
                    st.error("Failed to search historical incidents")
                    
            except Exception as e:
                st.error(f"Error searching historical incidents: {e}")


def show_bulk_operations(api_client):
    """Show bulk operations for RCAs"""
    
    st.subheader("⚙️ Bulk Operations")
    
    # Bulk vectorize closed RCAs
    st.write("**Vectorize Closed RCAs**")
    st.write("Store closed RCAs in the vector database for future similarity matching.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        vectorize_limit = st.number_input("Max RCAs to vectorize", min_value=1, max_value=1000, value=100)
    
    with col2:
        if st.button("Start Vectorization"):
            try:
                response = api_client.bulk_vectorize_rcas(vectorize_limit)
                
                if response and response.get("success"):
                    result = response.get("data", {})
                    st.success(f"Vectorization completed!")
                    st.write(f"- Processed: {result.get('processed', 0)}")
                    st.write(f"- Successful: {result.get('successful', 0)}")
                    st.write(f"- Failed: {result.get('failed', 0)}")
                else:
                    st.error("Failed to start vectorization")
                    
            except Exception as e:
                st.error(f"Error in bulk vectorization: {e}")
    
    st.markdown("---")
    
    # Regroup alerts
    st.write("**Regroup Alerts**")
    st.write("Re-analyze and regroup alerts from the specified time period.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        regroup_hours = st.selectbox("Time Period", [6, 12, 24, 48, 168], format_func=lambda x: f"Last {x} hours")
    
    with col2:
        if st.button("Regroup Alerts"):
            try:
                response = api_client.regroup_alerts(regroup_hours)
                
                if response and response.get("success"):
                    result = response.get("data", {})
                    st.success("Regrouping completed!")
                    st.write(f"- Processed alerts: {result.get('processed_alerts', 0)}")
                    st.write(f"- Grouped alerts: {result.get('grouped_alerts', 0)}")
                    st.write(f"- New groups: {result.get('new_groups', 0)}")
                else:
                    st.error("Failed to regroup alerts")
                    
            except Exception as e:
                st.error(f"Error regrouping alerts: {e}")
    
    st.markdown("---")
    
    # System information
    st.write("**System Status**")
    try:
        system_info = api_client.get_system_info()
        if system_info and system_info.get("success"):
            info = system_info.get("data", {})
            vector_stats = info.get("vector_stats", {})
            
            if vector_stats.get("status") == "available":
                stats = vector_stats.get("stats", {})
                st.info(f"Vector DB: {stats.get('total_documents', 0)} documents stored")
            else:
                st.warning("Vector DB not available")
        else:
            st.error("Failed to get system information")
    except Exception as e:
        st.error(f"Error getting system status: {e}")
