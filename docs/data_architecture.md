# Options Analysis Platform - Data Architecture

## Overview

The Options Analysis Platform uses a hybrid data storage architecture combining Parquet files for efficient analytical data storage and SQLite for metadata management. The system operates in **two modes**:

1. **Real-time Snapshot Collection**: Automated 5-minute interval snapshots during market hours
2. **Historical Data Analysis**: Manual archival and analysis of historical option data

The platform collects delayed market data snapshots to avoid real-time market data subscription requirements.

## Data Storage Formats

### 1. Primary Data Storage (Parquet)

#### Real-time Snapshot Data
- **Location**: `data/snapshots/{symbol}/{YYYY-MM-DD}/snapshots.parquet`
- **Format**: Apache Parquet with configurable compression
- **Schedule**: Every 5 minutes during market hours (9:45-16:45)
- **Organization**: Hierarchical by symbol and date
- **Purpose**: Capture intraday option price movements and volume changes

#### Historical Archive Data
- **Location**: `data/historical/{symbol}/historical_options.parquet`
- **Format**: Apache Parquet with configurable compression
- **Trigger**: Manual execution by user
- **Scope**: Consolidated historical data from last archive to current date - 1 day
- **Purpose**: Long-term historical analysis and backtesting

#### Legacy Options Chain Data (Maintained for Compatibility)
- **Location**: `data/processed/{symbol}/{date}/options.parquet`
- **Format**: Apache Parquet with configurable compression
- **Organization**: Hierarchical by symbol and date

**Schema - Real-time Snapshot Data**:
```python
{
    'symbol': str,              # Stock symbol (e.g., 'AAPL')
    'snapshot_time': datetime,  # 5-minute snapshot timestamp
    'expiration': str,          # Expiration date (YYYYMMDD format)
    'strike': float,            # Strike price
    'option_type': str,         # 'C' for Call, 'P' for Put
    'bid': float,               # Current bid price (delayed)
    'ask': float,               # Current ask price (delayed)
    'last': float,              # Last traded price
    'volume': int,              # Trading volume
    'open_interest': int,       # Current open interest
    'implied_volatility': float,# Current implied volatility
    'delta': float,             # Current delta Greek
    'gamma': float,             # Current gamma Greek
    'theta': float,             # Current theta Greek
    'vega': float,              # Current vega Greek
    'collected_at': datetime    # System collection timestamp
}
```

**Schema - Historical Archive Data**:
```python
{
    'symbol': str,              # Stock symbol (e.g., 'AAPL')
    'date': date,               # Trading date
    'expiration': str,          # Expiration date (YYYYMMDD format)
    'strike': float,            # Strike price
    'option_type': str,         # 'C' for Call, 'P' for Put
    'open': float,              # Opening price
    'high': float,              # Daily high price
    'low': float,               # Daily low price
    'close': float,             # Closing price
    'volume': int,              # Daily trading volume
    'archive_date': datetime    # Date when archived
}
```

**Schema - Legacy Options Chain Data**:
```python
{
    'symbol': str,              # Stock symbol (e.g., 'AAPL')
    'expiration': str,          # Expiration date (YYYYMMDD format)
    'strike': float,            # Strike price
    'option_type': str,         # 'C' for Call, 'P' for Put
    'bid': float,               # Bid price (0 for historical data)
    'ask': float,               # Ask price (0 for historical data)
    'last': float,              # Last traded price
    'volume': int,              # Trading volume
    'open_interest': int,       # Open interest (0 for historical data)
    'implied_volatility': float,# Implied volatility (0 for historical data)
    'delta': float,             # Delta Greek (0 for historical data)
    'gamma': float,             # Gamma Greek (0 for historical data)
    'theta': float,             # Theta Greek (0 for historical data)
    'vega': float,              # Vega Greek (0 for historical data)
    'timestamp': datetime,      # Data collection timestamp
    'collected_at': datetime    # System collection timestamp
}
```

