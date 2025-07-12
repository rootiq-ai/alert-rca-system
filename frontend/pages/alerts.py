import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json


def show_alerts_page(api_client):
    """Show the alerts management page"""
    
    st.header("🚨 Alert Management")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Alerts List", "Alert Groups", "Create Alert", "Analytics"])
    
    with tab1:
        show_alerts_list(api_client)
    
    with tab2:
        show_alert_groups(api_client)
    
    with tab3:
        show_create_alert(api_client)
    
    with tab4:
        show_alert_analytics(api_client)


def show_alerts_list(api_client):
    """Show list of alerts with filters"""
    
    st.subheader("📋 Alerts List")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        severity_filter = st.multiselect(
            "Severity",
            ["critical", "high", "medium", "low"],
            default=None
        )
    
    with col2:
        status_filter = st.multiselect(
            "Status", 
            ["active", "acknowledged", "resolved"],
            default=["active"]
        )
    
    with col3:
        source_filter = st.text_input("Source System")
    
    with col4:
        search_query = st.text_input("Search in title/description")
    
    # Date range filter
    col5, col6 = st.columns(2)
    with col5:
        start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=7))
    with col6:
        end_date = st.date_input("End Date", value=datetime.now())
    
    # Pagination controls
    col7, col8 = st.columns(2)
    with col7:
        page_size = st.selectbox("Items per page", [10, 20, 50, 100], index=1)
    with col8:
        if "alert_page" not in st.session_state:
            st.session_state.alert_page = 1
        current_page = st.number_input("Page", min_value=1, value=st.session_state.alert_page)
    
    # Fetch alerts
    filters = {
        "severity": severity_filter if severity_filter else None,
        "status": status_filter if status_filter else None,
        "source_system": source_filter if source_filter else None,
        "search_query": search_query if search_query else None,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None
    }
    
    try:
        response = api_client.get_alerts(page=current_page, size=page_size, **filters)
        
        if response and response.get("success"):
            alerts_data = response.get("data", {})
            alerts = alerts_data.get("items", [])
            total = alerts_data.get("total", 0)
            total_pages = alerts_data.get("pages", 1)
            
            st.write(f"**Total Alerts:** {total} (Page {current_page} of {total_pages})")
            
            if alerts:
                # Create DataFrame for display
                df = pd.DataFrame(alerts)
                
                # Format datetime columns
                if 'created_at' in df.columns:
                    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Display alerts table
                for i, alert in enumerate(alerts):
                    with st.expander(f"🚨 {alert.get('title', 'Unknown')} - {alert.get('severity', 'unknown').upper()}"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**Alert ID:** {alert.get('alert_id', 'N/A')}")
                            st.write(f"**Status:** {alert.get('status', 'N/A').upper()}")
                            st.write(f"**Severity:** {alert.get('severity', 'N/A').upper()}")
                            st.write(f"**Source:** {alert.get('source_system', 'N/A')}")
                        
                        with col2:
                            st.write(f"**Group ID:** {alert.get('group_id', 'N/A')}")
                            st.write(f"**Created:** {api_client.format_datetime(alert.get('created_at', ''))}")
                            if alert.get('metric_name'):
                                st.write(f"**Metric:** {alert.get('metric_name')} = {alert.get('metric_value', 'N/A')}")
                        
                        with col3:
                            # Action buttons
                            if st.button(f"View Details", key=f"view_{alert.get('alert_id')}"):
                                st.session_state.selected_alert = alert.get('alert_id')
                                st.rerun()
                            
                            if alert.get('status') == 'active':
                                if st.button(f"Acknowledge", key=f"ack_{alert.get('alert_id')}"):
                                    update_alert_status(api_client, alert.get('alert_id'), 'acknowledged')
                                
                                if st.button(f"Resolve", key=f"resolve_{alert.get('alert_id')}"):
                                    update_alert_status(api_client, alert.get('alert_id'), 'resolved')
                        
                        if alert.get('description'):
                            st.write(f"**Description:** {alert.get('description')}")
                        
                        # Show tags and labels if available
                        if alert.get('tags'):
                            st.write(f"**Tags:** {', '.join([f'{k}:{v}' for k, v in alert.get('tags', {}).items()])}")
                        
                        if alert.get('labels'):
                            st.write(f"**Labels:** {', '.join([f'{k}:{v}' for k, v in alert.get('labels', {}).items()])}")
                
                # Pagination buttons
                col_prev, col_next = st.columns([1, 1])
                with col_prev:
                    if current_page > 1:
                        if st.button("⬅️ Previous Page"):
                            st.session_state.alert_page = current_page - 1
                            st.rerun()
                
                with col_next:
                    if current_page < total_pages:
                        if st.button("Next Page ➡️"):
                            st.session_state.alert_page = current_page + 1
                            st.rerun()
            else:
                st.info("No alerts found matching the filters")
        else:
            st.error("Failed to fetch alerts")
            
    except Exception as e:
        st.error(f"Error fetching alerts: {e}")


def show_alert_groups(api_client):
    """Show alert groups"""
    
    st.subheader("📦 Alert Groups")
    
    # Filters for groups
    col1, col2 = st.columns(2)
    with col1:
        group_severity_filter = st.multiselect(
            "Group Severity",
            ["critical", "high", "medium", "low"],
            default=None,
            key="group_severity"
        )
    
    with col2:
        group_status_filter = st.selectbox(
            "Group Status",
            ["all", "active", "grouped", "resolved"],
            index=0
        )
    
    # Pagination
    page_size = st.selectbox("Groups per page", [5, 10, 20], index=1, key="groups_page_size")
    
    if "group_page" not in st.session_state:
        st.session_state.group_page = 1
    
    try:
        filters = {
            "severity": group_severity_filter if group_severity_filter else None,
            "status": group_status_filter if group_status_filter != "all" else None
        }
        
        response = api_client.get_alert_groups(page=st.session_state.group_page, size=page_size, **filters)
        
        if response and response.get("success"):
            groups_data = response.get("data", {})
            groups = groups_data.get("items", [])
            total = groups_data.get("total", 0)
            total_pages = groups_data.get("pages", 1)
            
            st.write(f"**Total Groups:** {total} (Page {st.session_state.group_page} of {total_pages})")
            
            if groups:
                for group in groups:
                    with st.expander(f"📦 {group.get('title', 'Unknown Group')} ({group.get('alert_count', 0)} alerts)"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**Group ID:** {group.get('group_id', 'N/A')}")
                            st.write(f"**Status:** {group.get('status', 'N/A').upper()}")
                            st.write(f"**Severity:** {group.get('severity', 'N/A').upper()}")
                            st.write(f"**Alert Count:** {group.get('alert_count', 0)}")
                        
                        with col2:
                            st.write(f"**Created:** {api_client.format_datetime(group.get('created_at', ''))}")
                            st.write(f"**Updated:** {api_client.format_datetime(group.get('updated_at', ''))}")
                            if group.get('similar_pattern'):
                                st.write(f"**Pattern:** {group.get('similar_pattern')}")
                        
                        with col3:
                            # Generate RCA button
                            if st.button(f"Generate RCA", key=f"gen_rca_{group.get('group_id')}"):
                                generate_rca_for_group(api_client, group.get('group_id'))
                            
                            # View group details
                            if st.button(f"View Details", key=f"view_group_{group.get('group_id')}"):
                                show_group_details(api_client, group.get('group_id'))
                        
                        if group.get('description'):
                            st.write(f"**Description:** {group.get('description')}")
                        
                        # Show alerts in the group
                        alerts = group.get('alerts', [])
                        if alerts:
                            st.write("**Alerts in this group:**")
                            for alert in alerts[:5]:  # Show first 5 alerts
                                st.write(f"- {alert.get('title', 'Unknown')} ({alert.get('severity', 'unknown')})")
                            if len(alerts) > 5:
                                st.write(f"... and {len(alerts) - 5} more alerts")
            else:
                st.info("No alert groups found")
        else:
            st.error("Failed to fetch alert groups")
            
    except Exception as e:
        st.error(f"Error fetching alert groups: {e}")


def show_create_alert(api_client):
    """Show create alert form"""
    
    st.subheader("➕ Create New Alert")
    
    with st.form("create_alert_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Alert Title*", placeholder="Enter alert title")
            severity = st.selectbox("Severity*", ["critical", "high", "medium", "low"])
            source_system = st.text_input("Source System*", placeholder="e.g., monitoring-system")
            metric_name = st.text_input("Metric Name", placeholder="e.g., cpu_usage")
        
        with col2:
            description = st.text_area("Description", placeholder="Detailed description of the alert")
            metric_value = st.number_input("Metric Value", value=0.0)
            threshold = st.number_input("Threshold", value=0.0)
        
        # Tags and labels
        st.subheader("Tags and Labels")
        col3, col4 = st.columns(2)
        
        with col3:
            tags_input = st.text_area("Tags (JSON format)", placeholder='{"environment": "prod", "service": "api"}')
        
        with col4:
            labels_input = st.text_area("Labels (JSON format)", placeholder='{"team": "sre", "priority": "high"}')
        
        # Raw data
        raw_data_input = st.text_area("Raw Alert Data (JSON)", placeholder='{"additional": "data"}')
        
        submitted = st.form_submit_button("Create Alert")
        
        if submitted:
            if not all([title, severity, source_system]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                try:
                    # Parse JSON inputs
                    tags = {}
                    labels = {}
                    raw_data = {}
                    
                    if tags_input.strip():
                        tags = json.loads(tags_input)
                    
                    if labels_input.strip():
                        labels = json.loads(labels_input)
                    
                    if raw_data_input.strip():
                        raw_data = json.loads(raw_data_input)
                    
                    # Create alert data
                    alert_data = {
                        "title": title,
                        "description": description if description else None,
                        "severity": severity,
                        "source_system": source_system,
                        "metric_name": metric_name if metric_name else None,
                        "metric_value": metric_value if metric_value else None,
                        "threshold": threshold if threshold else None,
                        "tags": tags if tags else None,
                        "labels": labels if labels else None,
                        "raw_data": raw_data if raw_data else None
                    }
                    
                    # Create alert
                    response = api_client.create_alert(alert_data)
                    
                    if response and response.get("success"):
                        st.success(f"Alert created successfully! Alert ID: {response.get('data', {}).get('alert_id')}")
                        st.info(f"Alert assigned to group: {response.get('data', {}).get('group_id')}")
                        # Clear form by rerunning
                        st.rerun()
                    else:
                        st.error("Failed to create alert")
                        
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON format: {e}")
                except Exception as e:
                    st.error(f"Error creating alert: {e}")


def show_alert_analytics(api_client):
    """Show alert analytics and statistics"""
    
    st.subheader("📊 Alert Analytics")
    
    # Time range selector
    col1, col2 = st.columns(2)
    with col1:
        hours_back = st.selectbox("Time Range", [1, 6, 12, 24, 48, 168], index=3, format_func=lambda x: f"Last {x} hours")
    
    with col2:
        if st.button("Refresh Data"):
            st.rerun()
    
    try:
        # Get alert statistics
        stats_response = api_client.get_alert_stats(hours_back=hours_back)
        
        if stats_response and stats_response.get("success"):
            stats = stats_response.get("data", {})
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Alerts", stats.get("total_alerts", 0))
            
            with col2:
                st.metric("Alert Groups", stats.get("total_groups", 0))
            
            with col3:
                status_dist = stats.get("status_distribution", {})
                st.metric("Active Alerts", status_dist.get("active", 0))
            
            with col4:
                severity_dist = stats.get("severity_distribution", {})
                st.metric("Critical Alerts", severity_dist.get("critical", 0))
            
            st.markdown("---")
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Severity distribution pie chart
                severity_data = stats.get("severity_distribution", {})
                if severity_data:
                    fig_severity = px.pie(
                        values=list(severity_data.values()),
                        names=list(severity_data.keys()),
                        title="Alerts by Severity",
                        color_discrete_map={
                            "critical": "#ff0000",
                            "high": "#ff4500",
                            "medium": "#ffa500", 
                            "low": "#32cd32"
                        }
                    )
                    st.plotly_chart(fig_severity, use_container_width=True)
            
            with col2:
                # Status distribution pie chart
                status_data = stats.get("status_distribution", {})
                if status_data:
                    fig_status = px.pie(
                        values=list(status_data.values()),
                        names=list(status_data.keys()),
                        title="Alerts by Status",
                        color_discrete_map={
                            "active": "#ff4b4b",
                            "acknowledged": "#ffa500",
                            "resolved": "#00ff00"
                        }
                    )
                    st.plotly_chart(fig_status, use_container_width=True)
            
            # Top source systems
            st.subheader("Top Source Systems")
            top_systems = stats.get("top_source_systems", [])
            if top_systems:
                systems_df = pd.DataFrame(top_systems)
                fig_systems = px.bar(
                    systems_df,
                    x="system",
                    y="count",
                    title="Alerts by Source System",
                    labels={"system": "Source System", "count": "Alert Count"}
                )
                st.plotly_chart(fig_systems, use_container_width=True)
            else:
                st.info("No source system data available")
        else:
            st.error("Failed to fetch alert statistics")
            
    except Exception as e:
        st.error(f"Error loading analytics: {e}")


def update_alert_status(api_client, alert_id: str, new_status: str):
    """Update alert status"""
    try:
        response = api_client.update_alert(alert_id, {"status": new_status})
        if response and response.get("success"):
            st.success(f"Alert status updated to {new_status}")
            st.rerun()
        else:
            st.error("Failed to update alert status")
    except Exception as e:
        st.error(f"Error updating alert: {e}")


def generate_rca_for_group(api_client, group_id: str):
    """Generate RCA for an alert group"""
    try:
        response = api_client.generate_rca(group_id)
        if response and response.get("success"):
            st.success("RCA generation started! Check the RCA Details page for updates.")
        else:
            st.error("Failed to start RCA generation")
    except Exception as e:
        st.error(f"Error generating RCA: {e}")


def show_group_details(api_client, group_id: str):
    """Show detailed information about an alert group"""
    try:
        response = api_client.get_alert_group(group_id)
        if response and response.get("success"):
            group = response.get("data", {})
            
            with st.expander("📦 Group Details", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Group ID:** {group.get('group_id')}")
                    st.write(f"**Title:** {group.get('title')}")
                    st.write(f"**Status:** {group.get('status')}")
                    st.write(f"**Severity:** {group.get('severity')}")
                
                with col2:
                    st.write(f"**Alert Count:** {group.get('alert_count')}")
                    st.write(f"**Created:** {api_client.format_datetime(group.get('created_at'))}")
                    st.write(f"**Updated:** {api_client.format_datetime(group.get('updated_at'))}")
                
                if group.get('description'):
                    st.write(f"**Description:** {group.get('description')}")
                
                if group.get('similar_pattern'):
                    st.write(f"**Pattern:** {group.get('similar_pattern')}")
        else:
            st.error("Failed to fetch group details")
    except Exception as e:
        st.error(f"Error fetching group details: {e}")
