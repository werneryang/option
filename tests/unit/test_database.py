import pytest
import tempfile
import os
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from src.data_sources.database import DatabaseManager, Symbol, DataDownload, Strategy

class TestDatabaseManager:
    
    @pytest.fixture
    def temp_db(self):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        db_manager = DatabaseManager(temp_file.name)
        yield db_manager
        
        # Cleanup
        os.unlink(temp_file.name)
    
    def test_database_creation(self, temp_db):
        # Database should be created and tables should exist
        with temp_db.get_session() as session:
            # Try to query each table - should not raise errors
            symbols = session.query(Symbol).all()
            downloads = session.query(DataDownload).all()
            strategies = session.query(Strategy).all()
            
            assert isinstance(symbols, list)
            assert isinstance(downloads, list)
            assert isinstance(strategies, list)
    
    def test_add_symbol(self, temp_db):
        symbol = temp_db.add_symbol('AAPL', 'Apple Inc.', 'Technology', 3000000000000.0)
        
        assert symbol.symbol == 'AAPL'
        assert symbol.company_name == 'Apple Inc.'
        assert symbol.sector == 'Technology'
        assert symbol.market_cap == 3000000000000.0
        assert symbol.is_active is True
        assert symbol.id is not None
    
    def test_add_duplicate_symbol(self, temp_db):
        # Add symbol first time
        symbol1 = temp_db.add_symbol('AAPL', 'Apple Inc.', 'Technology')
        
        # Add same symbol again - should return existing
        symbol2 = temp_db.add_symbol('AAPL', 'Apple Computer', 'Tech')
        
        assert symbol1.id == symbol2.id
        assert symbol1.company_name == symbol2.company_name  # Should keep original
    
    def test_get_symbols(self, temp_db):
        # Add some symbols
        temp_db.add_symbol('AAPL', 'Apple Inc.', 'Technology')
        temp_db.add_symbol('MSFT', 'Microsoft Corp.', 'Technology')
        temp_db.add_symbol('TSLA', 'Tesla Inc.', 'Automotive')
        
        symbols = temp_db.get_symbols()
        assert len(symbols) == 3
        
        symbol_names = [s.symbol for s in symbols]
        assert 'AAPL' in symbol_names
        assert 'MSFT' in symbol_names
        assert 'TSLA' in symbol_names
    
    def test_get_active_symbols_only(self, temp_db):
        # Add symbols
        temp_db.add_symbol('AAPL', 'Apple Inc.', 'Technology')
        temp_db.add_symbol('OLD', 'Old Company', 'Dead')
        
        # Manually deactivate one symbol
        with temp_db.get_session() as session:
            old_symbol = session.query(Symbol).filter(Symbol.symbol == 'OLD').first()
            old_symbol.is_active = False
            session.commit()
        
        # Get active symbols only
        active_symbols = temp_db.get_symbols(active_only=True)
        active_names = [s.symbol for s in active_symbols]
        
        assert 'AAPL' in active_names
        assert 'OLD' not in active_names
        
        # Get all symbols
        all_symbols = temp_db.get_symbols(active_only=False)
        all_names = [s.symbol for s in all_symbols]
        
        assert 'AAPL' in all_names
        assert 'OLD' in all_names
    
    def test_log_download(self, temp_db):
        download = temp_db.log_download(
            symbol='AAPL',
            data_type='options',
            status='pending',
            records_count=100,
            file_path='/path/to/file.parquet'
        )
        
        assert download.symbol == 'AAPL'
        assert download.data_type == 'options'
        assert download.status == 'pending'
        assert download.records_count == 100
        assert download.file_path == '/path/to/file.parquet'
        assert download.id is not None
        assert download.created_at is not None
    
    def test_update_download_status(self, temp_db):
        # Create initial download record
        download = temp_db.log_download('AAPL', 'options', 'pending')
        download_id = download.id
        
        # Update status
        temp_db.update_download_status(
            download_id,
            status='completed',
            records_count=250,
            file_path='/updated/path.parquet'
        )
        
        # Verify update
        with temp_db.get_session() as session:
            updated_download = session.query(DataDownload).filter(
                DataDownload.id == download_id
            ).first()
            
            assert updated_download.status == 'completed'
            assert updated_download.records_count == 250
            assert updated_download.file_path == '/updated/path.parquet'
            assert updated_download.completed_at is not None
    
    def test_update_download_with_error(self, temp_db):
        download = temp_db.log_download('AAPL', 'options', 'pending')
        
        temp_db.update_download_status(
            download.id,
            status='failed',
            error_message='Connection timeout'
        )
        
        with temp_db.get_session() as session:
            failed_download = session.query(DataDownload).filter(
                DataDownload.id == download.id
            ).first()
            
            assert failed_download.status == 'failed'
            assert failed_download.error_message == 'Connection timeout'
    
    def test_get_recent_downloads(self, temp_db):
        # Create downloads at different times
        now = datetime.now()
        
        # Recent download (today)
        recent = temp_db.log_download('AAPL', 'options', 'completed')
        recent.download_date = now
        
        # Old download (10 days ago)
        old = temp_db.log_download('MSFT', 'prices', 'completed')
        old.download_date = now - timedelta(days=10)
        
        # Update the database with our custom dates
        with temp_db.get_session() as session:
            session.merge(recent)
            session.merge(old)
            session.commit()
        
        # Get recent downloads (last 7 days)
        recent_downloads = temp_db.get_recent_downloads(days=7)
        
        download_symbols = [d.symbol for d in recent_downloads]
        assert 'AAPL' in download_symbols
        assert 'MSFT' not in download_symbols  # Too old
    
    def test_get_recent_downloads_by_symbol(self, temp_db):
        temp_db.log_download('AAPL', 'options', 'completed')
        temp_db.log_download('AAPL', 'prices', 'completed')
        temp_db.log_download('MSFT', 'options', 'completed')
        
        aapl_downloads = temp_db.get_recent_downloads(symbol='AAPL')
        assert len(aapl_downloads) == 2
        assert all(d.symbol == 'AAPL' for d in aapl_downloads)
    
    def test_get_recent_downloads_ordering(self, temp_db):
        # Create downloads
        download1 = temp_db.log_download('AAPL', 'options', 'completed')
        download2 = temp_db.log_download('AAPL', 'prices', 'completed')
        
        # Manually set different dates
        now = datetime.now()
        download1.download_date = now - timedelta(hours=2)
        download2.download_date = now - timedelta(hours=1)
        
        with temp_db.get_session() as session:
            session.merge(download1)
            session.merge(download2)
            session.commit()
        
        recent_downloads = temp_db.get_recent_downloads(symbol='AAPL')
        
        # Should be ordered by download_date desc (most recent first)
        assert len(recent_downloads) == 2
        assert recent_downloads[0].data_type == 'prices'  # More recent
        assert recent_downloads[1].data_type == 'options'  # Less recent

