"""
IWT Stud Sensor - Connect API client (v4)

How a sensor reports to Connect: once a sync interval, the minute's stud count
goes into a local buffer, and everything the buffer holds is posted to
connectCoreAPI as one report:

    POST {API_URL}/heading/headers/{HEAD_ID}/telemetry
    X-Device-Token: {DEVICE_TOKEN}
    {"readings": [{"at": "2026-10-09T10:22:00-04:00", "count": 64}, ...],
     "ip": "192.168.1.78", "boot": false}

The server writes `heading_rates` and the header's machine columns, and puts a
paused lot back to work when counts arrive. A sensor no longer talks to the
database at all, and holds no database credential.

The buffer (SQLite, `buffer.db` beside this file) is what makes a report safe to
lose: a count stays in it until the server has acknowledged it, survives a
reboot, and is resent if the answer never came. The server skips a reading it
already has (same header, same `at`), so a resend never counts twice.

Standard library only, so updating a Pi is `git pull` and a restart.
"""
import datetime
import json
import socket
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

# A buffered reading older than this is dropped: the server refuses anything
# past 7 days, and a week of a Pi's minutes is about 4,200 rows.
KEEP_SECONDS = 7 * 24 * 3600

# Readings per report. The server takes up to 2000; 500 keeps a report small
# and lets a backlog drain at 500 a minute.
BATCH = 500


def now_iso():
    """The local time with its UTC offset, e.g. 2026-10-09T10:22:00-04:00."""
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def local_ip():
    """This Pi's LAN address, or None. Opens no connection: a UDP socket only
    asks the kernel which interface would route to the address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None


class ReadingBuffer:
    """Readings not yet acknowledged by the server, oldest first."""

    def __init__(self, path):
        self.db = sqlite3.connect(str(path))
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS readings ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " at TEXT NOT NULL,"
            " epoch REAL NOT NULL,"
            " count INTEGER NOT NULL)"
        )
        self.db.commit()

    def add(self, at, count):
        self.db.execute("INSERT INTO readings (at, epoch, count) VALUES (?, ?, ?)", (at, time.time(), count))
        self.db.commit()

    def oldest(self, limit):
        return self.db.execute("SELECT id, at, count FROM readings ORDER BY id LIMIT ?", (limit,)).fetchall()

    def remove(self, ids):
        if ids:
            self.db.executemany("DELETE FROM readings WHERE id = ?", [(i,) for i in ids])
            self.db.commit()

    def prune(self):
        cur = self.db.execute("DELETE FROM readings WHERE epoch < ?", (time.time() - KEEP_SECONDS,))
        self.db.commit()
        return cur.rowcount

    def size(self):
        return self.db.execute("SELECT COUNT(*) FROM readings").fetchone()[0]

    def close(self):
        self.db.close()


class ConnectClient:
    """One endpoint: the header's telemetry."""

    def __init__(self, api_url, head_id, token, timeout=10):
        self.url = f"{api_url.rstrip('/')}/heading/headers/{head_id}/telemetry"
        self.token = token
        self.timeout = timeout

    def post(self, readings, ip, boot):
        """Returns (status, body): status None when the server was not reached."""
        payload = {"readings": readings, "boot": bool(boot)}
        if ip:
            payload["ip"] = ip

        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Device-Token": self.token or "",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, _json(response.read())
        except urllib.error.HTTPError as e:
            return e.code, _json(e.read())
        except (urllib.error.URLError, OSError) as e:
            return None, {"error": str(e)}


def _json(raw):
    try:
        return json.loads(raw.decode("utf-8")) if raw else {}
    except (ValueError, UnicodeDecodeError):
        return {}


class Reporter:
    """The sync step both sensor scripts run: buffer the count, send the buffer."""

    def __init__(self, client, buffer, logger):
        self.client = client
        self.buffer = buffer
        self.logger = logger
        self.boot_pending = True   # clears headerAlarm on the first report after start
        self.api_ok = False
        self.last_ip = None

    def report(self, count):
        """Buffer `count` (if any) and send what the buffer holds. Returns True
        when the server acknowledged the report."""
        if count > 0:
            self.buffer.add(now_iso(), count)

        dropped = self.buffer.prune()
        if dropped:
            self.logger.warning(f"Dropped {dropped} buffered readings older than 7 days")

        rows = self.buffer.oldest(BATCH)
        self.last_ip = local_ip()
        status, body = self.client.post([{"at": at, "count": c} for (_, at, c) in rows], self.last_ip, self.boot_pending)

        if status == 200:
            self.buffer.remove([row_id for (row_id, _, _) in rows])
            self.boot_pending = False
            self.api_ok = True
            sent = sum(c for (_, _, c) in rows)
            resumed = body.get("resumedLot")
            if rows:
                self.logger.info(
                    f"✓ Synced {sent} counts in {len(rows)} readings"
                    f" ({body.get('accepted', '?')} new, {body.get('duplicates', 0)} already had)"
                    f" (IP: {self.last_ip})"
                )
            else:
                self.logger.debug(f"✓ Heartbeat (IP: {self.last_ip})")
            if resumed:
                self.logger.info(f"✓ Lot {resumed} was paused and is heading again")
            if self.buffer.size():
                self.logger.info(f"Backlog: {self.buffer.size()} readings still to send")
            return True

        self.api_ok = False

        if status in (401, 403):
            self.logger.critical("✗ Connect refused the device token — check DEVICE_TOKEN in .env. Counts are kept.")
        elif status == 422:
            # A reading the server will never take (a clock jumped, say) would
            # block the buffer for good, so drop exactly the ones it named.
            bad = _rejected_rows(body, rows)
            self.buffer.remove(bad)
            self.logger.error(f"✗ Connect rejected the report: {body.get('errors')} — dropped {len(bad)} bad readings")
        elif status is None:
            self.logger.warning(f"✗ Connect unreachable ({body.get('error')}); {self.buffer.size()} readings buffered")
        else:
            self.logger.error(f"✗ Connect answered {status}: {body.get('detail', body)}; {self.buffer.size()} readings buffered")

        return False


def _rejected_rows(body, rows):
    """The buffer ids of the readings a 422 named as `readings.N`."""
    ids = []
    for key in (body.get("errors") or {}):
        if key.startswith("readings.") and key[9:].isdigit():
            index = int(key[9:])
            if index < len(rows):
                ids.append(rows[index][0])
    return ids
