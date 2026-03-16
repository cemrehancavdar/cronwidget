"""Tests for CronBuilder widget."""

from datetime import datetime

import pytest
import traitlets

from cronwidget.cron_builder import (
    CronBuilder,
    _field_matches,
    _validate_cron_expression,
    _validate_cron_token,
    describe_cron,
    next_runs,
)


class TestValidateCronToken:
    def test_star(self):
        assert _validate_cron_token("*", 0, 59)

    def test_single_number(self):
        assert _validate_cron_token("5", 0, 59)

    def test_number_out_of_range(self):
        assert not _validate_cron_token("60", 0, 59)

    def test_comma_separated(self):
        assert _validate_cron_token("1,15,30", 0, 59)

    def test_range(self):
        assert _validate_cron_token("1-5", 0, 59)

    def test_range_out_of_bounds(self):
        assert not _validate_cron_token("0-32", 1, 31)

    def test_step(self):
        assert _validate_cron_token("*/5", 0, 59)

    def test_step_zero(self):
        assert not _validate_cron_token("*/0", 0, 59)

    def test_invalid_text(self):
        assert not _validate_cron_token("abc", 0, 59)


class TestFieldMatches:
    def test_star_matches_everything(self):
        assert _field_matches(30, "*", 0)

    def test_step_matches(self):
        assert _field_matches(10, "*/5", 0)
        assert not _field_matches(11, "*/5", 0)

    def test_range_matches(self):
        assert _field_matches(3, "1-5", 0)
        assert not _field_matches(6, "1-5", 0)

    def test_list_matches(self):
        assert _field_matches(5, "1,5,10", 0)
        assert not _field_matches(7, "1,5,10", 0)

    def test_exact_match(self):
        assert _field_matches(12, "12", 0)
        assert not _field_matches(11, "12", 0)


class TestValidateCronExpression:
    def test_all_stars(self):
        assert _validate_cron_expression("* * * * *")

    def test_typical_expression(self):
        assert _validate_cron_expression("*/5 0 1,15 * 1-5")

    def test_too_few_fields(self):
        assert not _validate_cron_expression("* * *")

    def test_too_many_fields(self):
        assert not _validate_cron_expression("* * * * * *")

    def test_invalid_field(self):
        assert not _validate_cron_expression("60 * * * *")


class TestDescribeCron:
    def test_all_stars(self):
        desc = describe_cron("* * * * *")
        assert "Every minute" in desc

    def test_step(self):
        desc = describe_cron("*/5 * * * *")
        assert "5" in desc

    def test_range_month(self):
        desc = describe_cron("* * * 1-6 *")
        assert "Jan" in desc
        assert "Jun" in desc

    def test_weekday_range(self):
        desc = describe_cron("0 9 * * 1-5")
        assert "Mon" in desc
        assert "Fri" in desc

    def test_invalid_returns_raw(self):
        assert describe_cron("invalid") == "invalid"


class TestNextRuns:
    def test_every_minute_returns_consecutive(self):
        after = datetime(2026, 3, 16, 10, 0, 0)
        runs = next_runs("* * * * *", n=3, after=after)
        assert len(runs) == 3
        assert runs[0] == datetime(2026, 3, 16, 10, 1)
        assert runs[1] == datetime(2026, 3, 16, 10, 2)
        assert runs[2] == datetime(2026, 3, 16, 10, 3)

    def test_hourly_at_zero(self):
        after = datetime(2026, 3, 16, 10, 30, 0)
        runs = next_runs("0 * * * *", n=2, after=after)
        assert len(runs) == 2
        assert runs[0] == datetime(2026, 3, 16, 11, 0)
        assert runs[1] == datetime(2026, 3, 16, 12, 0)

    def test_step_every_5_minutes(self):
        after = datetime(2026, 3, 16, 10, 0, 0)
        runs = next_runs("*/5 * * * *", n=3, after=after)
        assert len(runs) == 3
        assert runs[0] == datetime(2026, 3, 16, 10, 5)
        assert runs[1] == datetime(2026, 3, 16, 10, 10)
        assert runs[2] == datetime(2026, 3, 16, 10, 15)

    def test_daily_at_noon(self):
        after = datetime(2026, 3, 16, 13, 0, 0)
        runs = next_runs("0 12 * * *", n=2, after=after)
        assert len(runs) == 2
        assert runs[0] == datetime(2026, 3, 17, 12, 0)
        assert runs[1] == datetime(2026, 3, 18, 12, 0)

    def test_invalid_expression_returns_empty(self):
        assert next_runs("bad", n=3) == []

    def test_returns_requested_count(self):
        after = datetime(2026, 1, 1, 0, 0, 0)
        runs = next_runs("* * * * *", n=5, after=after)
        assert len(runs) == 5


class TestCronBuilderWidget:
    def test_default_expression(self):
        w = CronBuilder()
        assert w.expression == "* * * * *"

    def test_custom_expression(self):
        w = CronBuilder(expression="*/5 0 * * 1-5")
        assert w.expression == "*/5 0 * * 1-5"

    def test_invalid_expression_raises(self):
        with pytest.raises(traitlets.TraitError):
            CronBuilder(expression="bad")

    def test_fields_property(self):
        w = CronBuilder(expression="*/5 0 1,15 * 1-5")
        fields = w.fields
        assert fields["minute"] == "*/5"
        assert fields["hour"] == "0"
        assert fields["day_of_month"] == "1,15"
        assert fields["month"] == "*"
        assert fields["day_of_week"] == "1-5"

    def test_describe(self):
        w = CronBuilder(expression="*/5 * * * *")
        desc = w.describe()
        assert "5" in desc

    def test_next_runs_method(self):
        w = CronBuilder(expression="* * * * *")
        after = datetime(2026, 1, 1, 0, 0, 0)
        runs = w.next_runs(n=3, after=after)
        assert len(runs) == 3

    def test_set_valid_expression(self):
        w = CronBuilder()
        w.expression = "0 12 * * *"
        assert w.expression == "0 12 * * *"

    def test_set_invalid_expression_raises(self):
        w = CronBuilder()
        with pytest.raises(traitlets.TraitError):
            w.expression = "not a cron"
