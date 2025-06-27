# Options Analysis Platform - Workflow Documentation

## Overview

The Options Analysis Platform operates with a dual workflow system designed to provide both real-time market monitoring and comprehensive historical analysis capabilities.

## Workflow 1: Automated Real-time Snapshot Collection

### Purpose
Capture delayed option chain snapshots at regular intervals during market hours to monitor intraday price movements, volume changes, and Greeks evolution.

### Schedule
- **Frequency**: Every 5 minutes
- **Market Hours**: 9:45 AM - 4:45 PM EST
- **Trading Days**: Monday through Friday (excludes market holidays)
- **Total Snapshots**: ~76 snapshots per trading day

### Data Collection Process

#### 1. Market Hours Validation
```python
# Check if current time is within collection window
if is_market_open() and 9:45 <= current_time <= 16:45:
    trigger_snapshot_collection()
```

#### 2. Symbol Processing
- Process all active symbols in the watchlist
- Collect option chain for each symbol independently
- Handle errors gracefully to avoid disrupting other symbols

#### 3. Data Capture
For each symbol, collect:
- All active option contracts (calls and puts)
- Current bid/ask prices (delayed 15-20 minutes)
- Last trade price and volume
- Open interest
- Implied volatility
- Greeks (Delta, Gamma, Theta, Vega, Rho)

#### 4. Data Storage
```
data/snapshots/{SYMBOL}/{YYYY-MM-DD}/snapshots.parquet
```
- **Accumulation**: Each snapshot is appended to the daily file
- **Compression**: Snappy compression for optimal performance
- **Indexing**: Timestamp-based for chronological querying

#### 5. Error Handling
- API connection failures: Retry with exponential backoff
- Data validation errors: Log and continue with next symbol
- Storage errors: Alert and attempt recovery

### Monitoring and Alerts

#### Health Checks
- Verify snapshot collection every hour
- Monitor data quality and completeness
- Alert on consecutive failures (>3 missed snapshots)

#### Performance Metrics
- Collection latency per symbol
- Data volume per snapshot
- Storage utilization growth

## Workflow 2: Manual Historical Data Archival

### Purpose
Download and consolidate historical option data for long-term analysis, backtesting, and research purposes.

### Trigger
Manual execution by user through:
- Web UI "Archive Historical Data" button
- Command line: `python main.py archive --symbol AAPL`
- Scheduled batch jobs (if configured)

### Archival Process

#### 1. Date Range Determination
```python
# Calculate archival range
last_archive_date = get_last_archive_date(symbol)
end_date = datetime.now().date() - timedelta(days=1)  # Yesterday
start_date = last_archive_date + timedelta(days=1) if last_archive_date else end_date - timedelta(days=30)
```

#### 2. Data Download
- **Source**: Interactive Brokers TWS API
- **Data Type**: Historical daily OHLC bars
- **Time Frame**: From start_date to end_date
- **Expiration Filter**: Active contracts within 2 months
- **Strike Filter**: ±20% around current price

#### 3. Data Consolidation
```python
# Combine with existing archive
existing_archive = load_historical_archive(symbol)
new_data = download_historical_data(symbol, start_date, end_date)
consolidated = merge_and_deduplicate(existing_archive, new_data)
```

#### 4. Archive Storage
```
data/historical/{SYMBOL}/historical_options.parquet
```
- **Format**: Single consolidated file per symbol
- **Deduplication**: Remove duplicate date/contract combinations
- **Sorting**: Chronological order by date, then by contract

#### 5. Metadata Update
- Log archival operation in database
- Update last_archive_date for the symbol
- Record data volume and quality metrics

### Archive Management

#### Data Retention
- **Snapshot Data**: Keep 90 days (configurable)
- **Historical Archive**: Permanent retention
- **Cache Data**: 30 days automatic cleanup

#### Quality Assurance
- Validate data completeness for each date range
- Check for gaps in the historical timeline
- Verify data integrity after consolidation

## Data Flow Integration

### Cross-Workflow Data Usage

#### 1. Real-time to Historical
- Daily snapshot summaries can seed historical archives
- End-of-day snapshot serves as data quality check
- Volume and open interest trends inform archival priorities

#### 2. Historical to Real-time
- Historical baselines for anomaly detection
- Pre-computed Greeks for validation
- Long-term volatility patterns for current analysis

### Data Access Patterns

