import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md("""
    # Background Worker Control Panel

    Configure and manage recurring checks on your local machine.
    Set cron schedules, enable/disable checks, and hit **Deploy** to start the worker.
    The worker plays a chime sound when something fails.
    """)
    return (mo,)


@app.cell
def _():
    import json
    import os
    import signal
    import sqlite3
    import subprocess
    from datetime import datetime
    from pathlib import Path

    from checks import (
        DB_PATH,
        init_db,
        run_disk_check,
        run_git_check,
        run_http_check,
        run_port_check,
    )
    from cronwidget.cron_builder import next_runs

    _HERE = Path(__file__).parent if "__file__" in dir() else Path(".")
    CONFIG_PATH = _HERE / "checks_config.json"
    WORKER_PATH = _HERE / "worker.py"
    PID_PATH = _HERE / ".worker.pid"

    init_db()
    return (
        CONFIG_PATH,
        DB_PATH,
        PID_PATH,
        WORKER_PATH,
        next_runs,
        json,
        os,
        run_disk_check,
        run_git_check,
        run_http_check,
        run_port_check,
        signal,
        sqlite3,
        subprocess,
    )


@app.cell
def _(CONFIG_PATH, PID_PATH, WORKER_PATH, json, os, signal, subprocess):
    def _kill_old_worker() -> None:
        if PID_PATH.exists():
            try:
                old_pid = int(PID_PATH.read_text().strip())
                os.kill(old_pid, signal.SIGTERM)
            except (ProcessLookupError, ValueError, OSError):
                pass
            PID_PATH.unlink(missing_ok=True)

    def deploy_worker(config: dict) -> str:
        CONFIG_PATH.write_text(json.dumps(config, indent=2))
        _kill_old_worker()
        proc = subprocess.Popen(
            ["uv", "run", "huey_consumer", "worker.huey", "-w", "2", "-k", "thread"],
            cwd=str(WORKER_PATH.parent),
            start_new_session=True,
        )
        PID_PATH.write_text(str(proc.pid))
        return f"Worker started (PID {proc.pid})"

    def stop_worker() -> str:
        _kill_old_worker()
        return "Worker stopped"

    def worker_status() -> str:
        if not PID_PATH.exists():
            return "stopped"
        try:
            pid = int(PID_PATH.read_text().strip())
            os.kill(pid, 0)
            return f"running (PID {pid})"
        except (ProcessLookupError, ValueError, OSError):
            PID_PATH.unlink(missing_ok=True)
            return "stopped"

    return deploy_worker, stop_worker, worker_status


@app.cell
def _():
    from cronwidget import CronBuilder

    return (CronBuilder,)


@app.cell
def _(mo):
    mo.md("""
    ---
    ## HTTP Health Check
    """)
    return


@app.cell
def _(CronBuilder, mo):
    http_url = mo.ui.text(value="https://httpbin.org/status/200", label="URL", full_width=True)
    http_cron = mo.ui.anywidget(CronBuilder(expression="*/5 * * * *"))
    http_enabled = mo.ui.switch(label="Enable", value=True)
    mo.vstack(
        [
            http_url,
            mo.hstack([mo.md("**Schedule:**"), http_cron, http_enabled], gap=1),
        ]
    )
    return http_cron, http_enabled, http_url


@app.cell
def _(mo):
    http_test_btn = mo.ui.run_button(label="Test Now")
    http_test_btn
    return (http_test_btn,)


