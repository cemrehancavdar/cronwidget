"""Check runner functions shared between the marimo app and the huey worker."""

import shutil
import socket
import sqlite3
from datetime import datetime
from pathlib import Path

import httpx

_HERE = Path(__file__).parent
DB_PATH = _HERE / "checks.db"


# -- Results database --------------------------------------------------------


def init_db() -> None:
    con = sqlite3.connect(str(DB_PATH))
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS check_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_name TEXT NOT NULL,
            ran_at TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT NOT NULL
        )
        """
    )
    con.commit()
    con.close()


def save_check(name: str, status: str, message: str) -> None:
    con = sqlite3.connect(str(DB_PATH))
    con.execute(
        "INSERT INTO check_runs (check_name, ran_at, status, message) VALUES (?, ?, ?, ?)",
        (name, datetime.now().isoformat(), status, message),
    )
    con.commit()
    con.close()


# -- Check runners -----------------------------------------------------------


def run_http_check(url: str) -> tuple[str, str]:
    """Ping a URL, return (status, message)."""
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        if resp.status_code < 400:
            return "ok", f"{resp.status_code} ({resp.elapsed.total_seconds():.2f}s)"
        return "fail", f"HTTP {resp.status_code}"
    except httpx.TimeoutException:
        return "fail", "timeout"
    except httpx.RequestError as e:
        return "fail", str(e)


def run_git_check(repo: str) -> tuple[str, str]:
    """Check a GitHub repo for the latest commit."""
    try:
        resp = httpx.get(
            f"https://api.github.com/repos/{repo}/commits",
            params={"per_page": 1},
            timeout=10,
        )
        if resp.status_code != 200:
            return "fail", f"GitHub API returned {resp.status_code}"
        commits = resp.json()
        if not commits:
            return "ok", "no commits"
        latest = commits[0]
        sha = latest["sha"][:7]
        msg = latest["commit"]["message"].split("\n")[0][:80]
        date = latest["commit"]["committer"]["date"]
        return "ok", f"{sha}: {msg} ({date})"
    except Exception as e:
        return "fail", str(e)


def run_disk_check(path: str, threshold_pct: int = 90) -> tuple[str, str]:
    """Check disk usage against a threshold."""
    try:
        usage = shutil.disk_usage(path)
        pct = (usage.used / usage.total) * 100
        msg = f"{pct:.1f}% used ({usage.free // (1024**3)}GB free)"
        if pct >= threshold_pct:
            return "fail", f"OVER THRESHOLD: {msg}"
        return "ok", msg
    except Exception as e:
        return "fail", str(e)


def run_port_check(host: str, port: int, label: str = "") -> tuple[str, str]:
    """Check if a TCP port is listening."""
    label = label or f"{host}:{port}"
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return "ok", f"{label} is listening on {host}:{port}"
        return "fail", f"{label} is NOT listening on {host}:{port}"
    except Exception as e:
        return "fail", f"{label}: {e}"
