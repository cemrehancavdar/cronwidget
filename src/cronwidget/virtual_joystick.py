"""VirtualJoystick - On-screen thumbstick widget with spring-back-to-center."""

from pathlib import Path
from typing import Any

import anywidget
import traitlets


class VirtualJoystick(anywidget.AnyWidget):
    """On-screen virtual joystick / thumbstick.

    Outputs ``x`` and ``y`` floats in the range ``-1.0`` to ``1.0``.
    Supports touch and mouse, with optional spring-back-to-center,
    deadzone, and configurable size.

    Examples:
        ```python
        stick = VirtualJoystick()
        stick
        ```

        ```python
        # Read current position
        print(stick.x, stick.y)  # e.g. 0.5, -0.3
        ```

        ```python
        # Robotics-style: with deadzone and no spring-back
        stick = VirtualJoystick(deadzone=0.15, spring_back=False)
        ```
    """

    _esm = Path(__file__).parent / "static" / "virtual-joystick.js"
    _css = Path(__file__).parent / "static" / "virtual-joystick.css"

    x = traitlets.Float(0.0).tag(sync=True)
    y = traitlets.Float(0.0).tag(sync=True)
    size = traitlets.Int(200).tag(sync=True)
    knob_ratio = traitlets.Float(0.35).tag(sync=True)
    deadzone = traitlets.Float(0.0).tag(sync=True)
    spring_back = traitlets.Bool(True).tag(sync=True)

    def __init__(
        self,
        *,
        x: float = 0.0,
        y: float = 0.0,
        size: int = 200,
        knob_ratio: float = 0.35,
        deadzone: float = 0.0,
        spring_back: bool = True,
        **kwargs: Any,
    ) -> None:
        """Create a VirtualJoystick widget.

        Args:
            x: Initial x position (-1.0 to 1.0).
            y: Initial y position (-1.0 to 1.0).
            size: Widget diameter in pixels.
            knob_ratio: Knob radius as fraction of total radius (0.1 to 0.5).
            deadzone: Deadzone radius as fraction (0.0 to 0.5). Values within
                this radius map to (0, 0).
            spring_back: Whether the knob snaps back to center on release.
            **kwargs: Forwarded to ``anywidget.AnyWidget``.
        """
        super().__init__(
            x=x,
            y=y,
            size=size,
            knob_ratio=knob_ratio,
            deadzone=deadzone,
            spring_back=spring_back,
            **kwargs,
        )

    @traitlets.validate("x", "y")
    def _valid_xy(self, proposal: dict[str, Any]) -> float:
        value = proposal["value"]
        return max(-1.0, min(1.0, float(value)))

    @traitlets.validate("knob_ratio")
    def _valid_knob_ratio(self, proposal: dict[str, Any]) -> float:
        value = proposal["value"]
        if not 0.1 <= value <= 0.5:
            raise traitlets.TraitError("knob_ratio must be between 0.1 and 0.5")
        return float(value)

    @traitlets.validate("deadzone")
    def _valid_deadzone(self, proposal: dict[str, Any]) -> float:
        value = proposal["value"]
        if not 0.0 <= value <= 0.5:
            raise traitlets.TraitError("deadzone must be between 0.0 and 0.5")
        return float(value)

    @traitlets.validate("size")
    def _valid_size(self, proposal: dict[str, Any]) -> int:
        value = proposal["value"]
        if value < 80:
            raise traitlets.TraitError("size must be at least 80 pixels")
        return int(value)

    @property
    def angle(self) -> float:
        """Angle in degrees (0 = right, 90 = up, counter-clockwise)."""
        import math

        return math.degrees(math.atan2(self.y, self.x))

    @property
    def magnitude(self) -> float:
        """Distance from center (0.0 to 1.0)."""
        import math

        return min(1.0, math.sqrt(self.x**2 + self.y**2))