@app.cell
def _(http_test_btn, http_url, mo, run_http_check):
    _result = None
    if http_test_btn.value:
        _status, _msg = run_http_check(http_url.value)
        _color = "green" if _status == "ok" else "red"
        _result = mo.md(f"<span style='color:{_color}'>**{_status.upper()}**: {_msg}</span>")
    _result if _result else mo.md("_Press Test Now to run this check_")
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Git Repo Monitor
    """)
    return


@app.cell
def _(CronBuilder, mo):
    git_repo = mo.ui.text(
        value="koaning/wigglystuff", label="GitHub repo (owner/name)", full_width=True
    )
    git_cron = mo.ui.anywidget(CronBuilder(expression="0 */2 * * *"))
    git_enabled = mo.ui.switch(label="Enable", value=True)
    mo.vstack(
        [
            git_repo,
            mo.hstack([mo.md("**Schedule:**"), git_cron, git_enabled], gap=1),
        ]
    )
    return git_cron, git_enabled, git_repo


@app.cell
def _(mo):
    git_test_btn = mo.ui.run_button(label="Test Now")
    git_test_btn
    return (git_test_btn,)


@app.cell
def _(git_repo, git_test_btn, mo, run_git_check):
    _result = None
    if git_test_btn.value:
        _status, _msg = run_git_check(git_repo.value)
        _color = "green" if _status == "ok" else "red"
        _result = mo.md(f"<span style='color:{_color}'>**{_status.upper()}**: {_msg}</span>")
    _result if _result else mo.md("_Press Test Now to run this check_")
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Disk Space Check
    """)
    return


@app.cell
def _(CronBuilder, mo):
    disk_path = mo.ui.text(value="/", label="Mount path", full_width=True)
    disk_threshold = mo.ui.slider(start=50, stop=99, step=1, value=90, label="Alert threshold (%)")
    disk_cron = mo.ui.anywidget(CronBuilder(expression="0 */6 * * *"))
    disk_enabled = mo.ui.switch(label="Enable", value=True)
    mo.vstack(
        [
            mo.hstack([disk_path, disk_threshold], gap=1),
            mo.hstack([mo.md("**Schedule:**"), disk_cron, disk_enabled], gap=1),
        ]
    )
    return disk_cron, disk_enabled, disk_path, disk_threshold


@app.cell
def _(mo):
    disk_test_btn = mo.ui.run_button(label="Test Now")
    disk_test_btn
    return (disk_test_btn,)


@app.cell
def _(disk_path, disk_test_btn, disk_threshold, mo, run_disk_check):
    _result = None
    if disk_test_btn.value:
        _status, _msg = run_disk_check(disk_path.value, disk_threshold.value)
        _color = "green" if _status == "ok" else "red"
        _result = mo.md(f"<span style='color:{_color}'>**{_status.upper()}**: {_msg}</span>")
    _result if _result else mo.md("_Press Test Now to run this check_")
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Port Check
    """)
    return


@app.cell
def _(CronBuilder, mo):
    port_host = mo.ui.text(value="localhost", label="Host")
    port_number = mo.ui.number(start=1, stop=65535, step=1, value=5432, label="Port")
    port_label = mo.ui.text(value="postgres", label="Service name")
    port_cron = mo.ui.anywidget(CronBuilder(expression="*/10 * * * *"))
    port_enabled = mo.ui.switch(label="Enable", value=False)
    mo.vstack(
        [
            mo.hstack([port_host, port_number, port_label], gap=1),
            mo.hstack([mo.md("**Schedule:**"), port_cron, port_enabled], gap=1),
        ]
    )
    return port_cron, port_enabled, port_host, port_label, port_number


@app.cell
def _(mo):
    port_test_btn = mo.ui.run_button(label="Test Now")
    port_test_btn
    return (port_test_btn,)


@app.cell
def _(mo, port_host, port_label, port_number, port_test_btn, run_port_check):
    _result = None
    if port_test_btn.value:
        _status, _msg = run_port_check(port_host.value, port_number.value, port_label.value)
        _color = "green" if _status == "ok" else "red"
        _result = mo.md(f"<span style='color:{_color}'>**{_status.upper()}**: {_msg}</span>")
    _result if _result else mo.md("_Press Test Now to run this check_")
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Worker Control
    """)
    return


@app.cell
def _(mo):
    refresh = mo.ui.refresh(default_interval="10s", label="Auto-refresh")
    refresh
    return (refresh,)


@app.cell
def _(mo, refresh, worker_status):
    refresh
    _status = worker_status()
    _color = "green" if "running" in _status else "red"
    mo.md(f"**Worker status:** <span style='color:{_color}'>{_status}</span>")
    return


