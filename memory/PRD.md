# Stock Dip Analyzer — PRD

## Problem Statement
Build a production-ready web app for long-term Indian stock investing that detects high-quality dip opportunities and presents them in a clean dashboard. Target user: small capital investor (~₹5k) doing long-term accumulation.

## Stack
- Backend: FastAPI + MongoDB (motor async)
- Frontend: React + TailwindCSS + Recharts + Shadcn UI
- Data: yfinance (Yahoo Finance) with MongoDB cache + in-memory fallback
- Notifications: ntfy.sh
- Scheduler: APScheduler (IST market-aware)

## Architecture
- `/app/backend/config.py` — env-driven config (watchlist defaults, ntfy topic, cache TTL)
- `/app/backend/data.py` — yfinance fetch + MongoDB cache with stale fallback + retries
- `/app/backend/indicators.py` — RSI (Wilder), MA50, MA200
- `/app/backend/scorer.py` — 0-100 scoring (Drawdown 30%, MA 25%, RSI 25%, Confidence 20%)
- `/app/backend/notifier.py` — ntfy POST with urgent priority, never raises
- `/app/backend/scheduler.py` — hourly cron 10-15 IST weekdays + post-close 15:45 IST, per-ticker daily dedupe
- `/app/backend/server.py` — API routes

## API
- `GET /api/analyze` — full watchlist analysis + best buy
- `GET /api/stock/{ticker}` — detail + 1y history (close, ma50, ma200, rsi)
- `GET /api/watchlist` — tickers (defaults + custom)
- `POST /api/watchlist` — add custom ticker (validated via yfinance)
- `DELETE /api/watchlist/{ticker}` — remove custom ticker
- `POST /api/refresh` — clear cache + re-analyze
- `POST /api/test-notification` — send test ntfy
- `GET /api/status` — scheduler + notifier health
- `GET /api/alerts/today` — today's sent alerts

## Implemented (2026-05-02)
- Backend: all endpoints, scoring, indicators, yfinance with Mongo cache, ntfy notifier, APScheduler market-aware jobs with daily dedupe
- Frontend: Dashboard with Header (scheduler/ntfy status), BestBuyCard, WatchlistManager (add/remove), AnalysisTable (color-coded), StockDetailDialog (price+MA + RSI Recharts)
- Design: light "Organic/Earthy" theme, Outfit + IBM Plex Sans fonts, custom signal color chips

### Update 2026-05-02 (feature: market discovery feed)
- Added `MARKET_UNIVERSE` (~40 curated NSE tickers: Nifty 50 + ETFs) in `config.py`
- New `GET /api/discover?top=N&include_weak=bool` — scans universe, returns top-scored opps sorted by score, uses the same 45-min cache
- Home screen now shows **DiscoveryFeed** at the top (ranked cards with "Watch"/"In watchlist" action), above Best Buy + Watchlist + Analysis Table
- UI includes "Show weak" toggle and per-card quick add-to-watchlist

### Update 2026-05-02 (feature: dip reasoning in detail dialog)
- `scorer.py` now returns `reasons[]` + `conclusion` — dynamic bullets based on drawdown severity, RSI zone, MA50/MA200 position
- `StockDetailDialog` shows "Why this is a dip" box with colored bullets and a signal-colored conclusion

### Update 2026-05-02 (feature: Investment Plan)
- New `GET /api/investment-plan?budget=5000` — picks top 1-2 stocks with score >= 60 from market universe, allocates proportional to score (rounded to ₹100, residual on last), falls back to full-budget NIFTYBEES.NS if none qualify
- Home screen `InvestmentPlan` section with visual allocation bar, per-stock cards (amount, %, score, shares, signal), budget input, clickable cards open detail dialog
- Validated: 29/29 backend tests (9 new), full frontend flows (iteration_3)

## Env Vars (backend/.env)
- `MONGO_URL`, `DB_NAME`
- `NTFY_TOPIC=deepraj-stock-dip-9827`
- `NTFY_BASE=https://ntfy.sh`
- `CACHE_TTL_MINUTES=45`

## Defaults
Watchlist: NIFTYBEES.NS, BANKBEES.NS, RELIANCE.NS, TCS.NS, INFY.NS
Max custom: 10

## Backlog / Next
- P1: SMS/email channel fallback for notifications
- P1: Persist historical scores for trend view
- P2: Portfolio simulation (entry price tracking)
- P2: Export CSV of analysis
- P2: Sector/industry grouping
