# KES / TZS Rate Tracker

A small local web app that periodically samples the Kenyan shilling to Tanzanian shilling exchange rate, stores successful samples on the computer running the app, and displays them on a visual dashboard.

## Run

1. Install Python 3.10 or later.
2. From this folder, run `python app.py`.
3. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).
4. Leave the process running to keep collecting. Stop it with `Ctrl+C`.

The app uses Python's standard library; it does not need packages or API credentials. The SQLite database is created at `data/rates.sqlite3`. Set `RATE_DB_PATH` to use another local path.

## Polling and rate source

The poller uses East Africa Time (UTC+3, no daylight-saving changes) and samples every 10 minutes from 06:00 through 18:00, inclusive. If launched during those hours it fetches once immediately, then continues on the next 10-minute clock boundary. While the app is stopped, no polling occurs.

Rates are fetched from the free, no-key `open.er-api.com` endpoint. The provider publishes rates on its own schedule (typically daily), so checking every 10 minutes records repeated observations when the provider has not published a new rate; it does not make the underlying quote update every 10 minutes. Samples that were successfully fetched are stored locally. The dashboard labels the local collection time and, when available, the provider's last-update time separately.

## Local endpoints

- `GET /api/status` — poller status and most recent saved sample.
- `GET /api/rates?limit=100` — saved samples, oldest first; `limit` can be 1–500.
