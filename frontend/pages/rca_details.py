import streamlit as st
import json
from datetime import datetime


def show_rca_details_page(api_client):
    """Show detailed RCA information and management"""
    
    st.header("🔍 RCA Details")
    
    # RCA selector
    col1, col2 = st.columns([3, 1])
    
    with col1:
        rca_id = st.text_input(
            "Enter RCA ID",
            value=st.session_state.get("selected_rca_id", ""),
            placeholder="Enter RCA ID to view details"
        )
    
    with col2:
        if st.button("Load RCA"):
            if rca_id:
                st.session_state.selected_rca_id = rca_id
                st.rerun()
    
    if rca_id:
        show_rca_full_details(api_client, rca_id)
    else:
        show_recent_rcas_selector(api_client)


def show_recent_rcas_selector(api_client):
    """Show recent RCAs for selection"""
    
    st.subheader("📋 Recent RCAs")
    st.write("Select an RCA to view detailed information:")
    
    try:
        response = api_client.get_rcas(page=1, size=10)
        
        if response and response.get("success"):
            rcas = response.get("data", {}).get("items", [])
            
            if rcas:
                for rca in rcas:
                    with st.expander(f"🔍 {rca.get('title', 'Unknown')} - {rca.get('status', 'unknown').upper()}"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**RCA ID:** {rca.get('rca_id')}")
                            st.write(f"**Status:** {rca.get('status', 'unknown').upper()}")
                            st.write(f"**Severity:** {rca.get('severity', 'unknown').upper()}")
                        
                        with col2:
                            st.write(f"**Created:** {api_client.format_datetime(rca.get('created_at', ''))}")
                            st.write(f"**Confidence:** {rca.get('confidence_score', 'N/A')}")
                        
                        with col3:
                            if st.button("View Details", key=f"select_{rca.get('rca_id')}"):
                                st.session_state.selected_rca_id = rca.get('rca_id')
                                st.rerun()
            else:
                st.info("No RCAs found")
        else:
            st.error("Failed to fetch recent RCAs")
            
    except Exception as e:
        st.error(f"Error fetching recent RCAs: {e}")


def show_rca_full_details(api_client, rca_id):
    """Show complete RCA details with editing capabilities"""
    
    try:
        response = api_client.get_rca(rca_id)
        
        if not response or not response.get("success"):
            st.error("RCA not found or failed to fetch details")
            return
        
        rca = response.get("data", {})
        
        # Header with key information
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status = rca.get("status", "unknown")
            status_color = api_client.get_status_color(status)
            st.markdown(f"**Status:** <span style='color: {status_color}'>**{status.upper()}**</span>", unsafe_allow_html=True)
        
        with col2:
            severity = rca.get("severity", "unknown")
            severity_color = api_client.get_severity_color(severity)
            st.markdown(f"**Severity:** <span style='color: {severity_color}'>**{severity.upper()}**</span>", unsafe_allow_html=True)
        
        with col3:
            st.write(f"**Confidence:** {rca.get('confidence_score', 'N/A')}")
        
        with col4:
            st.write(f"**Method:** {rca.get('analysis_method', 'N/A')}")
        
        st.markdown("---")
        
        # Tabs for different sections
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Analysis", "Related Alerts", "History", "Edit"])
        
        with tab1:
            show_rca_overview(api_client, rca)
        
        with tab2:
            show_rca_analysis(api_client, rca)
        
        with tab3:
            show_related_alerts_tab(api_client, rca_id)
        
        with tab4:
            show_rca_history_tab(api_client, rca_id)
        
        with tab5:
            show_rca_edit_tab(api_client, rca)
            
    except Exception as e:
        st.error(f"Error loading RCA details: {e}")


def show_rca_overview(api_client, rca):
    """Show RCA overview information"""
    
    st.subheader("📋 Overview")
    
    # Basic information
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**RCA ID:** `{rca.get('rca_id', 'N/A')}`")
        st.write(f"**Group ID:** `{rca.get('group_id', 'N/A')}`")
        st.write(f"**Title:** {rca.get('title', 'N/A')}")
        st.write(f"**Created:** {api_client.format_datetime(rca.get('created_at', ''))}")
        st.write(f"**Updated:** {api_client.format_datetime(rca.get('updated_at', ''))}")
    
    with col2:
        if rca.get('assigned_to'):
            st.write(f"**Assigned To:** {rca.get('assigned_to')}")
        
        if rca.get('closed_at'):
            st.write(f"**Closed At:** {api_client.format_datetime(rca.get('closed_at'))}")
        
        st.write(f"**Vectorized:** {'Yes' if rca.get('is_vectorized') else 'No'}")
        
        if rca.get('vector_id'):
            st.write(f"**Vector ID:** {rca.get('vector_id')}")
    
    # Affected systems
    if rca.get('affected_systems'):
        st.write("**Affected Systems:**")
        systems = rca.get('affected_systems', [])
        if isinstance(systems, list):
            for system in systems:
                st.write(f"- {system}")
        else:
            st.write(systems)
    
    # Timeline
    if rca.get('timeline'):
        st.write("**Timeline:**")
        timeline = rca.get('timeline', {})
        if isinstance(timeline, dict):
            for key, value in timeline.items():
                st.write(f"- **{key.replace('_', ' ').title()}:** {value}")
        else:
            st.write(timeline)
    
    # Notes
    if rca.get('notes'):
        st.write("**Notes:**")
        st.write(rca.get('notes'))


def show_rca_analysis(api_client, rca):
    """Show detailed RCA analysis"""
    
    st.subheader("🔬 Analysis")
    
    # Root cause analysis
    st.write("**Root Cause:**")
    if rca.get('root_cause'):
        st.markdown(f"<div style='background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4;'>{rca.get('root_cause')}</div>", unsafe_allow_html=True)
    else:
        st.info("Root cause analysis not available")
    
    st.markdown("---")
    
    # Impact analysis
    st.write("**Impact Analysis:**")
    if rca.get('impact_analysis'):
        st.markdown(f"<div style='background-color: #fff3cd; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #ffc107;'>{rca.get('impact_analysis')}</div>", unsafe_allow_html=True)
    else:
        st.info("Impact analysis not available")
    
    st.markdown("---")
    
    # Recommended actions
    st.write("**Recommended Actions:**")
    if rca.get('recommended_actions'):
        st.markdown(f"<div style='background-color: #d1edff; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #0066cc;'>{rca.get('recommended_actions')}</div>", unsafe_allow_html=True)
    else:
        st.info("Recommended actions not available")
    
    # Similar incidents
    if st.button("🔍 Find Similar Incidents"):
        find_similar_incidents(api_client, rca.get('rca_id'))


def show_related_alerts_tab(api_client, rca_id):
    """Show alerts related to the RCA"""
    
    st.subheader("🚨 Related Alerts")
    
    try:
        response = api_client.get_rca_alerts(rca_id)
        
        if response and response.get("success"):
            alerts = response.get("data", {}).get("alerts", [])
            
            if alerts:
                st.write(f"**Total Related Alerts:** {len(alerts)}")
                
                # Group alerts by severity
                severity_groups = {}
                for alert in alerts:
                    severity = alert.get('severity', 'unknown')
                    if severity not in severity_groups:
                        severity_groups[severity] = []
                    severity_groups[severity].append(alert)
                
                # Display alerts by severity
                for severity in ['critical', 'high', 'medium', 'low']:
                    if severity in severity_groups:
                        st.write(f"**{severity.upper()} Alerts ({len(severity_groups[severity])})**")
                        
                        for alert in severity_groups[severity]:
                            with st.expander(f"🚨 {alert.get('title', 'Unknown')}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write(f"**Alert ID:** {alert.get('alert_id')}")
                                    st.write(f"**Status:** {alert.get('status', 'unknown').upper()}")
                                    st.write(f"**Source:** {alert.get('source_system', 'N/A')}")
                                    st.write(f"**Created:** {api_client.format_datetime(alert.get('created_at', ''))}")
                                
                                with col2:
                                    if alert.get('metric_name'):
                                        st.write(f"**Metric:** {alert.get('metric_name')}")
                                        st.write(f"**Value:** {alert.get('metric_value', 'N/A')}")
                                        st.write(f"**Threshold:** {alert.get('threshold', 'N/A')}")
                                
                                if alert.get('description'):
                                    st.write(f"**Description:** {alert.get('description')}")
                                
                                if alert.get('tags'):
                                    tags = alert.get('tags', {})
                                    if tags:
                                        st.write(f"**Tags:** {', '.join([f'{k}:{v}' for k, v in tags.items()])}")
            else:
                st.info("No related alerts found")
        else:
            st.error("Failed to fetch related alerts")
            
    except Exception as e:
        st.error(f"Error fetching related alerts: {e}")


def show_rca_history_tab(api_client, rca_id):
    """Show RCA status change history"""
    
    st.subheader("📜 Status History")
    
    try:
        response = api_client.get_rca_history(rca_id)
        
        if response and response.get("success"):
            history = response.get("data", {}).get("history", [])
            
            if history:
                for entry in history:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 3])
                        
                        with col1:
                            st.write(f"**{api_client.format_datetime(entry.get('changed_at', ''))}**")
                        
                        with col2:
                            prev_status = entry.get('previous_status', 'N/A')
                            new_status = entry.get('new_status', 'N/A')
                            st.write(f"**{prev_status}** → **{new_status}**")
                        
                        with col3:
                            if entry.get('changed_by'):
                                st.write(f"Changed by: {entry.get('changed_by')}")
                            if entry.get('change_reason'):
                                st.write(f"Reason: {entry.get('change_reason')}")
                        
                        st.markdown("---")
            else:
                st.info("No status history found")
        else:
            st.error("Failed to fetch RCA history")
            
    except Exception as e:
        st.error(f"Error fetching RCA history: {e}")


