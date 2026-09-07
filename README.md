# Autonomous Options Paper Trading Bot 🤖
### Systematic NIFTY 50 (Quantman 1165) & SENSEX (1lyAlgos) Execution Engine
**Starting Virtual Capital: ₹ 10,00,000.00**

---

## 🏛️ System Overview

This autonomous paper trading bot executes two systematic algorithmic options buying strategies on Indian derivatives markets:

1. **NIFTY 50 (Quantman Strategy 1165)**:
   - **Allocation**: 80% (₹8,00,000 baseline)
   - **Timeframe**: 3-minute / 5-minute Supertrend (10, 2), Dual EMA (9/20), and VWAP alignment
   - **Risk Management**: -15% Stop Loss with immediate **2× Asymmetric Martingale Inversion**
   - **Target**: +30% with 15% trailing stop loss
   - **Execution Window**: 09:45 AM (Noise quarantine ends) to 15:14 IST (Mandatory square-off)

2. **SENSEX (1lyAlgos Early Momentum Catcher)**:
   - **Allocation**: 20% (₹2,00,000 baseline)
   - **Timeframe**: Opening 15-minute range breakout (09:15–09:30 AM)
   - **Risk Management**: Strict **40-point hard stop loss**
   - **Target**: +80 points (trailing stop to cost at +60 pts)
   - **Execution Window**: 09:30 AM entry window with **12:00 PM hard time cutoff**
   - **Discipline**: Strictly **1 trade per day** (zero re-entries)

---

## 📊 Day 1 Live Execution Journal (September 07, 2026)

The bot executed today's real session using live 5-minute candle data from Yahoo Finance:

```
================================================================
  📊 DAILY ALGO TRADE RECAP | 2026-09-07 | 🔴 LOSS
================================================================
• Initial Capital:        ₹ 10,00,000.00
• Current Portfolio Cash: ₹ 989,204.15
• Today's Gross P&L:      ₹ -10,472.15
• Brokerage & Taxes:      ₹ 323.70
• Today's Net P&L:        ₹ -10,795.85 (-1.08%)
• Trades Executed:        2 (Wins: 1 | Losses: 1 | Win Rate: 50.0%)
----------------------------------------------------------------
  INDIVIDUAL TRADE JOURNAL
----------------------------------------------------------------
Strategy    Instrument          Qty        Entry    Buy Px    Exit    Sell Px    Exit Reason           Net P&L     Result
----------  ------------------  ---------  -------  --------  ------  ---------  --------------------  ----------  --------
SENSEX_1LY  SENSEX26SEP76200PE  80 units   10:10    ₹435.6    12:00   ₹462.3     TIME_CUTOFF_12:00_PM  ₹+2,001.9   GAIN
NIFTY_1165  NIFTY26SEP23800CE   475 units  13:50    ₹160.7    15:05   ₹134.2     STOP_LOSS_-15%        ₹-12,797.8  LOSS
================================================================
• Next Active Session: Tomorrow at 09:15 AM IST
• Overnight Risk: 100% Cash | Flat Overnight Exposure
================================================================
```

### Key Execution Observations:
- **SENSEX 1lyAlgos**: Caught the morning opening breakdown on SENSEX at 10:10 AM with ATM Put (76200PE). The **12:00 PM Hard Time Cutoff Rule** exited the position at noon sharp, booking **+₹2,001.90 NET PROFIT (+6.1% on margin)**!
- **NIFTY Quantman 1165**: Entered ATM Call (23800CE) at 13:50 PM. As Nifty continued selling off towards 23,760, the **-15% Stop Loss** triggered at 15:05 PM, successfully cutting the trade at ₹134.2 and preventing catastrophic decay.
- **Daily Portfolio Risk Guard**: Overall portfolio drawdown was restricted to **-1.08%**, well below the maximum 2.5% daily risk budget. All trades closed flat before market close.

---

## 🌐 Live Web Terminal (Vercel)

