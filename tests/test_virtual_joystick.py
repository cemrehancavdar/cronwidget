"""Tests for VirtualJoystick widget."""


import pytest
import traitlets

from cronwidget.virtual_joystick import VirtualJoystick


class TestVirtualJoystickInit:
    def test_defaults(self):
        j = VirtualJoystick()
        assert j.x == 0.0
        assert j.y == 0.0
        assert j.size == 200
        assert j.spring_back is True
        assert j.deadzone == 0.0
        assert j.knob_ratio == 0.35

    def test_custom_values(self):
        j = VirtualJoystick(x=0.5, y=-0.3, size=300, deadzone=0.1, spring_back=False)
        assert j.x == 0.5
        assert j.y == -0.3
        assert j.size == 300
        assert j.deadzone == 0.1
        assert j.spring_back is False


class TestVirtualJoystickValidation:
    def test_x_clamped(self):
        j = VirtualJoystick()
        j.x = 2.0
        assert j.x == 1.0

    def test_x_clamped_negative(self):
        j = VirtualJoystick()
        j.x = -5.0
        assert j.x == -1.0

    def test_y_clamped(self):
        j = VirtualJoystick()
        j.y = 1.5
        assert j.y == 1.0

    def test_invalid_knob_ratio_raises(self):
        with pytest.raises(traitlets.TraitError):
            VirtualJoystick(knob_ratio=0.05)

    def test_invalid_deadzone_raises(self):
        with pytest.raises(traitlets.TraitError):
            VirtualJoystick(deadzone=0.8)

    def test_invalid_size_raises(self):
        with pytest.raises(traitlets.TraitError):
            VirtualJoystick(size=50)


class TestVirtualJoystickProperties:
    def test_angle_right(self):
        j = VirtualJoystick(x=1.0, y=0.0)
        assert abs(j.angle - 0.0) < 0.1

    def test_angle_up(self):
        j = VirtualJoystick(x=0.0, y=1.0)
        assert abs(j.angle - 90.0) < 0.1

    def test_angle_left(self):
        j = VirtualJoystick(x=-1.0, y=0.0)
        assert abs(j.angle - 180.0) < 0.1

    def test_magnitude_zero(self):
        j = VirtualJoystick(x=0.0, y=0.0)
        assert j.magnitude == 0.0

    def test_magnitude_max(self):
        j = VirtualJoystick(x=1.0, y=0.0)
        assert abs(j.magnitude - 1.0) < 0.01

    def test_magnitude_diagonal(self):
        j = VirtualJoystick(x=0.707, y=0.707)
        assert abs(j.magnitude - 1.0) < 0.01