class TestDatabaseModels:
    
    def test_symbol_model(self):
        symbol = Symbol(
            symbol='AAPL',
            company_name='Apple Inc.',
            sector='Technology',
            market_cap=3000000000000.0,
            is_active=True
        )
        
        assert symbol.symbol == 'AAPL'
        assert symbol.company_name == 'Apple Inc.'
        assert symbol.sector == 'Technology'
        assert symbol.market_cap == 3000000000000.0
        assert symbol.is_active is True
    
    def test_data_download_model(self):
        now = datetime.now()
        download = DataDownload(
            symbol='AAPL',
            download_date=now,
            data_type='options',
            status='pending',
            records_count=100,
            file_path='/path/to/file.parquet'
        )
        
        assert download.symbol == 'AAPL'
        assert download.download_date == now
        assert download.data_type == 'options'
        assert download.status == 'pending'
        assert download.records_count == 100
        assert download.file_path == '/path/to/file.parquet'
    
    def test_strategy_model(self):
        now = datetime.now()
        strategy = Strategy(
            name='Long Straddle',
            description='Buy call and put at same strike',
            strategy_type='straddle',
            configuration='{"strike": 150, "expiration": "2024-01-19"}'
        )
        
        assert strategy.name == 'Long Straddle'
        assert strategy.description == 'Buy call and put at same strike'
        assert strategy.strategy_type == 'straddle'
        assert strategy.configuration == '{"strike": 150, "expiration": "2024-01-19"}'