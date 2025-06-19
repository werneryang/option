import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import date, datetime

from .black_scholes import BlackScholesCalculator
from .volatility import HistoricalVolatilityCalculator

@dataclass
class IVAnalysis:
    """Implied volatility analysis result"""
    symbol: str
    expiration: date
    iv_call_avg: float
    iv_put_avg: float
    iv_overall_avg: float
    iv_skew: float  # Put IV - Call IV
    iv_term_structure: Dict[date, float]  # Expiration -> IV
    iv_rank: Optional[float]  # Percentile ranking
    iv_percentile: Optional[float]  # Alternative ranking method

@dataclass
class IVRankData:
    """IV Rank calculation data"""
    current_iv: float
    iv_52w_high: float
    iv_52w_low: float
    iv_rank: float  # (current - low) / (high - low)
    iv_percentile: float  # Percentile in historical distribution

class ImpliedVolatilityCalculator:
    """
    Calculate and analyze implied volatility from option prices
    """
    
    @staticmethod
    def calculate_iv_from_price(market_price: float, S: float, K: float, T: float,
                               r: float, option_type: str, q: float = 0.0) -> Optional[float]:
        """Calculate implied volatility from market price"""
        return BlackScholesCalculator.implied_volatility(
            market_price, S, K, T, r, option_type, q
        )
    
    @staticmethod
    def calculate_iv_for_chain(option_chain: pd.DataFrame, current_price: float,
                              risk_free_rate: float = 0.05) -> pd.DataFrame:
        """
        Calculate implied volatility for entire option chain
        
        Args:
            option_chain: DataFrame with option data (bid, ask, strike, expiration, option_type)
            current_price: Current underlying price
            risk_free_rate: Risk-free rate for calculation
            
        Returns:
            DataFrame with added implied volatility columns
        """
        df = option_chain.copy()
        
        # Add IV columns
        df['iv_bid'] = np.nan
        df['iv_ask'] = np.nan
        df['iv_mid'] = np.nan
        df['time_to_expiry'] = np.nan
        
        for idx, row in df.iterrows():
            try:
                # Calculate time to expiration
                T = BlackScholesCalculator.time_to_expiration(row['expiration'])
                df.loc[idx, 'time_to_expiry'] = T
                
                if T <= 0:
                    continue
                
                # Calculate IV for bid, ask, and mid prices
                if pd.notna(row['bid']) and row['bid'] > 0:
                    iv_bid = ImpliedVolatilityCalculator.calculate_iv_from_price(
                        row['bid'], current_price, row['strike'], T,
                        risk_free_rate, row['option_type']
                    )
                    df.loc[idx, 'iv_bid'] = iv_bid
                
                if pd.notna(row['ask']) and row['ask'] > 0:
                    iv_ask = ImpliedVolatilityCalculator.calculate_iv_from_price(
                        row['ask'], current_price, row['strike'], T,
                        risk_free_rate, row['option_type']
                    )
                    df.loc[idx, 'iv_ask'] = iv_ask
                
                # Mid price IV
                if pd.notna(row['bid']) and pd.notna(row['ask']) and row['ask'] > row['bid']:
                    mid_price = (row['bid'] + row['ask']) / 2
                    iv_mid = ImpliedVolatilityCalculator.calculate_iv_from_price(
                        mid_price, current_price, row['strike'], T,
                        risk_free_rate, row['option_type']
                    )
                    df.loc[idx, 'iv_mid'] = iv_mid
                    
            except Exception as e:
                continue
        
        return df
    
    @staticmethod
    def analyze_iv_skew(option_chain_with_iv: pd.DataFrame, 
                       expiration_filter: Optional[date] = None) -> Dict[str, float]:
        """
        Analyze implied volatility skew
        
        Args:
            option_chain_with_iv: Option chain with IV calculated
            expiration_filter: Filter to specific expiration (optional)
            
        Returns:
            Dictionary with skew metrics
        """
        df = option_chain_with_iv.copy()
        
        if expiration_filter:
            df = df[df['expiration'] == expiration_filter]
        
        if df.empty:
            return {}
        
        # Separate calls and puts
        calls = df[df['option_type'].str.upper() == 'C'].copy()
        puts = df[df['option_type'].str.upper() == 'P'].copy()
        
        # Calculate average IVs
        call_iv_avg = calls['iv_mid'].mean() if not calls.empty else np.nan
        put_iv_avg = puts['iv_mid'].mean() if not puts.empty else np.nan
        
        # ATM IV (closest to current price)
        if not df.empty and 'current_price' in df.columns:
            current_price = df['current_price'].iloc[0]
            atm_options = df.loc[(df['strike'] - current_price).abs().idxmin()]
            atm_iv = atm_options.get('iv_mid', np.nan)
        else:
            atm_iv = np.nan
        
        # OTM Put skew (25 delta equivalent)
        otm_put_iv = np.nan
        otm_call_iv = np.nan
        
        if not puts.empty:
            # Approximate 25-delta put (typically ~15-20% OTM)
            current_price_est = puts['strike'].median() * 1.1  # Rough estimate
            otm_puts = puts[puts['strike'] < current_price_est * 0.85]
            if not otm_puts.empty:
                otm_put_iv = otm_puts['iv_mid'].mean()
        
        if not calls.empty:
            # Approximate 25-delta call (typically ~15-20% OTM)
            current_price_est = calls['strike'].median() * 0.9  # Rough estimate
            otm_calls = calls[calls['strike'] > current_price_est * 1.15]
            if not otm_calls.empty:
                otm_call_iv = otm_calls['iv_mid'].mean()
        
        return {
            'call_iv_avg': call_iv_avg,
            'put_iv_avg': put_iv_avg,
            'atm_iv': atm_iv,
            'otm_put_iv': otm_put_iv,
            'otm_call_iv': otm_call_iv,
            'put_call_skew': put_iv_avg - call_iv_avg if pd.notna(put_iv_avg) and pd.notna(call_iv_avg) else np.nan,
            'smile_skew': otm_put_iv - otm_call_iv if pd.notna(otm_put_iv) and pd.notna(otm_call_iv) else np.nan
        }
    
    @staticmethod
    def calculate_iv_term_structure(option_chain_with_iv: pd.DataFrame) -> Dict[date, float]:
        """
        Calculate implied volatility term structure
        
        Args:
            option_chain_with_iv: Option chain with IV calculated
            
        Returns:
            Dictionary mapping expiration dates to average IV
        """
        df = option_chain_with_iv.copy()
        
        # Group by expiration and calculate average IV
        term_structure = {}
        
        for expiration, group in df.groupby('expiration'):
            valid_ivs = group['iv_mid'].dropna()
            if not valid_ivs.empty:
                term_structure[expiration] = valid_ivs.mean()
        
        return term_structure
    
    @staticmethod
    def calculate_iv_rank(historical_iv_data: pd.DataFrame, current_iv: float,
                         lookback_days: int = 252) -> Optional[IVRankData]:
        """
        Calculate IV Rank and IV Percentile
        
        Args:
            historical_iv_data: DataFrame with historical IV data
            current_iv: Current implied volatility
            lookback_days: Period for rank calculation
            
        Returns:
            IVRankData object with ranking information
        """
        if historical_iv_data.empty or pd.isna(current_iv):
            return None
        
        # Take the most recent lookback_days
        recent_data = historical_iv_data.tail(lookback_days)
        
        if 'iv' not in recent_data.columns and 'iv_mid' in recent_data.columns:
            iv_column = 'iv_mid'
        elif 'iv' in recent_data.columns:
            iv_column = 'iv'
        else:
            return None
        
        historical_ivs = recent_data[iv_column].dropna()
        
        if len(historical_ivs) < 20:  # Need minimum data points
            return None
        
        # Calculate 52-week high and low
        iv_high = historical_ivs.max()
        iv_low = historical_ivs.min()
        
        # IV Rank: (Current - Low) / (High - Low) * 100
        if iv_high != iv_low:
            iv_rank = (current_iv - iv_low) / (iv_high - iv_low) * 100
        else:
            iv_rank = 50.0  # If no variation, assume middle
        
        # IV Percentile: percentage of time current IV is higher than historical
        iv_percentile = (historical_ivs < current_iv).mean() * 100
        
        return IVRankData(
            current_iv=current_iv,
            iv_52w_high=iv_high,
            iv_52w_low=iv_low,
            iv_rank=max(0, min(100, iv_rank)),  # Clamp to 0-100
            iv_percentile=max(0, min(100, iv_percentile))  # Clamp to 0-100
        )
    
    @staticmethod
    def create_iv_surface(option_chain_with_iv: pd.DataFrame) -> pd.DataFrame:
        """
        Create implied volatility surface for visualization
        
        Args:
            option_chain_with_iv: Option chain with IV calculated
            
        Returns:
            DataFrame suitable for 3D surface plotting
        """
        df = option_chain_with_iv.copy()
        
        # Filter valid data
        valid_data = df.dropna(subset=['iv_mid', 'strike', 'time_to_expiry'])
        
        if valid_data.empty:
            return pd.DataFrame()
        
        # Create surface data
        surface_data = []
        
        for _, row in valid_data.iterrows():
            surface_data.append({
                'strike': row['strike'],
                'time_to_expiry': row['time_to_expiry'],
                'expiration': row['expiration'],
                'iv': row['iv_mid'],
                'option_type': row['option_type'],
                'moneyness': row['strike'] / row.get('current_price', row['strike']),
                'log_moneyness': np.log(row['strike'] / row.get('current_price', row['strike']))
            })
        
        return pd.DataFrame(surface_data)
    
    @staticmethod
    def compare_iv_hv(current_iv: float, historical_volatility: float) -> Dict[str, float]:
        """
        Compare implied volatility to historical volatility
        
        Args:
            current_iv: Current implied volatility
            historical_volatility: Historical volatility
            
        Returns:
            Dictionary with comparison metrics
        """
        if pd.isna(current_iv) or pd.isna(historical_volatility):
            return {}
        
        iv_hv_ratio = current_iv / historical_volatility if historical_volatility != 0 else np.nan
        iv_hv_spread = current_iv - historical_volatility
        
        # Determine if options are expensive or cheap
        if iv_hv_ratio > 1.2:
            relative_value = "expensive"
        elif iv_hv_ratio < 0.8:
            relative_value = "cheap"
        else:
            relative_value = "fair"
        
        return {
            'current_iv': current_iv,
            'historical_vol': historical_volatility,
            'iv_hv_ratio': iv_hv_ratio,
            'iv_hv_spread': iv_hv_spread,
            'relative_value': relative_value
        }

# Convenience functions
def calculate_option_iv(market_price: float, spot_price: float, strike: float,
                       time_to_expiry: float, option_type: str, 
                       risk_free_rate: float = 0.05) -> Optional[float]:
    """Quick IV calculation for a single option"""
    return ImpliedVolatilityCalculator.calculate_iv_from_price(
        market_price, spot_price, strike, time_to_expiry, risk_free_rate, option_type
    )

def get_iv_summary(option_chain_with_iv: pd.DataFrame) -> Dict[str, float]:
    """Get summary IV statistics for an option chain"""
    if option_chain_with_iv.empty:
        return {}
    
    valid_ivs = option_chain_with_iv['iv_mid'].dropna()
    
    if valid_ivs.empty:
        return {}
    
    return {
        'iv_mean': valid_ivs.mean(),
        'iv_median': valid_ivs.median(),
        'iv_std': valid_ivs.std(),
        'iv_min': valid_ivs.min(),
        'iv_max': valid_ivs.max(),
        'iv_count': len(valid_ivs)
    }