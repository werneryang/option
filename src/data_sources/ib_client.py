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
        
        self.ib = IB()
        self.connected = False
    
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
            ticker = self.ib.reqMktData(contract)
            await asyncio.sleep(2)  # Wait for market data
            
            if ticker.last and ticker.last > 0:
                price_data = {
                    'symbol': symbol,
                    'price': float(ticker.last),
                    'bid': float(ticker.bid) if ticker.bid else None,
                    'ask': float(ticker.ask) if ticker.ask else None,
                    'timestamp': datetime.now()
                }
                logger.info(f"Retrieved stock price for {symbol}: ${ticker.last}")
                return price_data
            else:
                logger.warning(f"No valid price data for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting stock price for {symbol}: {e}")
            return None
        finally:
            self.ib.cancelMktData(contract)
    
    async def get_option_chain(self, symbol: str, expiration_date: date = None) -> Optional[pd.DataFrame]:
        if not self.connected:
            logger.error("Not connected to IB TWS")
            return None
        
        download_id = db_manager.log_download(symbol, "options", "pending")
        
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
            
            option_data = []
            
            for expiration in expirations:
                strikes = sorted(chain.strikes)
                
                for strike in strikes:
                    for right in ['C', 'P']:  # Call and Put
                        option = Option(symbol, expiration, strike, right, 'SMART')
                        try:
                            qualified_options = await self.ib.qualifyContractsAsync(option)
                            if qualified_options:
                                option_contract = qualified_options[0]
                                ticker = self.ib.reqMktData(option_contract)
                                await asyncio.sleep(0.1)  # Brief pause to get data
                                
                                option_info = {
                                    'symbol': symbol,
                                    'expiration': expiration,
                                    'strike': strike,
                                    'option_type': right,
                                    'bid': float(ticker.bid) if ticker.bid else 0,
                                    'ask': float(ticker.ask) if ticker.ask else 0,
                                    'last': float(ticker.last) if ticker.last else 0,
                                    'volume': int(ticker.volume) if ticker.volume else 0,
                                    'open_interest': getattr(ticker, 'openInterest', 0),
                                    'implied_volatility': getattr(ticker, 'impliedVolatility', 0),
                                    'delta': getattr(ticker, 'delta', 0),
                                    'gamma': getattr(ticker, 'gamma', 0),
                                    'theta': getattr(ticker, 'theta', 0),
                                    'vega': getattr(ticker, 'vega', 0),
                                    'timestamp': datetime.now()
                                }
                                option_data.append(option_info)
                                self.ib.cancelMktData(option_contract)
                                
                        except Exception as e:
                            logger.warning(f"Failed to get data for {symbol} {expiration} {strike} {right}: {e}")
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
                
                logger.info(f"Successfully downloaded option chain for {symbol}: {len(df)} contracts")
                return df
            else:
                error_msg = f"No option data retrieved for {symbol}"
                logger.error(error_msg)
                db_manager.update_download_status(download_id, "failed", error_message=error_msg)
                return None
                
        except Exception as e:
            error_msg = f"Error downloading option chain for {symbol}: {e}"
            logger.error(error_msg)
            db_manager.update_download_status(download_id, "failed", error_message=error_msg)
            return None
    
    async def get_historical_option_data(self, symbol: str, duration: str = "1 M", 
                                       bar_size: str = "1 hour") -> Optional[pd.DataFrame]:
        """Download historical option data with intraday snapshots including 16:00 close"""
        if not self.connected:
            logger.error("Not connected to IB TWS")
            return None
        
        download_id = db_manager.log_download(symbol, "historical_options", "pending")
        
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
            
            # Filter expirations to within 1 year
            current_date = datetime.now().date()
            one_year_later = current_date + timedelta(days=365)
            
            all_expirations = sorted(chain.expirations)
            expirations = []
            for exp_str in all_expirations:
                exp_date = datetime.strptime(exp_str, '%Y%m%d').date()
                if current_date <= exp_date <= one_year_later:
                    expirations.append(exp_str)
            
            strikes = sorted(chain.strikes)
            
            # Expand to strikes within 20% of current price
            current_price = await self.get_stock_price(symbol)
            if current_price:
                price = current_price['price']
                # Get strikes within 20% of current price
                expanded_strikes = [s for s in strikes if abs(s - price) / price <= 0.20]
                strikes = sorted(expanded_strikes)
            else:
                # If can't get current price, use a reasonable range around middle strikes
                mid_idx = len(strikes) // 2
                start_idx = max(0, mid_idx - 20)
                end_idx = min(len(strikes), mid_idx + 21)
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
                                
                                # Request historical data with hourly bars
                                bars = await self.ib.reqHistoricalDataAsync(
                                    option_contract,
                                    endDateTime='',
                                    durationStr=duration,
                                    barSizeSetting=bar_size,
                                    whatToShow='TRADES',
                                    useRTH=True,  # Regular trading hours
                                    formatDate=1
                                )
                                
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
        
        download_id = db_manager.log_download(symbol, "stock_price", "pending")
        
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

downloader = DataDownloader()