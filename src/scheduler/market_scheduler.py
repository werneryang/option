"""
Market Data Scheduler
Automated collection of intraday option data including 16:00 market close
"""

import asyncio
from datetime import datetime, time, timedelta
from typing import List, Optional
import schedule
from loguru import logger

from ..data_sources.ib_client import IBClient


class MarketScheduler:
    """Scheduler for automated intraday option data collection"""
    
    # Market hours: 9:30 AM to 4:00 PM ET
    MARKET_OPEN = time(9, 30)
    MARKET_CLOSE = time(16, 0)
    
    # Collection times (including 16:00 market close)
    COLLECTION_TIMES = [
        time(9, 30),   # Market open
        time(10, 0),   # 10:00 AM
        time(11, 0),   # 11:00 AM  
        time(12, 0),   # 12:00 PM
        time(13, 0),   # 1:00 PM
        time(14, 0),   # 2:00 PM
        time(15, 0),   # 3:00 PM
        time(16, 0),   # 4:00 PM (Market close)
    ]
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['AAPL', 'SPY', 'TSLA']
        self.client = IBClient()
        self.running = False
        
    def schedule_collection(self):
        """Set up scheduled data collection"""
        logger.info("Setting up market data collection schedule")
        
        for collection_time in self.COLLECTION_TIMES:
            time_str = collection_time.strftime("%H:%M")
            
            # Schedule for weekdays only
            schedule.every().monday.at(time_str).do(self._collect_snapshot)
            schedule.every().tuesday.at(time_str).do(self._collect_snapshot)
            schedule.every().wednesday.at(time_str).do(self._collect_snapshot)
            schedule.every().thursday.at(time_str).do(self._collect_snapshot)
            schedule.every().friday.at(time_str).do(self._collect_snapshot)
            
            logger.info(f"Scheduled data collection at {time_str}")
        
        logger.info(f"Scheduler configured for symbols: {', '.join(self.symbols)}")
        logger.info("Collection includes 16:00 market close snapshot")
    
    def _collect_snapshot(self):
        """Collect option data snapshot"""
        current_time = datetime.now().time()
        logger.info(f"Starting scheduled data collection at {current_time}")
        
        try:
            asyncio.run(self._async_collect_snapshot())
        except Exception as e:
            logger.error(f"Error in scheduled collection: {e}")
    
    async def _async_collect_snapshot(self):
        """Async version of snapshot collection"""
        async with self.client:
            for symbol in self.symbols:
                try:
                    logger.info(f"Collecting option chain for {symbol}")
                    option_data = await self.client.get_option_chain(symbol)
                    
                    if option_data is not None:
                        logger.info(f"Successfully collected {len(option_data)} options for {symbol}")
                    else:
                        logger.warning(f"No option data collected for {symbol}")
                        
                except Exception as e:
                    logger.error(f"Error collecting data for {symbol}: {e}")
                
                await asyncio.sleep(1)  # Rate limiting
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.schedule_collection()
        self.running = True
        
        logger.info("Market data scheduler started")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while self.running:
                schedule.run_pending()
                asyncio.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear()
        logger.info("Market data scheduler stopped")
    
    def get_next_collection_time(self) -> Optional[datetime]:
        """Get the next scheduled collection time"""
        next_run = schedule.next_run()
        return next_run if next_run else None
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        now = datetime.now().time()
        return self.MARKET_OPEN <= now <= self.MARKET_CLOSE
    
    def get_collection_status(self) -> dict:
        """Get current scheduler status"""
        return {
            'running': self.running,
            'symbols': self.symbols,
            'collection_times': [t.strftime("%H:%M") for t in self.COLLECTION_TIMES],
            'next_run': self.get_next_collection_time(),
            'market_hours': self.is_market_hours(),
            'scheduled_jobs': len(schedule.jobs)
        }


def run_scheduler(symbols: List[str] = None):
    """Convenience function to run the scheduler"""
    scheduler = MarketScheduler(symbols)
    scheduler.start()


if __name__ == "__main__":
    # Run with default symbols
    run_scheduler()