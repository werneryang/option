# Options Analysis Platform - Configuration Guide

## Overview

The Options Analysis Platform uses environment variables and configuration files to manage system settings, data collection parameters, and operational behaviors.

## Configuration Files

### 1. Environment Variables (.env)

Create a `.env` file in the project root directory to override default settings:

```bash
# Interactive Brokers TWS Connection
IB_HOST=127.0.0.1               # TWS/Gateway host address
IB_PORT=7497                    # TWS port (7497=paper, 7496=live)
IB_CLIENT_ID=1                  # Unique client identifier

# Data Storage Configuration
DATA_ROOT=./data                # Base directory for all data files
DB_PATH=data/options_platform.db # SQLite database path
PARQUET_COMPRESSION=snappy      # Parquet compression algorithm

# Snapshot Collection Settings
SNAPSHOT_INTERVAL_MINUTES=5     # Collection frequency (minutes)
MARKET_START_TIME=09:45         # Start time (HH:MM format)
MARKET_END_TIME=16:45           # End time (HH:MM format)
SNAPSHOT_RETENTION_DAYS=90      # How long to keep snapshot data

# Historical Archival Settings
MAX_ARCHIVE_DAYS_PER_REQUEST=30 # Max days per download request
ARCHIVE_EXPIRY_MONTHS=2         # Expiration window for options
ARCHIVE_STRIKE_RANGE_PERCENT=20 # Strike range around current price

# System Configuration
LOG_LEVEL=INFO                  # Logging verbosity (DEBUG,INFO,WARN,ERROR)
CACHE_EXPIRY_HOURS=24          # Cache TTL in hours
STREAMLIT_PORT=8501            # Web UI port
```

### 2. Configuration Class (src/utils/config.py)

The configuration is managed through a Pydantic settings class that automatically loads from environment variables:

```python
from src.utils.config import config

# Access configuration values
print(f"Data root: {config.data_root}")
print(f"Snapshot interval: {config.snapshot_interval_minutes} minutes")
print(f"Market hours: {config.market_start_time} - {config.market_end_time}")
```

## Data Storage Paths

### Automatic Directory Creation

The system automatically creates the following directory structure:

```
data/
├── raw/                        # Raw downloaded data
├── processed/                  # Legacy processed data  
├── snapshots/                  # Real-time snapshot data
├── historical/                 # Archived historical data
├── cache/                      # Computed analytics cache
└── options_platform.db         # SQLite metadata database
```

### Path Configuration

Each data type has its own configured path:

```python
# Access via config properties
config.snapshots_data_path      # data/snapshots/
config.historical_data_path     # data/historical/
config.processed_data_path      # data/processed/
config.cache_data_path          # data/cache/
```

## Workflow Configuration

### 1. Snapshot Collection Workflow

#### Timing Configuration
```bash
# Collection runs every 5 minutes during market hours
SNAPSHOT_INTERVAL_MINUTES=5

# Market hours: 9:45 AM to 4:45 PM EST
MARKET_START_TIME=09:45
MARKET_END_TIME=16:45

# Data retention: Keep 90 days of snapshots
SNAPSHOT_RETENTION_DAYS=90
```

#### Collection Behavior
- **Frequency**: Every N minutes (configurable)
- **Market Hours**: Only during specified time window
- **Weekends/Holidays**: Automatically skipped using trading calendar
- **Error Handling**: Continue on individual symbol failures

#### File Organization
```
data/snapshots/
└── {SYMBOL}/
    └── {YYYY-MM-DD}/
        └── snapshots.parquet    # Cumulative daily file
```

### 2. Historical Archival Workflow

#### Archive Settings
```bash
# Download up to 30 days of historical data per request
MAX_ARCHIVE_DAYS_PER_REQUEST=30

# Focus on options expiring within 2 months
ARCHIVE_EXPIRY_MONTHS=2

# Select strikes within ±20% of current price
ARCHIVE_STRIKE_RANGE_PERCENT=20
```

#### Archive Behavior
- **Trigger**: Manual execution only
- **Date Range**: From last archive date to yesterday
- **Deduplication**: Automatic removal of duplicate records
- **Consolidation**: Single file per symbol

#### File Organization
```
data/historical/
└── {SYMBOL}/
    └── historical_options.parquet    # Consolidated archive
```

## Interactive Brokers Configuration

### Connection Settings

#### TWS/Gateway Setup
```bash
# Local TWS instance
IB_HOST=127.0.0.1
IB_PORT=7497                    # Paper trading port
IB_CLIENT_ID=1                  # Must be unique per connection

# Remote TWS instance (advanced)
IB_HOST=192.168.1.100
IB_PORT=7496                    # Live trading port (use with caution)
IB_CLIENT_ID=10                 # Different client ID
```

#### Port Configuration
- **7497**: Paper Trading TWS (recommended for development)
- **7496**: Live Trading TWS (production use only)
- **4001**: IB Gateway Paper Trading
- **4000**: IB Gateway Live Trading

#### Client ID Management
- Each connection requires a unique client ID
- Snapshot collector: Client ID 1
- Manual downloads: Client ID 99
- UI operations: Client ID 1 (shared with snapshots)

