"""
Google Finance Connector for ELITE v20
======================================
Connects to Google Sheets with GOOGLEFINANCE() formulas
for real-time macro data.

Author: ELITE v20 System
Date: 2026-02-18
"""

from typing import Dict, Any, Optional
from datetime import datetime

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    print("⚠️ gspread not installed. Run: pip install gspread google-auth")


class GoogleFinanceConnector:
    """
    Connects to Google Sheets for macro data
    """
    
    def __init__(self, sheet_name: str = "Elite_v20_Macro_Pulse", credentials_path: Optional[str] = None):
        """
        Initialize connection to Google Sheets
        
        Args:
            sheet_name: Name of the Google Sheet
            credentials_path: Path to service account JSON (optional)
        """
        self.sheet_name = sheet_name
        self.credentials_path = credentials_path
        self.client = None
        self.sheet = None
        
        if not GSPREAD_AVAILABLE:
            print("❌ gspread unavailable")
            return
        
        try:
            if credentials_path:
                # Use service account
                scope = [
                    'https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive'
                ]
                creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
                self.client = gspread.authorize(creds)
            else:
                # Try OAuth (user consent) - simpler for personal use
                self.client = gspread.oauth()
            
            # Open the sheet
            self.sheet = self.client.open(sheet_name).sheet1
            print(f"✅ Connected to Google Sheet: {sheet_name}")
            
        except Exception as e:
            # Silent failure - module is optional
            # print(f"⚠️ Google Sheets not connected: {e}")
            self.client = None
            self.sheet = None
    
    def fetch_macro_data(self) -> Dict[str, Any]:
        """
        Fetch macro data from Google Sheet
        
        Expected Sheet format:
        A1: BTC ETF Flow  | B1: <value>
        A2: VIX           | B2: <value>
        A3: S&P 500       | B3: <value>
        A4: BTC Price     | B4: <value>
        A5: Sentiment     | B5: Bullish/Bearish/Neutral
        
        Returns:
            Dict with macro data
        """
        if not self.sheet:
            return {
                'status': 'unavailable',
                'error': 'Sheet not connected',
                'btc_etf_flow_24h': 0,
                'sp500_change': 0,
                'vix': 0,
                'sentiment': 'NEUTRAL',
                'fed_rate_cut_prob': 0
            }
        
        try:
            # Fetch values from Sheet
            btc_etf = self.sheet.acell('B1').value
            vix = self.sheet.acell('B2').value
            sp500 = self.sheet.acell('B3').value
            sentiment = self.sheet.acell('B5').value
            
            # Convert to proper types
            macro_data = {
                'status': 'live',
                'btc_etf_flow_24h': float(btc_etf) if btc_etf else 0,
                'sp500_change': float(sp500) if sp500 else 0,
                'vix': float(vix) if vix else 0,
                'sentiment': sentiment if sentiment else 'NEUTRAL',
                'fed_rate_cut_prob': 50,  # Can add another cell for this
                'timestamp': datetime.now().isoformat(),
                'source': 'Google Sheets'
            }
            
            return macro_data
            
        except Exception as e:
            print(f"⚠️ Error fetching from Sheets: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'btc_etf_flow_24h': 0,
                'sp500_change': 0,
                'vix': 0,
                'sentiment': 'NEUTRAL',
                'fed_rate_cut_prob': 0
            }


# Test mode
if __name__ == "__main__":
    print("🧪 Testing Google Finance Connector...")
    
    connector = GoogleFinanceConnector()
    
    if connector.sheet:
        print("✅ Sheet connected!")
        
        data = connector.fetch_macro_data()
        print(f"\n📊 Macro Data:")
        print(f"BTC ETF Flow: ${data['btc_etf_flow_24h']:+.0f}M")
        print(f"S&P 500: {data['sp500_change']:+.2f}%")
        print(f"VIX: {data['vix']:.1f}")
        print(f"Sentiment: {data['sentiment']}")
    else:
        print("❌ Sheet not connected")
        print("Follow setup guide: GOOGLE_SHEETS_SETUP.md")
