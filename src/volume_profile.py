"""Volume Profile and Order Flow analysis module.

Provides:
- Volume Profile: price levels with highest volume concentration
- Order Flow Delta: buy/sell pressure estimation from ticks
- VWAP: Volume Weighted Average Price
- Volume analysis for SMC/ICT trading

Note: True VP requires tick-level data. This uses candle volumes which is an approximation.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VolumeProfile:
    """Volume Profile data for a price range."""
    poc: float  # Point of Control - price with highest volume
    vah: float  # Value Area High - 70% volume area top
    val: float  # Value Area Low - 70% volume area bottom
    total_volume: float
    profile: dict[float, float]  # price level -> volume


@dataclass
class OrderFlowData:
    """Order Flow and Delta data."""
    delta: float  # Buy volume - Sell volume
    buy_volume: float
    sell_volume: float
    delta_ratio: float  # delta / total (normalized)
    trend: str  # "buying", "selling", "balanced"


@dataclass
class VWAPData:
    """Volume Weighted Average Price."""
    vwap: float
    vwap_upper: float  # +1 std
    vwap_lower: float  # -1 std


class VolumeProfileAnalyzer:
    """Volume Profile and Order Flow analyzer."""

    def __init__(self, num_bins: int = 20):
        self.num_bins = num_bins

    def calculate_vp(
        self, candles: pd.DataFrame, lookback: int = 50
    ) -> Optional[VolumeProfile]:
        """Calculate Volume Profile for recent candles.
        
        Args:
            candles: DataFrame with high, low, close, volume columns
            lookback: Number of candles to analyze
            
        Returns:
            VolumeProfile object or None if insufficient data
        """
        if len(candles) < lookback:
            return None
            
        df = candles.tail(lookback).copy()
        
        price_range = df["high"].max() - df["low"].min()
        if price_range == 0:
            return None
            
        bin_size = price_range / self.num_bins
        
        profile = {}
        total_volume = 0
        
        for _, row in df.iterrows():
            low = row["low"]
            high = row["high"]
            volume = row.get("volume", row.get("tick_volume", 1))
            
            start_bin = int((low - df["low"].min()) / bin_size)
            end_bin = int((high - df["low"].min()) / bin_size)
            
            for bin_idx in range(start_bin, min(end_bin + 1, self.num_bins)):
                price_level = df["low"].min() + (bin_idx + 0.5) * bin_size
                profile[price_level] = profile.get(price_level, 0) + volume
                total_volume += volume
        
        if not profile:
            return None
            
        poc = max(profile.keys(), key=lambda p: profile[p])
        
        sorted_levels = sorted(profile.items(), key=lambda x: x[1], reverse=True)
        cumsum = 0
        target_70 = total_volume * 0.70
        
        vah = poc
        val = poc
        
        for price, vol in sorted_levels:
            cumsum += vol
            if cumsum <= target_70:
                if price > poc:
                    vah = price
                elif price < poc:
                    val = price
        
        return VolumeProfile(
            poc=poc,
            vah=vah,
            val=val,
            total_volume=total_volume,
            profile=profile
        )

    def calculate_vwap(self, candles: pd.DataFrame, lookback: int = 50) -> Optional[VWAPData]:
        """Calculate VWAP and standard deviation bands.
        
        Args:
            candles: DataFrame with high, low, close, volume columns
            lookback: Number of candles to analyze
            
        Returns:
            VWAPData object or None if insufficient data
        """
        if len(candles) < lookback:
            return None
            
        df = candles.tail(lookback).copy()
        
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        volume = df.get("volume", df.get("tick_volume", 1))
        
        vwap = (typical_price * volume).sum() / volume.sum()
        
        std = np.sqrt(((typical_price - vwap) ** 2 * volume).sum() / volume.sum())
        
        return VWAPData(
            vwap=vwap,
            vwap_upper=vwap + std,
            vwap_lower=vwap - std
        )

    def calculate_order_flow(
        self, candles: pd.DataFrame, ticks: Optional[list] = None
    ) -> Optional[OrderFlowData]:
        """Calculate Order Flow Delta from candles or ticks.
        
        Uses candle close vs open to estimate buy/sell pressure:
        - Close > Open = more buying
        - Close < Open = more selling
        
        For more accurate delta, pass tick data with bid/ask volumes.
        
        Args:
            candles: DataFrame with open, close, volume
            ticks: Optional tick data list with bid/ask volumes
            
        Returns:
            OrderFlowData object
        """
        if len(candles) < 5:
            return None
            
        df = candles.tail(20).copy()
        
        if ticks:
            buy_vol = sum(t.get("buy_volume", 0) for t in ticks)
            sell_vol = sum(t.get("sell_volume", 0) for t in ticks)
        else:
            df["body"] = df["close"] - df["open"]
            
            buy_vol = 0
            sell_vol = 0
            
            for _, row in df.iterrows():
                body = row["body"]
                volume = row.get("volume", row.get("tick_volume", 1))
                
                if body > 0:
                    buy_vol += abs(body / (abs(body) + 1e-10)) * volume
                else:
                    sell_vol += abs(body / (abs(body) + 1e-10)) * volume
        
        total = buy_vol + sell_vol
        if total == 0:
            return None
            
        delta = buy_vol - sell_vol
        delta_ratio = delta / total
        
        if delta_ratio > 0.2:
            trend = "buying"
        elif delta_ratio < -0.2:
            trend = "selling"
        else:
            trend = "balanced"
            
        return OrderFlowData(
            delta=delta,
            buy_volume=buy_vol,
            sell_volume=sell_vol,
            delta_ratio=delta_ratio,
            trend=trend
        )

    def analyze_market_structure(
        self, candles: pd.DataFrame
    ) -> dict:
        """Comprehensive market structure analysis.
        
        Analyzes:
        - Trend direction (based on price vs VWAP)
        - Volume confirmation
        - Value area position
        
        Args:
            candles: DataFrame with OHLCV data
            
        Returns:
            Dictionary with analysis results
        """
        if len(candles) < 50:
            return {}
            
        vwap = self.calculate_vwap(candles)
        vp = self.calculate_vp(candles)
        of = self.calculate_order_flow(candles)
        
        current_price = candles.iloc[-1]["close"]
        
        result = {
            "current_price": current_price,
            "trend": "bullish" if current_price > vwap.vwap else "bearish" if current_price < vwap.vwap else "neutral",
            "vwap": vwap.vwap if vwap else None,
            "vwap_above": current_price > vwap.vwap if vwap else False,
            "poc": vp.poc if vp else None,
            "vah": vp.vah if vp else None,
            "val": vp.val if vp else None,
            "price_in_value_area": vp.val <= current_price <= vp.vah if vp else None,
            "delta_trend": of.trend if of else "unknown",
            "delta_ratio": of.delta_ratio if of else 0,
        }
        
        if vp:
            if current_price > vp.vah:
                result["zone"] = "over_value"
            elif current_price < vp.val:
                result["zone"] = "under_value"
            else:
                result["zone"] = "in_value"
        
        return result
