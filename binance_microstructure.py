#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔴 LIVE MICROSTRUCTURE - Binance WebSocket
Real-time orderbook + aggTrades for TRUECVD calculation

Replaces OHLCV proxy with actual market microstructure
"""

import asyncio
import websockets
import json
import numpy as np
import pandas as pd
from datetime import datetime
from collections import deque
from typing import Dict, List, Optional, Callable


class BinanceMicrostructure:
    """
    Live market microstructure from Binance WebSocket
    
    Streams:
    - Orderbook depth (top N levels)
    - Aggregate trades (for CVD)
    - Book ticker (best bid/ask)
    
    Output:
    - TRUECVD (cumulative volume delta)
    - Book imbalance (bid vs ask pressure)
    - Trade flow (institutional vs retail)
    """
    
    def __init__(self, 
                 symbol: str = "btcusdt",
                 depth_levels: int = 20,
                 trades_window: int = 100):
        """
        Args:
            symbol: Trading pair (lowercase)
            depth_levels: Orderbook depth to track
            trades_window: Number of recent trades to keep
        """
        self.symbol = symbol.lower()
        self.depth_levels = depth_levels
        
        # State
        self.orderbook = {'bids': [], 'asks': []}
        self.trades = deque(maxlen=trades_window)
        self.cvd = 0.0  # Cumulative Volume Delta
        self.last_update = None
        self.is_active = False # Health flag for dashboard
        
        # Callbacks
        self.on_orderbook_update: Optional[Callable] = None
        self.on_trade_update: Optional[Callable] = None
        
        # WebSocket URLs
        self.depth_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@depth{depth_levels}"
        self.trades_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@aggTrade"
    
    # =========================================================================
    # WEBSOCKET HANDLERS
    # =========================================================================
    
    async def _handle_depth(self, ws):
        """Handle orderbook depth updates"""
        async for message in ws:
            try:
                data = json.loads(message)
                
                # Update orderbook
                self.orderbook = {
                    'bids': [[float(p), float(q)] for p, q in data['bids']],
                    'asks': [[float(p), float(q)] for p, q in data['asks']],
                    'timestamp': datetime.now()
                }
                
                self.last_update = datetime.now()
                
                # Callback
                if self.on_orderbook_update:
                    self.on_orderbook_update(self.orderbook)
                    
            except Exception as e:
                print(f"Depth error: {e}")
    
    async def _handle_trades(self, ws):
        """Handle aggregate trades"""
        async for message in ws:
            try:
                data = json.loads(message)
                
                # Parse trade
                trade = {
                    'price': float(data['p']),
                    'quantity': float(data['q']),
                    'is_buyer_maker': data['m'],  # True = sell, False = buy
                    'timestamp': pd.Timestamp(data['T'], unit='ms')
                }
                
                # ── Dust Filter (Bug 5): skip noise trades < 10 BTC ──
                if trade['quantity'] < 10.0:
                    continue
                
                # Update CVD
                if trade['is_buyer_maker']:
                    # Sell (market sell hit bid)
                    self.cvd -= trade['quantity']
                else:
                    # Buy (market buy hit ask)
                    self.cvd += trade['quantity']
                
                # Store trade
                self.trades.append(trade)
                
                # Callback
                if self.on_trade_update:
                    self.on_trade_update(trade)
                    
            except Exception as e:
                print(f"Trade error: {e}")
    
    async def start(self):
        """Start WebSocket streams with auto-reconnect logic"""
        retry_delay = 1
        while True:
            try:
                print(f"🔴 Connecting to Binance Microstructure for {self.symbol.upper()}...")
                async with websockets.connect(self.depth_url) as ws_depth, \
                           websockets.connect(self.trades_url) as ws_trades:
                    
                    self.is_active = True
                    retry_delay = 1 # Reset on success
                    
                    # Run both streams concurrently
                    await asyncio.gather(
                        self._handle_depth(ws_depth),
                        self._handle_trades(ws_trades)
                    )
            except Exception as e:
                self.is_active = False
                print(f"⚠️ Microstructure Disconnect: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60) # Max 1 min backoff
    
    # =========================================================================
    # INDICATORS
    # =========================================================================
    
    def get_book_imbalance(self) -> float:
        """
        Calculate orderbook imbalance
        
        Imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        
        Returns:
            -1.0 to +1.0
            +1.0 = all bids (strong buy pressure)
            -1.0 = all asks (strong sell pressure)
        """
        if not self.orderbook['bids'] or not self.orderbook['asks']:
            return 0.0
        
        bid_volume = sum(q for p, q in self.orderbook['bids'])
        ask_volume = sum(q for p, q in self.orderbook['asks'])
        
        total = bid_volume + ask_volume
        if total == 0:
            return 0.0
        
        return (bid_volume - ask_volume) / total
    
    def get_truecvd(self) -> float:
        """
        Get current TRUECVD (Cumulative Volume Delta)
        
        Returns:
            Cumulative delta (buys - sells)
        """
        return self.cvd
    
    def get_trade_flow(self, window_minutes: int = 5) -> Dict:
        """
        Analyze trade flow over window
        
        Returns:
            Dict with buy/sell breakdown
        """
        if not self.trades:
            return {
                'buy_volume': 0,
                'sell_volume': 0,
                'net_volume': 0,
                'buy_trades': 0,
                'sell_trades': 0
            }
        
        # Filter to window
        cutoff = datetime.now() - pd.Timedelta(minutes=window_minutes)
        recent = [t for t in self.trades if t['timestamp'] > cutoff]
        
        buy_volume = sum(t['quantity'] for t in recent if not t['is_buyer_maker'])
        sell_volume = sum(t['quantity'] for t in recent if t['is_buyer_maker'])
        
        buy_trades = sum(1 for t in recent if not t['is_buyer_maker'])
        sell_trades = sum(1 for t in recent if t['is_buyer_maker'])
        
        return {
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'net_volume': buy_volume - sell_volume,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'imbalance': (buy_volume - sell_volume) / (buy_volume + sell_volume) if (buy_volume + sell_volume) > 0 else 0
        }
    
    def get_spread(self) -> float:
        """Get bid-ask spread in bps"""
        if not self.orderbook['bids'] or not self.orderbook['asks']:
            return 0.0
        
        best_bid = self.orderbook['bids'][0][0]
        best_ask = self.orderbook['asks'][0][0]
        mid = (best_bid + best_ask) / 2
        
        spread_bps = ((best_ask - best_bid) / mid) * 10000
        return spread_bps

    def calculate_impact_cost(self, size_usd: float, side: str = 'BUY') -> Dict:
        """
        Estimates the expected slippage/impact for a trade of size_usd.
        
        Args:
            size_usd: Trade size in USD
            side: 'BUY' or 'SELL'
            
        Returns:
            Dict with avg_price, slippage_bps, and impact_status
        """
        book = self.orderbook['asks'] if side == 'BUY' else self.orderbook['bids']
        if not book:
            return {'error': 'No orderbook data'}
            
        remaining_usd = size_usd
        total_qty = 0
        weighted_sum = 0
        
        for price, qty in book:
            level_usd = price * qty
            if remaining_usd <= level_usd:
                fill_qty = remaining_usd / price
                total_qty += fill_qty
                weighted_sum += remaining_usd
                remaining_usd = 0
                break
            else:
                total_qty += qty
                weighted_sum += level_usd
                remaining_usd -= level_usd
        
        if total_qty == 0:
            return {'error': 'Orderbook too thin for size'}
            
        avg_price = weighted_sum / total_qty
        entry_price = book[0][0]
        
        slippage_bps = abs((avg_price - entry_price) / entry_price) * 10000
        
        # Renaissance Threshold: > 50bps is considered "high friction"
        status = "HIGH FRICTION" if slippage_bps > 50 else "LIQUID" if slippage_bps < 10 else "MODERATE"
        
        return {
            'avg_price': avg_price,
            'slippage_bps': slippage_bps,
            'impact_status': status,
            'fill_pct': (1 - (remaining_usd / size_usd)) * 100
        }

    def get_liquidity_knots(self) -> List[Dict]:
        """
        Identifies "Gravity Anchors" (Knots) - prices with disproportionately large depth.
        Part of the Topological Liquidity mapping.
        """
        knots = []
        all_levels = self.orderbook['bids'] + self.orderbook['asks']
        if not all_levels:
            return []
            
        avg_qty = np.mean([q for p, q in all_levels])
        
        for p, q in all_levels:
            if q > avg_qty * 3: # X3 average level depth
                side = "SUPPORT" if any(p == bp for bp, bq in self.orderbook['bids']) else "RESISTANCE"
                knots.append({
                    'price': p,
                    'quantity': q,
                    'type': side,
                    'strength': q / avg_qty
                })
        return knots
    
    def get_snapshot(self) -> Dict:
        """
        Get current microstructure snapshot
        
        Returns full state for analysis
        """
        return {
            'timestamp': self.last_update,
            'truecvd': self.get_truecvd(),
            'book_imbalance': self.get_book_imbalance(),
            'spread_bps': self.get_spread(),
            'trade_flow': self.get_trade_flow(),
            'orderbook_depth': {
                'bids': len(self.orderbook['bids']),
                'asks': len(self.orderbook['asks'])
            },
            'liquidity_knots': self.get_liquidity_knots()
        }


# =============================================================================
# USAGE EXAMPLE (Async)
# =============================================================================

async def example_usage():
    """Example: Run live microstructure and print updates"""
    
    micro = BinanceMicrostructure(symbol="btcusdt", depth_levels=10)
    
    # Set callbacks
    def on_book_update(book):
        imbalance = micro.get_book_imbalance()
        print(f"📊 Book Imbalance: {imbalance:+.3f}")
    
    def on_trade_update(trade):
        side = "BUY" if not trade['is_buyer_maker'] else "SELL"
        print(f"💱 Trade: {side} {trade['quantity']:.4f} @ ${trade['price']:,.2f} | CVD: {micro.get_truecvd():+.2f}")
    
    micro.on_orderbook_update = on_book_update
    micro.on_trade_update = on_trade_update
    
    # Start (runs forever)
    await micro.start()


if __name__ == '__main__':
    # Run example
    print("Starting Binance microstructure feed...")
    print("Press Ctrl+C to stop")
    
    try:
        asyncio.run(example_usage())
    except KeyboardInterrupt:
        print("\n✅ Stopped")