**Schema - Historical Options Data**:
```python
{
    'symbol': str,              # Stock symbol
    'date': date,               # Trading date
    'time': str,                # Time (HH:MM:SS format)
    'expiration': str,          # Expiration date (YYYYMMDD)
    'strike': float,            # Strike price
    'option_type': str,         # 'C' for Call, 'P' for Put
    'open': float,              # Opening price
    'high': float,              # Highest price
    'low': float,               # Lowest price
    'close': float,             # Closing price
    'volume': int,              # Trading volume
    'timestamp': datetime       # Bar timestamp
}
```

#### Stock Price Data
- **Location**: `data/processed/{symbol}/prices.parquet`
- **Format**: Apache Parquet

**Schema**:
```python
{
    'date': date,               # Trading date
    'open': float,              # Opening price
    'high': float,              # Highest price
    'low': float,               # Lowest price
    'close': float,             # Closing price
    'volume': int,              # Trading volume
    'symbol': str               # Stock symbol
}
```

#### Analytics Cache
- **Location**: `data/cache/{symbol}/{analysis_type}/results.parquet`
- **Purpose**: Cache computed analytics results
- **TTL**: Configurable expiration (default 24 hours)

### 2. Metadata Storage (SQLite)

#### Database Location
- **File**: `data/options_platform.db`
- **Purpose**: Track downloads, metadata, and system state

#### Key Tables
- **data_downloads**: Download history and status tracking
- **symbols**: Symbol registry and metadata
- **system_config**: Configuration and settings

## Data Collection Parameters

### Real-time Snapshot Collection
- **Schedule**: Every 5 minutes during market hours
- **Market Hours**: 9:45 AM - 4:45 PM EST (covers market open to close + settlement)
- **Data Type**: Delayed option chain snapshots (bid, ask, last, Greeks)
- **Storage**: Cumulative daily files per symbol
- **Automation**: Runs automatically during market days

### Historical Data Archival
- **Trigger**: Manual execution by user
- **Time Range**: From last archived date to current date - 1 day
- **Historical Data Duration**: 1 Month (`"1 M"`) per request
- **Bar Size**: Daily (`"1 day"`) for archival
- **Trading Hours**: 9:30 AM - 4:00 PM EST
- **Data Points**: OHLC daily bars

### Expiration Date Targeting
- **Selection Window**: Next 60 days from current date
- **Quantity Limit**: First 2 expiration dates only
- **Format**: YYYYMMDD string format
- **Filtering Logic**:
  ```python
  current_date <= expiration_date <= current_date + 60 days
  ```

### Strike Price Targeting
- **Selection Strategy**: Middle strike range to avoid real-time data requirements
- **Range**: ±5 strikes from middle price point
- **Total Strikes**: Approximately 11 strike prices per expiration
- **Logic**:
  ```python
  mid_idx = len(strikes) // 2
  selected_strikes = strikes[mid_idx-5:mid_idx+6]
  ```

## Data Flow Architecture

### 1. Data Ingestion Pipeline
```
IB TWS API → IBClient → Historical Data Request → Parquet Storage
                    ↓
            SQLite Metadata Logging
```

### 2. Storage Organization
```
data/
├── snapshots/              # Real-time snapshot data (5-min intervals)
│   └── {SYMBOL}/
│       └── {YYYY-MM-DD}/
│           └── snapshots.parquet  # Daily cumulative snapshots
├── historical/             # Archived historical data
│   └── {SYMBOL}/
│       └── historical_options.parquet  # Consolidated historical archive
├── processed/              # Legacy processed data (maintained for compatibility)
│   └── {SYMBOL}/
│       ├── prices.parquet  # Stock price history
│       └── {YYYY-MM-DD}/
│           └── options.parquet  # Daily options data
├── cache/                  # Computed analytics cache
│   └── {SYMBOL}/
│       └── {analysis_type}/
│           └── results.parquet
└── options_platform.db     # Metadata and tracking
```

### 3. Data Access Patterns

