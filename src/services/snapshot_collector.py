"""
Real-time Option Snapshot Collector

Collects delayed option chain snapshots every 5 minutes during market hours
and stores them in cumulative daily files for intraday analysis.
"""

import asyncio
import threading
from datetime import datetime, time, date
from typing import List, Dict, Optional, Any
import pandas as pd
from loguru import logger

from ..data_sources.ib_client import IBClient
from ..data_sources.storage import storage
from ..data_sources.database import db_manager
from ..utils.config import config
from ..utils.trading_calendar import trading_calendar


class SnapshotCollector:
    """Real-time snapshot collector for option chain data"""
    
    def __init__(self):
        self.ib_client = None
        self.is_running = False
        self.collection_thread = None
        self._stop_event = threading.Event()
        
        # Collection settings from config
        self.interval_minutes = config.snapshot_interval_minutes
        self.market_start = self._parse_time(config.market_start_time)
        self.market_end = self._parse_time(config.market_end_time)
        
    def _parse_time(self, time_str: str) -> time:
        """Parse time string HH:MM to time object"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return time(hour, minute)
        except Exception as e:
            logger.error(f"Error parsing time '{time_str}': {e}")
            return time(9, 45)  # Default fallback
    
    def _is_market_hours(self, current_time: datetime = None) -> bool:
        """Check if current time is within market hours on a trading day"""
        if current_time is None:
            current_time = datetime.now()
        
        # Check if it's a trading day
        if not trading_calendar.is_trading_day(current_time.date()):
            return False
        
        # Check if it's within market hours
        current_time_only = current_time.time()
        return self.market_start <= current_time_only <= self.market_end
    
    def _should_collect_now(self) -> bool:
        """Check if we should collect a snapshot now based on schedule"""
        current_time = datetime.now()
        
        # Must be during market hours
        if not self._is_market_hours(current_time):
            return False
        
        # Check if it's time for next collection (every N minutes)
        minutes_since_market_open = (current_time.time().hour * 60 + current_time.time().minute) - \
                                   (self.market_start.hour * 60 + self.market_start.minute)
        
        return minutes_since_market_open % self.interval_minutes == 0
    
    async def _connect_to_ib(self) -> bool:
        """Connect to Interactive Brokers TWS"""
        try:
            if self.ib_client is None:
                # Use unique client ID for snapshot collector
                self.ib_client = IBClient(client_id=2)  # Different from manual downloads
            
            if not self.ib_client.connected:
                connected = await self.ib_client.connect()
                if connected:
                    logger.info("Snapshot collector connected to IB TWS")
                    return True
                else:
                    logger.error("Failed to connect snapshot collector to IB TWS")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error connecting snapshot collector to IB TWS: {e}")
            return False
    
    async def _collect_symbol_snapshot(self, symbol: str) -> Optional[pd.DataFrame]:
        """Collect option chain snapshot for a single symbol"""
        try:
            if not await self._connect_to_ib():
                return None
            
            logger.info(f"Collecting snapshot for {symbol}")
            
            # Get current option chain snapshot (this would be a new method in IBClient)
            # For now, we'll use the existing historical method as a placeholder
            snapshot_data = await self.ib_client.get_option_chain(symbol)
            
            if snapshot_data is not None and len(snapshot_data) > 0:
                logger.info(f"Collected snapshot for {symbol}: {len(snapshot_data)} contracts")
                return snapshot_data
            else:
                logger.warning(f"No snapshot data collected for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error collecting snapshot for {symbol}: {e}")
            return None
    
    async def _collect_all_snapshots(self) -> Dict[str, Any]:
        """Collect snapshots for all active symbols"""
        timestamp = datetime.now()
        results = {
            "timestamp": timestamp,
            "symbols_processed": 0,
            "symbols_successful": 0,
            "total_contracts": 0,
            "errors": []
        }
        
        try:
            # Get active symbols from data service
            active_symbols = db_manager.get_active_symbols()
            if not active_symbols:
                logger.warning("No active symbols found for snapshot collection")
                return results
            
            symbol_names = [s.symbol for s in active_symbols]
            logger.info(f"Starting snapshot collection for {len(symbol_names)} symbols")
            
            for symbol in symbol_names:
                try:
                    results["symbols_processed"] += 1
                    
                    # Collect snapshot for this symbol
                    snapshot_df = await self._collect_symbol_snapshot(symbol)
                    
                    if snapshot_df is not None and len(snapshot_df) > 0:
                        # Save snapshot to storage
                        storage.save_snapshot(symbol, timestamp, snapshot_df)
                        results["symbols_successful"] += 1
                        results["total_contracts"] += len(snapshot_df)
                        
                        logger.info(f"Saved snapshot for {symbol}: {len(snapshot_df)} contracts")
                    else:
                        error_msg = f"No data collected for {symbol}"
                        results["errors"].append(error_msg)
                        logger.warning(error_msg)
                
                except Exception as e:
                    error_msg = f"Error processing {symbol}: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
                
                # Small delay between symbols to avoid overwhelming the API
                await asyncio.sleep(0.5)
            
            # Log collection summary
            logger.info(f"Snapshot collection completed: {results['symbols_successful']}/{results['symbols_processed']} symbols successful, {results['total_contracts']} total contracts")
            
            # Log to database
            db_manager.log_download(
                symbol="ALL_SYMBOLS", 
                data_type="snapshot", 
                status="completed" if results["symbols_successful"] > 0 else "failed",
                records_count=results["total_contracts"]
            )
            
        except Exception as e:
            error_msg = f"Error in snapshot collection: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def _collection_loop(self):
        """Main collection loop running in background thread"""
        logger.info("Snapshot collection loop started")
        
        async def async_loop():
            while not self._stop_event.is_set():
                try:
                    current_time = datetime.now()
                    
                    # Check if we should collect now
                    if self._should_collect_now():
                        logger.info(f"Starting scheduled snapshot collection at {current_time}")
                        results = await self._collect_all_snapshots()
                        
                        if results["symbols_successful"] > 0:
                            logger.info(f"Snapshot collection successful: {results['symbols_successful']} symbols")
                        else:
                            logger.warning(f"Snapshot collection failed: {results['errors']}")
                    
                    # Wait for next check (every minute to check if it's time to collect)
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Error in collection loop: {e}")
                    await asyncio.sleep(60)  # Wait before retrying
        
        # Run the async loop
        try:
            asyncio.run(async_loop())
        except Exception as e:
            logger.error(f"Error running async collection loop: {e}")
        finally:
            if self.ib_client:
                asyncio.run(self.ib_client.disconnect())
            logger.info("Snapshot collection loop ended")
    
    def start_collection(self) -> bool:
        """Start the snapshot collection service"""
        if self.is_running:
            logger.warning("Snapshot collection is already running")
            return False
        
        try:
            logger.info("Starting snapshot collection service")
            
            # Reset stop event
            self._stop_event.clear()
            
            # Start collection thread
            self.collection_thread = threading.Thread(
                target=self._collection_loop,
                name="SnapshotCollector",
                daemon=True
            )
            self.collection_thread.start()
            
            self.is_running = True
            logger.info("Snapshot collection service started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting snapshot collection service: {e}")
            return False
    
    def stop_collection(self) -> bool:
        """Stop the snapshot collection service"""
        if not self.is_running:
            logger.warning("Snapshot collection is not running")
            return False
        
        try:
            logger.info("Stopping snapshot collection service")
            
            # Signal stop
            self._stop_event.set()
            
            # Wait for thread to finish (with timeout)
            if self.collection_thread and self.collection_thread.is_alive():
                self.collection_thread.join(timeout=30)
                if self.collection_thread.is_alive():
                    logger.warning("Collection thread did not stop within timeout")
            
            self.is_running = False
            logger.info("Snapshot collection service stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping snapshot collection service: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the snapshot collector"""
        return {
            "is_running": self.is_running,
            "is_market_hours": self._is_market_hours(),
            "next_collection_eligible": self._should_collect_now(),
            "market_hours": f"{self.market_start} - {self.market_end}",
            "collection_interval": f"{self.interval_minutes} minutes",
            "current_time": datetime.now(),
            "is_trading_day": trading_calendar.is_trading_day(date.today()),
            "ib_connected": self.ib_client.connected if self.ib_client else False
        }
    
    async def collect_now(self, symbol: str = None) -> Dict[str, Any]:
        """Manually trigger snapshot collection (for testing/debugging)"""
        if symbol:
            # Collect for specific symbol
            logger.info(f"Manual snapshot collection for {symbol}")
            snapshot_df = await self._collect_symbol_snapshot(symbol)
            
            if snapshot_df is not None:
                timestamp = datetime.now()
                storage.save_snapshot(symbol, timestamp, snapshot_df)
                return {
                    "symbol": symbol,
                    "success": True,
                    "contracts": len(snapshot_df),
                    "timestamp": timestamp
                }
            else:
                return {
                    "symbol": symbol,
                    "success": False,
                    "error": "No data collected"
                }
        else:
            # Collect for all symbols
            logger.info("Manual snapshot collection for all symbols")
            return await self._collect_all_snapshots()


# Global instance
snapshot_collector = SnapshotCollector()