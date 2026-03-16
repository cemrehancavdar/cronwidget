import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md("# CronBuilder Widget Demo")
    return (mo,)


@app.cell
def _():
    from cronwidget import CronBuilder

    cron = CronBuilder(expression="*/5 * * * *")
    cron
    return (cron,)


@app.cell
def _(cron, mo):
    mo.md(f"""
    **Current expression:** `{cron.expression}`

    **Description:** {cron.describe()}

    **Fields:** {cron.fields}
    """)
    return


if __name__ == "__main__":
    app.run()