#### UI Dashboard Access
```python
# Current market view
snapshots = get_latest_snapshots(symbol, limit=12)  # Last hour

# Historical analysis
archive = get_historical_data(symbol, start_date, end_date)

# Trend analysis
combined = merge_snapshot_and_historical(snapshots, archive)
```

#### Analytical Workflows
- **Intraday Analysis**: Use snapshot data for minute-by-minute analysis
- **Daily Analysis**: Use historical archive for day-over-day comparisons
- **Long-term Studies**: Combine both datasets for comprehensive research

## Configuration and Scheduling

### Environment Configuration
```bash
# Snapshot collection settings
SNAPSHOT_INTERVAL_MINUTES=5
MARKET_START_TIME=09:45
MARKET_END_TIME=16:45

# Historical archival settings
MAX_ARCHIVE_DAYS_PER_REQUEST=30
ARCHIVE_EXPIRY_MONTHS=2
ARCHIVE_STRIKE_RANGE_PERCENT=20

# Storage settings
SNAPSHOT_RETENTION_DAYS=90
CACHE_CLEANUP_HOURS=24
```

### Scheduling Framework
```python
# Cron-like scheduling for snapshots
@schedule.every(5).minutes.during("09:45", "16:45").on_weekdays
def collect_snapshots():
    for symbol in get_active_symbols():
        collect_option_snapshot(symbol)

# Manual archival with progress tracking
def archive_historical_data(symbol, progress_callback=None):
    # Implementation with progress updates
    pass
```

## Error Recovery and Resilience

### Snapshot Collection Resilience
- **Network Failures**: Exponential backoff with jitter
- **API Rate Limits**: Dynamic throttling
- **Data Corruption**: Atomic writes with validation
- **System Restart**: Resume from last successful timestamp

### Archival Process Recovery
- **Partial Downloads**: Resume from last successful date
- **Data Conflicts**: Smart merging with conflict resolution
- **Storage Failures**: Backup to alternative location
- **API Timeout**: Retry with smaller date ranges

### Monitoring and Alerting
```python
# Health monitoring
def check_system_health():
    snapshot_health = verify_recent_snapshots()
    storage_health = check_disk_usage()
    api_health = test_ib_connection()
    return combine_health_status(snapshot_health, storage_health, api_health)

# Alert conditions
if consecutive_failures > 3:
    send_alert("Snapshot collection degraded")
if disk_usage > 90:
    send_alert("Storage capacity critical")
if api_latency > 30_seconds:
    send_alert("API performance degraded")
```

## Performance Optimization

### Snapshot Collection Optimization
- **Parallel Processing**: Collect multiple symbols concurrently
- **Connection Pooling**: Reuse IB TWS connections
- **Data Compression**: Use efficient Parquet encoding
- **Memory Management**: Stream data to disk to avoid memory bloat

### Archival Process Optimization
- **Batch Processing**: Group multiple date ranges
- **Incremental Updates**: Only download new data
- **Index Optimization**: Maintain sorted order for fast queries
- **Compression Tuning**: Balance speed vs. storage efficiency

### Storage Optimization
```python
# Efficient snapshot storage
def store_snapshot(symbol, timestamp, data):
    # Use partitioned Parquet with time-based indexing
    # Implement row group optimization for query performance
    # Apply column-specific compression algorithms
    pass

# Historical archive optimization
def optimize_archive(symbol):
    # Reorder columns for analytical access patterns
    # Apply dictionary encoding for categorical data
    # Use delta encoding for timestamp columns
    pass
```

## Future Enhancements

### Workflow Improvements
1. **Smart Scheduling**: Adaptive intervals based on market volatility
2. **Predictive Archival**: Automatic triggering based on data gaps
3. **Real-time Analytics**: On-the-fly calculations during snapshot collection
4. **Multi-Asset Support**: Extend to futures, ETFs, and other instruments

### Technical Enhancements
1. **Cloud Integration**: Support for cloud storage backends
2. **Distributed Processing**: Multi-node data collection
3. **Stream Processing**: Real-time data processing pipelines
4. **Advanced Compression**: Machine learning-optimized compression

### Operational Improvements
1. **Self-Healing**: Automatic recovery from common failures
2. **Performance Tuning**: Adaptive optimization based on usage patterns
3. **Cost Optimization**: Intelligent data lifecycle management
4. **Compliance**: Enhanced audit trails and data governance

---

*Document Version: 1.0*  
*Last Updated: 2025-06-27*  
*Next Review: 2025-07-27*