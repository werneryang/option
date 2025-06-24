"""
Trading calendar utilities for checking trading days and market hours
"""
from datetime import datetime, date, time, timedelta
from typing import List, Optional
import holidays


class TradingCalendar:
    """US Stock Market Trading Calendar"""
    
    def __init__(self):
        # US stock market holidays
        self.us_holidays = holidays.US()
        
        # Market open/close times (Eastern Time)
        self.market_open = time(9, 30)  # 9:30 AM ET
        self.market_close = time(16, 0)  # 4:00 PM ET
        
    def is_trading_day(self, check_date: date) -> bool:
        """
        Check if a given date is a trading day
        
        Args:
            check_date: Date to check
            
        Returns:
            True if it's a trading day, False otherwise
        """
        # Check if it's a weekend
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
            
        # Check if it's a holiday
        if check_date in self.us_holidays:
            return False
            
        return True
    
    def get_last_trading_day(self, reference_date: date = None) -> date:
        """
        Get the last trading day before or on the reference date
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            Last trading day
        """
        if reference_date is None:
            reference_date = date.today()
            
        current_date = reference_date
        
        while not self.is_trading_day(current_date):
            current_date -= timedelta(days=1)
            
        return current_date
    
    def get_next_trading_day(self, reference_date: date = None) -> date:
        """
        Get the next trading day after the reference date
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            Next trading day
        """
        if reference_date is None:
            reference_date = date.today()
            
        current_date = reference_date + timedelta(days=1)
        
        while not self.is_trading_day(current_date):
            current_date += timedelta(days=1)
            
        return current_date
    
    def is_market_hours(self, check_time: datetime = None) -> bool:
        """
        Check if current time is during market hours (9:30 AM - 4:00 PM ET)
        
        Args:
            check_time: Time to check (defaults to now)
            
        Returns:
            True if during market hours, False otherwise
        """
        if check_time is None:
            check_time = datetime.now()
            
        # Convert to time only for comparison
        current_time = check_time.time()
        
        return self.market_open <= current_time <= self.market_close
    
    def is_before_market_close_cutoff(self, check_time: datetime = None, 
                                    cutoff_time: time = time(16, 30)) -> bool:
        """
        Check if current time is before the market close cutoff (default 4:30 PM)
        
        Args:
            check_time: Time to check (defaults to now)
            cutoff_time: Cutoff time (defaults to 4:30 PM)
            
        Returns:
            True if before cutoff, False otherwise
        """
        if check_time is None:
            check_time = datetime.now()
            
        current_time = check_time.time()
        return current_time < cutoff_time
    
    def should_check_previous_trading_day(self, check_time: datetime = None) -> bool:
        """
        Determine if we should check for previous trading day data
        
        Logic:
        - If current time is before 4:30 PM on a trading day, check previous trading day
        - If current time is after 4:30 PM on a trading day, check current trading day
        - If current time is on a non-trading day, check last trading day
        
        Args:
            check_time: Time to check (defaults to now)
            
        Returns:
            True if should check previous trading day, False if should check current/last trading day
        """
        if check_time is None:
            check_time = datetime.now()
            
        current_date = check_time.date()
        
        # If today is not a trading day, we should check the last trading day
        if not self.is_trading_day(current_date):
            return False  # Should check last trading day (not previous)
        
        # If today is a trading day, check the time
        if self.is_before_market_close_cutoff(check_time):
            return True  # Check previous trading day
        else:
            return False  # Check current trading day
    
    def get_expected_last_data_date(self, check_time: datetime = None) -> date:
        """
        Get the expected date for the most recent data
        
        Args:
            check_time: Time to check (defaults to now)
            
        Returns:
            Expected date for most recent data
        """
        if check_time is None:
            check_time = datetime.now()
            
        current_date = check_time.date()
        
        if self.should_check_previous_trading_day(check_time):
            # Need previous trading day data
            if self.is_trading_day(current_date):
                # Get the trading day before today
                previous_date = current_date - timedelta(days=1)
                return self.get_last_trading_day(previous_date)
            else:
                # If today is not trading day, get last trading day
                return self.get_last_trading_day(current_date)
        else:
            # Need current/last trading day data
            return self.get_last_trading_day(current_date)


# Global instance
trading_calendar = TradingCalendar()