def show_rca_edit_tab(api_client, rca):
    """Show RCA editing interface"""
    
    st.subheader("✏️ Edit RCA")
    
    with st.form("edit_rca_form"):
        # Basic fields
        col1, col2 = st.columns(2)
        
        with col1:
            new_title = st.text_input("Title", value=rca.get('title', ''))
            new_status = st.selectbox(
                "Status",
                ["open", "in_progress", "closed"],
                index=["open", "in_progress", "closed"].index(rca.get('status', 'open'))
            )
            new_assigned_to = st.text_input("Assigned To", value=rca.get('assigned_to', ''))
        
        with col2:
            new_severity = st.selectbox(
                "Severity",
                ["critical", "high", "medium", "low"],
                index=["critical", "high", "medium", "low"].index(rca.get('severity', 'medium'))
            )
            new_confidence = st.selectbox(
                "Confidence Score",
                ["high", "medium", "low"],
                index=["high", "medium", "low"].index(rca.get('confidence_score', 'medium'))
            )
        
        # Text areas
        new_root_cause = st.text_area("Root Cause", value=rca.get('root_cause', ''), height=150)
        new_impact_analysis = st.text_area("Impact Analysis", value=rca.get('impact_analysis', ''), height=100)
        new_recommended_actions = st.text_area("Recommended Actions", value=rca.get('recommended_actions', ''), height=100)
        new_notes = st.text_area("Notes", value=rca.get('notes', ''), height=100)
        
        # Change reason
        change_reason = st.text_input("Change Reason", placeholder="Describe what you're changing and why")
        
        # Submit buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submitted = st.form_submit_button("Save Changes", type="primary")
        
        with col2:
            if st.form_submit_button("Save & Close RCA"):
                if update_rca(api_client, rca, {
                    "title": new_title,
                    "status": "closed",
                    "root_cause": new_root_cause,
                    "impact_analysis": new_impact_analysis,
                    "recommended_actions": new_recommended_actions,
                    "assigned_to": new_assigned_to,
                    "notes": new_notes
                }, change_reason or "RCA completed"):
                    st.success("RCA updated and closed successfully!")
                    st.rerun()
        
        with col3:
            if st.form_submit_button("Delete RCA", type="secondary"):
                if st.button("Confirm Delete", key="confirm_delete"):
                    delete_rca(api_client, rca.get('rca_id'))
        
        if submitted:
            update_data = {
                "title": new_title,
                "status": new_status,
                "root_cause": new_root_cause,
                "impact_analysis": new_impact_analysis,
                "recommended_actions": new_recommended_actions,
                "assigned_to": new_assigned_to,
                "notes": new_notes
            }
            
            if update_rca(api_client, rca, update_data, change_reason):
                st.success("RCA updated successfully!")
                st.rerun()


