import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Config(BaseSettings):
    ib_host: str = Field(default="127.0.0.1", env="IB_HOST")
    ib_port: int = Field(default=7497, env="IB_PORT")
    ib_client_id: int = Field(default=1, env="IB_CLIENT_ID")
    
    db_path: str = Field(default="data/options_platform.db", env="DB_PATH")
    data_root: str = Field(default="data", env="DATA_ROOT")
    parquet_compression: str = Field(default="snappy", env="PARQUET_COMPRESSION")
    
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
    def cache_data_path(self) -> Path:
        return self.data_root_path / "cache"
    
    def ensure_directories(self):
        for path in [self.raw_data_path, self.processed_data_path, self.cache_data_path]:
            path.mkdir(parents=True, exist_ok=True)

config = Config()