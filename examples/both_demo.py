import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md("# Widget Prototypes")
    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    ## CronBuilder
    """)
    return


@app.cell
def _(mo):
    from cronwidget import CronBuilder

    # Wrap with mo.ui.anywidget to get .value reactivity
    cron = mo.ui.anywidget(CronBuilder(expression="*/5 * * * 1-5"))
    cron
    return (cron,)


@app.cell
def _(cron, mo):
    mo.md(f"""
    **`.value` (reactive dict):**
    ```python
    {cron.value}
    ```

    **`.expression` (direct trait):** `{cron.expression}`

    **`.widget.describe()`:** {cron.widget.describe()}

    **`.widget.fields`:** `{cron.widget.fields}`

    **`.widget.next_runs(3)`:** {cron.widget.next_runs(3)}
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## VirtualJoystick
    """)
    return


@app.cell
def _(mo):
    from cronwidget import VirtualJoystick

    stick = mo.ui.anywidget(VirtualJoystick(size=220, deadzone=0.1))
    stick
    return (stick,)


@app.cell
def _(mo, stick):
    mo.md(f"""
    **`.value`:**
    ```python
    {stick.value}
    ```

    | Property  | Value |
    |-----------|-------|
    | X         | {stick.x:.3f} |
    | Y         | {stick.y:.3f} |
    | Angle     | {stick.widget.angle:.1f} deg |
    | Magnitude | {stick.widget.magnitude:.3f} |
    """)
    return


if __name__ == "__main__":
    app.run()
