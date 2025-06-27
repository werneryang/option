"""
Real-time Option Snapshot Collector

Collects delayed option chain snapshots every 5 minutes during market hours
and stores them in cumulative daily files for intraday analysis.
"""

import asyncio
import threading
from datetime import datetime, time, date, timedelta
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
        
        # Scheduler state
        self._last_collection_time = None
        self._next_collection_time = None
        
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
    
    def _calculate_next_collection_time(self, current_time: datetime = None) -> Optional[datetime]:
        """Calculate the next scheduled collection time"""
        if current_time is None:
            current_time = datetime.now()
        
        # If not a trading day, no collection needed
        if not trading_calendar.is_trading_day(current_time.date()):
            return None
        
        # Get today's market start and end times
        today = current_time.date()
        market_start_today = datetime.combine(today, self.market_start)
        market_end_today = datetime.combine(today, self.market_end)
        
        # If before market hours, next collection is at market start
        if current_time < market_start_today:
            return market_start_today
        
        # If after market hours, no more collections today
        if current_time > market_end_today:
            return None
        
        # Calculate next collection time based on interval
        # Find the next interval boundary after current time
        minutes_since_market_start = (current_time - market_start_today).total_seconds() / 60
        next_interval = ((int(minutes_since_market_start) // self.interval_minutes) + 1) * self.interval_minutes
        next_collection = market_start_today + timedelta(minutes=next_interval)
        
        # Don't schedule past market close
        if next_collection > market_end_today:
            return None
        
        return next_collection
    
    def _should_collect_now(self) -> bool:
        """Check if we should collect a snapshot now based on schedule"""
        current_time = datetime.now()
        
        # Must be during market hours
        if not self._is_market_hours(current_time):
            self._next_collection_time = None
            return False
        
        # Initialize next collection time if not set
        if self._next_collection_time is None:
            self._next_collection_time = self._calculate_next_collection_time(current_time)
        
        # Check if it's time to collect (within 30 seconds of scheduled time)
        if (self._next_collection_time and 
            abs((current_time - self._next_collection_time).total_seconds()) <= 30):
            
            # Prevent duplicate collections within same minute
            if (self._last_collection_time is None or 
                (current_time - self._last_collection_time).total_seconds() >= 60):
                
                # Update last collection time and calculate next
                self._last_collection_time = current_time
                self._next_collection_time = self._calculate_next_collection_time(current_time)
                
                return True
        
        return False
    
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
        """Collect real-time option chain snapshot for a single symbol"""
        try:
            if not await self._connect_to_ib():
                return None
            
            logger.info(f"Collecting real-time snapshot for {symbol}")
            
            # Use the real snapshot collection method
            snapshot_data = await self.ib_client.get_current_option_snapshot(symbol)
            
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
            # Get active symbols from database
            active_symbols = db_manager.get_symbols(active_only=True)
            if not active_symbols:
                logger.warning("No active symbols found in database, using default symbols")
                # Fallback to default symbols if database is empty
                from ..data_sources.storage import storage
                fallback_symbols = storage.get_symbols_with_data()
                if not fallback_symbols:
                    fallback_symbols = ['AAPL', 'SPY', 'TSLA']  # Final fallback
                symbol_names = fallback_symbols
            else:
                symbol_names = [s.symbol for s in active_symbols]
            
            logger.info(f"Starting snapshot collection for {len(symbol_names)} symbols: {symbol_names}")
            
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
        current_time = datetime.now()
        next_collection = self._calculate_next_collection_time(current_time)
        
        return {
            "is_running": self.is_running,
            "is_market_hours": self._is_market_hours(),
            "should_collect_now": self._should_collect_now(),
            "market_hours": f"{self.market_start} - {self.market_end}",
            "collection_interval": f"{self.interval_minutes} minutes",
            "current_time": current_time,
            "next_collection_time": next_collection,
            "last_collection_time": self._last_collection_time,
            "is_trading_day": trading_calendar.is_trading_day(date.today()),
            "ib_connected": self.ib_client.connected if self.ib_client else False
        }
    
    async def collect_now(self, symbol: str = None) -> Dict[str, Any]:
        """Manually trigger snapshot collection (for testing/debugging) with timeout"""
        if symbol:
            # Collect for specific symbol with comprehensive test results and timeout
            start_time = datetime.now()
            logger.info(f"Manual snapshot collection for {symbol}")
            
            # Initialize test results
            test_results = {
                "symbol": symbol,
                "test_start_time": start_time,
                "success": False,
                "contracts": 0,
                "timestamp": None,
                "connection_status": "disconnected",
                "data_quality": {},
                "performance": {},
                "errors": [],
                "warnings": []
            }
            
            try:
                # Use timeout to prevent hanging
                timeout_seconds = 60  # 1 minute timeout for test
                
                # Test IB connection with timeout
                connection_start = datetime.now()
                logger.info(f"Attempting to connect to IB TWS (timeout: {timeout_seconds}s)")
                
                try:
                    connected = await asyncio.wait_for(
                        self._connect_to_ib(), 
                        timeout=30  # 30 second connection timeout
                    )
                    
                    if not connected:
                        test_results["errors"].append("Failed to connect to IB TWS")
                        test_results["error"] = "Connection failed"
                        return test_results
                        
                except asyncio.TimeoutError:
                    test_results["errors"].append("Connection timeout (30s) - IB TWS may not be running")
                    test_results["error"] = "Connection timeout"
                    return test_results
                
                connection_time = (datetime.now() - connection_start).total_seconds()
                test_results["connection_status"] = "connected"
                test_results["performance"]["connection_time_seconds"] = connection_time
                logger.info(f"Connected to IB TWS in {connection_time:.2f}s")
                
                # Collect snapshot data with timeout
                collection_start = datetime.now()
                logger.info(f"Collecting snapshot data for {symbol} (timeout: 30s)")
                
                try:
                    snapshot_df = await asyncio.wait_for(
                        self._collect_symbol_snapshot(symbol),
                        timeout=30  # 30 second collection timeout
                    )
                except asyncio.TimeoutError:
                    test_results["errors"].append("Data collection timeout (30s) - market may be closed or data unavailable")
                    test_results["error"] = "Collection timeout"
                    collection_time = (datetime.now() - collection_start).total_seconds()
                    test_results["performance"]["collection_time_seconds"] = collection_time
                    return test_results
                
                collection_time = (datetime.now() - collection_start).total_seconds()
                test_results["performance"]["collection_time_seconds"] = collection_time
                logger.info(f"Data collection completed in {collection_time:.2f}s")
                
                if snapshot_df is not None and len(snapshot_df) > 0:
                    timestamp = datetime.now()
                    
                    # Analyze data quality
                    test_results["data_quality"] = self._analyze_data_quality(snapshot_df)
                    
                    # Save snapshot
                    try:
                        storage.save_snapshot(symbol, timestamp, snapshot_df)
                        logger.info(f"Snapshot saved to storage")
                    except Exception as save_error:
                        test_results["warnings"].append(f"Failed to save snapshot: {str(save_error)}")
                        logger.warning(f"Failed to save snapshot: {save_error}")
                    
                    # Update test results
                    test_results.update({
                        "success": True,
                        "contracts": len(snapshot_df),
                        "timestamp": timestamp,
                        "test_duration_seconds": (timestamp - start_time).total_seconds()
                    })
                    
                    logger.info(f"Test collection successful for {symbol}: {len(snapshot_df)} contracts")
                    
                else:
                    test_results["errors"].append("No data collected from IB")
                    test_results["error"] = "No data collected"
                    test_results["warnings"].append("Check market hours and IB data subscriptions")
                    logger.warning(f"No snapshot data collected for {symbol}")
                    
            except asyncio.TimeoutError:
                error_msg = f"Test collection timeout after {timeout_seconds} seconds"
                test_results["errors"].append(error_msg)
                test_results["error"] = "Timeout"
                logger.error(error_msg)
                
            except Exception as e:
                error_msg = f"Test collection error: {str(e)}"
                test_results["errors"].append(error_msg)
                test_results["error"] = str(e)
                logger.error(error_msg)
            
            finally:
                test_results["test_end_time"] = datetime.now()
                test_results["total_test_time_seconds"] = (
                    test_results["test_end_time"] - start_time
                ).total_seconds()
                
                # Disconnect if connected
                if self.ib_client and self.ib_client.connected:
                    try:
                        await self.ib_client.disconnect()
                        logger.info("Disconnected from IB TWS after test")
                    except Exception as disconnect_error:
                        logger.warning(f"Error disconnecting after test: {disconnect_error}")
            
            return test_results
        else:
            # Collect for all symbols
            logger.info("Manual snapshot collection for all symbols")
            return await self._collect_all_snapshots()
    
    def _analyze_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze quality of collected snapshot data"""
        quality = {
            "total_contracts": len(df),
            "call_contracts": 0,
            "put_contracts": 0,
            "unique_expirations": 0,
            "unique_strikes": 0,
            "has_bid_ask": 0,
            "has_last_price": 0,
            "has_volume": 0,
            "price_data_completeness": 0.0,
            "issues": []
        }
        
        try:
            # Basic contract analysis
            if 'right' in df.columns:
                quality["call_contracts"] = len(df[df['right'] == 'C'])
                quality["put_contracts"] = len(df[df['right'] == 'P'])
            
            if 'expiration' in df.columns:
                quality["unique_expirations"] = df['expiration'].nunique()
            
            if 'strike' in df.columns:
                quality["unique_strikes"] = df['strike'].nunique()
            
            # Price data analysis
            price_columns = ['bid', 'ask', 'last', 'close']
            available_price_cols = [col for col in price_columns if col in df.columns]
            
            if available_price_cols:
                for col in available_price_cols:
                    non_null_count = df[col].notna().sum()
                    if col in ['bid', 'ask']:
                        quality["has_bid_ask"] += non_null_count
                    elif col in ['last', 'close']:
                        quality["has_last_price"] += non_null_count
                
                # Calculate overall price data completeness
                total_price_fields = len(df) * len(available_price_cols)
                filled_price_fields = sum(df[col].notna().sum() for col in available_price_cols)
                quality["price_data_completeness"] = (
                    filled_price_fields / total_price_fields * 100 if total_price_fields > 0 else 0
                )
            
            # Volume analysis
            if 'volume' in df.columns:
                quality["has_volume"] = df['volume'].notna().sum()
            
            # Quality issues detection
            if quality["total_contracts"] == 0:
                quality["issues"].append("No contracts collected")
            elif quality["total_contracts"] < 10:
                quality["issues"].append("Very few contracts collected (< 10)")
            
            if quality["price_data_completeness"] < 50:
                quality["issues"].append("Low price data completeness (< 50%)")
            
            if quality["call_contracts"] == 0 and quality["put_contracts"] == 0:
                quality["issues"].append("No call/put classification available")
            
            if quality["unique_expirations"] == 0:
                quality["issues"].append("No expiration dates available")
                
        except Exception as e:
            quality["issues"].append(f"Data analysis error: {str(e)}")
        
        return quality


# Global instance
snapshot_collector = SnapshotCollector()