import pytest
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from datetime import date, datetime, timedelta

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from src.data_sources.storage import ParquetStorage

class TestParquetStorage:
    
    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        storage = ParquetStorage(base_path=temp_dir)
        yield storage
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_option_data(self):
        return pd.DataFrame({
            'symbol': ['AAPL'] * 4,
            'expiration': [date.today() + timedelta(days=30)] * 4,
            'strike': [150.0, 155.0, 150.0, 155.0],
            'option_type': ['C', 'C', 'P', 'P'],
            'bid': [5.0, 2.5, 3.0, 4.5],
            'ask': [5.2, 2.7, 3.2, 4.7],
            'last': [5.1, 2.6, 3.1, 4.6],
            'volume': [100, 50, 75, 25],
            'timestamp': [datetime.now()] * 4
        })
    
    @pytest.fixture
    def sample_price_data(self):
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        return pd.DataFrame({
            'date': [d.date() for d in dates],
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [105.0, 106.0, 107.0, 108.0, 109.0],
            'low': [95.0, 96.0, 97.0, 98.0, 99.0],
            'close': [102.0, 103.0, 104.0, 105.0, 106.0],
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000],
            'symbol': ['AAPL'] * 5
        })
    
    def test_save_and_load_option_chain(self, temp_storage, sample_option_data):
        symbol = 'AAPL'
        test_date = date.today()
        
        # Save option chain
        file_path = temp_storage.save_option_chain(symbol, test_date, sample_option_data)
        assert file_path.exists()
        
        # Load option chain
        loaded_data = temp_storage.load_option_chain(symbol, test_date)
        assert loaded_data is not None
        assert len(loaded_data) == len(sample_option_data)
        assert loaded_data['symbol'].iloc[0] == symbol
    
    def test_load_nonexistent_option_chain(self, temp_storage):
        loaded_data = temp_storage.load_option_chain('NONEXISTENT', date.today())
        assert loaded_data is None
    
    def test_save_and_load_price_history(self, temp_storage, sample_price_data):
        symbol = 'AAPL'
        
        # Save price history
        file_path = temp_storage.save_price_history(symbol, sample_price_data)
        assert file_path.exists()
        
        # Load price history
        loaded_data = temp_storage.load_price_history(symbol)
        assert loaded_data is not None
        assert len(loaded_data) == len(sample_price_data)
        assert loaded_data['symbol'].iloc[0] == symbol
    
    def test_price_history_date_filtering(self, temp_storage, sample_price_data):
        symbol = 'AAPL'
        temp_storage.save_price_history(symbol, sample_price_data)
        
        # Load with date filter
        start_date = date(2023, 1, 2)
        end_date = date(2023, 1, 4)
        
        filtered_data = temp_storage.load_price_history(symbol, start_date, end_date)
        assert filtered_data is not None
        assert len(filtered_data) == 3  # 3 days in range
        assert all(start_date <= d <= end_date for d in filtered_data['date'])
    
    def test_price_history_append(self, temp_storage, sample_price_data):
        symbol = 'AAPL'
        
        # Save initial data
        temp_storage.save_price_history(symbol, sample_price_data)
        
        # Create new data with some overlap
        new_dates = pd.date_range(start='2023-01-04', periods=3, freq='D')
        new_data = pd.DataFrame({
            'date': [d.date() for d in new_dates],
            'open': [104.0, 105.0, 106.0],
            'high': [109.0, 110.0, 111.0],
            'low': [99.0, 100.0, 101.0],
            'close': [106.0, 107.0, 108.0],
            'volume': [1500000, 1600000, 1700000],
            'symbol': ['AAPL'] * 3
        })
        
        # Save new data (should merge)
        temp_storage.save_price_history(symbol, new_data)
        
        # Load all data
        all_data = temp_storage.load_price_history(symbol)
        assert len(all_data) == 6  # 5 + 3 - 2 overlaps (Jan 4 & 5) = 6
        
        # Should be sorted by date
        dates = pd.to_datetime(all_data['date'])
        assert dates.is_monotonic_increasing
    
    def test_analytics_cache(self, temp_storage):
        symbol = 'AAPL'
        analysis_type = 'greeks'
        
        cache_data = pd.DataFrame({
            'strike': [150.0, 155.0],
            'delta': [0.6, 0.4],
            'gamma': [0.02, 0.015],
            'theta': [-0.05, -0.03]
        })
        
        # Save to cache
        file_path = temp_storage.save_analytics_cache(symbol, analysis_type, cache_data)
        assert file_path.exists()
        
        # Load from cache
        loaded_cache = temp_storage.load_analytics_cache(symbol, analysis_type)
        assert loaded_cache is not None
        assert len(loaded_cache) == len(cache_data)
        assert 'delta' in loaded_cache.columns
    
    def test_cache_expiry(self, temp_storage):
        symbol = 'AAPL'
        analysis_type = 'test_expiry'
        
        cache_data = pd.DataFrame({'test': [1, 2, 3]})
        temp_storage.save_analytics_cache(symbol, analysis_type, cache_data)
        
        # Should load when within expiry time
        loaded = temp_storage.load_analytics_cache(symbol, analysis_type, max_age_hours=1)
        assert loaded is not None
        
        # Should return None when cache is "expired" (using 0 hours)
        expired = temp_storage.load_analytics_cache(symbol, analysis_type, max_age_hours=0)
        assert expired is None
    
    def test_get_available_dates(self, temp_storage, sample_option_data):
        symbol = 'AAPL'
        
        # Save option chains for multiple dates
        dates = [date.today(), date.today() + timedelta(days=1)]
        for test_date in dates:
            temp_storage.save_option_chain(symbol, test_date, sample_option_data)
        
        available_dates = temp_storage.get_available_dates(symbol)
        assert len(available_dates) == 2
        assert all(d in available_dates for d in dates)
        assert available_dates == sorted(available_dates)  # Should be sorted
    
    def test_get_symbols_with_data(self, temp_storage, sample_option_data):
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        for symbol in symbols:
            temp_storage.save_option_chain(symbol, date.today(), sample_option_data)
        
        symbols_with_data = temp_storage.get_symbols_with_data()
        assert len(symbols_with_data) == 3
        assert all(s in symbols_with_data for s in symbols)
        assert symbols_with_data == sorted(symbols_with_data)  # Should be sorted
    
    def test_get_storage_stats(self, temp_storage, sample_option_data, sample_price_data):
        # Save some data
        temp_storage.save_option_chain('AAPL', date.today(), sample_option_data)
        temp_storage.save_price_history('AAPL', sample_price_data)
        temp_storage.save_option_chain('MSFT', date.today(), sample_option_data)
        
        stats = temp_storage.get_storage_stats()
        
        assert stats['total_symbols'] == 2
        assert stats['total_files'] > 0
        assert stats['total_size_mb'] > 0
        assert 'AAPL' in stats['symbols']
        assert 'MSFT' in stats['symbols']
        
        # Check symbol-specific stats
        aapl_stats = stats['symbols']['AAPL']
        assert aapl_stats['files'] == 2  # option chain + price history
        assert len(aapl_stats['available_dates']) == 1
    
    def test_empty_storage_stats(self, temp_storage):
        stats = temp_storage.get_storage_stats()
        
        assert stats['total_symbols'] == 0
        assert stats['total_files'] == 0
        assert stats['total_size_mb'] == 0
        assert len(stats['symbols']) == 0
    
    def test_path_methods(self, temp_storage):
        symbol = 'AAPL'
        date_str = '2023-01-01'
        analysis_type = 'greeks'
        
        options_path = temp_storage._get_options_path(symbol, date_str)
        prices_path = temp_storage._get_prices_path(symbol)
        cache_path = temp_storage._get_cache_path(symbol, analysis_type)
        
        # Check path structure
        assert symbol in str(options_path)
        assert date_str in str(options_path)
        assert 'options.parquet' in str(options_path)
        
        assert symbol in str(prices_path)
        assert 'prices.parquet' in str(prices_path)
        
        assert symbol in str(cache_path)
        assert analysis_type in str(cache_path)
        assert 'results.parquet' in str(cache_path)