@app.cell
def _(
    next_runs,
    mo,
    http_url,
    http_cron,
    http_enabled,
    git_repo,
    git_cron,
    git_enabled,
    disk_path,
    disk_cron,
    disk_enabled,
    port_label,
    port_cron,
    port_enabled,
):
    def _next_run(expression: str) -> str:
        runs = next_runs(expression, n=1)
        return runs[0].strftime("%H:%M %a %b %d") if runs else "?"

    _checks = [
        ("HTTP Health", http_url.value, http_cron.expression, http_enabled.value),
        ("Git Monitor", git_repo.value, git_cron.expression, git_enabled.value),
        ("Disk Space", disk_path.value, disk_cron.expression, disk_enabled.value),
        ("Port Check", port_label.value, port_cron.expression, port_enabled.value),
    ]

    _rows = []
    for name, target, expr, enabled in _checks:
        _status_icon = (
            "<span style='color:green'>ON</span>"
            if enabled
            else "<span style='color:gray'>OFF</span>"
        )
        _next = _next_run(expr) if enabled else "--"
        _rows.append(f"| {_status_icon} | **{name}** | {target} | `{expr}` | {_next} |")

    mo.md(
        "| Status | Check | Target | Schedule | Next Run |\n"
        "|--------|-------|--------|----------|----------|\n" + "\n".join(_rows)
    )
    return


@app.cell
def _(mo):
    deploy_btn = mo.ui.run_button(label="Deploy", kind="success")
    stop_btn = mo.ui.run_button(label="Stop Worker", kind="danger")
    mo.hstack([deploy_btn, stop_btn], gap=1)
    return deploy_btn, stop_btn


@app.cell
def _(
    deploy_btn,
    deploy_worker,
    disk_cron,
    disk_enabled,
    disk_path,
    disk_threshold,
    git_cron,
    git_enabled,
    git_repo,
    http_cron,
    http_enabled,
    http_url,
    json,
    mo,
    port_cron,
    port_enabled,
    port_host,
    port_label,
    port_number,
    stop_btn,
    stop_worker,
):
    _result = None
    if deploy_btn.value:
        _config = {
            "checks": {
                "http_health": {
                    "type": "http",
                    "url": http_url.value,
                    "expression": http_cron.expression,
                    "enabled": http_enabled.value,
                },
                "git_monitor": {
                    "type": "git",
                    "repo": git_repo.value,
                    "expression": git_cron.expression,
                    "enabled": git_enabled.value,
                },
                "disk_space": {
                    "type": "disk",
                    "path": disk_path.value,
                    "threshold_pct": disk_threshold.value,
                    "expression": disk_cron.expression,
                    "enabled": disk_enabled.value,
                },
                "port_check": {
                    "type": "port",
                    "host": port_host.value,
                    "port": port_number.value,
                    "label": port_label.value,
                    "expression": port_cron.expression,
                    "enabled": port_enabled.value,
                },
            }
        }
        _msg = deploy_worker(_config)
        _result = mo.md(f"{_msg}\n\n```json\n{json.dumps(_config, indent=2)}\n```")
    elif stop_btn.value:
        _msg = stop_worker()
        _result = mo.md(_msg)
    _result if _result else mo.md("_Configure checks above, then hit Deploy._")
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Check History
    """)
    return


@app.cell
def _(DB_PATH, mo, refresh, sqlite3):
    refresh

    _con = sqlite3.connect(str(DB_PATH))
    _rows = _con.execute(
        "SELECT check_name, ran_at, status, message FROM check_runs ORDER BY id DESC LIMIT 30"
    ).fetchall()
    _con.close()

    _output = None
    if _rows:
        _table_data = [
            {"Check": r[0], "Ran At": r[1], "Status": r[2], "Message": r[3]} for r in _rows
        ]
        _output = mo.ui.table(_table_data)
    else:
        _output = mo.md("_No check runs yet. Deploy the worker to start._")
    _output
    return


if __name__ == "__main__":
    app.run()
