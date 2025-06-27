import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import fcntl
import time
import os
from loguru import logger

from ..utils.config import config

class FileLock:
    """Cross-platform file locking context manager"""
    
    def __init__(self, file_path: Path, timeout: int = 30):
        self.file_path = file_path
        self.timeout = timeout
        self.lock_file_path = file_path.with_suffix(f"{file_path.suffix}.lock")
        self.lock_file = None
    
    def __enter__(self):
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            try:
                # Create lock file
                self.lock_file = open(self.lock_file_path, 'w')
                
                # Try to acquire exclusive lock
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                logger.debug(f"Acquired file lock: {self.lock_file_path}")
                return self
                
            except (IOError, OSError):
                # Lock not available, close file and retry
                if self.lock_file:
                    self.lock_file.close()
                    self.lock_file = None
                
                time.sleep(0.1)  # Wait 100ms before retrying
        
        raise TimeoutError(f"Could not acquire file lock for {self.file_path} within {self.timeout} seconds")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                
                # Clean up lock file
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()
                
                logger.debug(f"Released file lock: {self.lock_file_path}")
                
            except Exception as e:
                logger.warning(f"Error releasing file lock {self.lock_file_path}: {e}")
            
            finally:
                self.lock_file = None


class ParquetStorage:
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or config.processed_data_path
        self.compression = config.parquet_compression
        
        config.ensure_directories()
    
    # Legacy processed data paths (maintained for compatibility)
    def _get_options_path(self, symbol: str, date_str: str) -> Path:
        return self.base_path / symbol / date_str / "options.parquet"
    
    def _get_prices_path(self, symbol: str) -> Path:
        return self.base_path / symbol / "prices.parquet"
    
    # New snapshot data paths
    def _get_snapshots_path(self, symbol: str, date_str: str) -> Path:
        return config.snapshots_data_path / symbol / date_str / "snapshots.parquet"
    
    # Historical archive data paths  
    def _get_historical_path(self, symbol: str) -> Path:
        return config.historical_data_path / symbol / "historical_options.parquet"
    
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
        
        # Use file locking to prevent concurrent write conflicts
        with FileLock(file_path, timeout=30):
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

    # === NEW METHODS FOR DUAL WORKFLOW ===
    
    def save_snapshot(self, symbol: str, timestamp: datetime, df: pd.DataFrame) -> Path:
        """Save real-time option snapshot - appends to daily cumulative file with file locking"""
        date_str = timestamp.strftime("%Y-%m-%d")
        file_path = self._get_snapshots_path(symbol, date_str)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use file locking to prevent concurrent write conflicts
        with FileLock(file_path, timeout=30):
            try:
                # Add snapshot timestamp if not present
                if 'snapshot_time' not in df.columns:
                    df['snapshot_time'] = timestamp
                if 'collected_at' not in df.columns:
                    df['collected_at'] = datetime.now()
                
                # Append to existing file or create new one
                if file_path.exists():
                    existing_df = pd.read_parquet(file_path)
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                    # Remove duplicates based on symbol, snapshot_time, strike, option_type
                    combined_df = combined_df.drop_duplicates(
                        subset=['symbol', 'snapshot_time', 'strike', 'option_type'], 
                        keep='last'
                    ).sort_values(['snapshot_time', 'strike', 'option_type'])
                else:
                    combined_df = df.sort_values(['snapshot_time', 'strike', 'option_type'])
                
                combined_df.to_parquet(
                    file_path,
                    compression=self.compression,
                    index=False
                )
                logger.info(f"Saved snapshot for {symbol} at {timestamp}: {len(df)} new records, {len(combined_df)} total")
                return file_path
            except Exception as e:
                logger.error(f"Failed to save snapshot for {symbol} at {timestamp}: {e}")
                raise
    
    def load_snapshots(self, symbol: str, date_obj: date, 
                      start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """Load snapshots for a specific date with optional time filtering"""
        date_str = date_obj.strftime("%Y-%m-%d")
        file_path = self._get_snapshots_path(symbol, date_str)
        
        if not file_path.exists():
            logger.warning(f"Snapshot file not found: {file_path}")
            return None
        
        try:
            df = pd.read_parquet(file_path)
            
            # Convert snapshot_time to datetime if needed
            if 'snapshot_time' in df.columns:
                df['snapshot_time'] = pd.to_datetime(df['snapshot_time'])
                
                # Apply time filtering if specified
                if start_time:
                    df = df[df['snapshot_time'] >= start_time]
                if end_time:
                    df = df[df['snapshot_time'] <= end_time]
            
            logger.info(f"Loaded snapshots for {symbol} on {date_str}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Failed to load snapshots for {symbol} on {date_str}: {e}")
            return None
    
    def save_historical_archive(self, symbol: str, df: pd.DataFrame) -> Path:
        """Save consolidated historical archive - replaces existing archive with file locking"""
        file_path = self._get_historical_path(symbol)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use file locking to prevent read corruption during write
        with FileLock(file_path, timeout=30):
            try:
                # Add archive timestamp
                if 'archive_date' not in df.columns:
                    df['archive_date'] = datetime.now()
                
                # Sort by date and contract details for efficient querying
                df = df.sort_values(['date', 'expiration', 'strike', 'option_type'])
                
                df.to_parquet(
                    file_path,
                    compression=self.compression,
                    index=False
                )
                logger.info(f"Saved historical archive for {symbol}: {len(df)} records")
                return file_path
            except Exception as e:
                logger.error(f"Failed to save historical archive for {symbol}: {e}")
                raise
    
    def load_historical_archive(self, symbol: str, 
                               start_date: Optional[date] = None, 
                               end_date: Optional[date] = None) -> Optional[pd.DataFrame]:
        """Load historical archive with optional date filtering"""
        file_path = self._get_historical_path(symbol)
        
        if not file_path.exists():
            logger.warning(f"Historical archive not found: {file_path}")
            return None
        
        try:
            df = pd.read_parquet(file_path)
            
            # Convert date column if needed
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.date
                
                # Apply date filtering if specified
                if start_date:
                    df = df[df['date'] >= start_date]
                if end_date:
                    df = df[df['date'] <= end_date]
            
            logger.info(f"Loaded historical archive for {symbol}: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Failed to load historical archive for {symbol}: {e}")
            return None
    
    def get_available_snapshot_dates(self, symbol: str) -> List[date]:
        """Get list of dates with available snapshot data"""
        symbol_path = config.snapshots_data_path / symbol
        if not symbol_path.exists():
            return []
        
        dates = []
        for date_dir in symbol_path.iterdir():
            if date_dir.is_dir() and (date_dir / "snapshots.parquet").exists():
                try:
                    date_obj = datetime.strptime(date_dir.name, "%Y-%m-%d").date()
                    dates.append(date_obj)
                except ValueError:
                    continue
        
        return sorted(dates)
    
    def get_last_archive_date(self, symbol: str) -> Optional[date]:
        """Get the latest date in the historical archive"""
        archive_df = self.load_historical_archive(symbol)
        if archive_df is not None and len(archive_df) > 0 and 'date' in archive_df.columns:
            return max(archive_df['date'])
        return None
    
    def cleanup_old_snapshots(self, days_to_keep: int = None) -> Dict[str, int]:
        """Clean up snapshot files older than specified days"""
        days_to_keep = days_to_keep or config.snapshot_retention_days
        cutoff_date = date.today() - timedelta(days=days_to_keep)
        
        cleanup_stats = {"files_deleted": 0, "symbols_processed": 0}
        
        snapshots_path = config.snapshots_data_path
        if not snapshots_path.exists():
            return cleanup_stats
        
        for symbol_dir in snapshots_path.iterdir():
            if symbol_dir.is_dir():
                cleanup_stats["symbols_processed"] += 1
                for date_dir in symbol_dir.iterdir():
                    if date_dir.is_dir():
                        try:
                            dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d").date()
                            if dir_date < cutoff_date:
                                snapshot_file = date_dir / "snapshots.parquet"
                                if snapshot_file.exists():
                                    snapshot_file.unlink()
                                    cleanup_stats["files_deleted"] += 1
                                    logger.info(f"Deleted old snapshot: {snapshot_file}")
                                # Remove empty directory
                                try:
                                    date_dir.rmdir()
                                except OSError:
                                    pass  # Directory not empty
                        except ValueError:
                            continue
        
        logger.info(f"Snapshot cleanup completed: {cleanup_stats}")
        return cleanup_stats

storage = ParquetStorage()