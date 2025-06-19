import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    fixed_records: int = 0
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)

class OptionDataValidator:
    def __init__(self):
        self.required_columns = [
            'symbol', 'expiration', 'strike', 'option_type', 
            'bid', 'ask', 'last', 'volume', 'timestamp'
        ]
        self.numeric_columns = ['strike', 'bid', 'ask', 'last', 'volume']
        self.greek_columns = ['delta', 'gamma', 'theta', 'vega', 'implied_volatility']
    
    def validate_option_chain(self, df: pd.DataFrame, symbol: str = None) -> ValidationResult:
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if df is None or df.empty:
            result.add_error("DataFrame is None or empty")
            return result
        
        self._validate_columns(df, result)
        if not result.is_valid:
            return result
        
        self._validate_data_types(df, result)
        self._validate_option_basics(df, result, symbol)
        self._validate_prices(df, result)
        self._validate_greeks(df, result)
        self._validate_expiration_dates(df, result)
        
        return result
    
    def _validate_columns(self, df: pd.DataFrame, result: ValidationResult):
        missing_cols = [col for col in self.required_columns if col not in df.columns]
        if missing_cols:
            result.add_error(f"Missing required columns: {missing_cols}")
        
        extra_cols = [col for col in df.columns if col not in self.required_columns + self.greek_columns + ['open_interest']]
        if extra_cols:
            result.add_warning(f"Unexpected columns found: {extra_cols}")
    
    def _validate_data_types(self, df: pd.DataFrame, result: ValidationResult):
        for col in self.numeric_columns:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        result.add_warning(f"Converted {col} to numeric type")
                    except Exception:
                        result.add_error(f"Cannot convert {col} to numeric type")
        
        if 'expiration' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['expiration']):
                try:
                    df['expiration'] = pd.to_datetime(df['expiration'])
                    result.add_warning("Converted expiration to datetime")
                except Exception:
                    result.add_error("Cannot convert expiration to datetime")
        
        if 'option_type' in df.columns:
            valid_types = {'C', 'P', 'CALL', 'PUT'}
            invalid_types = set(df['option_type'].unique()) - valid_types
            if invalid_types:
                result.add_error(f"Invalid option types found: {invalid_types}")
    
    def _validate_option_basics(self, df: pd.DataFrame, result: ValidationResult, symbol: str = None):
        if symbol and 'symbol' in df.columns:
            wrong_symbols = df[df['symbol'] != symbol]
            if not wrong_symbols.empty:
                result.add_error(f"Found {len(wrong_symbols)} records with wrong symbol")
        
        if 'strike' in df.columns:
            invalid_strikes = df[(df['strike'] <= 0) | (df['strike'].isna())]
            if not invalid_strikes.empty:
                result.add_error(f"Found {len(invalid_strikes)} records with invalid strikes")
        
        if 'option_type' in df.columns:
            null_types = df[df['option_type'].isna()]
            if not null_types.empty:
                result.add_error(f"Found {len(null_types)} records with null option types")
    
    def _validate_prices(self, df: pd.DataFrame, result: ValidationResult):
        price_cols = ['bid', 'ask', 'last']
        
        for col in price_cols:
            if col in df.columns:
                negative_prices = df[df[col] < 0]
                if not negative_prices.empty:
                    result.add_error(f"Found {len(negative_prices)} records with negative {col}")
        
        if 'bid' in df.columns and 'ask' in df.columns:
            invalid_spread = df[df['bid'] > df['ask']]
            if not invalid_spread.empty:
                result.add_warning(f"Found {len(invalid_spread)} records with bid > ask")
        
        if 'volume' in df.columns:
            negative_volume = df[df['volume'] < 0]
            if not negative_volume.empty:
                result.add_error(f"Found {len(negative_volume)} records with negative volume")
    
    def _validate_greeks(self, df: pd.DataFrame, result: ValidationResult):
        if 'delta' in df.columns:
            invalid_delta = df[(df['delta'] < -1) | (df['delta'] > 1)]
            if not invalid_delta.empty:
                result.add_warning(f"Found {len(invalid_delta)} records with delta outside [-1, 1]")
        
        if 'gamma' in df.columns:
            negative_gamma = df[df['gamma'] < 0]
            if not negative_gamma.empty:
                result.add_warning(f"Found {len(negative_gamma)} records with negative gamma")
        
        if 'implied_volatility' in df.columns:
            invalid_iv = df[(df['implied_volatility'] < 0) | (df['implied_volatility'] > 10)]
            if not invalid_iv.empty:
                result.add_warning(f"Found {len(invalid_iv)} records with suspicious IV values")
    
    def _validate_expiration_dates(self, df: pd.DataFrame, result: ValidationResult):
        if 'expiration' in df.columns:
            today = pd.Timestamp.now().normalize()
            expired_options = df[pd.to_datetime(df['expiration']) < today]
            if not expired_options.empty:
                result.add_warning(f"Found {len(expired_options)} expired options")
            
            far_future = today + pd.Timedelta(days=1095)  # 3 years
            far_options = df[pd.to_datetime(df['expiration']) > far_future]
            if not far_options.empty:
                result.add_warning(f"Found {len(far_options)} options expiring more than 3 years out")

