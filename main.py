#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path
from loguru import logger

sys.path.append(str(Path(__file__).parent / "src"))

from src.utils.config import config
from src.data_sources.database import db_manager
from src.data_sources.ib_client import downloader

def setup_logging():
    logger.remove()
    logger.add(
        sys.stderr,
        level=config.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

async def download_sample_data():
    """Download sample data for testing purposes"""
    logger.info("Starting sample data download...")
    
    sample_symbols = ["AAPL", "SPY", "TSLA"]
    
    try:
        config.ensure_directories()
        Path("logs").mkdir(exist_ok=True)
        
        results = await downloader.download_multiple_symbols(
            sample_symbols,
            include_options=True,
            include_history=True
        )
        
        logger.info("Download results:")
        for result in results:
            if result['success']:
                logger.info(f"✓ {result['symbol']}: Success")
                if 'price_records' in result:
                    logger.info(f"  - Price records: {result['price_records']}")
                if 'option_records' in result:
                    logger.info(f"  - Option records: {result['option_records']}")
            else:
                logger.error(f"✗ {result['symbol']}: Failed - {result['errors']}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error during sample data download: {e}")
        return []

def show_data_status():
    """Show current data storage status"""
    from src.data_sources.storage import storage
    
    logger.info("Data Storage Status:")
    stats = storage.get_storage_stats()
    
    logger.info(f"Total symbols with data: {stats['total_symbols']}")
    logger.info(f"Total files: {stats['total_files']}")
    logger.info(f"Total storage: {stats['total_size_mb']} MB")
    
    for symbol, symbol_stats in stats['symbols'].items():
        logger.info(f"  {symbol}: {symbol_stats['files']} files, {symbol_stats['size_mb']:.2f} MB")
        logger.info(f"    Available dates: {len(symbol_stats['available_dates'])} days")

def show_recent_downloads():
    """Show recent download history"""
    downloads = db_manager.get_recent_downloads(days=7)
    
    logger.info("Recent Downloads (last 7 days):")
    for download in downloads:
        status_emoji = "✓" if download.status == "completed" else "✗"
        logger.info(
            f"  {status_emoji} {download.symbol} ({download.data_type}) - "
            f"{download.download_date.strftime('%Y-%m-%d %H:%M')} - "
            f"{download.status}"
        )
        if download.records_count:
            logger.info(f"    Records: {download.records_count}")
        if download.error_message:
            logger.info(f"    Error: {download.error_message}")

async def main():
    """Main application entry point"""
    setup_logging()
    logger.info("Options Analysis Platform - Data Infrastructure")
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "download":
            await download_sample_data()
        elif command == "status":
            show_data_status()
        elif command == "history":
            show_recent_downloads()
        elif command == "setup":
            logger.info("Setting up database and directories...")
            config.ensure_directories()
            db_manager.create_tables()
            logger.info("✓ Setup complete")
        else:
            logger.error(f"Unknown command: {command}")
            print_usage()
    else:
        print_usage()

def print_usage():
    """Print usage information"""
    print("""
Options Analysis Platform - Data Infrastructure

Usage:
    python main.py <command>

Commands:
    setup     - Initialize database and directories
    download  - Download sample data from IB TWS
    status    - Show data storage status
    history   - Show recent download history

Examples:
    python main.py setup
    python main.py download
    python main.py status

Note: Make sure Interactive Brokers TWS or IB Gateway is running 
      before using the download command.
""")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)