# binance_Trading_Bot

A clean, structured Python CLI application for placing orders on the Binance USDT-M Futures Testnet.

Project Structure
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Low-level Binance REST client (signing, HTTP, error handling)
│   ├── orders.py          # Order placement logic (MARKET, LIMIT, STOP_MARKET)
│   ├── validators.py      # Input validation (all fields, cross-field rules)
│   └── logging_config.py  # Rotating file + console logger setup
├── logs/
│   └── trading_bot.log    # Auto-created on first run
├── cli.py                 # CLI entry point (argparse)
├── .env.example           # Template for credentials
├── requirements.txt
└── README.md
Setup
1. Register a Binance Futures Testnet account
Visit https://testnet.binancefuture.com
Log in with your GitHub account
Navigate to API Management → generate a new API key pair
Copy both the API Key and Secret Key
2. Clone and install dependencies
git clone https://github.com/your-username/trading_bot.git
cd trading_bot

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
3. Set credentials
cp .env.example .env
# Edit .env and fill in your testnet keys

# Load into shell (Linux/macOS):
export BINANCE_API_KEY=your_key_here
export BINANCE_API_SECRET=your_secret_here

# Windows PowerShell:
# $env:BINANCE_API_KEY="your_key_here"
# $env:BINANCE_API_SECRET="your_secret_here"
How to Run
Place a MARKET order
# BUY 0.001 BTC at market price
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# SELL 0.01 ETH at market price
python cli.py place --symbol ETHUSDT --side SELL --type MARKET --quantity 0.01
Place a LIMIT order
# SELL 0.001 BTC when price reaches $98,000 (GTC)
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 98000

# BUY 0.001 BTC with IOC time-in-force
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 94000 --tif IOC
Place a STOP_MARKET order (bonus)
# Trigger a market SELL if BTC drops to $75,000
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 75000
Account info
python cli.py account
View open orders
python cli.py open-orders
python cli.py open-orders --symbol BTCUSDT
Help
python cli.py --help
python cli.py place --help
Example Output
════════════════════════════════════════════════════════════
  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────────────
  Symbol:               BTCUSDT
  Side:                 BUY
  Type:                 MARKET
  Quantity:             0.001
────────────────────────────────────────────────────────────
  ✓ ORDER PLACED SUCCESSFULLY
────────────────────────────────────────────────────────────
  Order ID:             4049785514
  Client Order ID:      web_zs6LB5NcJDECCKFEG5yw
  Status:               FILLED
  Executed Qty:         0.001
  Avg Price:            96124.50000
  Orig Qty:             0.001
  Price:                MARKET
════════════════════════════════════════════════════════════
Logging
All activity is written to logs/trading_bot.log (rotating, max 5 MB × 3 backups):

DEBUG: full request params (signature redacted) and raw response body
INFO: human-readable order summaries and results
ERROR: API errors, validation failures, network problems
Console output is INFO level and above.

Validation Rules
Parameter	Rule
symbol	Non-empty, alphabetic only (e.g. BTCUSDT)
side	Must be BUY or SELL
type	Must be MARKET, LIMIT, or STOP_MARKET
quantity	Positive decimal number
price	Required for LIMIT; must be positive; must NOT be set for MARKET
stop-price	Required for STOP_MARKET; must be positive
Assumptions
Testnet only — the base URL is hardcoded to https://testnet.binancefuture.com. Do not use real credentials here.
USDT-M Futures — all orders target the /fapi/ endpoint (not COIN-M /dapi/).
Credentials via environment variables — no credential file is read at runtime. Use export or a .env loader of your choice.
Quantity precision — the bot forwards the raw quantity string to Binance. If you hit a -1111 (invalid precision) error, reduce decimal places to match the symbol's lot size (e.g. BTC = 3 decimal places on testnet).
Timestamp sync — the client fetches server time on startup to compute a clock offset, avoiding -1021 timestamp out of range errors.
No order persistence — the bot is stateless; it does not store order history locally.
Requirements
Python 3.9+
requests >= 2.31.0
python-dotenv >= 1.0.0 (optional, for .env file loading)
License
MIT
