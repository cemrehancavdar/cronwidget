import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md("""
# Data Pipeline Scheduler

Configure fetch schedules for each data source using the cron builders below.
Pipelines run automatically on their cron schedule. Toggle **Enable** to start/stop each one.
Results are stored in a local SQLite database.
""")
    return (mo,)


@app.cell
def _():
    import json
    import logging
    import sqlite3
    import threading
    from datetime import datetime
    from pathlib import Path

    import httpx
    from croniter import croniter

    DB_PATH = Path("pipelines.db")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    def init_db() -> None:
        con = sqlite3.connect(str(DB_PATH))
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                record_count INTEGER NOT NULL,
                sample TEXT NOT NULL
            )
            """
        )
        con.commit()
        con.close()

    init_db()
    return DB_PATH, croniter, datetime, httpx, json, logging, sqlite3, threading


@app.cell
def _(DB_PATH, datetime, httpx, json, sqlite3):
    def save_run(pipeline: str, records: list[dict]) -> int:
        con = sqlite3.connect(str(DB_PATH))
        sample = json.dumps(records[:3], default=str)
        con.execute(
            "INSERT INTO pipeline_runs (pipeline, fetched_at, record_count, sample) VALUES (?, ?, ?, ?)",
            (pipeline, datetime.now().isoformat(), len(records), sample),
        )
        con.commit()
        con.close()
        return len(records)

    def fetch_hn_top_stories(limit: int = 10) -> list[dict]:
        story_ids = httpx.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10
        ).json()[:limit]
        stories = []
        for sid in story_ids:
            data = httpx.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10
            ).json()
            stories.append(
                {
                    "id": data.get("id"),
                    "title": data.get("title", ""),
                    "url": data.get("url", ""),
                    "score": data.get("score", 0),
                }
            )
        return stories

    def fetch_github_trending() -> list[dict]:
        resp = httpx.get(
            "https://api.github.com/search/repositories",
            params={"q": "created:>2026-03-14", "sort": "stars", "order": "desc", "per_page": 10},
            timeout=10,
        )
        items = resp.json().get("items", [])
        return [
            {
                "name": r["full_name"],
                "stars": r["stargazers_count"],
                "language": r.get("language", ""),
                "description": (r.get("description") or "")[:100],
            }
            for r in items
        ]

    def fetch_quotes(count: int = 5) -> list[dict]:
        quotes = []
        for _ in range(count):
            resp = httpx.get("https://zenquotes.io/api/random", timeout=10)
            data = resp.json()
            if data:
                quotes.append({"quote": data[0].get("q", ""), "author": data[0].get("a", "")})
        return quotes

    return fetch_github_trending, fetch_hn_top_stories, fetch_quotes, save_run


@app.cell
def _(
    croniter,
    datetime,
    logging,
    threading,
    save_run,
    fetch_hn_top_stories,
    fetch_github_trending,
    fetch_quotes,
):
    _logger = logging.getLogger("scheduler")

    _PIPELINES = {
        "hacker_news": fetch_hn_top_stories,
        "github_trending": fetch_github_trending,
        "quotes": fetch_quotes,
    }

    _scheduler_state: dict[str, dict] = {}

    def _run_loop(name: str, state: dict) -> None:
        stop_event = state["stop_event"]
        last_fire_minute = None

        while not stop_event.is_set():
            now = datetime.now()
            current_minute = now.replace(second=0, microsecond=0)

            if croniter.match(state["expression"], now) and current_minute != last_fire_minute:
                last_fire_minute = current_minute
                _logger.info("FIRING pipeline=%s expression=%s", name, state["expression"])
                try:
                    records = _PIPELINES[name]()
                    save_run(name, records)
                    _logger.info("SUCCESS pipeline=%s records=%d", name, len(records))
                except Exception as e:
                    _logger.error("FAILED pipeline=%s error=%s", name, e)

            stop_event.wait(timeout=30)

    def start_pipeline(name: str, expression: str) -> None:
        stop_pipeline(name)
        stop_event = threading.Event()
        state = {"expression": expression, "stop_event": stop_event, "thread": None}
        _scheduler_state[name] = state
        t = threading.Thread(target=_run_loop, args=(name, state), daemon=True)
        state["thread"] = t
        t.start()
        _logger.info("STARTED pipeline=%s expression=%s", name, expression)

    def stop_pipeline(name: str) -> None:
        if name in _scheduler_state:
            old = _scheduler_state.pop(name)
            old["stop_event"].set()
            if old["thread"] and old["thread"].is_alive():
                old["thread"].join(timeout=2)
            _logger.info("STOPPED pipeline=%s", name)

    def update_expression(name: str, expression: str) -> None:
        if name in _scheduler_state:
            _scheduler_state[name]["expression"] = expression

    return start_pipeline, stop_pipeline, update_expression


@app.cell
def _():
    from cronwidget import CronBuilder

    return (CronBuilder,)


@app.cell
def _(mo):
    mo.md("---\n## Hacker News Top Stories")
    return


@app.cell
def _(CronBuilder, mo):
    hn_cron = mo.ui.anywidget(CronBuilder(expression="0 */6 * * *"))
    hn_enabled = mo.ui.switch(label="Enable", value=False)
    mo.hstack([mo.md("**Schedule:**"), hn_cron, hn_enabled], gap=1)
    return hn_cron, hn_enabled


@app.cell
def _(hn_cron, hn_enabled, start_pipeline, stop_pipeline, update_expression, mo):
    if hn_enabled.value:
        start_pipeline("hacker_news", hn_cron.expression)
        mo.md(f"Pipeline **hacker_news** running on `{hn_cron.expression}`")
    else:
        stop_pipeline("hacker_news")
        mo.md("Pipeline **hacker_news** stopped")
    update_expression("hacker_news", hn_cron.expression)
    return


@app.cell
def _(mo):
    hn_btn = mo.ui.run_button(label="Run Now")
    hn_btn
    return (hn_btn,)


@app.cell
def _(fetch_hn_top_stories, hn_btn, mo, save_run):
    _result = None
    if hn_btn.value:
        _stories = fetch_hn_top_stories(limit=10)
        _count = save_run("hacker_news", _stories)
        _result = mo.md(
            f"Fetched **{_count}** stories\n\n"
            + "\n".join(f"- **{s['title']}** (score: {s['score']})" for s in _stories[:5])
        )
    _result if _result else mo.md("_Press Run Now to test manually_")
    return


@app.cell
def _(mo):
    mo.md("---\n## GitHub Trending Repos")
    return


@app.cell
def _(CronBuilder, mo):
    gh_cron = mo.ui.anywidget(CronBuilder(expression="0 9 * * 1-5"))
    gh_enabled = mo.ui.switch(label="Enable", value=False)
    mo.hstack([mo.md("**Schedule:**"), gh_cron, gh_enabled], gap=1)
    return gh_cron, gh_enabled


@app.cell
def _(gh_cron, gh_enabled, start_pipeline, stop_pipeline, update_expression, mo):
    if gh_enabled.value:
        start_pipeline("github_trending", gh_cron.expression)
        mo.md(f"Pipeline **github_trending** running on `{gh_cron.expression}`")
    else:
        stop_pipeline("github_trending")
        mo.md("Pipeline **github_trending** stopped")
    update_expression("github_trending", gh_cron.expression)
    return


@app.cell
def _(mo):
    gh_btn = mo.ui.run_button(label="Run Now")
    gh_btn
    return (gh_btn,)


@app.cell
def _(fetch_github_trending, gh_btn, mo, save_run):
    _result = None
    if gh_btn.value:
        _repos = fetch_github_trending()
        _count = save_run("github_trending", _repos)
        _result = mo.md(
            f"Fetched **{_count}** repos\n\n"
            + "\n".join(
                f"- **{r['name']}** ({r['stars']} stars) -- {r['description']}" for r in _repos[:5]
            )
        )
    _result if _result else mo.md("_Press Run Now to test manually_")
    return


@app.cell
def _(mo):
    mo.md("---\n## Random Quotes")
    return


@app.cell
def _(CronBuilder, mo):
    qt_cron = mo.ui.anywidget(CronBuilder(expression="*/30 * * * *"))
    qt_enabled = mo.ui.switch(label="Enable", value=False)
    mo.hstack([mo.md("**Schedule:**"), qt_cron, qt_enabled], gap=1)
    return qt_cron, qt_enabled


@app.cell
def _(qt_cron, qt_enabled, start_pipeline, stop_pipeline, update_expression, mo):
    if qt_enabled.value:
        start_pipeline("quotes", qt_cron.expression)
        mo.md(f"Pipeline **quotes** running on `{qt_cron.expression}`")
    else:
        stop_pipeline("quotes")
        mo.md("Pipeline **quotes** stopped")
    update_expression("quotes", qt_cron.expression)
    return


@app.cell
def _(mo):
    qt_btn = mo.ui.run_button(label="Run Now")
    qt_btn
    return (qt_btn,)


@app.cell
def _(fetch_quotes, mo, qt_btn, save_run):
    _result = None
    if qt_btn.value:
        _quotes = fetch_quotes(count=5)
        _count = save_run("quotes", _quotes)
        _result = mo.md(
            f"Fetched **{_count}** quotes\n\n"
            + "\n".join(f'- _"{q["quote"]}"_ -- {q["author"]}' for q in _quotes)
        )
    _result if _result else mo.md("_Press Run Now to test manually_")
    return


@app.cell
def _(mo):
    mo.md("---\n## Pipeline Run History")
    return


@app.cell
def _(DB_PATH, mo, sqlite3):
    _con = sqlite3.connect(str(DB_PATH))
    _rows = _con.execute(
        "SELECT pipeline, fetched_at, record_count FROM pipeline_runs ORDER BY id DESC LIMIT 20"
    ).fetchall()
    _con.close()

    _output = None
    if _rows:
        _table_data = [{"Pipeline": r[0], "Fetched At": r[1], "Records": r[2]} for r in _rows]
        _output = mo.ui.table(_table_data)
    else:
        _output = mo.md("_No runs yet. Hit a Run Now button or enable a pipeline._")
    _output
    return


if __name__ == "__main__":
    app.run()
