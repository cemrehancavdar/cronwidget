"""CronBuilder - Compact visual cron expression editor widget."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import anywidget
import traitlets

# Valid cron field ranges for validation
_FIELD_RANGES = [
    (0, 59),  # minute
    (0, 23),  # hour
    (1, 31),  # day of month
    (1, 12),  # month
    (0, 6),  # day of week
]

_FIELD_NAMES = ["minute", "hour", "day_of_month", "month", "day_of_week"]


def _validate_cron_expression(expr: str) -> bool:
    """Check that a cron expression has 5 space-separated fields with valid tokens."""
    tokens = expr.strip().split()
    if len(tokens) != 5:
        return False
    for token, (lo, hi) in zip(tokens, _FIELD_RANGES, strict=True):
        if not _validate_cron_token(token, lo, hi):
            return False
    return True


def _validate_cron_token(token: str, lo: int, hi: int) -> bool:
    """Validate a single cron field token against min/max bounds."""
    if token == "*":
        return True
    # Step: */N or N/M
    if "/" in token:
        parts = token.split("/")
        if len(parts) != 2:
            return False
        base, step = parts
        if base != "*" and not base.isdigit():
            return False
        return step.isdigit() and int(step) >= 1
    # Range: M-N
    if "-" in token:
        parts = token.split("-")
        if len(parts) != 2:
            return False
        if not (parts[0].isdigit() and parts[1].isdigit()):
            return False
        a, b = int(parts[0]), int(parts[1])
        return lo <= a <= hi and lo <= b <= hi
    # Comma-separated specific values
    for part in token.split(","):
        part = part.strip()
        if not part.isdigit():
            return False
        v = int(part)
        if v < lo or v > hi:
            return False
    return True


def _field_matches(value: int, token: str, lo: int) -> bool:
    """Check if a datetime field value matches a cron token."""
    if token == "*":
        return True
    if "/" in token:
        step = int(token.split("/")[1])
        return (value - lo) % step == 0
    if "-" in token:
        a, b = token.split("-")
        return int(a) <= value <= int(b)
    return value in [int(v.strip()) for v in token.split(",")]


def describe_cron(expression: str) -> str:
    """Return a human-readable description of a cron expression.

    Args:
        expression: A standard 5-field cron expression string.

    Returns:
        A human-readable string describing the schedule.
    """
    tokens = expression.strip().split()
    if len(tokens) != 5:
        return expression

    month_names = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    dow_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    def _desc_token(token: str, idx: int) -> str:
        labels = ["minute", "hour", "day of month", "month", "day of week"]
        if token == "*":
            return f"every {labels[idx]}"
        if "/" in token:
            step = token.split("/")[1]
            return f"every {step} {labels[idx]}(s)"
        if "-" in token:
            a, b = token.split("-")
            if idx == 3:
                a_n = month_names[int(a) - 1] if a.isdigit() and 1 <= int(a) <= 12 else a
                b_n = month_names[int(b) - 1] if b.isdigit() and 1 <= int(b) <= 12 else b
                return f"{a_n} through {b_n}"
            if idx == 4:
                a_n = dow_names[int(a)] if a.isdigit() and 0 <= int(a) <= 6 else a
                b_n = dow_names[int(b)] if b.isdigit() and 0 <= int(b) <= 6 else b
                return f"{a_n} through {b_n}"
            return f"{a} through {b}"
        return token

    parts = [_desc_token(t, i) for i, t in enumerate(tokens)]
    desc = ""
    # Minute
    desc = "Every minute" if tokens[0] == "*" else f"At {parts[0]}"
    # Hour
    if tokens[1] != "*":
        desc += f", past {parts[1]}"
    # Day of month
    if tokens[2] != "*":
        desc += f", on day {parts[2]}"
    # Month
    if tokens[3] != "*":
        desc += f" of {parts[3]}"
    # Day of week
    if tokens[4] != "*":
        desc += f", {parts[4]}"
    return desc


def next_runs(expression: str, n: int = 3, after: datetime | None = None) -> list[datetime]:
    """Compute the next N run times for a cron expression.

    Args:
        expression: A 5-field cron expression string.
        n: Number of upcoming runs to compute (default 3).
        after: Start searching after this time (default: now).

    Returns:
        A list of datetime objects for the next N matching times.
    """
    tokens = expression.strip().split()
    if len(tokens) != 5:
        return []

    if after is None:
        after = datetime.now()

    # Start from next minute boundary
    current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    runs: list[datetime] = []
    max_iterations = 525_600  # scan up to 1 year of minutes

    for _ in range(max_iterations):
        if len(runs) >= n:
            break
        # Python isoweekday(): Mon=1..Sun=7. Cron: Sun=0..Sat=6.
        # isoweekday() % 7 gives: Sun=0, Mon=1, ..., Sat=6
        cron_dow = current.isoweekday() % 7
        if (
            _field_matches(current.minute, tokens[0], 0)
            and _field_matches(current.hour, tokens[1], 0)
            and _field_matches(current.day, tokens[2], 1)
            and _field_matches(current.month, tokens[3], 1)
            and _field_matches(cron_dow, tokens[4], 0)
        ):
            runs.append(current)
        current += timedelta(minutes=1)

    return runs


class CronBuilder(anywidget.AnyWidget):
    """Compact visual cron expression builder.

    Displays 5 inline dropdown selectors in a horizontal row,
    with a human-readable description and next run times below.
    Includes a preset dropdown for common schedules.

    Examples:
        ```python
        cron = CronBuilder(expression="*/5 * * * *")
        cron
        ```

        ```python
        print(cron.expression)     # "*/5 * * * *"
        print(cron.describe())     # "At every 5 minute(s)"
        print(cron.next_runs(3))   # [datetime, datetime, datetime]
        ```
    """

    _esm = Path(__file__).parent / "static" / "cron-builder.js"
    _css = Path(__file__).parent / "static" / "cron-builder.css"

    expression = traitlets.Unicode("* * * * *").tag(sync=True)

    def __init__(
        self,
        *,
        expression: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Create a CronBuilder widget.

        Args:
            expression: Initial cron expression (default ``"* * * * *"``).
            **kwargs: Forwarded to ``anywidget.AnyWidget``.
        """
        if expression is None:
            expression = "* * * * *"
        super().__init__(expression=expression, **kwargs)

    @traitlets.validate("expression")
    def _valid_expression(self, proposal: dict[str, Any]) -> str:
        value = proposal["value"]
        if not _validate_cron_expression(value):
            raise traitlets.TraitError(
                f"Invalid cron expression: {value!r}. "
                "Expected 5 space-separated fields (minute hour day month weekday)."
            )
        return value

    def describe(self) -> str:
        """Return a human-readable description of the current cron expression."""
        return describe_cron(self.expression)

    def next_runs(self, n: int = 3, after: datetime | None = None) -> list[datetime]:
        """Return the next N scheduled run times.

        Args:
            n: Number of runs to return (default 3).
            after: Start time (default: now).
        """
        return next_runs(self.expression, n=n, after=after)

    @property
    def fields(self) -> dict[str, str]:
        """Return individual cron fields as a dictionary."""
        tokens = self.expression.strip().split()
        return dict(zip(_FIELD_NAMES, tokens, strict=True))