The live algorithmic trading dashboard is permanently deployed on Vercel:
👉 **[https://options-paper-trader.vercel.app](https://options-paper-trader.vercel.app)**

- **Real-time Serverless API**: `https://options-paper-trader.vercel.app/api/all`
- **Interactive Equity Curve**: Powered by ApexCharts & Tailwind
- **Live Trade Ledger**: Filterable by strategy (SENSEX 1lyAlgos & NIFTY 1165)

---

## 🚢 Deployment Guide

This system supports multiple production deployment models depending on your infrastructure:

### Option 1: Native macOS Background Daemon (Zero Cost, Native)
Runs automatically in the background on your Mac via `launchd`, starting upon system login.
```bash
# 1. Install & start the background daemon
./deploy/install_mac_daemon.sh

# 2. Check running status & recent logs
./deploy/check_status.sh

# 3. Stream live logs
tail -f logs/daemon.log

# 4. Uninstall when needed
./deploy/uninstall_mac_daemon.sh
```

### Option 2: Docker & Docker Compose (Self-Hosted / VPS)
Runs both the background daemon and the web dashboard in isolated containers with persistent SQLite storage:
```bash
# Build & start services in background
docker compose up -d

# Check running containers
docker compose ps

# View logs
docker compose logs -f daemon

# Stop services
docker compose down
```
Access the web dashboard at `http://localhost:8501`.

### Option 3: Serverless GitHub Actions (100% Free Cloud Cron)
The repository includes a ready-to-use GitHub Actions workflow (`.github/workflows/daily_trading_session.yml`):
- **Trigger**: Every Monday to Friday at **15:45 IST** (10:15 UTC).
- **Execution**: Fetches today's intraday data, simulates candle ticks, applies slippage & statutory taxes.
- **Persistence**: Automatically commits and pushes the updated `data/paper_trader.db` back to your repo.
- **Cost**: 100% Free on GitHub standard runners.

### Option 4: Cloud PaaS (Render / Railway)
- **Render**: Connect this repository to Render. It automatically detects `render.yaml` and launches the Streamlit dashboard on a free web service.
- **Railway**: Connect repo and select Dockerfile or `Procfile`.

---

## 🔔 Real-Time Webhook Alerts

Receive daily trading recaps on your phone immediately after 15:35 IST. Set the following environment variables (or add them as GitHub Repository Secrets):

```bash
# Discord Webhook
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR/WEBHOOK/URL"

# Telegram Bot Alert
export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="987654321"
```

---

## 💻 Manual CLI & Dashboard Commands

```bash
# Check current account balance & margin
python main.py status

# Run today's market session immediately
python main.py run-today

# Run a specific historical date
python main.py run-today --date 2026-09-07

# Print daily report card
python main.py report

# Launch local web dashboard
python main.py dashboard
```

---

## 📁 Architecture & File Layout

```
options-paper-trader/
├── config/
│   └── settings.py          # Capital, lot sizing, brokerage & risk parameters
├── database/
│   └── ledger.py            # Persistent SQLite database (accounts, trades, snapshots)
├── execution/
│   ├── option_model.py      # ATM strike resolution & option pricing model
│   └── paper_broker.py      # Virtual broker with realistic slippage & statutory taxes
├── strategies/
│   ├── nifty_1165.py        # NIFTY 4-case engine + 2x Martingale recovery
│   └── sensex_1ly.py        # SENSEX opening breakout + 40-pt SL + 12:00 PM cutoff
├── scheduler/
│   ├── session_runner.py    # Daily session coordinator (ingests candles & executes)
│   └── daemon.py            # 24/7 background scheduler waking up on market mornings
├── reporting/
│   ├── dashboard.py         # Streamlit interactive web dashboard
│   └── notifier.py          # Daily recap generator with Discord & Telegram webhooks
├── deploy/
│   ├── com.likhith.optionspapertrader.plist  # macOS LaunchAgent configuration
│   ├── install_mac_daemon.sh               # 1-command installer
│   ├── uninstall_mac_daemon.sh             # Uninstaller
│   └── check_status.sh                     # Daemon status & log monitor
├── .github/workflows/
│   └── daily_trading_session.yml           # Automated cloud cron execution
├── Dockerfile               # Container build recipe
├── docker-compose.yml       # Multi-service daemon + dashboard composition
├── requirements.txt         # Pinned python dependencies
├── render.yaml              # Cloud PaaS deployment blueprint
├── Procfile                 # Process file for Heroku/Railway
├── data/
│   └── paper_trader.db      # SQLite persistent database file
├── tests/
│   └── test_paper_trader.py # Unit tests
├── run_daily.sh             # Shell execution wrapper
├── main.py                  # CLI entrypoint
└── README.md                # Master documentation
```
