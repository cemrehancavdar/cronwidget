import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md("# VirtualJoystick Widget Demo")
    return (mo,)


@app.cell
def _():
    from cronwidget import VirtualJoystick

    stick = VirtualJoystick(size=250, deadzone=0.1)
    stick
    return (stick,)


@app.cell
def _(mo, stick):
    mo.md(
        f"""
        **Position:** x={stick.x:.3f}, y={stick.y:.3f}

        **Angle:** {stick.angle:.1f} degrees

        **Magnitude:** {stick.magnitude:.3f}
        """
    )
    return


@app.cell
def _():
    from cronwidget import VirtualJoystick as VJ

    stick_no_spring = VJ(size=150, spring_back=False, deadzone=0.15)
    stick_no_spring
    return (stick_no_spring,)


@app.cell
def _(mo, stick_no_spring):
    mo.md(
        f"""
        **No spring-back stick:** x={stick_no_spring.x:.3f}, y={stick_no_spring.y:.3f}
        """
    )
    return


if __name__ == "__main__":
    app.run()
