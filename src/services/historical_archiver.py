"""
Historical Options Data Archiver

Downloads historical option data from last archive date to current date - 1 day
and consolidates it into single archive files for long-term analysis.
"""

import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
import pandas as pd
from loguru import logger

from ..data_sources.ib_client import IBClient
from ..data_sources.storage import storage
from ..data_sources.database import db_manager
from ..utils.config import config
from ..utils.trading_calendar import trading_calendar


class HistoricalArchiver:
    """Service for downloading and archiving historical option data"""
    
    def __init__(self):
        self.ib_client = None
        
    async def _connect_to_ib(self) -> bool:
        """Connect to Interactive Brokers TWS"""
        try:
            if self.ib_client is None:
                # Use unique client ID for archiver
                self.ib_client = IBClient(client_id=3)
            
            if not self.ib_client.connected:
                connected = await self.ib_client.connect()
                if connected:
                    logger.info("Historical archiver connected to IB TWS")
                    return True
                else:
                    logger.error("Failed to connect historical archiver to IB TWS")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error connecting historical archiver to IB TWS: {e}")
            return False
    
    def _calculate_archive_date_range(self, symbol: str) -> tuple[date, date]:
        """Calculate the date range for archival"""
        try:
            # Get last archive date
            last_archive_date = storage.get_last_archive_date(symbol)
            
            # End date is yesterday (current date - 1)
            end_date = date.today() - timedelta(days=1)
            
            if last_archive_date is None:
                # First time archival - go back configured number of days
                start_date = end_date - timedelta(days=config.max_archive_days_per_request)
            else:
                # Continue from last archive date + 1
                start_date = last_archive_date + timedelta(days=1)
                
                # Limit the range to prevent too large downloads
                max_end_date = start_date + timedelta(days=config.max_archive_days_per_request)
                if end_date > max_end_date:
                    end_date = max_end_date
            
            # Ensure start date is not after end date
            if start_date > end_date:
                logger.warning(f"Archive for {symbol} is up to date. Last: {last_archive_date}, Current: {date.today()}")
                return None, None
            
            logger.info(f"Archive date range for {symbol}: {start_date} to {end_date}")
            return start_date, end_date
            
        except Exception as e:
            logger.error(f"Error calculating archive date range for {symbol}: {e}")
            return None, None
    
    async def _download_historical_data(self, symbol: str, start_date: date, end_date: date) -> Optional[pd.DataFrame]:
        """Download historical option data for date range"""
        try:
            if not await self._connect_to_ib():
                return None
            
            logger.info(f"Downloading historical data for {symbol} from {start_date} to {end_date}")
            
            # Use the existing historical data download method
            historical_data = await self.ib_client.get_historical_option_data(
                symbol=symbol,
                duration=f"{(end_date - start_date).days + 1} D",
                bar_size="1 day"
            )
            
            if historical_data is not None and len(historical_data) > 0:
                # Filter data to the requested date range
                historical_data['date'] = pd.to_datetime(historical_data['date']).dt.date
                filtered_data = historical_data[
                    (historical_data['date'] >= start_date) &
                    (historical_data['date'] <= end_date)
                ].copy()
                
                logger.info(f"Downloaded {len(filtered_data)} historical records for {symbol}")
                return filtered_data
            else:
                logger.warning(f"No historical data downloaded for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading historical data for {symbol}: {e}")
            return None
    
    def _merge_with_existing_archive(self, symbol: str, new_data: pd.DataFrame) -> pd.DataFrame:
        """Merge new data with existing archive"""
        try:
            # Load existing archive
            existing_archive = storage.load_historical_archive(symbol)
            
            if existing_archive is None or len(existing_archive) == 0:
                logger.info(f"No existing archive for {symbol}, creating new archive")
                return new_data
            
            # Combine and deduplicate
            combined_data = pd.concat([existing_archive, new_data], ignore_index=True)
            
            # Remove duplicates based on date, strike, option_type, expiration
            dedup_columns = ['date', 'strike', 'option_type', 'expiration']
            available_columns = [col for col in dedup_columns if col in combined_data.columns]
            
            if available_columns:
                combined_data = combined_data.drop_duplicates(
                    subset=available_columns,
                    keep='last'  # Keep newer data in case of conflicts
                )
            
            # Sort by date for efficient querying
            if 'date' in combined_data.columns:
                combined_data = combined_data.sort_values(['date', 'expiration', 'strike', 'option_type'])
            
            logger.info(f"Merged archive for {symbol}: {len(existing_archive)} existing + {len(new_data)} new = {len(combined_data)} total")
            return combined_data
            
        except Exception as e:
            logger.error(f"Error merging archive data for {symbol}: {e}")
            return new_data  # Return new data as fallback
    
    async def archive_symbol(self, symbol: str, force_date_range: tuple[date, date] = None) -> Dict[str, Any]:
        """Archive historical data for a single symbol"""
        result = {
            "symbol": symbol,
            "success": False,
            "start_date": None,
            "end_date": None,
            "records_downloaded": 0,
            "total_archive_records": 0,
            "message": "",
            "error": None
        }
        
        try:
            # Calculate date range
            if force_date_range:
                start_date, end_date = force_date_range
            else:
                start_date, end_date = self._calculate_archive_date_range(symbol)
            
            if start_date is None or end_date is None:
                result["message"] = "Archive is up to date or invalid date range"
                result["success"] = True  # Not an error, just nothing to do
                return result
            
            result["start_date"] = start_date
            result["end_date"] = end_date
            
            # Log download start
            download_record = db_manager.log_download(symbol, "historical_archive", "pending")
            
            try:
                # Download historical data
                new_data = await self._download_historical_data(symbol, start_date, end_date)
                
                if new_data is None or len(new_data) == 0:
                    result["error"] = "No data downloaded"
                    result["message"] = f"No historical data available for {symbol} in date range"
                    db_manager.update_download_status(download_record.id, "failed", error_message=result["error"])
                    return result
                
                result["records_downloaded"] = len(new_data)
                
                # Merge with existing archive
                merged_data = self._merge_with_existing_archive(symbol, new_data)
                result["total_archive_records"] = len(merged_data)
                
                # Save consolidated archive
                storage.save_historical_archive(symbol, merged_data)
                
                # Update download status
                db_manager.update_download_status(
                    download_record.id, 
                    "completed", 
                    records_count=result["records_downloaded"]
                )
                
                result["success"] = True
                result["message"] = f"Successfully archived {result['records_downloaded']} new records"
                logger.info(f"Archive completed for {symbol}: {result['records_downloaded']} new records")
                
            except Exception as e:
                db_manager.update_download_status(download_record.id, "failed", error_message=str(e))
                raise
                
        except Exception as e:
            result["error"] = str(e)
            result["message"] = f"Error archiving {symbol}: {e}"
            logger.error(result["message"])
        
        finally:
            # Disconnect IB client
            if self.ib_client:
                await self.ib_client.disconnect()
                self.ib_client = None
        
        return result
    
    async def archive_multiple_symbols(self, symbols: List[str], 
                                     force_date_range: tuple[date, date] = None) -> Dict[str, Any]:
        """Archive historical data for multiple symbols"""
        results = {
            "symbols_processed": 0,
            "symbols_successful": 0,
            "total_records_downloaded": 0,
            "results": {},
            "start_time": datetime.now(),
            "end_time": None,
            "errors": []
        }
        
        logger.info(f"Starting archive operation for {len(symbols)} symbols")
        
        for symbol in symbols:
            try:
                results["symbols_processed"] += 1
                logger.info(f"Archiving {symbol} ({results['symbols_processed']}/{len(symbols)})")
                
                # Archive this symbol
                symbol_result = await self.archive_symbol(symbol, force_date_range)
                results["results"][symbol] = symbol_result
                
                if symbol_result["success"]:
                    results["symbols_successful"] += 1
                    results["total_records_downloaded"] += symbol_result["records_downloaded"]
                else:
                    results["errors"].append(f"{symbol}: {symbol_result.get('error', 'Unknown error')}")
                
                # Small delay between symbols
                await asyncio.sleep(1)
                
            except Exception as e:
                error_msg = f"Error processing {symbol}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        results["end_time"] = datetime.now()
        results["duration"] = (results["end_time"] - results["start_time"]).total_seconds()
        
        logger.info(f"Archive operation completed: {results['symbols_successful']}/{results['symbols_processed']} symbols successful, {results['total_records_downloaded']} total records")
        
        return results
    
    def get_archive_status(self, symbol: str) -> Dict[str, Any]:
        """Get archive status for a symbol"""
        try:
            last_archive_date = storage.get_last_archive_date(symbol)
            archive_summary = storage.load_historical_archive(symbol)
            
            status = {
                "symbol": symbol,
                "has_archive": archive_summary is not None and len(archive_summary) > 0,
                "last_archive_date": last_archive_date,
                "archive_records": len(archive_summary) if archive_summary is not None else 0,
                "needs_update": False,
                "days_behind": 0
            }
            
            if last_archive_date:
                yesterday = date.today() - timedelta(days=1)
                status["days_behind"] = (yesterday - last_archive_date).days
                status["needs_update"] = status["days_behind"] > 0
            else:
                status["needs_update"] = True
                status["days_behind"] = config.max_archive_days_per_request
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting archive status for {symbol}: {e}")
            return {
                "symbol": symbol,
                "error": str(e),
                "has_archive": False,
                "needs_update": True
            }
    
    def get_all_archive_status(self) -> Dict[str, Dict[str, Any]]:
        """Get archive status for all active symbols"""
        try:
            active_symbols = db_manager.get_active_symbols()
            status_dict = {}
            
            for symbol_obj in active_symbols:
                status_dict[symbol_obj.symbol] = self.get_archive_status(symbol_obj.symbol)
            
            return status_dict
            
        except Exception as e:
            logger.error(f"Error getting all archive status: {e}")
            return {}


# Global instance
historical_archiver = HistoricalArchiver()