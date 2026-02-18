#!/usr/bin/env python3
"""
CryptoQuant API Diagnostic Tool
Tests your API key to see what you really have access to
"""

import requests
import json
from datetime import datetime, timedelta

# ============================================================================
# PUT YOUR CRYPTOQUANT API KEY HERE
# ============================================================================
CRYPTOQUANT_API_KEY = "YOUR_API_KEY_HERE"  # 👈 הכנס את ה-API key שלך כאן

BASE_URL = "https://api.cryptoquant.com/v1"
headers = {"Authorization": f"Bearer {CRYPTOQUANT_API_KEY}"}


def test_api_key():
    """Test basic API key validity"""
    print("=" * 80)
    print("🔑 Testing CryptoQuant API Key...")
    print("=" * 80)
    
    try:
        # Test discovery endpoints (should work for any valid key)
        r = requests.get(f"{BASE_URL}/discovery/endpoints", headers=headers, timeout=10)
        
        if r.status_code == 401:
            print("❌ API KEY INVALID - 401 Unauthorized")
            print("   Check your API key is correct")
            return False
        elif r.status_code == 200:
            print("✅ API Key is VALID")
            data = r.json()
            total_endpoints = len(data.get('result', {}).get('data', []))
            print(f"   Total endpoints in catalog: {total_endpoints}")
            return True
        else:
            print(f"⚠️ Unexpected status: {r.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def test_my_scope():
    """Test what endpoints YOU have access to"""
    print("\n" + "=" * 80)
    print("🔍 Checking YOUR API Scope...")
    print("=" * 80)
    
    try:
        r = requests.get(f"{BASE_URL}/my/discovery/endpoints", headers=headers, timeout=10)
        
        if r.status_code != 200:
            print(f"❌ Cannot fetch scope: {r.status_code}")
            return None
        
        data = r.json()
        my_endpoints = data.get('result', {}).get('data', [])
        
        print(f"✅ You have access to {len(my_endpoints)} endpoints")
        print()
        
        # Categorize endpoints
        categories = {}
        for ep in my_endpoints:
            path = ep.get('path', '')
            # Extract category from path like /v1/btc/exchange-flows/netflow
            parts = path.split('/')
            if len(parts) >= 4:
                category = parts[3]  # e.g., 'exchange-flows'
                if category not in categories:
                    categories[category] = []
                categories[category].append(parts[4] if len(parts) > 4 else 'root')
        
        # Print categories
        print("📊 Your endpoint categories:")
        for cat, endpoints in sorted(categories.items()):
            print(f"   • {cat}: {len(endpoints)} endpoints")
        
        return my_endpoints
        
    except Exception as e:
        print(f"❌ Error checking scope: {e}")
        return None


def test_critical_endpoints():
    """Test the critical endpoints Elite v20 needs"""
    print("\n" + "=" * 80)
    print("🎯 Testing CRITICAL Endpoints for Elite v20...")
    print("=" * 80)
    
    # Date for testing (last 7 days)
    from_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
    
    critical_tests = {
        "Exchange Netflow": f"/btc/exchange-flows/netflow?window=day&from={from_date}&exchange=all_exchange",
        "Exchange Reserve": f"/btc/exchange-flows/reserve?window=day&from={from_date}&exchange=all_exchange",
        "SOPR": f"/btc/market-indicator/sopr?window=day&from={from_date}",
        "Whale Inflows (Top 10)": f"/btc/exchange-flows/inflow-top10?window=day&from={from_date}&exchange=all_exchange",
    }
    
    results = {}
    
    for name, endpoint in critical_tests.items():
        try:
            url = f"{BASE_URL}{endpoint}"
            r = requests.get(url, headers=headers, timeout=10)
            
            if r.status_code == 200:
                data = r.json()
                data_points = len(data.get('result', {}).get('data', []))
                results[name] = "✅ WORKING"
                print(f"✅ {name}: WORKING ({data_points} data points)")
            elif r.status_code == 403:
                results[name] = "❌ FORBIDDEN (not on your plan)"
                print(f"❌ {name}: FORBIDDEN - Not included in your plan!")
            elif r.status_code == 429:
                results[name] = "⚠️ RATE LIMITED"
                print(f"⚠️ {name}: Rate limited (too many requests)")
            else:
                results[name] = f"⚠️ Status {r.status_code}"
                print(f"⚠️ {name}: HTTP {r.status_code}")
                
        except Exception as e:
            results[name] = f"❌ Error: {str(e)[:50]}"
            print(f"❌ {name}: Error - {e}")
    
    return results


def print_diagnosis(my_endpoints, test_results):
    """Print final diagnosis and recommendations"""
    print("\n" + "=" * 80)
    print("🩺 DIAGNOSIS")
    print("=" * 80)
    
    # Check if only discovery endpoints
    if my_endpoints and len(my_endpoints) <= 5:
        print("\n❌ PROBLEM DETECTED:")
        print("   You only have access to DISCOVERY endpoints!")
        print("   This means you have NO actual data access.")
        print()
        print("   Your endpoints:")
        for ep in my_endpoints:
            print(f"   • {ep.get('path', 'unknown')}")
        print()
        print("📋 LIKELY CAUSES:")
        print("   1. You have Free/Trial tier (no API access)")
        print("   2. You have Advanced plan ($29/mo) - web only, no API")
        print("   3. API key provisioning error")
        print()
        print("🔧 SOLUTION:")
        print("   Contact CryptoQuant support:")
        print("   - Verify you have Professional plan ($99/mo)")
        print("   - Request API key reissuance")
        print("   - Ask to enable data endpoints")
        return "NO_DATA_ACCESS"
    
    # Check critical endpoint results
    working = sum(1 for r in test_results.values() if "✅" in r)
    forbidden = sum(1 for r in test_results.values() if "❌ FORBIDDEN" in r)
    
    if working == len(test_results):
        print("\n✅ EXCELLENT!")
        print("   All critical endpoints are WORKING!")
        print("   Your Professional plan is correctly configured.")
        print()
        print("🚀 NEXT STEP:")
        print("   Ready to integrate with Elite v20!")
        return "READY"
    
    elif forbidden > 0:
        print("\n⚠️ PARTIAL ACCESS DETECTED:")
        print(f"   Working: {working}/{len(test_results)}")
        print(f"   Forbidden: {forbidden}/{len(test_results)}")
        print()
        print("📋 LIKELY CAUSE:")
        print("   Your plan does not include exchange-flows endpoints")
        print("   (Professional plan should have these)")
        print()
        print("🔧 SOLUTIONS:")
        print("   Option 1: Contact CryptoQuant support")
        print("   Option 2: Switch to Glassnode ($29/mo)")
        print("   Option 3: Use PROXY mode (free, 80% accuracy)")
        return "PARTIAL_ACCESS"
    
    else:
        print("\n⚠️ UNKNOWN ISSUE:")
        print(f"   Working: {working}/{len(test_results)}")
        print("   Please check network connection and try again")
        return "UNKNOWN"


def main():
    """Main diagnostic flow"""
    print("\n" + "=" * 80)
    print("🧬 ELITE v20 - CryptoQuant API Diagnostic")
    print("=" * 80)
    print()
    
    if CRYPTOQUANT_API_KEY == "YOUR_API_KEY_HERE":
        print("❌ ERROR: Please edit this file and add your API key!")
        print("   Open: utils/test_cryptoquant_api.py")
        print("   Line 14: CRYPTOQUANT_API_KEY = 'YOUR_KEY_HERE'")
        return
    
    # Step 1: Test API key validity
    if not test_api_key():
        print("\n❌ Cannot proceed - API key is invalid")
        return
    
    # Step 2: Check your scope
    my_endpoints = test_my_scope()
    if my_endpoints is None:
        print("\n❌ Cannot check scope")
        return
    
    # Step 3: Test critical endpoints
    test_results = test_critical_endpoints()
    
    # Step 4: Print diagnosis
    status = print_diagnosis(my_endpoints, test_results)
    
    # Final recommendations
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    
    if status == "READY":
        print("""
✅ Your CryptoQuant API is ready for Elite v20!

Next steps:
1. Add your API key to Elite v20:
   Edit: elite_v20_production/.env
   Add: CRYPTOQUANT_API_KEY=your_key_here

2. Run Elite v20 dashboard:
   streamlit run elite_v20_dashboard.py

3. Check the dashboard shows LIVE on-chain data
        """)
    
    elif status == "NO_DATA_ACCESS":
        print("""
❌ Your API key has NO data access!

Immediate action required:
1. Contact CryptoQuant support:
   support@cryptoquant.com
   
   Say: "I have Professional plan but my API key only has
   discovery endpoints. Please enable data endpoints."

2. Alternative: Switch to Glassnode
   - $29/month (vs $99/month)
   - Better data (hourly resolution)
   - Simpler API
   
3. Free option: Use PROXY mode
   - Edit Elite v20 config
   - Use volume-based estimates
   - 80% accuracy (vs 95% with real data)
        """)
    
    elif status == "PARTIAL_ACCESS":
        print("""
⚠️ Some endpoints work, others are forbidden

Options:
1. Contact CryptoQuant support (verify plan includes all endpoints)
2. Switch to Glassnode ($29/mo, all endpoints included)
3. Use working endpoints + PROXY mode for missing data
        """)
    
    print("\n" + "=" * 80)
    print("📝 Save this output and send to support if needed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