#### Historical Analysis
- **Time Series**: Load multiple date files for trend analysis
- **Cross-Sectional**: Single date, multiple strikes/expirations
- **Method**: `load_historical_option_chains(symbol, start_date, end_date)`

#### Real-time Dashboard
- **Latest Data**: Most recent date available
- **Data Freshness**: Check against trading calendar
- **Method**: `check_data_freshness(symbol)`

## Data Quality & Validation

### 1. Data Integrity Checks
- **Required Fields**: All schema fields must be present
- **Data Types**: Strict type validation on load/save
- **Date Validation**: Expiration dates must be valid trading days
- **Price Validation**: Positive prices, reasonable ranges

### 2. Completeness Monitoring
- **Download Tracking**: All requests logged with status
- **Missing Data Detection**: Compare against expected trading days
- **Data Gaps**: Identify and flag incomplete datasets

### 3. Freshness Management
- **Trading Calendar Integration**: Account for holidays and weekends
- **Expected Data Dates**: Calculate last expected trading day
- **Staleness Alerts**: Flag data older than expected

## Performance Optimizations

### 1. Storage Efficiency
- **Compression**: Configurable Parquet compression (default: snappy)
- **Partitioning**: Date-based partitioning for time series queries
- **Column Storage**: Parquet's columnar format for analytical queries

### 2. Query Performance
- **Date-based Indexing**: Directory structure enables fast date filtering
- **Caching Layer**: Pre-computed analytics cached in Parquet
- **Lazy Loading**: Data loaded only when needed

### 3. Memory Management
- **Streaming Reads**: Large datasets processed in chunks
- **Connection Pooling**: Efficient database connection management
- **Background Processing**: Heavy downloads run asynchronously

## Security & Compliance

### 1. Data Access
- **Local Storage**: All data stored locally, no cloud dependencies
- **File Permissions**: Restricted access to data directories
- **No PII**: Only public market data stored

### 2. API Compliance
- **Historical Data Only**: No real-time market data subscriptions
- **Rate Limiting**: Built-in delays between API calls
- **Error Handling**: Graceful handling of API limits and errors

## Monitoring & Maintenance

### 1. Data Monitoring
- **Download Success Rates**: Track successful vs failed downloads
- **Data Volume Metrics**: Monitor storage growth and usage
- **Performance Metrics**: Query execution times and throughput

### 2. Maintenance Tasks
- **Cache Cleanup**: Automatic removal of expired cache files
- **Data Archival**: Long-term data retention policies
- **Database Optimization**: Regular SQLite maintenance operations

## Configuration

### Environment Variables
```bash
IB_HOST=127.0.0.1          # Interactive Brokers TWS host
IB_PORT=7497               # TWS port (paper trading: 7497, live: 7496)
IB_CLIENT_ID=1             # Unique client identifier
DATA_PATH=./data           # Base data storage path
PARQUET_COMPRESSION=snappy # Compression algorithm
```

### File Structure Configuration
```python
# Paths configured in src/utils/config.py
processed_data_path = Path("data/processed")
cache_data_path = Path("data/cache")
database_path = Path("data/options_platform.db")
```

## Disaster Recovery

### 1. Backup Strategy
- **Data Files**: Regular backup of Parquet files
- **Database**: SQLite database backup with transaction logs
- **Configuration**: Version-controlled configuration files

### 2. Recovery Procedures
- **Data Reconstruction**: Re-download historical data if needed
- **Metadata Recovery**: Rebuild download logs from file system
- **System Restoration**: Automated setup scripts for clean installation

## Future Enhancements

### 1. Scalability Improvements
- **Distributed Storage**: Support for cloud storage backends
- **Parallel Processing**: Multi-threaded data download and processing
- **Data Compression**: Advanced compression for long-term storage

### 2. Advanced Analytics
- **Real-time Greeks**: Calculate Greeks from historical data
- **Volatility Surface**: Build implied volatility surfaces
- **Risk Metrics**: Value at Risk and other risk calculations

---

*Document Version: 1.0*  
*Last Updated: 2025-01-26*  
*Maintained by: Options Analysis Platform Team*