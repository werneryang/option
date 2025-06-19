# Options Analysis Platform

A comprehensive options analysis platform focused on historical data analysis and strategy evaluation, inspired by OptionStrat.

## Features

- **Option Chain Analysis**: Download and analyze historical option chain data
- **Interactive Brokers Integration**: Fetch data from IB TWS API
- **Data Storage**: Efficient storage using SQLite (metadata) + Parquet files (time series)
- **Data Validation**: Comprehensive validation and cleaning pipelines
- **Extensible Architecture**: Modular design for easy feature additions

## Quick Start

### 1. Prerequisites

- Python 3.9+
- Interactive Brokers TWS or IB Gateway (for data downloads)

### 2. Installation

```bash
# Clone or download the project
cd options-analysis-platform

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .[dev]
```

### 3. Configuration

Copy the environment template and configure:

```bash
cp .env.example .env
# Edit .env with your IB connection settings
```

### 4. Setup

Initialize the database and directories:

```bash
python main.py setup
```

### 5. Download Sample Data

Make sure IB TWS or IB Gateway is running, then:

```bash
python main.py download
```

This will download sample data for AAPL, SPY, and TSLA.

### 6. Check Status

```bash
python main.py status
python main.py history
```

## Project Structure

```
├── src/
│   ├── data_sources/     # Data acquisition and storage
│   │   ├── database.py   # SQLite database management
│   │   ├── ib_client.py  # Interactive Brokers API client
│   │   ├── storage.py    # Parquet file storage
│   │   └── validation.py # Data validation and cleaning
│   ├── analytics/        # Options calculations (Phase 2)
│   ├── ui/              # Streamlit interface (Phase 4)
│   └── utils/           # Utilities and configuration
├── data/
│   ├── raw/             # Raw downloaded data
│   ├── processed/       # Cleaned and processed data
│   └── cache/           # Analytics cache
└── tests/               # Test suites
```

## Data Storage

### Database (SQLite)
- **symbols**: Symbol metadata and information
- **data_downloads**: Download history and status tracking
- **strategies**: Saved trading strategies (Phase 3)

### Parquet Files
- **Option Chains**: `data/processed/{symbol}/{date}/options.parquet`
- **Price History**: `data/processed/{symbol}/prices.parquet`
- **Analytics Cache**: `data/cache/{symbol}/{analysis_type}/results.parquet`

## Development Status

✅ **Phase 1 Complete**: Foundation & Data Infrastructure
- [x] Project structure and dependencies
- [x] SQLite schema for metadata management
- [x] Parquet data storage handlers
- [x] IB TWS API integration
- [x] Data validation and cleaning pipelines
- [x] Basic configuration management

✅ **Phase 2 Complete**: Core Analytics Engine
- [x] Black-Scholes options pricing with full Greeks
- [x] Advanced implied volatility analysis
- [x] Comprehensive historical volatility calculations
- [x] Complete options strategy framework

✅ **Phase 4 Complete**: User Interface & Visualization
- [x] Professional Streamlit web application
- [x] Interactive option chain analysis
- [x] Visual strategy builder with P&L charts
- [x] Advanced analytics dashboard

## Interactive Brokers Setup

1. Download and install IB TWS or IB Gateway
2. Configure API access:
   - Go to Configuration > API > Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Set socket port (default: 7497 for TWS, 4002 for Gateway)
   - Add your IP to trusted IPs if needed
3. Update your `.env` file with connection details

## Available Commands

```bash
python main.py setup     # Initialize database and directories
python main.py download  # Download sample data
python main.py status    # Show storage status
python main.py history   # Show download history

# Launch Web Application
python run_ui.py         # Start Streamlit web interface
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
black src/ tests/
flake8 src/ tests/
```

### Adding New Symbols

The platform currently downloads sample data for AAPL, SPY, and TSLA. To add more symbols, modify the `sample_symbols` list in `main.py` or use the database API:

```python
from src.data_sources.database import db_manager
db_manager.add_symbol("MSFT", "Microsoft Corporation", "Technology")
```

## Troubleshooting

### Common Issues

1. **Connection Refused to IB TWS**
   - Ensure TWS/Gateway is running
   - Check API settings are enabled
   - Verify port numbers in `.env`

2. **Permission Errors**
   - Ensure write permissions to data/ directory
   - Check if antivirus is blocking file operations

3. **Import Errors**
   - Run `pip install -r requirements.txt`
   - Check Python version (3.9+ required)

### Logging

Logs are written to:
- Console: INFO level and above
- File: `logs/app.log` (DEBUG level, rotating)

## License

MIT License - see LICENSE file for details.