### API Permissions

Ensure TWS/Gateway is configured to allow:
- **API connections**: Enable in TWS settings
- **Historical data**: Requires market data subscription
- **Option chains**: Included with equity data permissions
- **Socket connections**: Allow from localhost or specific IPs

## Performance Tuning

### Data Collection Performance

#### Snapshot Collection Optimization
```bash
# Reduce collection frequency during low volatility
SNAPSHOT_INTERVAL_MINUTES=10    # Slower collection

# Extend market hours for after-hours analysis
MARKET_START_TIME=09:30         # Earlier start
MARKET_END_TIME=17:00           # Later end
```

#### Historical Download Optimization
```bash
# Smaller batch sizes for better reliability
MAX_ARCHIVE_DAYS_PER_REQUEST=7  # Weekly batches

# Narrower strike range for faster downloads
ARCHIVE_STRIKE_RANGE_PERCENT=10 # ±10% instead of ±20%
```

### Storage Performance

#### Compression Settings
```bash
# Fast compression (default)
PARQUET_COMPRESSION=snappy

# Better compression ratio
PARQUET_COMPRESSION=gzip

# No compression (fastest writes)
PARQUET_COMPRESSION=none
```

#### Cache Management
```bash
# Longer cache retention for stable data
CACHE_EXPIRY_HOURS=72          # 3 days

# Shorter cache for volatile calculations
CACHE_EXPIRY_HOURS=1           # 1 hour
```

### Memory Management

#### Large Dataset Handling
```bash
# Shorter retention for memory-constrained systems
SNAPSHOT_RETENTION_DAYS=30     # 1 month instead of 3

# Smaller archive batches
MAX_ARCHIVE_DAYS_PER_REQUEST=1 # Daily batches
```

## Security Configuration

### Data Protection

#### File Permissions
```bash
# Restrict data directory access (Unix/Linux)
chmod 700 data/
chmod 600 data/options_platform.db
```

#### Network Security
```bash
# Bind to localhost only
IB_HOST=127.0.0.1              # No external access

# Use non-standard ports if needed
STREAMLIT_PORT=8502            # Alternative web UI port
```

### API Security

#### Connection Limits
- Limit concurrent connections to TWS
- Use unique client IDs to avoid conflicts
- Monitor connection status and reconnect automatically

#### Data Validation
- Validate all incoming data before storage
- Check data ranges and types
- Log suspicious data patterns

## Monitoring Configuration

### Logging Settings

#### Log Levels
```bash
# Development debugging
LOG_LEVEL=DEBUG                # Verbose logging

# Production operation
LOG_LEVEL=INFO                 # Standard logging

# Error tracking only
LOG_LEVEL=ERROR               # Minimal logging
```

#### Log Outputs
- Console output for development
- File output for production
- Structured JSON for log aggregation

### Health Monitoring

#### Collection Health
- Monitor snapshot collection success rate
- Track API response times
- Alert on consecutive failures

#### Storage Health
- Monitor disk usage growth
- Check data integrity
- Alert on storage errors

## Troubleshooting Configuration

### Common Issues and Solutions

#### Connection Problems
```bash
# TWS not accepting connections
# Solution: Enable API in TWS settings, check client ID uniqueness

# Port conflicts
# Solution: Use alternative ports, check firewall settings

# Authentication failures
# Solution: Verify TWS login, check paper vs live trading mode
```

#### Data Collection Issues
```bash
# Missing snapshots
# Solution: Check market hours config, verify TWS connection

# Incomplete archives
# Solution: Reduce batch size, increase timeout settings

# Storage errors
# Solution: Check disk space, verify write permissions
```

#### Performance Issues
```bash
# Slow collection
# Solution: Reduce symbol count, increase interval, optimize network

# High memory usage
# Solution: Reduce retention days, enable compression, restart services

# Database locks
# Solution: Reduce concurrent operations, optimize queries
```

## Configuration Examples

### Development Environment
```bash
# .env.development
IB_HOST=127.0.0.1
IB_PORT=7497
SNAPSHOT_INTERVAL_MINUTES=1
MARKET_START_TIME=09:30
MARKET_END_TIME=16:00
LOG_LEVEL=DEBUG
SNAPSHOT_RETENTION_DAYS=7
```

### Production Environment
```bash
# .env.production
IB_HOST=127.0.0.1
IB_PORT=7496
SNAPSHOT_INTERVAL_MINUTES=5
MARKET_START_TIME=09:45
MARKET_END_TIME=16:45
LOG_LEVEL=INFO
SNAPSHOT_RETENTION_DAYS=90
PARQUET_COMPRESSION=gzip
```

### High-Frequency Collection
```bash
# .env.hft
SNAPSHOT_INTERVAL_MINUTES=1
MARKET_START_TIME=09:30
MARKET_END_TIME=16:00
ARCHIVE_STRIKE_RANGE_PERCENT=30
MAX_ARCHIVE_DAYS_PER_REQUEST=1
```

---

*Document Version: 1.0*  
*Last Updated: 2025-06-27*  
*Configuration Schema Version: 1.0*