class PriceDataValidator:
    def __init__(self):
        self.required_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']
        self.price_columns = ['open', 'high', 'low', 'close']
    
    def validate_price_data(self, df: pd.DataFrame, symbol: str = None) -> ValidationResult:
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if df is None or df.empty:
            result.add_error("DataFrame is None or empty")
            return result
        
        self._validate_columns(df, result)
        if not result.is_valid:
            return result
        
        self._validate_data_types(df, result)
        self._validate_price_relationships(df, result)
        self._validate_dates(df, result)
        self._validate_symbol(df, result, symbol)
        
        return result
    
    def _validate_columns(self, df: pd.DataFrame, result: ValidationResult):
        missing_cols = [col for col in self.required_columns if col not in df.columns]
        if missing_cols:
            result.add_error(f"Missing required columns: {missing_cols}")
    
    def _validate_data_types(self, df: pd.DataFrame, result: ValidationResult):
        for col in self.price_columns + ['volume']:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        result.add_warning(f"Converted {col} to numeric type")
                    except Exception:
                        result.add_error(f"Cannot convert {col} to numeric type")
        
        if 'date' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['date']):
                try:
                    df['date'] = pd.to_datetime(df['date'])
                    result.add_warning("Converted date to datetime")
                except Exception:
                    result.add_error("Cannot convert date to datetime")
    
    def _validate_price_relationships(self, df: pd.DataFrame, result: ValidationResult):
        price_cols = self.price_columns
        
        for col in price_cols:
            if col in df.columns:
                negative_prices = df[df[col] <= 0]
                if not negative_prices.empty:
                    result.add_error(f"Found {len(negative_prices)} records with non-positive {col}")
        
        if all(col in df.columns for col in ['high', 'low']):
            invalid_range = df[df['high'] < df['low']]
            if not invalid_range.empty:
                result.add_error(f"Found {len(invalid_range)} records with high < low")
        
        if all(col in df.columns for col in ['open', 'high', 'low']):
            invalid_open = df[(df['open'] > df['high']) | (df['open'] < df['low'])]
            if not invalid_open.empty:
                result.add_error(f"Found {len(invalid_open)} records with open outside high/low range")
        
        if all(col in df.columns for col in ['close', 'high', 'low']):
            invalid_close = df[(df['close'] > df['high']) | (df['close'] < df['low'])]
            if not invalid_close.empty:
                result.add_error(f"Found {len(invalid_close)} records with close outside high/low range")
        
        if 'volume' in df.columns:
            negative_volume = df[df['volume'] < 0]
            if not negative_volume.empty:
                result.add_error(f"Found {len(negative_volume)} records with negative volume")
    
    def _validate_dates(self, df: pd.DataFrame, result: ValidationResult):
        if 'date' in df.columns:
            duplicate_dates = df[df.duplicated(subset=['date'], keep=False)]
            if not duplicate_dates.empty:
                result.add_warning(f"Found {len(duplicate_dates)} records with duplicate dates")
            
            future_dates = df[pd.to_datetime(df['date']) > pd.Timestamp.now()]
            if not future_dates.empty:
                result.add_warning(f"Found {len(future_dates)} records with future dates")
    
    def _validate_symbol(self, df: pd.DataFrame, result: ValidationResult, symbol: str = None):
        if symbol and 'symbol' in df.columns:
            wrong_symbols = df[df['symbol'] != symbol]
            if not wrong_symbols.empty:
                result.add_error(f"Found {len(wrong_symbols)} records with wrong symbol")

