import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Config(BaseSettings):
    # IB TWS Connection Settings
    ib_host: str = Field(default="127.0.0.1", env="IB_HOST")
    ib_port: int = Field(default=7497, env="IB_PORT")
    ib_client_id: int = Field(default=1, env="IB_CLIENT_ID")
    
    # Data Storage Settings
    db_path: str = Field(default="data/options_platform.db", env="DB_PATH")
    data_root: str = Field(default="data", env="DATA_ROOT")
    parquet_compression: str = Field(default="snappy", env="PARQUET_COMPRESSION")
    
    # Snapshot Collection Settings
    snapshot_interval_minutes: int = Field(default=5, env="SNAPSHOT_INTERVAL_MINUTES")
    market_start_time: str = Field(default="09:45", env="MARKET_START_TIME")
    market_end_time: str = Field(default="16:45", env="MARKET_END_TIME")
    snapshot_retention_days: int = Field(default=90, env="SNAPSHOT_RETENTION_DAYS")
    
    # Historical Archival Settings
    max_archive_days_per_request: int = Field(default=30, env="MAX_ARCHIVE_DAYS_PER_REQUEST")
    archive_expiry_months: int = Field(default=2, env="ARCHIVE_EXPIRY_MONTHS")
    archive_strike_range_percent: int = Field(default=20, env="ARCHIVE_STRIKE_RANGE_PERCENT")
    
    # System Settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    cache_expiry_hours: int = Field(default=24, env="CACHE_EXPIRY_HOURS")
    streamlit_port: int = Field(default=8501, env="STREAMLIT_PORT")
    
    @property
    def data_root_path(self) -> Path:
        return Path(self.data_root)
    
    @property
    def raw_data_path(self) -> Path:
        return self.data_root_path / "raw"
    
    @property
    def processed_data_path(self) -> Path:
        return self.data_root_path / "processed"
        
    @property
    def snapshots_data_path(self) -> Path:
        return self.data_root_path / "snapshots"
        
    @property
    def historical_data_path(self) -> Path:
        return self.data_root_path / "historical"
    
    @property
    def cache_data_path(self) -> Path:
        return self.data_root_path / "cache"
    
    def ensure_directories(self):
        for path in [self.raw_data_path, self.processed_data_path, 
                    self.snapshots_data_path, self.historical_data_path, 
                    self.cache_data_path]:
            path.mkdir(parents=True, exist_ok=True)

config = Config()