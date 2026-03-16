"""Huey worker — reads checks_config.json, registers periodic tasks, runs them.

Started automatically by the marimo control panel via Deploy, or manually:
    cd examples && uv run huey_consumer worker.huey -w 2 -k thread
"""

import json
import logging
from pathlib import Path

import chime
from huey import SqliteHuey, crontab

from checks import (
    init_db,
    run_disk_check,
    run_git_check,
    run_http_check,
    run_port_check,
    save_check,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("worker")

_HERE = Path(__file__).parent
CONFIG_PATH = _HERE / "checks_config.json"
HUEY_DB_PATH = _HERE / "huey.db"

huey = SqliteHuey(filename=str(HUEY_DB_PATH))
chime.theme("material")

CHECK_RUNNERS = {
    "http": lambda cfg: run_http_check(cfg["url"]),
    "git": lambda cfg: run_git_check(cfg["repo"]),
    "disk": lambda cfg: run_disk_check(cfg.get("path", "/"), cfg.get("threshold_pct", 90)),
    "port": lambda cfg: run_port_check(
        cfg.get("host", "localhost"), cfg.get("port", 5432), cfg.get("label", "")
    ),
}


def cron_to_huey(expression: str) -> crontab:
    """Convert a 5-field cron expression string to a huey crontab."""
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Expected 5-field cron expression, got: {expression!r}")
    minute, hour, day, month, day_of_week = parts
    return crontab(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week)


def load_and_register() -> None:
    """Load config and register all enabled checks as huey periodic tasks."""
    if not CONFIG_PATH.exists():
        logger.error("Config not found at %s. Deploy from the marimo app first.", CONFIG_PATH)
        return

    config = json.loads(CONFIG_PATH.read_text())
    checks = config.get("checks", {})
    enabled = {n: c for n, c in checks.items() if c.get("enabled", False)}

    if not enabled:
        logger.warning("No enabled checks in config.")
        return

    logger.info("Loading %d enabled check(s):", len(enabled))
    for name, cfg in enabled.items():
        check_type = cfg["type"]
        expression = cfg["expression"]
        runner = CHECK_RUNNERS.get(check_type)
        if not runner:
            logger.error("Unknown check type %s for %s, skipping", check_type, name)
            continue

        schedule = cron_to_huey(expression)

        @huey.periodic_task(schedule, name=name)
        def _task(cfg=cfg, name=name, check_type=check_type, runner=runner):
            logger.info("RUNNING %s [%s]", name, check_type)
            try:
                status, message = runner(cfg)
            except Exception as e:
                status, message = "fail", str(e)

            save_check(name, status, message)

            if status == "ok":
                logger.info("  OK: %s", message)
            else:
                logger.warning("  FAIL: %s", message)
                chime.error()

        logger.info("  %s [%s] -> %s", name, check_type, expression)


init_db()
load_and_register()
