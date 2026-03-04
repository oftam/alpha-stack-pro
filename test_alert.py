#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Alert Generator
Creates a test alert to verify popup system works

Run: python test_alert.py
"""

import json
from datetime import datetime

print("🧪 Creating test alert...")

# Create test alert
alert = {
    'type': 'test',
    'severity': 'high',
    'title': '🔴 TEST POPUP',
    'message': 'This is a test alert!\n\nIf you see this popup, your alert system is working correctly! ✅',
    'timestamp': datetime.now().isoformat(),
    'data': {
        'test': True,
        'system': 'Whale Alert Monitor'
    }
}

# Load existing history
try:
    with open('alert_history.json', 'r') as f:
        history = json.load(f)
    print(f"📋 Loaded {len(history)} existing alerts")
except:
    history = []
    print("📋 Creating new alert history")

# Add test alert
history.append(alert)

# Save
with open('alert_history.json', 'w') as f:
    json.dump(history, f, indent=2)

print("✅ Test alert created!")
print("\n📍 Next steps:")
print("1. Refresh your dashboard (it auto-refreshes every 60 sec)")
print("2. Or manually refresh browser")
print("3. 💥 POPUP should appear!")
print("\nIf you don't see it:")
print("- Check alert_popup.py is in same folder")
print("- Check ultimate_v20_ELITE_COMPLETE.py has alert imports")
print("- Check browser console for errors (F12)")
