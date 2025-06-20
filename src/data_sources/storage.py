import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from loguru import logger

from ..utils.config import config

class ParquetStorage:
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or config.processed_data_path
        self.compression = config.parquet_compression
        
        config.ensure_directories()
    
    def _get_options_path(self, symbol: str, date_str: str) -> Path:
        return self.base_path / symbol / date_str / "options.parquet"
    
    def _get_prices_path(self, symbol: str) -> Path:
        return self.base_path / symbol / "prices.parquet"
    
    def _get_cache_path(self, symbol: str, analysis_type: str) -> Path:
        cache_path = config.cache_data_path / symbol / analysis_type
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path / "results.parquet"
    
    def save_option_chain(self, symbol: str, date_obj: date, df: pd.DataFrame) -> Path:
        """Save option chain for a specific date - supports historical time series"""
        date_str = date_obj.strftime("%Y-%m-%d")
        file_path = self._get_options_path(symbol, date_str)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Add timestamp to track when data was collected
            if 'collected_at' not in df.columns:
                df['collected_at'] = datetime.now()
            
            df.to_parquet(
                file_path,
                compression=self.compression,
                index=False
            )
            logger.info(f"Saved option chain for {symbol} on {date_str}: {len(df)} records")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save option chain for {symbol} on {date_str}: {e}")
            raise
    
    def load_option_chain(self, symbol: str, date_obj: date) -> Optional[pd.DataFrame]:
        date_str = date_obj.strftime("%Y-%m-%d")
        file_path = self._get_options_path(symbol, date_str)
        
        if not file_path.exists():
            logger.warning(f"Option chain file not found: {file_path}")
            return None
        
        try:
            df = pd.read_parquet(file_path)
            logger.info(f"Loaded option chain for {symbol} on {date_str}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Failed to load option chain for {symbol} on {date_str}: {e}")
            return None
    
    def save_price_history(self, symbol: str, df: pd.DataFrame) -> Path:
        file_path = self._get_prices_path(symbol)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            existing_df = self.load_price_history(symbol)
            if existing_df is not None:
                combined_df = pd.concat([existing_df, df]).drop_duplicates(
                    subset=['date'], keep='last'
                ).sort_values('date')
            else:
                combined_df = df.sort_values('date')
            
            combined_df.to_parquet(
                file_path,
                compression=self.compression,
                index=False
            )
            logger.info(f"Saved price history for {symbol}: {len(combined_df)} records")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save price history for {symbol}: {e}")
            raise
    
    def load_price_history(self, symbol: str, start_date: Optional[date] = None, 
                          end_date: Optional[date] = None) -> Optional[pd.DataFrame]:
        file_path = self._get_prices_path(symbol)
        
        if not file_path.exists():
            logger.warning(f"Price history file not found: {file_path}")
            return None
        
        try:
            df = pd.read_parquet(file_path)
            
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.date
                
                if start_date:
                    df = df[df['date'] >= start_date]
                if end_date:
                    df = df[df['date'] <= end_date]
            
            logger.info(f"Loaded price history for {symbol}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Failed to load price history for {symbol}: {e}")
            return None
    
    def save_analytics_cache(self, symbol: str, analysis_type: str, df: pd.DataFrame) -> Path:
        file_path = self._get_cache_path(symbol, analysis_type)
        
        try:
            df.to_parquet(
                file_path,
                compression=self.compression,
                index=False
            )
            logger.info(f"Cached {analysis_type} analytics for {symbol}: {len(df)} records")
            return file_path
        except Exception as e:
            logger.error(f"Failed to cache {analysis_type} analytics for {symbol}: {e}")
            raise
    
    def load_analytics_cache(self, symbol: str, analysis_type: str, 
                           max_age_hours: Optional[int] = None) -> Optional[pd.DataFrame]:
        file_path = self._get_cache_path(symbol, analysis_type)
        
        if not file_path.exists():
            return None
        
        if max_age_hours is not None:
            file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_age.total_seconds() > max_age_hours * 3600:
                logger.info(f"Cache expired for {analysis_type} analytics for {symbol}")
                return None
        
        try:
            df = pd.read_parquet(file_path)
            logger.info(f"Loaded cached {analysis_type} analytics for {symbol}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Failed to load cached {analysis_type} analytics for {symbol}: {e}")
            return None
    
    def get_available_dates(self, symbol: str) -> List[date]:
        symbol_path = self.base_path / symbol
        if not symbol_path.exists():
            return []
        
        dates = []
        for date_dir in symbol_path.iterdir():
            if date_dir.is_dir() and (date_dir / "options.parquet").exists():
                try:
                    date_obj = datetime.strptime(date_dir.name, "%Y-%m-%d").date()
                    dates.append(date_obj)
                except ValueError:
                    continue
        
        return sorted(dates)
    
    def get_symbols_with_data(self) -> List[str]:
        if not self.base_path.exists():
            return []
        
        symbols = []
        for symbol_dir in self.base_path.iterdir():
            if symbol_dir.is_dir() and any(symbol_dir.rglob("*.parquet")):
                symbols.append(symbol_dir.name)
        
        return sorted(symbols)
    
    def load_historical_option_chains(self, symbol: str, start_date: date, end_date: date) -> Optional[pd.DataFrame]:
        """Load option chains for a date range - key method for historical analysis"""
        try:
            available_dates = self.get_available_dates(symbol)
            target_dates = [d for d in available_dates if start_date <= d <= end_date]
            
            if not target_dates:
                logger.warning(f"No option chain data found for {symbol} between {start_date} and {end_date}")
                return None
            
            combined_dfs = []
            for target_date in target_dates:
                df = self.load_option_chain(symbol, target_date)
                if df is not None:
                    df['data_date'] = target_date
                    combined_dfs.append(df)
            
            if combined_dfs:
                result = pd.concat(combined_dfs, ignore_index=True)
                logger.info(f"Loaded historical option chains for {symbol}: {len(result)} records across {len(target_dates)} dates")
                return result
            
            return None
        except Exception as e:
            logger.error(f"Failed to load historical option chains for {symbol}: {e}")
            return None
    
    def get_option_chain_summary(self, symbol: str) -> Dict[str, Any]:
        """Get summary statistics for option chain data"""
        try:
            available_dates = self.get_available_dates(symbol)
            if not available_dates:
                return {"symbol": symbol, "date_count": 0, "date_range": None, "total_records": 0}
            
            total_records = 0
            for date_obj in available_dates:
                df = self.load_option_chain(symbol, date_obj)
                if df is not None:
                    total_records += len(df)
            
            return {
                "symbol": symbol,
                "date_count": len(available_dates),
                "date_range": (min(available_dates), max(available_dates)),
                "total_records": total_records,
                "latest_date": max(available_dates) if available_dates else None
            }
        except Exception as e:
            logger.error(f"Failed to get option chain summary for {symbol}: {e}")
            return {"symbol": symbol, "date_count": 0, "date_range": None, "total_records": 0}
    
    def get_storage_stats(self) -> Dict[str, Any]:
        stats = {
            "total_symbols": 0,
            "total_files": 0,
            "total_size_mb": 0,
            "symbols": {}
        }
        
        if not self.base_path.exists():
            return stats
        
        for symbol_dir in self.base_path.iterdir():
            if symbol_dir.is_dir():
                symbol = symbol_dir.name
                symbol_stats = {
                    "files": 0,
                    "size_mb": 0,
                    "available_dates": [],
                    "option_chain_summary": {}
                }
                
                for file_path in symbol_dir.rglob("*.parquet"):
                    symbol_stats["files"] += 1
                    symbol_stats["size_mb"] += file_path.stat().st_size / (1024 * 1024)
                
                symbol_stats["available_dates"] = self.get_available_dates(symbol)
                symbol_stats["option_chain_summary"] = self.get_option_chain_summary(symbol)
                
                if symbol_stats["files"] > 0:
                    stats["symbols"][symbol] = symbol_stats
                    stats["total_symbols"] += 1
                    stats["total_files"] += symbol_stats["files"]
                    stats["total_size_mb"] += symbol_stats["size_mb"]
        
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return stats

storage = ParquetStorage()