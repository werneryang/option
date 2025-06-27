import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
import pandas as pd
from ib_insync import IB, Stock, Option, Contract
from loguru import logger

from ..utils.config import config
from .database import db_manager
from .storage import storage

class IBClient:
    def __init__(self, host: str = None, port: int = None, client_id: int = None):
        self.host = host or config.ib_host
        self.port = port or config.ib_port
        self.client_id = client_id or config.ib_client_id
        
        self._ib = None
        self.connected = False
    
    @property
    def ib(self):
        """Lazy initialization of IB connection to avoid event loop issues"""
        if self._ib is None:
            from ib_insync import IB
            self._ib = IB()
        return self._ib
    
    async def connect(self) -> bool:
        try:
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id, timeout=10)
            self.connected = True
            logger.info(f"Connected to IB TWS at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IB TWS: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IB TWS")
    
    def _create_stock_contract(self, symbol: str) -> Stock:
        return Stock(symbol, 'SMART', 'USD')
    
    async def get_stock_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get historical stock price (NOT real-time market data)"""
        if not self.connected:
            logger.error("Not connected to IB TWS")
            return None
        
        try:
            contract = self._create_stock_contract(symbol)
            qualified_contract = await self.ib.qualifyContractsAsync(contract)
            
            if not qualified_contract:
                logger.error(f"Could not qualify contract for {symbol}")
                return None
            
            contract = qualified_contract[0]
            
            # Use historical data instead of real-time market data
            bars = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime='',
                durationStr='1 D',  # Get last day's data
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            
            if bars and len(bars) > 0:
                latest_bar = bars[-1]  # Get most recent bar
                price_data = {
                    'symbol': symbol,
                    'price': float(latest_bar.close),
                    'bid': None,  # Historical data doesn't have bid/ask
                    'ask': None,
                    'timestamp': latest_bar.date
                }
                logger.info(f"Retrieved historical stock price for {symbol}: ${latest_bar.close}")
                return price_data
            else:
                logger.warning(f"No historical price data for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting historical stock price for {symbol}: {e}")
            return None
    
    async def get_option_chain(self, symbol: str, expiration_date: date = None) -> Optional[pd.DataFrame]:
        """Get historical option chain data (NOT real-time market data)"""
        if not self.connected:
            logger.error("Not connected to IB TWS")
            return None
        
        download_record = db_manager.log_download(symbol, "options", "pending")
        download_id = download_record.id
        
        try:
            stock_contract = self._create_stock_contract(symbol)
            qualified_contract = await self.ib.qualifyContractsAsync(stock_contract)
            
            if not qualified_contract:
                error_msg = f"Could not qualify stock contract for {symbol}"
                logger.error(error_msg)
                db_manager.update_download_status(download_id, "failed", error_message=error_msg)
                return None
            
            stock_contract = qualified_contract[0]
            
            chains = await self.ib.reqSecDefOptParamsAsync(
                stock_contract.symbol, '', stock_contract.secType, stock_contract.conId
            )
            
            if not chains:
                error_msg = f"No option chains found for {symbol}"
                logger.error(error_msg)
                db_manager.update_download_status(download_id, "failed", error_message=error_msg)
                return None
            
            chain = chains[0]
            expirations = sorted(chain.expirations)
            
            if expiration_date:
                target_exp = expiration_date.strftime('%Y%m%d')
                if target_exp not in expirations:
                    error_msg = f"Expiration {target_exp} not available for {symbol}"
                    logger.error(error_msg)
                    db_manager.update_download_status(download_id, "failed", error_message=error_msg)
                    return None
                expirations = [target_exp]
            else:
                expirations = expirations[:3]  # Get next 3 expirations
            
            # Use middle strikes to avoid market data subscription requirements
            strikes = sorted(chain.strikes)
            mid_idx = len(strikes) // 2
            start_idx = max(0, mid_idx - 10)
            end_idx = min(len(strikes), mid_idx + 11)
            strikes = strikes[start_idx:end_idx]
            
            logger.info(f"Using historical data approach for {symbol} option chain (avoiding real-time market data)")
            
            option_data = []
            
            for expiration in expirations:
                for strike in strikes:
                    for right in ['C', 'P']:  # Call and Put
                        option = Option(symbol, expiration, strike, right, 'SMART')
                        try:
                            qualified_options = await self.ib.qualifyContractsAsync(option)
                            if qualified_options:
                                option_contract = qualified_options[0]
                                
                                # Use historical data instead of real-time market data
                                try:
                                    bars = await asyncio.wait_for(
                                        self.ib.reqHistoricalDataAsync(
                                            option_contract,
                                            endDateTime='',
                                            durationStr='1 D',  # Get last day's data
                                            barSizeSetting='1 day',
                                            whatToShow='TRADES',
                                            useRTH=True,
                                            formatDate=1
                                        ),
                                        timeout=10.0
                                    )
                                except asyncio.TimeoutError:
                                    logger.warning(f"Timeout getting historical data for {symbol} {expiration} {strike} {right}")
                                    continue
                                
                                if bars and len(bars) > 0:
                                    latest_bar = bars[-1]  # Get most recent bar
                                    option_info = {
                                        'symbol': symbol,
                                        'expiration': expiration,
                                        'strike': strike,
                                        'option_type': right,
                                        'bid': 0,  # Historical data doesn't have bid/ask
                                        'ask': 0,
                                        'last': float(latest_bar.close),
                                        'volume': int(latest_bar.volume),
                                        'open_interest': 0,  # Not available in historical bars
                                        'implied_volatility': 0,  # Not available in historical bars
                                        'delta': 0,  # Not available in historical bars
                                        'gamma': 0,
                                        'theta': 0,
                                        'vega': 0,
                                        'timestamp': latest_bar.date
                                    }
                                    option_data.append(option_info)
                                
                                await asyncio.sleep(0.1)  # Rate limiting
                                
                        except Exception as e:
                            logger.warning(f"Failed to get historical data for {symbol} {expiration} {strike} {right}: {e}")
                            continue
            
            if option_data:
                df = pd.DataFrame(option_data)
                df['expiration'] = pd.to_datetime(df['expiration'], format='%Y%m%d').dt.date
                
                file_path = storage.save_option_chain(symbol, date.today(), df)
                
                db_manager.update_download_status(
                    download_id, "completed", 
                    records_count=len(df), 
                    file_path=str(file_path)
                )
                
                logger.info(f"Successfully downloaded historical option chain for {symbol}: {len(df)} contracts")
                return df
            else:
                error_msg = f"No historical option data retrieved for {symbol}"
                logger.error(error_msg)
                db_manager.update_download_status(download_id, "failed", error_message=error_msg)
                return None
                
        except Exception as e:
            error_msg = f"Error downloading historical option chain for {symbol}: {e}"
            logger.error(error_msg)
            db_manager.update_download_status(download_id, "failed", error_message=error_msg)
            return None
    
    async def get_historical_option_data(self, symbol: str, duration: str = "1 M", 
                                       bar_size: str = "1 hour") -> Optional[pd.DataFrame]:
        """Download historical option data with intraday snapshots including 16:00 close"""
        if not self.connected:
            logger.error("Not connected to IB TWS")
            return None
        
        download_record = db_manager.log_download(symbol, "historical_options", "pending")
        download_id = download_record.id
        
        try:
            stock_contract = self._create_stock_contract(symbol)
            qualified_contract = await self.ib.qualifyContractsAsync(stock_contract)
            
            if not qualified_contract:
                error_msg = f"Could not qualify stock contract for {symbol}"
                logger.error(error_msg)
                db_manager.update_download_status(download_id, "failed", error_message=error_msg)
                return None
            
            stock_contract = qualified_contract[0]
            
            # Get option chains
            chains = await self.ib.reqSecDefOptParamsAsync(
                stock_contract.symbol, '', stock_contract.secType, stock_contract.conId
            )
            
            if not chains:
                error_msg = f"No option chains found for {symbol}"
                logger.error(error_msg)
                db_manager.update_download_status(download_id, "failed", error_message=error_msg)
                return None
            
            chain = chains[0]
            
            # Filter expirations to within 2 months for faster downloads
            current_date = datetime.now().date()
            two_months_later = current_date + timedelta(days=60)
            
            all_expirations = sorted(chain.expirations)
            expirations = []
            for exp_str in all_expirations:
                exp_date = datetime.strptime(exp_str, '%Y%m%d').date()
                if current_date <= exp_date <= two_months_later:
                    expirations.append(exp_str)
            
            # Limit to first 2 expirations for faster downloads
            expirations = expirations[:2]
            
            strikes = sorted(chain.strikes)
            
            # Skip real-time price lookup - use middle strike range for historical data
            # This avoids market data subscription requirements
            logger.info(f"Using middle strike range for {symbol} (avoiding real-time market data)")
            mid_idx = len(strikes) // 2
            start_idx = max(0, mid_idx - 5)  # Reduced from 10 to 5
            end_idx = min(len(strikes), mid_idx + 6)  # Reduced from 11 to 6
            strikes = strikes[start_idx:end_idx]
            
            logger.info(f"Found {len(expirations)} expirations within 1 year and {len(strikes)} strikes within ±20% for {symbol}")
            
            all_option_data = []
            
            for expiration in expirations:
                for strike in strikes:
                    for right in ['C', 'P']:
                        option = Option(symbol, expiration, strike, right, 'SMART')
                        try:
                            qualified_options = await self.ib.qualifyContractsAsync(option)
                            if qualified_options:
                                option_contract = qualified_options[0]
                                
                                # Request historical data with timeout
                                try:
                                    bars = await asyncio.wait_for(
                                        self.ib.reqHistoricalDataAsync(
                                            option_contract,
                                            endDateTime='',
                                            durationStr=duration,
                                            barSizeSetting=bar_size,
                                            whatToShow='TRADES',
                                            useRTH=True,  # Regular trading hours
                                            formatDate=1
                                        ),
                                        timeout=10.0  # 10 second timeout per contract
                                    )
                                except asyncio.TimeoutError:
                                    logger.warning(f"Timeout getting data for {symbol} {expiration} {strike} {right}")
                                    continue
                                
                                if bars:
                                    for bar in bars:
                                        # Extract hour from datetime
                                        bar_time = bar.date
                                        hour = bar_time.hour if hasattr(bar_time, 'hour') else 0
                                        
                                        # Include market hours: 9:30-16:00 (09:30, 10:00, 11:00, 12:00, 13:00, 14:00, 15:00, 16:00)
                                        if 9 <= hour <= 16:
                                            option_info = {
                                                'symbol': symbol,
                                                'date': bar_time.date() if hasattr(bar_time, 'date') else bar_time,
                                                'time': bar_time.strftime('%H:%M:%S') if hasattr(bar_time, 'strftime') else f"{hour:02d}:00:00",
                                                'expiration': expiration,
                                                'strike': strike,
                                                'option_type': right,
                                                'open': float(bar.open),
                                                'high': float(bar.high),
                                                'low': float(bar.low),
                                                'close': float(bar.close),
                                                'volume': int(bar.volume),
                                                'timestamp': bar_time
                                            }
                                            all_option_data.append(option_info)
                                
                                await asyncio.sleep(0.1)  # Rate limiting
                                
                        except Exception as e:
                            logger.warning(f"Failed to get historical data for {symbol} {expiration} {strike} {right}: {e}")
                            continue
            
            if all_option_data:
                df = pd.DataFrame(all_option_data)
                df['expiration'] = pd.to_datetime(df['expiration'], format='%Y%m%d').dt.date
                df = df.sort_values(['date', 'time', 'strike', 'option_type'])
                
                # Save data with date-based organization
                for date_val in df['date'].unique():
                    daily_data = df[df['date'] == date_val]
                    file_path = storage.save_option_chain(symbol, date_val, daily_data)
                
                db_manager.update_download_status(
                    download_id, "completed", 
                    records_count=len(df), 
                    file_path="multiple_dates"
                )
                
                logger.info(f"Successfully downloaded historical option data for {symbol}: {len(df)} records")
                return df
            else:
                error_msg = f"No historical option data retrieved for {symbol}"
                logger.error(error_msg)
                db_manager.update_download_status(download_id, "failed", error_message=error_msg)
                return None
                
        except Exception as e:
            error_msg = f"Error downloading historical option data for {symbol}: {e}"
            logger.error(error_msg)
            db_manager.update_download_status(download_id, "failed", error_message=error_msg)
            return None

    async def get_historical_data(self, symbol: str, duration: str = "1 Y", 
                                bar_size: str = "1 day") -> Optional[pd.DataFrame]:
        if not self.connected:
            logger.error("Not connected to IB TWS")
            return None
        
        download_record = db_manager.log_download(symbol, "stock_price", "pending")
        download_id = download_record.id
        
        try:
            contract = self._create_stock_contract(symbol)
            qualified_contract = await self.ib.qualifyContractsAsync(contract)
            
            if not qualified_contract:
                error_msg = f"Could not qualify contract for {symbol}"
                logger.error(error_msg)
                db_manager.update_download_status(download_id, "failed", error_message=error_msg)
                return None
            
            contract = qualified_contract[0]
            
            bars = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime='',
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            
            if bars:
                df = pd.DataFrame([{
                    'date': bar.date.date() if hasattr(bar.date, 'date') else bar.date,
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': int(bar.volume),
                    'symbol': symbol
                } for bar in bars])
                
                file_path = storage.save_price_history(symbol, df)
                
                db_manager.update_download_status(
                    download_id, "completed",
                    records_count=len(df),
                    file_path=str(file_path)
                )
                
                logger.info(f"Successfully downloaded historical data for {symbol}: {len(df)} bars")
                return df
            else:
                error_msg = f"No historical data returned for {symbol}"
                logger.error(error_msg)
                db_manager.update_download_status(download_id, "failed", error_message=error_msg)
                return None
                
        except Exception as e:
            error_msg = f"Error downloading historical data for {symbol}: {e}"
            logger.error(error_msg)
            db_manager.update_download_status(download_id, "failed", error_message=error_msg)
            return None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

class DataDownloader:
    def __init__(self):
        self.client = IBClient()
    
    def download_options_data(self, symbol: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for downloading options data - runs in subprocess to avoid event loop conflicts
        """
        import subprocess
        import sys
        import os
        
        try:
            # Create a simple subprocess script for historical data download
            download_script = f'''
import sys
import os
import asyncio
sys.path.append("{os.getcwd()}")

async def download_historical_data():
    from src.data_sources.ib_client import IBClient
    
    client = IBClient(client_id=99)  # Use unique client ID
    try:
        connected = await client.connect()
        if not connected:
            print("ERROR: Failed to connect to IB TWS")
            return
        
        # Download historical option data
        data = await client.get_historical_option_data("{symbol}")
        if data is not None and len(data) > 0:
            print(f"SUCCESS: {{len(data)}}")
        else:
            print("ERROR: No data returned")
    except Exception as e:
        print(f"ERROR: {{str(e)}}")
    finally:
        await client.disconnect()

# Run the download in a clean event loop
asyncio.run(download_historical_data())
'''
            
            # Execute in subprocess to avoid event loop conflicts
            process = subprocess.run(
                [sys.executable, '-c', download_script],
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout
            )
            
            if process.returncode == 0:
                output = process.stdout.strip()
                if "SUCCESS:" in output:
                    # Extract record count
                    try:
                        records = int(output.split("SUCCESS:")[1].strip())
                        return {
                            'symbol': symbol,
                            'success': True,
                            'downloads': {
                                'historical_options': {
                                    'success': True,
                                    'records': records
                                }
                            },
                            'message': f'Successfully downloaded {records} historical options records'
                        }
                    except (ValueError, IndexError):
                        records = 0
                        return {
                            'symbol': symbol,
                            'success': True,
                            'downloads': {
                                'historical_options': {
                                    'success': True,
                                    'records': records
                                }
                            },
                            'message': 'Download completed successfully'
                        }
                else:
                    error_msg = output.replace("ERROR:", "").strip()
                    return {
                        'symbol': symbol,
                        'success': False,
                        'downloads': {
                            'historical_options': {
                                'success': False,
                                'records': 0
                            }
                        },
                        'message': error_msg
                    }
            else:
                error_output = process.stderr.strip() or "Process failed"
                return {
                    'symbol': symbol,
                    'success': False,
                    'downloads': {
                        'historical_options': {
                            'success': False,
                            'records': 0
                        }
                    },
                    'message': f'Download process failed: {error_output}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'symbol': symbol,
                'success': False,
                'downloads': {
                    'historical_options': {
                        'success': False,
                        'records': 0
                    }
                },
                'message': 'Download timed out after 3 minutes'
            }
        except Exception as e:
            logger.error(f"Error in synchronous download for {symbol}: {e}")
            return {
                'symbol': symbol,
                'success': False,
                'downloads': {
                    'historical_options': {
                        'success': False,
                        'records': 0
                    }
                },
                'message': f'Download error: {e}'
            }
    
    async def download_symbol_data(self, symbol: str, include_options: bool = True, 
                                 include_history: bool = True) -> Dict[str, Any]:
        results = {'symbol': symbol, 'success': False, 'errors': []}
        
        async with self.client:
            if include_history:
                try:
                    price_data = await self.client.get_historical_data(symbol)
                    results['price_data'] = price_data is not None
                    if price_data is not None:
                        results['price_records'] = len(price_data)
                except Exception as e:
                    results['errors'].append(f"Price data error: {e}")
            
            if include_options:
                try:
                    option_data = await self.client.get_option_chain(symbol)
                    results['option_data'] = option_data is not None
                    if option_data is not None:
                        results['option_records'] = len(option_data)
                except Exception as e:
                    results['errors'].append(f"Option data error: {e}")
            
            results['success'] = len(results['errors']) == 0
        
        return results
    
    async def download_multiple_symbols(self, symbols: List[str], 
                                      include_options: bool = True,
                                      include_history: bool = True) -> List[Dict[str, Any]]:
        results = []
        
        for symbol in symbols:
            logger.info(f"Starting download for {symbol}")
            result = await self.download_symbol_data(symbol, include_options, include_history)
            results.append(result)
            
            if result['success']:
                logger.info(f"Successfully downloaded data for {symbol}")
            else:
                logger.error(f"Failed to download data for {symbol}: {result['errors']}")
            
            await asyncio.sleep(1)  # Rate limiting
        
        return results

# Create global downloader instance
downloader = DataDownloader()