def update_rca(api_client, rca, update_data, change_reason):
    """Update RCA with the provided data"""
    try:
        response = api_client.update_rca(
            rca.get('rca_id'),
            update_data,
            changed_by="user",
            change_reason=change_reason or "Manual update"
        )
        
        if response and response.get("success"):
            return True
        else:
            st.error("Failed to update RCA")
            return False
            
    except Exception as e:
        st.error(f"Error updating RCA: {e}")
        return False


def delete_rca(api_client, rca_id):
    """Delete an RCA"""
    try:
        response = api_client.delete_rca(rca_id)
        
        if response and response.get("success"):
            st.success("RCA deleted successfully!")
            st.session_state.selected_rca_id = ""
            st.rerun()
        else:
            st.error("Failed to delete RCA")
            
    except Exception as e:
        st.error(f"Error deleting RCA: {e}")


def find_similar_incidents(api_client, rca_id):
    """Find similar historical incidents"""
    
    # Create a search query based on the current RCA
    # This would typically use the RCA content to search
    st.subheader("🔍 Similar Historical Incidents")
    
    # For now, show a placeholder
    st.info("Similar incident search functionality would analyze the current RCA content and find related historical incidents from the vector database.")
    
    # You could implement this by:
    # 1. Getting the current RCA details
    # 2. Creating a search query from the root cause and description
    # 3. Using the search_historical_incidents API
    
    with st.expander("Manual Search"):
        search_query = st.text_input("Enter search terms:")
        if st.button("Search") and search_query:
            try:
                response = api_client.search_historical_incidents(search_query, 5)
                if response and response.get("success"):
                    incidents = response.get("data", {}).get("incidents", [])
                    
                    if incidents:
                        for incident in incidents:
                            st.write(f"**Similarity:** {incident.get('similarity_score', 0):.2f}")
                            st.write(f"**RCA ID:** {incident.get('rca_id')}")
                            st.write(f"**Severity:** {incident.get('severity')}")
                            st.write(f"**Systems:** {', '.join(incident.get('source_systems', []))}")
                            if incident.get('summary'):
                                st.write(f"**Summary:** {incident.get('summary')[:200]}...")
                            st.markdown("---")
                    else:
                        st.info("No similar incidents found")
                else:
                    st.error("Failed to search for similar incidents")
            except Exception as e:
                st.error(f"Error searching similar incidents: {e}")
