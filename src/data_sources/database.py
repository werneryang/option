from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from pathlib import Path

from ..utils.config import config

Base = declarative_base()

class Symbol(Base):
    __tablename__ = "symbols"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    company_name = Column(String(255))
    sector = Column(String(100))
    market_cap = Column(Float)
    last_updated = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)

class DataDownload(Base):
    __tablename__ = "data_downloads"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    download_date = Column(DateTime, nullable=False, index=True)
    data_type = Column(String(50), nullable=False)  # 'options', 'stock_price', etc.
    status = Column(String(20), nullable=False)  # 'pending', 'completed', 'failed'
    records_count = Column(Integer)
    file_path = Column(String(500))
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)

class Strategy(Base):
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    strategy_type = Column(String(50), nullable=False)  # 'straddle', 'strangle', etc.
    configuration = Column(Text)  # JSON string of strategy parameters
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        self.create_tables()
    
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    def add_symbol(self, symbol: str, company_name: str = None, sector: str = None, market_cap: float = None) -> Symbol:
        with self.get_session() as session:
            existing = session.query(Symbol).filter(Symbol.symbol == symbol).first()
            if existing:
                return existing
            
            new_symbol = Symbol(
                symbol=symbol,
                company_name=company_name,
                sector=sector,
                market_cap=market_cap
            )
            session.add(new_symbol)
            session.commit()
            session.refresh(new_symbol)
            return new_symbol
    
    def get_symbols(self, active_only: bool = True) -> List[Symbol]:
        with self.get_session() as session:
            query = session.query(Symbol)
            if active_only:
                query = query.filter(Symbol.is_active == True)
            return query.all()
    
    def get_symbol(self, symbol: str) -> Optional[Symbol]:
        """Get a specific symbol from the database"""
        with self.get_session() as session:
            return session.query(Symbol).filter(Symbol.symbol == symbol).first()
    
    def log_download(self, symbol: str, data_type: str, status: str = "pending", 
                    records_count: int = None, file_path: str = None, 
                    error_message: str = None) -> DataDownload:
        with self.get_session() as session:
            download = DataDownload(
                symbol=symbol,
                download_date=datetime.now(),
                data_type=data_type,
                status=status,
                records_count=records_count,
                file_path=file_path,
                error_message=error_message
            )
            session.add(download)
            session.commit()
            session.refresh(download)
            return download
    
    def update_download_status(self, download_id: int, status: str, 
                              records_count: int = None, file_path: str = None,
                              error_message: str = None):
        with self.get_session() as session:
            download = session.query(DataDownload).filter(DataDownload.id == download_id).first()
            if download:
                download.status = status
                download.completed_at = datetime.now()
                if records_count is not None:
                    download.records_count = records_count
                if file_path:
                    download.file_path = file_path
                if error_message:
                    download.error_message = error_message
                session.commit()
    
    def get_recent_downloads(self, symbol: str = None, days: int = 7) -> List[DataDownload]:
        with self.get_session() as session:
            query = session.query(DataDownload)
            if symbol:
                query = query.filter(DataDownload.symbol == symbol)
            
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            return query.filter(DataDownload.download_date >= cutoff_date).order_by(
                DataDownload.download_date.desc()
            ).all()

db_manager = DatabaseManager()