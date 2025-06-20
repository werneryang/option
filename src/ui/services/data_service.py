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
            # First try database
            symbols = self.db.get_symbols()
            db_symbols = [symbol.symbol for symbol in symbols if symbol.is_active]
            
            # Fall back to storage if database is empty
            if not db_symbols:
                storage_symbols = self.storage.get_symbols_with_data()
                if storage_symbols:
                    logger.info(f"Using storage symbols: {storage_symbols}")
                    return storage_symbols
            
            return db_symbols if db_symbols else ['AAPL', 'SPY', 'TSLA']  # Final fallback
        except Exception as e:
            logger.error(f"Error loading symbols: {e}")
            # Try storage as fallback
            try:
                storage_symbols = self.storage.get_symbols_with_data()
                return storage_symbols if storage_symbols else ['AAPL', 'SPY', 'TSLA']
            except:
                return ['AAPL', 'SPY', 'TSLA']
    
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
    
    def get_historical_option_chains(self, symbol: str, start_date: date, end_date: date) -> Optional[pd.DataFrame]:
        """Get historical option chain data for a date range - key method for analysis"""
        if not symbol:
            return None
        try:
            cache_key = f"historical_chains_{symbol}_{start_date}_{end_date}"
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            result = self.storage.load_historical_option_chains(symbol, start_date, end_date)
            if result is not None:
                self._cache[cache_key] = result
            return result
        except Exception as e:
            logger.error(f"Error loading historical option chains for {symbol}: {e}")
            return None
    
    def get_available_option_dates(self, symbol: str) -> List[date]:
        """Get list of dates with available option chain data"""
        if not symbol:
            return []
        try:
            return self.storage.get_available_dates(symbol)
        except Exception as e:
            logger.error(f"Error getting available dates for {symbol}: {e}")
            return []
    
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
    
    def get_iv_analysis(self, symbol: str, start_date: date, end_date: date, 
                       expiry_days: List[int] = [30, 60, 90]) -> Dict:
        """Analyze implied volatility trends over time"""
        try:
            historical_chains = self.get_historical_option_chains(symbol, start_date, end_date)
            if historical_chains is None or len(historical_chains) == 0:
                return {}
            
            # Group by date and calculate IV metrics
            iv_analysis = {}
            for days in expiry_days:
                # Filter options close to target expiry
                target_expiry_min = days - 7
                target_expiry_max = days + 7
                
                filtered_chains = historical_chains[
                    (historical_chains['days_to_expiry'] >= target_expiry_min) &
                    (historical_chains['days_to_expiry'] <= target_expiry_max)
                ].copy() if 'days_to_expiry' in historical_chains.columns else historical_chains.copy()
                
                if len(filtered_chains) > 0:
                    daily_iv = filtered_chains.groupby('data_date')['implied_volatility'].mean()
                    iv_analysis[f'{days}d_expiry'] = {
                        'dates': daily_iv.index.tolist(),
                        'iv_values': daily_iv.values.tolist(),
                        'avg_iv': daily_iv.mean(),
                        'iv_std': daily_iv.std()
                    }
            
            return iv_analysis
        except Exception as e:
            logger.error(f"Error analyzing IV for {symbol}: {e}")
            return {}
    
    def get_greeks_evolution(self, symbol: str, start_date: date, end_date: date) -> Dict:
        """Track how Greeks evolved over time for historical analysis"""
        try:
            historical_chains = self.get_historical_option_chains(symbol, start_date, end_date)
            if historical_chains is None or len(historical_chains) == 0:
                return {}
            
            # Calculate daily aggregated Greeks
            daily_greeks = historical_chains.groupby('data_date').agg({
                'delta': ['mean', 'sum'],
                'gamma': ['mean', 'sum'], 
                'theta': ['mean', 'sum'],
                'vega': ['mean', 'sum']
            }).round(4) if all(col in historical_chains.columns for col in ['delta', 'gamma', 'theta', 'vega']) else pd.DataFrame()
            
            if len(daily_greeks) > 0:
                return {
                    'dates': daily_greeks.index.tolist(),
                    'delta_avg': daily_greeks[('delta', 'mean')].tolist(),
                    'gamma_avg': daily_greeks[('gamma', 'mean')].tolist(), 
                    'theta_avg': daily_greeks[('theta', 'mean')].tolist(),
                    'vega_avg': daily_greeks[('vega', 'mean')].tolist()
                }
            
            return {}
        except Exception as e:
            logger.error(f"Error analyzing Greeks evolution for {symbol}: {e}")
            return {}
    
    def get_data_summary(self) -> Dict:
        """Get enhanced summary of available data including historical info"""
        try:
            stats = self.storage.get_storage_stats()
            recent_downloads = self.db.get_recent_downloads(days=7)
            
            # Enhanced summary with historical data info
            summary = {
                'total_symbols': stats['total_symbols'],
                'total_files': stats['total_files'],
                'total_size_mb': stats['total_size_mb'],
                'recent_downloads': len(recent_downloads),
                'symbols_with_data': list(stats['symbols'].keys()),
                'historical_coverage': {}
            }
            
            # Add historical coverage info for each symbol
            for symbol, symbol_stats in stats['symbols'].items():
                if 'option_chain_summary' in symbol_stats:
                    oc_summary = symbol_stats['option_chain_summary']
                    summary['historical_coverage'][symbol] = {
                        'option_dates': oc_summary.get('date_count', 0),
                        'date_range': oc_summary.get('date_range'),
                        'total_option_records': oc_summary.get('total_records', 0),
                        'latest_option_date': oc_summary.get('latest_date')
                    }
            
            return summary
        except Exception as e:
            logger.error(f"Error getting data summary: {e}")
            return {
                'total_symbols': 0,
                'total_files': 0,
                'total_size_mb': 0,
                'recent_downloads': 0,
                'symbols_with_data': [],
                'historical_coverage': {}
            }
    
    def clear_cache(self):
        """Clear internal cache"""
        self._cache.clear()
        logger.info("Data service cache cleared")