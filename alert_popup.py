"""
Alert Popup Modal - Dramatic alerts that jump in your face!
Cannot be missed. Shows in center of screen with overlay.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import os
from datetime import datetime, timedelta


def render_alert_popup():
    """
    Render dramatic alert popup modal
    Shows center of screen, cannot be missed
    Auto-dismisses after being seen
    """
    
    # Check if alert history exists
    if not os.path.exists('alert_history.json'):
        return
    
    try:
        with open('alert_history.json', 'r') as f:
            history = json.load(f)
    except:
        return
    
    if not history:
        return
    
    # Get most recent alert
    latest_alert = history[-1]
    
    # Check if already seen
    alert_id = latest_alert.get('timestamp', '')
    if 'seen_alerts' not in st.session_state:
        st.session_state.seen_alerts = []
    
    if alert_id in st.session_state.seen_alerts:
        return  # Already dismissed
    
    # Check if alert is very recent (< 5 minutes)
    try:
        alert_time = datetime.fromisoformat(latest_alert.get('timestamp'))
        now = datetime.now()
        time_diff = now - alert_time
        
        if time_diff > timedelta(minutes=5):
            return  # Alert too old for popup
    except:
        return
    
    # Get alert details
    severity = latest_alert.get('severity', 'medium')
    title = latest_alert.get('title', 'Alert')
    message = latest_alert.get('message', '')
    data = latest_alert.get('data', {})
    
    # Determine colors and icon
    if severity == 'high':
        bg_color = "#ff2244"
        border_color = "#ff0000"
        icon = "🔴"
        sound = "https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"
    elif severity == 'medium':
        bg_color = "#ff9933"
        border_color = "#ff6600"
        icon = "🟡"
        sound = "https://assets.mixkit.co/active_storage/sfx/2870/2870-preview.mp3"
    else:
        bg_color = "#44cc44"
        border_color = "#00aa00"
        icon = "🟢"
        sound = None
    
    # Create popup HTML
    popup_html = f"""
    <style>
        @keyframes popIn {{
            0% {{
                transform: scale(0.5) translateY(-100px);
                opacity: 0;
            }}
            50% {{
                transform: scale(1.05) translateY(0);
            }}
            100% {{
                transform: scale(1) translateY(0);
                opacity: 1;
            }}
        }}
        
        @keyframes pulse {{
            0%, 100% {{
                box-shadow: 0 0 20px {border_color}, 0 0 40px {border_color};
            }}
            50% {{
                box-shadow: 0 0 40px {border_color}, 0 0 60px {border_color};
            }}
        }}
        
        .alert-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(5px);
            z-index: 999999;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s ease-out;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        .alert-modal {{
            background: linear-gradient(135deg, {bg_color} 0%, {bg_color}dd 100%);
            border: 4px solid {border_color};
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            width: 90%;
            color: white;
            text-align: center;
            animation: popIn 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55), 
                       pulse 2s ease-in-out infinite;
            position: relative;
        }}
        
        .alert-icon {{
            font-size: 4em;
            margin-bottom: 20px;
            animation: bounce 1s ease-in-out infinite;
        }}
        
        @keyframes bounce {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-10px); }}
        }}
        
        .alert-title {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}
        
        .alert-message {{
            font-size: 1.1em;
            line-height: 1.6;
            margin-bottom: 25px;
            white-space: pre-wrap;
        }}
        
        .alert-data {{
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 25px;
            font-size: 0.95em;
        }}
        
        .alert-buttons {{
            display: flex;
            gap: 15px;
            justify-content: center;
        }}
        
        .alert-button {{
            padding: 12px 30px;
            border: none;
            border-radius: 25px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .alert-button-primary {{
            background: white;
            color: {bg_color};
        }}
        
        .alert-button-primary:hover {{
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(255,255,255,0.3);
        }}
        
        .alert-button-secondary {{
            background: rgba(255,255,255,0.2);
            color: white;
        }}
        
        .alert-button-secondary:hover {{
            background: rgba(255,255,255,0.3);
        }}
        
        .close-button {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            font-size: 1.5em;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .close-button:hover {{
            background: rgba(255,255,255,0.4);
            transform: rotate(90deg);
        }}
    </style>
    
    <div id="alert-overlay" class="alert-overlay">
        <div class="alert-modal">
            <button class="close-button" onclick="dismissAlert()">✕</button>
            
            <div class="alert-icon">{icon}</div>
            
            <div class="alert-title">{title}</div>
            
            <div class="alert-message">{message[:300]}</div>
            
            <div class="alert-data">
                <div style="margin-bottom: 10px;">
                    <strong>Time:</strong> Just now
                </div>
                <div>
                    <strong>Severity:</strong> {severity.upper()}
                </div>
            </div>
            
            <div class="alert-buttons">
                <button class="alert-button alert-button-primary" onclick="dismissAlert()">
                    ✓ Got it!
                </button>
                <button class="alert-button alert-button-secondary" onclick="goToHistory()">
                    Details →
                </button>
            </div>
        </div>
    </div>
    
    {"<audio autoplay><source src='" + sound + "' type='audio/mpeg'></audio>" if sound else ""}
    
    <script>
        function dismissAlert() {{
            // Send signal to Streamlit to mark as seen
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: 'dismissed'
            }}, '*');
            
            // Hide overlay
            document.getElementById('alert-overlay').style.display = 'none';
        }}
        
        function goToHistory() {{
            // Dismiss and scroll to Tab 7
            dismissAlert();
            // Note: actual tab switching would need additional integration
        }}
        
        // Auto-dismiss after 30 seconds if not clicked
        setTimeout(dismissAlert, 30000);
    </script>
    """
    
    # Render popup
    components.html(popup_html, height=0, scrolling=False)
    
    # Check for dismissal
    if st.session_state.get('alert_dismissed'):
        st.session_state.seen_alerts.append(alert_id)
        st.session_state.alert_dismissed = False


def render_compact_alert_banner():
    """
    Compact banner at top (backup for popup)
    Shows after popup is dismissed
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
    
    latest_alert = history[-1]
    
    # Check if recent
    try:
        alert_time = datetime.fromisoformat(latest_alert.get('timestamp'))
        now = datetime.now()
        time_diff = now - alert_time
        
        if time_diff > timedelta(hours=1):
            return
    except:
        return
    
    severity = latest_alert.get('severity', 'medium')
    title = latest_alert.get('title', 'Alert')
    
    if severity == 'high':
        color = "#ff4444"
        icon = "🔴"
    elif severity == 'medium':
        color = "#ff9944"
        icon = "🟡"
    else:
        color = "#44ff44"
        icon = "🟢"
    
    minutes_ago = int(time_diff.total_seconds() / 60)
    if minutes_ago < 1:
        time_str = "just now"
    elif minutes_ago < 60:
        time_str = f"{minutes_ago}m ago"
    else:
        time_str = f"{int(minutes_ago/60)}h ago"
    
    st.markdown(f"""
    <div style="
        background: {color};
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    ">
        <span style="font-weight: bold;">{icon} {title}</span>
        <span style="font-size: 0.9em;">{time_str} | {severity.upper()}</span>
    </div>
    """, unsafe_allow_html=True)


# Usage in dashboard:
"""
# At top of ultimate_v20_ELITE_COMPLETE.py, after st.set_page_config:

from alert_popup import render_alert_popup, render_compact_alert_banner

# Initialize session state
if 'seen_alerts' not in st.session_state:
    st.session_state.seen_alerts = []

# Render popup (will show if new alert)
render_alert_popup()

# Render compact banner (backup)
render_compact_alert_banner()

# Auto-refresh every 60 seconds
st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)

# Rest of dashboard...
"""