class DataCleaner:
    def __init__(self):
        self.option_validator = OptionDataValidator()
        self.price_validator = PriceDataValidator()
    
    def clean_option_data(self, df: pd.DataFrame, symbol: str = None) -> Tuple[pd.DataFrame, ValidationResult]:
        if df is None or df.empty:
            return df, ValidationResult(False, ["Empty DataFrame"], [])
        
        df_clean = df.copy()
        result = ValidationResult(True, [], [])
        
        df_clean = self._standardize_option_types(df_clean, result)
        df_clean = self._clean_prices(df_clean, result)
        df_clean = self._remove_invalid_records(df_clean, result)
        
        validation_result = self.option_validator.validate_option_chain(df_clean, symbol)
        result.errors.extend(validation_result.errors)
        result.warnings.extend(validation_result.warnings)
        result.is_valid = validation_result.is_valid
        
        return df_clean, result
    
    def clean_price_data(self, df: pd.DataFrame, symbol: str = None) -> Tuple[pd.DataFrame, ValidationResult]:
        if df is None or df.empty:
            return df, ValidationResult(False, ["Empty DataFrame"], [])
        
        df_clean = df.copy()
        result = ValidationResult(True, [], [])
        
        df_clean = self._remove_duplicate_dates(df_clean, result)
        df_clean = self._clean_prices(df_clean, result)
        df_clean = self._sort_by_date(df_clean, result)
        
        validation_result = self.price_validator.validate_price_data(df_clean, symbol)
        result.errors.extend(validation_result.errors)
        result.warnings.extend(validation_result.warnings)
        result.is_valid = validation_result.is_valid
        
        return df_clean, result
    
    def _standardize_option_types(self, df: pd.DataFrame, result: ValidationResult) -> pd.DataFrame:
        if 'option_type' in df.columns:
            original_count = len(df)
            df['option_type'] = df['option_type'].str.upper()
            df['option_type'] = df['option_type'].replace({'CALL': 'C', 'PUT': 'P'})
            
            valid_types = df['option_type'].isin(['C', 'P'])
            df = df[valid_types]
            
            removed_count = original_count - len(df)
            if removed_count > 0:
                result.add_warning(f"Removed {removed_count} records with invalid option types")
                result.fixed_records += removed_count
        
        return df
    
    def _clean_prices(self, df: pd.DataFrame, result: ValidationResult) -> pd.DataFrame:
        price_cols = ['bid', 'ask', 'last', 'open', 'high', 'low', 'close']
        
        for col in price_cols:
            if col in df.columns:
                original_count = len(df)
                df = df[df[col] >= 0]  # Remove negative prices
                
                removed_count = original_count - len(df)
                if removed_count > 0:
                    result.add_warning(f"Removed {removed_count} records with negative {col}")
                    result.fixed_records += removed_count
        
        return df
    
    def _remove_invalid_records(self, df: pd.DataFrame, result: ValidationResult) -> pd.DataFrame:
        original_count = len(df)
        
        if 'strike' in df.columns:
            df = df[df['strike'] > 0]
        
        if 'expiration' in df.columns:
            today = pd.Timestamp.now().normalize()
            df = df[pd.to_datetime(df['expiration']) >= today]
        
        removed_count = original_count - len(df)
        if removed_count > 0:
            result.add_warning(f"Removed {removed_count} invalid records")
            result.fixed_records += removed_count
        
        return df
    
    def _remove_duplicate_dates(self, df: pd.DataFrame, result: ValidationResult) -> pd.DataFrame:
        if 'date' in df.columns:
            original_count = len(df)
            df = df.drop_duplicates(subset=['date'], keep='last')
            
            removed_count = original_count - len(df)
            if removed_count > 0:
                result.add_warning(f"Removed {removed_count} duplicate date records")
                result.fixed_records += removed_count
        
        return df
    
    def _sort_by_date(self, df: pd.DataFrame, result: ValidationResult) -> pd.DataFrame:
        if 'date' in df.columns:
            df = df.sort_values('date')
            result.add_warning("Sorted data by date")
        
        return df

option_validator = OptionDataValidator()
price_validator = PriceDataValidator()
data_cleaner = DataCleaner()