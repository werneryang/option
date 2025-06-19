import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from src.data_sources.validation import (
    OptionDataValidator, PriceDataValidator, DataCleaner, ValidationResult
)

class TestOptionDataValidator:
    
    @pytest.fixture
    def valid_option_data(self):
        return pd.DataFrame({
            'symbol': ['AAPL', 'AAPL', 'AAPL', 'AAPL'],
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
    def validator(self):
        return OptionDataValidator()
    
    def test_valid_option_data(self, validator, valid_option_data):
        result = validator.validate_option_chain(valid_option_data, 'AAPL')
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_missing_columns(self, validator):
        df = pd.DataFrame({'symbol': ['AAPL'], 'strike': [150.0]})
        result = validator.validate_option_chain(df)
        assert not result.is_valid
        assert any('Missing required columns' in error for error in result.errors)
    
    def test_negative_prices(self, validator, valid_option_data):
        valid_option_data.loc[0, 'bid'] = -1.0
        result = validator.validate_option_chain(valid_option_data)
        assert not result.is_valid
        assert any('negative bid' in error for error in result.errors)
    
    def test_invalid_bid_ask_spread(self, validator, valid_option_data):
        valid_option_data.loc[0, 'bid'] = 10.0
        valid_option_data.loc[0, 'ask'] = 5.0  # bid > ask
        result = validator.validate_option_chain(valid_option_data)
        assert any('bid > ask' in warning for warning in result.warnings)
    
    def test_invalid_option_type(self, validator, valid_option_data):
        valid_option_data.loc[0, 'option_type'] = 'X'
        result = validator.validate_option_chain(valid_option_data)
        assert not result.is_valid
        assert any('Invalid option types' in error for error in result.errors)
    
    def test_invalid_strikes(self, validator, valid_option_data):
        valid_option_data.loc[0, 'strike'] = -50.0
        result = validator.validate_option_chain(valid_option_data)
        assert not result.is_valid
        assert any('invalid strikes' in error for error in result.errors)
    
    def test_expired_options(self, validator, valid_option_data):
        valid_option_data.loc[0, 'expiration'] = date.today() - timedelta(days=1)
        result = validator.validate_option_chain(valid_option_data)
        assert any('expired options' in warning for warning in result.warnings)

class TestPriceDataValidator:
    
    @pytest.fixture
    def valid_price_data(self):
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        return pd.DataFrame({
            'date': dates,
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [105.0, 106.0, 107.0, 108.0, 109.0],
            'low': [95.0, 96.0, 97.0, 98.0, 99.0],
            'close': [102.0, 103.0, 104.0, 105.0, 106.0],
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000],
            'symbol': ['AAPL'] * 5
        })
    
    @pytest.fixture
    def validator(self):
        return PriceDataValidator()
    
    def test_valid_price_data(self, validator, valid_price_data):
        result = validator.validate_price_data(valid_price_data, 'AAPL')
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_missing_columns(self, validator):
        df = pd.DataFrame({'date': [date.today()], 'close': [100.0]})
        result = validator.validate_price_data(df)
        assert not result.is_valid
        assert any('Missing required columns' in error for error in result.errors)
    
    def test_high_low_relationship(self, validator, valid_price_data):
        valid_price_data.loc[0, 'high'] = 90.0  # high < low
        valid_price_data.loc[0, 'low'] = 95.0
        result = validator.validate_price_data(valid_price_data)
        assert not result.is_valid
        assert any('high < low' in error for error in result.errors)
    
    def test_open_outside_range(self, validator, valid_price_data):
        valid_price_data.loc[0, 'open'] = 110.0  # open > high
        result = validator.validate_price_data(valid_price_data)
        assert not result.is_valid
        assert any('open outside high/low range' in error for error in result.errors)
    
    def test_negative_prices(self, validator, valid_price_data):
        valid_price_data.loc[0, 'close'] = -10.0
        result = validator.validate_price_data(valid_price_data)
        assert not result.is_valid
        assert any('non-positive close' in error for error in result.errors)
    
    def test_duplicate_dates(self, validator, valid_price_data):
        valid_price_data.loc[1, 'date'] = valid_price_data.loc[0, 'date']
        result = validator.validate_price_data(valid_price_data)
        assert any('duplicate dates' in warning for warning in result.warnings)

class TestDataCleaner:
    
    @pytest.fixture
    def cleaner(self):
        return DataCleaner()
    
    @pytest.fixture
    def dirty_option_data(self):
        return pd.DataFrame({
            'symbol': ['AAPL', 'AAPL', 'AAPL', 'AAPL'],
            'expiration': [date.today() + timedelta(days=30)] * 4,
            'strike': [150.0, 155.0, -10.0, 160.0],  # negative strike
            'option_type': ['C', 'CALL', 'P', 'X'],  # mixed formats, invalid type
            'bid': [5.0, 2.5, -1.0, 4.5],  # negative bid
            'ask': [5.2, 2.7, 3.2, 4.7],
            'last': [5.1, 2.6, 3.1, 4.6],
            'volume': [100, 50, 75, 25],
            'timestamp': [datetime.now()] * 4
        })
    
    def test_clean_option_data(self, cleaner, dirty_option_data):
        cleaned_df, result = cleaner.clean_option_data(dirty_option_data, 'AAPL')
        
        # Should remove records with negative strike and invalid option type
        assert len(cleaned_df) < len(dirty_option_data)
        
        # Should standardize option types
        assert all(opt_type in ['C', 'P'] for opt_type in cleaned_df['option_type'])
        
        # Should have removed negative prices
        assert all(cleaned_df['bid'] >= 0)
        
        # Should have some warnings about fixed records
        assert result.fixed_records > 0
    
    def test_clean_price_data_removes_duplicates(self, cleaner):
        df = pd.DataFrame({
            'date': [date.today(), date.today(), date.today() + timedelta(days=1)],
            'open': [100.0, 101.0, 102.0],
            'high': [105.0, 106.0, 107.0],
            'low': [95.0, 96.0, 97.0],
            'close': [102.0, 103.0, 104.0],
            'volume': [1000000, 1100000, 1200000],
            'symbol': ['AAPL'] * 3
        })
        
        cleaned_df, result = cleaner.clean_price_data(df, 'AAPL')
        
        # Should remove duplicate dates
        assert len(cleaned_df) == 2  # One duplicate removed
        assert result.fixed_records > 0
    
    def test_empty_dataframe_handling(self, cleaner):
        empty_df = pd.DataFrame()
        cleaned_df, result = cleaner.clean_option_data(empty_df)
        
        assert not result.is_valid
        assert "Empty DataFrame" in result.errors
        assert cleaned_df.empty

class TestValidationResult:
    
    def test_validation_result_creation(self):
        result = ValidationResult(True, [], [])
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert result.fixed_records == 0
    
    def test_add_error_sets_invalid(self):
        result = ValidationResult(True, [], [])
        result.add_error("Test error")
        
        assert not result.is_valid
        assert "Test error" in result.errors
    
    def test_add_warning_keeps_valid(self):
        result = ValidationResult(True, [], [])
        result.add_warning("Test warning")
        
        assert result.is_valid  # Should still be valid
        assert "Test warning" in result.warnings