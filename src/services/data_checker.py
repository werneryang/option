"""
Historical data checker service
"""
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from loguru import logger

from ..data_sources.database import db_manager, DataDownload
from ..data_sources.storage import storage
from ..utils.trading_calendar import trading_calendar


class DataChecker:
    """Service for checking and maintaining historical data"""
    
    def __init__(self):
        self.storage = storage
        self.db_manager = db_manager
        self.trading_calendar = trading_calendar
        self._downloader = None
    
    @property
    def downloader(self):
        """Lazy load downloader to avoid event loop issues at startup"""
        if self._downloader is None:
            from ..data_sources.ib_client import downloader
            self._downloader = downloader
        return self._downloader
    
    def get_last_download_date(self, symbol: str, data_type: str = "historical_options") -> Optional[date]:
        """
        Get the last successful download date for a symbol and data type
        
        Args:
            symbol: Stock symbol
            data_type: Type of data to check
            
        Returns:
            Last download date or None if no downloads found
        """
        try:
            # First try to get from database records
            with self.db_manager.get_session() as session:
                last_download = session.query(DataDownload).filter(
                    DataDownload.symbol == symbol,
                    DataDownload.data_type == data_type,
                    DataDownload.status == "completed"
                ).order_by(DataDownload.download_date.desc()).first()
                
                if last_download:
                    return last_download.download_date.date()
            
            # If no completed database records, check actual data files
            if data_type == "historical_options":
                try:
                    available_dates = self.storage.get_available_dates(symbol)
                    if available_dates:
                        latest_date = max(available_dates)
                        # Verify data exists for this date
                        data = self.storage.load_option_chain(symbol, latest_date)
                        if data is not None and len(data) > 0:
                            logger.info(f"Found existing data for {symbol}: {len(data)} records on {latest_date}")
                            return latest_date
                except Exception as e:
                    logger.debug(f"Error checking actual data files for {symbol}: {e}")
            
            return None
                
        except Exception as e:
            logger.error(f"Error getting last download date for {symbol}: {e}")
            return None
    
    def check_data_freshness(self, symbol: str, check_time: datetime = None) -> Dict[str, Any]:
        """
        Check if historical data is up to date for a given symbol
        
        Args:
            symbol: Stock symbol to check
            check_time: Time to check against (defaults to now)
            
        Returns:
            Dict with check results
        """
        if check_time is None:
            check_time = datetime.now()
            
        result = {
            'symbol': symbol,
            'check_time': check_time,
            'is_up_to_date': False,
            'needs_download': False,
            'last_download_date': None,
            'expected_date': None,
            'reason': '',
            'download_types_needed': []
        }
        
        try:
            # Get expected last data date based on trading calendar
            expected_date = self.trading_calendar.get_expected_last_data_date(check_time)
            result['expected_date'] = expected_date
            
            # Check historical options data
            last_options_date = self.get_last_download_date(symbol, "historical_options")
            result['last_download_date'] = last_options_date
            
            if last_options_date is None:
                # No historical data found
                result['needs_download'] = True
                result['reason'] = "No historical data found"
                result['download_types_needed'] = ["historical_options", "stock_price"]
            elif last_options_date < expected_date:
                # Data is outdated
                result['needs_download'] = True
                result['reason'] = f"Data outdated. Last: {last_options_date}, Expected: {expected_date}"
                result['download_types_needed'] = ["historical_options"]
            else:
                # Data is up to date - adjust expected date for UI clarity
                result['is_up_to_date'] = True
                result['reason'] = "Data is up to date"
                
                # If we have data newer than expected, show the actual data date as expected
                # This makes the UI more intuitive when showing "Last Download" vs "Expected Date"
                if last_options_date > expected_date:
                    result['expected_date'] = last_options_date
            
            logger.info(f"Data freshness check for {symbol}: {result['reason']}")
            return result
            
        except Exception as e:
            error_msg = f"Error checking data freshness for {symbol}: {e}"
            logger.error(error_msg)
            result['reason'] = error_msg
            return result
    
    def get_data_status_summary(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive data status summary for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with data status summary
        """
        summary = {
            'symbol': symbol,
            'historical_options': {'available': False, 'last_date': None, 'record_count': 0},
            'stock_prices': {'available': False, 'last_date': None, 'record_count': 0},
            'recent_downloads': [],
            'total_downloads': 0
        }
        
        try:
            # Check historical options data availability
            try:
                options_data = self.storage.load_all_option_data(symbol)
                if options_data is not None and not options_data.empty:
                    summary['historical_options']['available'] = True
                    summary['historical_options']['record_count'] = len(options_data)
                    if 'date' in options_data.columns:
                        summary['historical_options']['last_date'] = options_data['date'].max()
            except Exception as e:
                logger.debug(f"No historical options data found for {symbol}: {e}")
            
            # Check stock price data availability
            try:
                price_data = self.storage.load_price_history(symbol)
                if price_data is not None and not price_data.empty:
                    summary['stock_prices']['available'] = True
                    summary['stock_prices']['record_count'] = len(price_data)
                    if 'date' in price_data.columns:
                        summary['stock_prices']['last_date'] = price_data['date'].max()
            except Exception as e:
                logger.debug(f"No stock price data found for {symbol}: {e}")
            
            # Get recent download history
            recent_downloads = self.db_manager.get_recent_downloads(symbol, days=30)
            summary['recent_downloads'] = [
                {
                    'date': download.download_date,
                    'data_type': download.data_type,
                    'status': download.status,
                    'records_count': download.records_count,
                    'error_message': download.error_message
                }
                for download in recent_downloads
            ]
            summary['total_downloads'] = len(recent_downloads)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting data status summary for {symbol}: {e}")
            summary['error'] = str(e)
            return summary
    
    async def download_missing_data(self, symbol: str, data_types: List[str] = None) -> Dict[str, Any]:
        """
        Download missing historical data for a symbol
        
        Args:
            symbol: Stock symbol
            data_types: List of data types to download (defaults to all)
            
        Returns:
            Dict with download results
        """
        if data_types is None:
            data_types = ["historical_options", "stock_price"]
            
        results = {
            'symbol': symbol,
            'started_at': datetime.now(),
            'downloads': {},
            'success': False,
            'errors': []
        }
        
        try:
            # Ensure symbol exists in database
            self.db_manager.add_symbol(symbol)
            
            for data_type in data_types:
                download_result = {'success': False, 'error': None}
                
                try:
                    if data_type == "historical_options":
                        data = await self.downloader.client.get_historical_option_data(symbol)
                        download_result['success'] = data is not None
                        if data is not None:
                            download_result['records'] = len(data)
                    elif data_type == "stock_price":
                        data = await self.downloader.client.get_historical_data(symbol)
                        download_result['success'] = data is not None
                        if data is not None:
                            download_result['records'] = len(data)
                    else:
                        download_result['error'] = f"Unknown data type: {data_type}"
                        
                except Exception as e:
                    download_result['error'] = str(e)
                    results['errors'].append(f"{data_type}: {e}")
                
                results['downloads'][data_type] = download_result
            
            # Check overall success
            results['success'] = all(
                result['success'] for result in results['downloads'].values()
            )
            results['completed_at'] = datetime.now()
            
            logger.info(f"Download completed for {symbol}. Success: {results['success']}")
            return results
            
        except Exception as e:
            error_msg = f"Error downloading data for {symbol}: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            results['completed_at'] = datetime.now()
            return results
    
    async def check_and_update_data(self, symbol: str, force_download: bool = False) -> Dict[str, Any]:
        """
        Complete data check and update workflow
        
        Args:
            symbol: Stock symbol
            force_download: Force download even if data appears up to date
            
        Returns:
            Dict with complete workflow results
        """
        workflow_result = {
            'symbol': symbol,
            'started_at': datetime.now(),
            'freshness_check': None,
            'download_result': None,
            'final_status': None,
            'action_taken': 'none'
        }
        
        try:
            # Step 1: Check data freshness
            freshness_check = self.check_data_freshness(symbol)
            workflow_result['freshness_check'] = freshness_check
            
            # Step 2: Decide if download is needed
            needs_download = force_download or freshness_check['needs_download']
            
            if needs_download:
                logger.info(f"Downloading data for {symbol}. Reason: {freshness_check['reason']}")
                
                # Step 3: Download missing data
                download_types = freshness_check.get('download_types_needed', ["historical_options"])
                download_result = await self.download_missing_data(symbol, download_types)
                workflow_result['download_result'] = download_result
                workflow_result['action_taken'] = 'download'
                
                # Step 4: Get final status
                final_status = self.get_data_status_summary(symbol)
                workflow_result['final_status'] = final_status
            else:
                logger.info(f"No download needed for {symbol}. Data is up to date.")
                workflow_result['action_taken'] = 'none'
                workflow_result['final_status'] = self.get_data_status_summary(symbol)
            
            workflow_result['completed_at'] = datetime.now()
            return workflow_result
            
        except Exception as e:
            error_msg = f"Error in check and update workflow for {symbol}: {e}"
            logger.error(error_msg)
            workflow_result['error'] = error_msg
            workflow_result['completed_at'] = datetime.now()
            return workflow_result


# Global instance
data_checker = DataChecker()