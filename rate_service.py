"""Fetches KES/TZS rates and runs the daytime polling schedule."""

import json
import sqlite3
import threading
from datetime import datetime, time, timedelta, timezone
from urllib.request import Request, urlopen


EAT = timezone(timedelta(hours=3), name="EAT")
START_TIME = time(6, 0)
END_TIME = time(18, 0)
POLL_MINUTES = 10
RATE_API_URL = "https://open.er-api.com/v6/latest/KES"


def now_eat():
    return datetime.now(EAT)


def is_polling_time(moment):
    local_time = moment.astimezone(EAT).time().replace(tzinfo=None)
    return START_TIME <= local_time <= END_TIME


def next_poll_time(moment):
    """Return the next 10-minute clock boundary within the daily window."""
    moment = moment.astimezone(EAT)
    local_time = moment.time().replace(tzinfo=None)
    if local_time < START_TIME:
        return datetime.combine(moment.date(), START_TIME, EAT)
    if local_time >= END_TIME:
        return datetime.combine(moment.date() + timedelta(days=1), START_TIME, EAT)

    next_minute = ((moment.minute // POLL_MINUTES) + 1) * POLL_MINUTES
    boundary = moment.replace(second=0, microsecond=0)
    if next_minute == 60:
        boundary = boundary.replace(minute=0) + timedelta(hours=1)
    else:
        boundary = boundary.replace(minute=next_minute)

    if boundary.time() > END_TIME:
        return datetime.combine(moment.date() + timedelta(days=1), START_TIME, EAT)
    return boundary


def fetch_kes_tzs_rate():
    request = Request(
        RATE_API_URL,
        headers={"User-Agent": "KES-TZS-Rate-Tracker/1.0"},
    )
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)

    if not isinstance(payload, dict):
        raise RuntimeError("Rate provider returned an invalid response.")
    if payload.get("result") != "success":
        raise RuntimeError(f"Rate provider returned an unsuccessful response: {payload.get('result')}")

    rates = payload.get("rates")
    rate = rates.get("TZS") if isinstance(rates, dict) else None
    if not isinstance(rate, (int, float)) or rate <= 0:
        raise RuntimeError("Rate provider response did not contain a valid TZS rate.")

    return float(rate), payload.get("time_last_update_utc")


class RatePoller:
    def __init__(self, store):
        self.store = store
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._state = {
            "last_attempt": None,
            "last_error": None,
            "next_poll": None,
        }
        self._thread = threading.Thread(target=self._run, name="rate-poller", daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def status(self):
        with self._lock:
            state = dict(self._state)
        return {
            **state,
            "running": self._thread.is_alive() and not self._stop_event.is_set(),
            "in_polling_window": is_polling_time(now_eat()),
        }

    def _poll_once(self):
        attempted_at = now_eat().isoformat(timespec="seconds")
        with self._lock:
            self._state["last_attempt"] = attempted_at
        try:
            rate, provider_updated_at = fetch_kes_tzs_rate()
            self.store.save_sample(
                attempted_at,
                rate,
                provider_updated_at,
            )
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
            with self._lock:
                self._state["last_error"] = str(error)
        else:
            with self._lock:
                self._state["last_error"] = None

    def _run(self):
        # Fetch once on launch during business hours, then align future polls to
        # the next 10-minute clock boundary (06:00, 06:10, ... 18:00 EAT).
        if is_polling_time(now_eat()):
            self._poll_once()

        while not self._stop_event.is_set():
            current_time = now_eat()
            scheduled_time = next_poll_time(current_time)
            with self._lock:
                self._state["next_poll"] = scheduled_time.isoformat(timespec="seconds")
            delay = max(0, (scheduled_time - current_time).total_seconds())
            if self._stop_event.wait(delay):
                break
            if is_polling_time(now_eat()):
                self._poll_once()
