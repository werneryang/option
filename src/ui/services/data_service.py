"""
Data Service Layer

Provides a clean interface between the UI components and the backend
analytics engine, handling data loading, caching, and transformation
for optimal UI performance.
"""

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path

from src.data_sources.storage import ParquetStorage
from src.data_sources.database import DatabaseManager
from src.analytics.black_scholes import BlackScholesCalculator
from src.analytics.strategies import OptionsStrategyBuilder, StrategyPnLCalculator
from src.analytics.implied_volatility import ImpliedVolatilityCalculator
from src.analytics.volatility import HistoricalVolatilityCalculator
from src.analytics.backtesting import StrategyBacktester
from src.utils.config import config

logger = logging.getLogger(__name__)

class DataService:
    """Service layer for UI data operations"""
    
    def __init__(self):
        self.storage = ParquetStorage()
        self.db = DatabaseManager()
        self.iv_calc = ImpliedVolatilityCalculator()
        self.vol_calc = HistoricalVolatilityCalculator()
        self.backtester = None  # Will be initialized when needed with price data
        
        # Cache for expensive calculations
        self._cache = {}
    
    def get_available_symbols(self) -> List[str]:
        """Get list of symbols with available data"""
        try:
            symbols = self.db.get_symbols()
            return [symbol.symbol for symbol in symbols if symbol.is_active]
        except Exception as e:
            logger.error(f"Error loading symbols: {e}")
            return ['AAPL', 'SPY', 'TSLA']  # Fallback
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """Get detailed information about a symbol"""
        if not symbol:
            return {
                'symbol': 'Unknown',
                'name': 'Unknown',
                'sector': 'Unknown',
                'market_cap': None,
                'is_active': True
            }
        try:
            symbol_obj = self.db.get_symbol(symbol)
            if symbol_obj:
                return {
                    'symbol': symbol_obj.symbol,
                    'name': symbol_obj.name,
                    'sector': symbol_obj.sector,
                    'market_cap': symbol_obj.market_cap,
                    'is_active': symbol_obj.is_active
                }
        except Exception as e:
            logger.error(f"Error loading symbol info for {symbol}: {e}")
        
        return {
            'symbol': symbol,
            'name': f'{symbol} Inc.',
            'sector': 'Unknown',
            'market_cap': None,
            'is_active': True
        }
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get the most recent price for a symbol"""
        if not symbol:
            return None
        try:
            price_history = self.storage.load_price_history(symbol)
            if price_history is not None and len(price_history) > 0:
                return float(price_history.iloc[-1]['close'])
        except Exception as e:
            logger.error(f"Error loading current price for {symbol}: {e}")
        return None
    
    def get_price_history(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        """Get price history for a symbol"""
        if not symbol:
            return None
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            return self.storage.load_price_history(symbol, start_date, end_date)
        except Exception as e:
            logger.error(f"Error loading price history for {symbol}: {e}")
            return None
    
    def get_option_chain(self, symbol: str, target_date: Optional[date] = None) -> Optional[pd.DataFrame]:
        """Get option chain data for a symbol"""
        if not symbol:
            return None
        try:
            if target_date is None:
                # Get most recent date with data
                available_dates = self.storage.get_available_dates(symbol)
                if not available_dates:
                    return None
                target_date = max(available_dates)
            
            return self.storage.load_option_chain(symbol, target_date)
        except Exception as e:
            logger.error(f"Error loading option chain for {symbol}: {e}")
            return None
    
    def calculate_greeks(self, symbol: str, option_data: pd.DataFrame,
                        current_price: float, risk_free_rate: float = 0.05) -> pd.DataFrame:
        """Calculate Greeks for option chain"""
        try:
            cache_key = f"greeks_{symbol}_{hash(str(option_data.values.tobytes()))}"
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            results = []
            for _, row in option_data.iterrows():
                time_to_expiry = (row['expiration'] - date.today()).days / 365.0
                if time_to_expiry <= 0:
                    continue
                
                volatility = 0.25  # Default volatility, should be calculated from IV
                
                greeks = {
                    'strike': row['strike'],
                    'option_type': row['option_type'],
                    'delta': BlackScholesCalculator.delta(
                        current_price, row['strike'], time_to_expiry,
                        risk_free_rate, volatility, row['option_type'].lower()
                    ),
                    'gamma': BlackScholesCalculator.gamma(
                        current_price, row['strike'], time_to_expiry,
                        risk_free_rate, volatility
                    ),
                    'theta': BlackScholesCalculator.theta(
                        current_price, row['strike'], time_to_expiry,
                        risk_free_rate, volatility, row['option_type'].lower()
                    ),
                    'vega': BlackScholesCalculator.vega(
                        current_price, row['strike'], time_to_expiry,
                        risk_free_rate, volatility
                    ),
                    'rho': BlackScholesCalculator.rho(
                        current_price, row['strike'], time_to_expiry,
                        risk_free_rate, volatility, row['option_type'].lower()
                    )
                }
                results.append(greeks)
            
            result_df = pd.DataFrame(results)
            self._cache[cache_key] = result_df
            return result_df
            
        except Exception as e:
            logger.error(f"Error calculating Greeks for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_volatility_analysis(self, symbol: str, periods: List[int] = [30, 60, 90]) -> Dict:
        """Get historical volatility analysis"""
        try:
            price_history = self.get_price_history(symbol, max(periods) + 10)
            if price_history is None or len(price_history) < max(periods):
                return {}
            
            results = {}
            for period in periods:
                vol = self.vol_calc.calculate_historical_volatility(
                    price_history.tail(period), period_days=period
                )
                results[f'{period}d'] = vol
            
            return results
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return {}
    
    def build_strategy(self, strategy_type: str, parameters: Dict) -> Optional[object]:
        """Build an options strategy"""
        try:
            if strategy_type == "long_call":
                return OptionsStrategyBuilder.long_call(
                    parameters['strike'], parameters['expiration'],
                    parameters.get('premium')
                )
            elif strategy_type == "straddle":
                return OptionsStrategyBuilder.straddle(
                    parameters['strike'], parameters['expiration']
                )
            elif strategy_type == "strangle":
                return OptionsStrategyBuilder.strangle(
                    parameters['call_strike'], parameters['put_strike'],
                    parameters['expiration']
                )
            # Add more strategy types as needed
            
        except Exception as e:
            logger.error(f"Error building strategy {strategy_type}: {e}")
            return None
    
    def calculate_strategy_pnl(self, strategy: object, current_price: float,
                              price_range: Tuple[float, float] = None,
                              time_to_expiry: float = 0.0) -> Optional[object]:
        """Calculate P&L for a strategy"""
        try:
            if price_range is None:
                price_range = (current_price * 0.7, current_price * 1.3)
            
            price_points = np.linspace(price_range[0], price_range[1], 100)
            
            return StrategyPnLCalculator.calculate_strategy_pnl(
                strategy, price_points, current_price,
                time_to_expiry, volatility=0.25
            )
        except Exception as e:
            logger.error(f"Error calculating strategy P&L: {e}")
            return None
    
    def get_data_summary(self) -> Dict:
        """Get summary of available data"""
        try:
            stats = self.storage.get_storage_stats()
            recent_downloads = self.db.get_recent_downloads(days=7)
            
            return {
                'total_symbols': stats['total_symbols'],
                'total_files': stats['total_files'],
                'total_size_mb': stats['total_size_mb'],
                'recent_downloads': len(recent_downloads),
                'symbols_with_data': list(stats['symbols'].keys())
            }
        except Exception as e:
            logger.error(f"Error getting data summary: {e}")
            return {
                'total_symbols': 0,
                'total_files': 0,
                'total_size_mb': 0,
                'recent_downloads': 0,
                'symbols_with_data': []
            }
    
    def clear_cache(self):
        """Clear internal cache"""
        self._cache.clear()
        logger.info("Data service cache cleared")