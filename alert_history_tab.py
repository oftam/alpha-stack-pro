"""
Alert History Tab - Dashboard Integration
Shows recent whale alerts and system status

Add to ultimate_v20_ELITE_COMPLETE.py as Tab 7
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import os


def render_alert_history_tab():
    """
    Tab 7: Alert History
    Shows whale alerts, statistics, and system status
    """
    
    st.header("🔔 Whale Alert History")
    
    # Check if alert system is configured
    config_exists = os.path.exists('alert_config.json')
    history_exists = os.path.exists('alert_history.json')
    
    if not config_exists:
        st.warning("⚠️ Alert system not configured yet")
        st.info("""
        **To enable whale alerts:**
        1. Follow setup in WHALE_ALERT_SETUP_GUIDE.md
        2. Create Telegram bot
        3. Configure alert_config.json
        4. Run: `python whale_alert_monitor.py`
        """)
        return
    
    # Load configuration
    try:
        with open('alert_config.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        return
    
    # System Status
    st.subheader("📊 System Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        telegram_configured = bool(config.get('telegram_bot_token')) and \
                             config.get('telegram_bot_token') != "PASTE_YOUR_BOT_TOKEN_HERE"
        status = "🟢 Active" if telegram_configured else "🔴 Not Configured"
        st.metric("Telegram", status)
    
    with col2:
        interval = config.get('check_interval_minutes', 15)
        st.metric("Check Interval", f"{interval} min")
    
    with col3:
        severity = config.get('severity_filter', 'medium').title()
        st.metric("Severity Filter", severity)
    
    with col4:
        cooldown = config.get('cooldown_hours', 6)
        st.metric("Cooldown", f"{cooldown}h")
    
    st.markdown("---")
    
    # Alert History
    if history_exists:
        try:
            with open('alert_history.json', 'r') as f:
                history = json.load(f)
        except Exception as e:
            st.error(f"Error loading history: {e}")
            history = []
    else:
        history = []
        st.info("📭 No alerts yet. Monitor will create history when first alert triggers.")
    
    if history:
        st.subheader(f"📜 Recent Alerts ({len(history)} total)")
        
        # Statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Count by type
            types = {}
            for alert in history:
                alert_type = alert.get('type', 'unknown')
                types[alert_type] = types.get(alert_type, 0) + 1
            most_common = max(types.items(), key=lambda x: x[1]) if types else ('none', 0)
            st.metric("Most Common", f"{most_common[0]}", f"{most_common[1]} alerts")
        
        with col2:
            # Recent alerts
            recent = [a for a in history if _is_recent(a.get('timestamp'), hours=24)]
            st.metric("Last 24 Hours", len(recent))
        
        with col3:
            # High severity count
            high_severity = [a for a in history if a.get('severity') == 'high']
            st.metric("High Severity", len(high_severity))
        
        st.markdown("---")
        
        # Alert list
        st.subheader("Recent Alerts")
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            filter_days = st.selectbox("Show alerts from:", 
                                       ["Last 24 hours", "Last 7 days", "Last 30 days", "All time"],
                                       index=1)
        
        with col2:
            filter_severity = st.multiselect("Severity:", 
                                             ["low", "medium", "high"],
                                             default=["medium", "high"])
        
        # Apply filters
        filtered_history = _filter_alerts(history, filter_days, filter_severity)
        
        if not filtered_history:
            st.info("No alerts match your filters.")
        else:
            # Display alerts
            for alert in reversed(filtered_history[-20:]):  # Show last 20
                _render_alert_card(alert)
        
        # Export option
        st.markdown("---")
        if st.button("📥 Export Alert History"):
            df = pd.DataFrame(filtered_history)
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "whale_alert_history.csv",
                "text/csv"
            )
    
    # Configuration Preview
    st.markdown("---")
    with st.expander("⚙️ View Current Configuration"):
        st.json(config)
    
    # Quick Actions
    st.markdown("---")
    st.subheader("🔧 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh History"):
            st.rerun()
    
    with col2:
        if st.button("📖 Setup Guide"):
            st.info("See WHALE_ALERT_SETUP_GUIDE.md in your project folder")
    
    with col3:
        if st.button("🚀 Quick Start"):
            st.info("See QUICK_START.md for 5-minute setup")


def _is_recent(timestamp_str: str, hours: int = 24) -> bool:
    """Check if timestamp is within last N hours"""
    try:
        alert_time = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        return (now - alert_time) < timedelta(hours=hours)
    except:
        return False


def _filter_alerts(history, days_filter, severity_filter):
    """Filter alerts by time range and severity"""
    filtered = []
    
    # Time filter
    if days_filter == "Last 24 hours":
        hours = 24
    elif days_filter == "Last 7 days":
        hours = 24 * 7
    elif days_filter == "Last 30 days":
        hours = 24 * 30
    else:
        hours = None  # All time
    
    for alert in history:
        # Time check
        if hours and not _is_recent(alert.get('timestamp'), hours):
            continue
        
        # Severity check
        if alert.get('severity') not in severity_filter:
            continue
        
        filtered.append(alert)
    
    return filtered


def _render_alert_card(alert):
    """Render a single alert as a card"""
    severity = alert.get('severity', 'medium')
    alert_type = alert.get('type', 'unknown')
    title = alert.get('title', 'Alert')
    message = alert.get('message', '')
    timestamp = alert.get('timestamp', '')
    
    # Color by severity
    if severity == 'high':
        color = "#ff4444"
        icon = "🔴"
    elif severity == 'medium':
        color = "#ff9944"
        icon = "🟡"
    else:
        color = "#44ff44"
        icon = "🟢"
    
    # Format timestamp
    try:
        dt = datetime.fromisoformat(timestamp)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        time_ago = _time_ago(dt)
    except:
        time_str = timestamp
        time_ago = ""
    
    # Render
    with st.container():
        st.markdown(f"""
        <div style="border-left: 4px solid {color}; padding: 10px; margin: 10px 0; background-color: #1e1e1e;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="font-size: 1.1em;">{icon} {title}</strong>
                    <br>
                    <span style="color: #888; font-size: 0.9em;">{time_str} ({time_ago})</span>
                </div>
                <div>
                    <span style="background-color: {color}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.8em;">
                        {severity.upper()}
                    </span>
                </div>
            </div>
            <div style="margin-top: 10px; white-space: pre-wrap;">
                {message}
            </div>
        </div>
        """, unsafe_allow_html=True)


def _time_ago(dt):
    """Convert datetime to 'time ago' string"""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes}m ago"
    else:
        return "just now"


# Example usage in main dashboard:
"""
# In ultimate_v20_ELITE_COMPLETE.py, add as Tab 7:

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📈 Chart",
    "🎯 Elite Analysis", 
    "📊 Metrics",
    "🔮 Projection",
    "🗃️ Raw Data",
    "📖 Decision Guide",
    "🔔 Alert History"  # NEW
])

with tab7:
    from alert_history_tab import render_alert_history_tab
    render_alert_history_tab()
"""
