"""
Alert Banner Component - Real-time alerts in dashboard
Shows latest alert at top of dashboard with auto-refresh
"""

import streamlit as st
import json
import os
from datetime import datetime, timedelta


def render_alert_banner():
    """
    Render alert banner at top of dashboard
    Shows most recent alert if within last hour
    Auto-refreshes every minute
    """
    
    # Check if alert history exists
    if not os.path.exists('alert_history.json'):
        return  # No alerts yet
    
    try:
        with open('alert_history.json', 'r') as f:
            history = json.load(f)
    except:
        return  # Error reading
    
    if not history:
        return  # Empty history
    
    # Get most recent alert
    latest_alert = history[-1]
    
    # Check if alert is recent (< 1 hour)
    try:
        alert_time = datetime.fromisoformat(latest_alert.get('timestamp'))
        now = datetime.now()
        time_diff = now - alert_time
        
        if time_diff > timedelta(hours=1):
            return  # Alert too old
    except:
        return  # Invalid timestamp
    
    # Determine color based on severity
    severity = latest_alert.get('severity', 'medium')
    
    if severity == 'high':
        bg_color = "#ff4444"
        icon = "🔴"
        text_color = "white"
    elif severity == 'medium':
        bg_color = "#ff9944"
        icon = "🟡"
        text_color = "white"
    else:
        bg_color = "#44ff44"
        icon = "🟢"
        text_color = "black"
    
    # Format time ago
    minutes_ago = int(time_diff.total_seconds() / 60)
    if minutes_ago < 1:
        time_str = "just now"
    elif minutes_ago < 60:
        time_str = f"{minutes_ago} min ago"
    else:
        hours_ago = int(minutes_ago / 60)
        time_str = f"{hours_ago}h ago"
    
    # Get alert title and message
    title = latest_alert.get('title', 'Alert')
    message = latest_alert.get('message', '')
    
    # Truncate message if too long
    if len(message) > 150:
        message = message[:150] + "..."
    
    # Render banner
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {bg_color} 0%, {bg_color}dd 100%);
        color: {text_color};
        padding: 15px 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 6px solid {bg_color};
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        animation: slideDown 0.5s ease-out;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="flex: 1;">
                <div style="font-size: 1.2em; font-weight: bold; margin-bottom: 5px;">
                    {icon} {title}
                </div>
                <div style="font-size: 0.9em; opacity: 0.95;">
                    {message}
                </div>
            </div>
            <div style="text-align: right; min-width: 120px;">
                <div style="font-size: 0.85em; opacity: 0.9;">
                    {time_str}
                </div>
                <div style="margin-top: 5px;">
                    <span style="
                        background-color: rgba(255,255,255,0.2);
                        padding: 3px 8px;
                        border-radius: 12px;
                        font-size: 0.75em;
                        font-weight: bold;
                    ">
                        {severity.upper()}
                    </span>
                </div>
            </div>
        </div>
    </div>
    
    <style>
    @keyframes slideDown {{
        from {{
            transform: translateY(-20px);
            opacity: 0;
        }}
        to {{
            transform: translateY(0);
            opacity: 1;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Add expander for full details
    with st.expander("📋 View Full Alert Details"):
        st.json(latest_alert)


def render_alert_summary_widget():
    """
    Render compact alert summary widget
    Shows count of recent alerts by severity
    """
    
    if not os.path.exists('alert_history.json'):
        return
    
    try:
        with open('alert_history.json', 'r') as f:
            history = json.load(f)
    except:
        return
    
    if not history:
        return
    
    # Count recent alerts (last 24 hours)
    now = datetime.now()
    recent = {
        'high': 0,
        'medium': 0,
        'low': 0
    }
    
    for alert in history:
        try:
            alert_time = datetime.fromisoformat(alert.get('timestamp'))
            if now - alert_time < timedelta(hours=24):
                severity = alert.get('severity', 'medium')
                recent[severity] = recent.get(severity, 0) + 1
        except:
            continue
    
    # Render if there are recent alerts
    total = sum(recent.values())
    if total == 0:
        return
    
    st.markdown(f"""
    <div style="
        background: #1e1e1e;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        border-left: 3px solid #ffd700;
    ">
        <div style="font-size: 0.9em; font-weight: bold; margin-bottom: 5px;">
            📊 Alerts (24h): {total}
        </div>
        <div style="display: flex; gap: 15px; font-size: 0.85em;">
            <span>🔴 High: {recent['high']}</span>
            <span>🟡 Med: {recent['medium']}</span>
            <span>🟢 Low: {recent['low']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# Example usage in main dashboard:
"""
# At the very top of ultimate_v20_ELITE_COMPLETE.py, after st.set_page_config:

from alert_banner import render_alert_banner, render_alert_summary_widget

# Auto-refresh every 60 seconds
st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)

# Render alert banner
render_alert_banner()

# Optional: compact summary widget in sidebar
with st.sidebar:
    render_alert_summary_widget()

# Rest of dashboard...
"""
