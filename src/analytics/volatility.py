import pandas as pd
import numpy as np
from typing import List, Dict, Union, Optional
from datetime import date, datetime, timedelta
from dataclasses import dataclass

@dataclass
class VolatilityResult:
    """Result of volatility calculation"""
    symbol: str
    period_days: int
    volatility: float  # Annualized volatility
    start_date: date
    end_date: date
    observations: int

class HistoricalVolatilityCalculator:
    """
    Calculate historical volatility using various methods and lookback periods
    """
    
    @staticmethod
    def calculate_returns(prices: pd.Series) -> pd.Series:
        """Calculate log returns from price series"""
        return np.log(prices / prices.shift(1)).dropna()
    
    @staticmethod
    def simple_volatility(price_data: pd.DataFrame, period_days: int = 30, 
                         price_column: str = 'close') -> Optional[VolatilityResult]:
        """
        Calculate simple historical volatility using log returns
        
        Args:
            price_data: DataFrame with price data
            period_days: Number of trading days to look back
            price_column: Column name for prices
            
        Returns:
            VolatilityResult object or None
        """
        if len(price_data) < period_days + 1:
            return None
        
        # Sort by date and take the most recent period_days
        df = price_data.sort_values('date').tail(period_days + 1)
        prices = df[price_column]
        
        # Calculate log returns
        returns = HistoricalVolatilityCalculator.calculate_returns(prices)
        
        if len(returns) < 2:
            return None
        
        # Calculate volatility (annualized)
        daily_vol = returns.std()
        annual_vol = daily_vol * np.sqrt(252)  # 252 trading days per year
        
        return VolatilityResult(
            symbol=df['symbol'].iloc[0] if 'symbol' in df.columns else 'Unknown',
            period_days=period_days,
            volatility=annual_vol,
            start_date=df['date'].iloc[0],
            end_date=df['date'].iloc[-1],
            observations=len(returns)
        )
    
    @staticmethod
    def garch_volatility(price_data: pd.DataFrame, period_days: int = 30,
                        price_column: str = 'close') -> Optional[VolatilityResult]:
        """
        Calculate GARCH-like weighted volatility (exponential weighting)
        
        Args:
            price_data: DataFrame with price data
            period_days: Number of trading days to look back
            price_column: Column name for prices
            
        Returns:
            VolatilityResult object or None
        """
        if len(price_data) < period_days + 1:
            return None
        
        # Sort by date and take the most recent period_days
        df = price_data.sort_values('date').tail(period_days + 1)
        prices = df[price_column]
        
        # Calculate log returns
        returns = HistoricalVolatilityCalculator.calculate_returns(prices)
        
        if len(returns) < 2:
            return None
        
        # Exponential weighting (lambda = 0.94, commonly used)
        lambda_param = 0.94
        weights = np.array([lambda_param**(i) for i in range(len(returns)-1, -1, -1)])
        weights = weights / weights.sum()
        
        # Weighted variance
        weighted_mean = np.sum(weights * returns)
        weighted_variance = np.sum(weights * (returns - weighted_mean)**2)
        
        # Annualized volatility
        annual_vol = np.sqrt(weighted_variance * 252)
        
        return VolatilityResult(
            symbol=df['symbol'].iloc[0] if 'symbol' in df.columns else 'Unknown',
            period_days=period_days,
            volatility=annual_vol,
            start_date=df['date'].iloc[0],
            end_date=df['date'].iloc[-1],
            observations=len(returns)
        )
    
    @staticmethod
    def parkinson_volatility(price_data: pd.DataFrame, period_days: int = 30) -> Optional[VolatilityResult]:
        """
        Calculate Parkinson volatility using high-low estimator
        More efficient than close-to-close for intraday volatility
        
        Args:
            price_data: DataFrame with OHLC data
            period_days: Number of trading days to look back
            
        Returns:
            VolatilityResult object or None
        """
        required_cols = ['high', 'low']
        if not all(col in price_data.columns for col in required_cols):
            return None
        
        if len(price_data) < period_days:
            return None
        
        # Sort by date and take the most recent period_days
        df = price_data.sort_values('date').tail(period_days)
        
        # Parkinson estimator: (1/(4*ln(2))) * ln(High/Low)^2
        hl_ratios = np.log(df['high'] / df['low'])**2
        parkinson_var = (1 / (4 * np.log(2))) * hl_ratios.mean()
        
        # Annualized volatility
        annual_vol = np.sqrt(parkinson_var * 252)
        
        return VolatilityResult(
            symbol=df['symbol'].iloc[0] if 'symbol' in df.columns else 'Unknown',
            period_days=period_days,
            volatility=annual_vol,
            start_date=df['date'].iloc[0],
            end_date=df['date'].iloc[-1],
            observations=len(df)
        )
    
    @staticmethod
    def garman_klass_volatility(price_data: pd.DataFrame, period_days: int = 30) -> Optional[VolatilityResult]:
        """
        Calculate Garman-Klass volatility estimator
        Uses OHLC data for more accurate volatility estimation
        
        Args:
            price_data: DataFrame with OHLC data
            period_days: Number of trading days to look back
            
        Returns:
            VolatilityResult object or None
        """
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in price_data.columns for col in required_cols):
            return None
        
        if len(price_data) < period_days:
            return None
        
        # Sort by date and take the most recent period_days
        df = price_data.sort_values('date').tail(period_days)
        
        # Garman-Klass estimator
        hl_term = 0.5 * (np.log(df['high'] / df['low']))**2
        oc_term = (2 * np.log(2) - 1) * (np.log(df['close'] / df['open']))**2
        
        gk_variance = (hl_term - oc_term).mean()
        
        # Annualized volatility
        annual_vol = np.sqrt(gk_variance * 252)
        
        return VolatilityResult(
            symbol=df['symbol'].iloc[0] if 'symbol' in df.columns else 'Unknown',
            period_days=period_days,
            volatility=annual_vol,
            start_date=df['date'].iloc[0],
            end_date=df['date'].iloc[-1],
            observations=len(df)
        )
    
    @staticmethod
    def multi_period_volatility(price_data: pd.DataFrame, 
                               periods: List[int] = [10, 20, 30, 60, 90, 252],
                               method: str = 'simple') -> Dict[int, VolatilityResult]:
        """
        Calculate volatility for multiple lookback periods
        
        Args:
            price_data: DataFrame with price data
            periods: List of periods (in trading days) to calculate
            method: 'simple', 'garch', 'parkinson', or 'garman_klass'
            
        Returns:
            Dictionary mapping period to VolatilityResult
        """
        results = {}
        
        for period in periods:
            if method == 'simple':
                result = HistoricalVolatilityCalculator.simple_volatility(price_data, period)
            elif method == 'garch':
                result = HistoricalVolatilityCalculator.garch_volatility(price_data, period)
            elif method == 'parkinson':
                result = HistoricalVolatilityCalculator.parkinson_volatility(price_data, period)
            elif method == 'garman_klass':
                result = HistoricalVolatilityCalculator.garman_klass_volatility(price_data, period)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            if result:
                results[period] = result
        
        return results
    
    @staticmethod
    def volatility_percentile(current_vol: float, price_data: pd.DataFrame,
                             lookback_days: int = 252, window_days: int = 30) -> Optional[float]:
        """
        Calculate volatility percentile (IV Rank equivalent for HV)
        
        Args:
            current_vol: Current volatility to rank
            price_data: Historical price data
            lookback_days: How far back to look for percentile calculation
            window_days: Rolling window for volatility calculation
            
        Returns:
            Percentile (0-100) where current volatility ranks
        """
        if len(price_data) < lookback_days + window_days:
            return None
        
        # Calculate rolling volatility
        df = price_data.sort_values('date').tail(lookback_days + window_days)
        rolling_vols = []
        
        for i in range(window_days, len(df)):
            subset = df.iloc[i-window_days:i]
            vol_result = HistoricalVolatilityCalculator.simple_volatility(subset, window_days)
            if vol_result:
                rolling_vols.append(vol_result.volatility)
        
        if not rolling_vols:
            return None
        
        # Calculate percentile
        rolling_vols = np.array(rolling_vols)
        percentile = (rolling_vols < current_vol).mean() * 100
        
        return percentile
    
    @staticmethod
    def volatility_surface_data(price_data: pd.DataFrame, 
                               periods: List[int] = [10, 20, 30, 60, 90, 180, 252]) -> pd.DataFrame:
        """
        Generate volatility surface data for visualization
        
        Args:
            price_data: DataFrame with price data
            periods: List of periods to calculate
            
        Returns:
            DataFrame with volatility surface data
        """
        surface_data = []
        
        # Calculate for different methods
        methods = ['simple', 'garch', 'parkinson', 'garman_klass']
        
        for method in methods:
            try:
                results = HistoricalVolatilityCalculator.multi_period_volatility(
                    price_data, periods, method
                )
                
                for period, result in results.items():
                    surface_data.append({
                        'method': method,
                        'period_days': period,
                        'volatility': result.volatility,
                        'annualized_vol_pct': result.volatility * 100,
                        'start_date': result.start_date,
                        'end_date': result.end_date,
                        'observations': result.observations
                    })
            except Exception:
                # Skip methods that fail (e.g., missing OHLC data)
                continue
        
        return pd.DataFrame(surface_data)

# Convenience functions
def calculate_historical_volatility(price_data: pd.DataFrame, period_days: int = 30) -> Optional[float]:
    """Quick historical volatility calculation - returns just the volatility value"""
    result = HistoricalVolatilityCalculator.simple_volatility(price_data, period_days)
    return result.volatility if result else None

def get_volatility_metrics(price_data: pd.DataFrame) -> Dict[str, float]:
    """Get common volatility metrics for a symbol"""
    metrics = {}
    
    # Standard periods
    periods = [10, 20, 30, 60, 90, 252]
    
    for period in periods:
        result = HistoricalVolatilityCalculator.simple_volatility(price_data, period)
        if result:
            metrics[f'hv_{period}d'] = result.volatility
    
    # Current volatility percentiles
    if 'hv_30d' in metrics:
        percentile = HistoricalVolatilityCalculator.volatility_percentile(
            metrics['hv_30d'], price_data, 252, 30
        )
        if percentile is not None:
            metrics['hv_percentile'] = percentile
    
    return metrics