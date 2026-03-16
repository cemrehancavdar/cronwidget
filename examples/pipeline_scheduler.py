import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md("""
# Data Pipeline Scheduler

Configure fetch schedules for each data source using the cron builders below.
Hit **Run Now** to test a pipeline, or copy the cron expression into your scheduler.
Results are stored in a local SQLite database.
""")
    return (mo,)


@app.cell
def _():
    import json
    import sqlite3
    from datetime import datetime
    from pathlib import Path

    import httpx

    DB_PATH = Path("pipelines.db")

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
    return DB_PATH, datetime, httpx, json, sqlite3


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

    return save_run, fetch_hn_top_stories, fetch_github_trending, fetch_quotes


@app.cell
def _():
    from cronwidget import CronBuilder

    return (CronBuilder,)


@app.cell
def _(mo):
    mo.md("## Hacker News Top Stories")
    return


@app.cell
def _(CronBuilder, mo):
    hn_cron = mo.ui.anywidget(CronBuilder(expression="0 */6 * * *"))
    mo.hstack([mo.md("**Schedule:**"), hn_cron], gap=1)
    return (hn_cron,)


@app.cell
def _(mo):
    hn_btn = mo.ui.run_button(label="Run Now")
    hn_btn
    return (hn_btn,)


@app.cell
def _(hn_btn, hn_cron, fetch_hn_top_stories, save_run, mo):
    _result = None
    if hn_btn.value:
        _stories = fetch_hn_top_stories(limit=10)
        _count = save_run("hacker_news", _stories)
        _result = mo.md(
            f"Fetched **{_count}** stories. Schedule: `{hn_cron.expression}`\n\n"
            + "\n".join(f"- **{s['title']}** (score: {s['score']})" for s in _stories[:5])
        )
    _result if _result else mo.md("_Press Run Now to test this pipeline_")
    return


@app.cell
def _(mo):
    mo.md("## GitHub Trending Repos")
    return


@app.cell
def _(CronBuilder, mo):
    gh_cron = mo.ui.anywidget(CronBuilder(expression="0 9 * * 1-5"))
    mo.hstack([mo.md("**Schedule:**"), gh_cron], gap=1)
    return (gh_cron,)


@app.cell
def _(mo):
    gh_btn = mo.ui.run_button(label="Run Now")
    gh_btn
    return (gh_btn,)


@app.cell
def _(gh_btn, gh_cron, fetch_github_trending, save_run, mo):
    _result = None
    if gh_btn.value:
        _repos = fetch_github_trending()
        _count = save_run("github_trending", _repos)
        _result = mo.md(
            f"Fetched **{_count}** repos. Schedule: `{gh_cron.expression}`\n\n"
            + "\n".join(
                f"- **{r['name']}** ({r['stars']} stars) -- {r['description']}" for r in _repos[:5]
            )
        )
    _result if _result else mo.md("_Press Run Now to test this pipeline_")
    return


@app.cell
def _(mo):
    mo.md("## Random Quotes")
    return


@app.cell
def _(CronBuilder, mo):
    qt_cron = mo.ui.anywidget(CronBuilder(expression="*/30 * * * *"))
    mo.hstack([mo.md("**Schedule:**"), qt_cron], gap=1)
    return (qt_cron,)


@app.cell
def _(mo):
    qt_btn = mo.ui.run_button(label="Run Now")
    qt_btn
    return (qt_btn,)


@app.cell
def _(qt_btn, qt_cron, fetch_quotes, save_run, mo):
    _result = None
    if qt_btn.value:
        _quotes = fetch_quotes(count=5)
        _count = save_run("quotes", _quotes)
        _result = mo.md(
            f"Fetched **{_count}** quotes. Schedule: `{qt_cron.expression}`\n\n"
            + "\n".join(f'- _"{q["quote"]}"_ -- {q["author"]}' for q in _quotes)
        )
    _result if _result else mo.md("_Press Run Now to test this pipeline_")
    return


@app.cell
def _(mo):
    mo.md("---\n## Pipeline Run History")
    return


@app.cell
def _(DB_PATH, sqlite3, mo):
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
        _output = mo.md("_No runs yet. Hit a Run Now button above to get started._")
    _output
    return


if __name__ == "__main__":
    app.run()
