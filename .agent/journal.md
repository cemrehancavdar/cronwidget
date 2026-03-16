---
### [OK] CRONWIDGET-RAIL-UI | 2026-03-16
- **Status**: [OK] ADOPTED
- **Objective**: Add mode-switch rail under each cron segment
- **Hypothesis**: Thin rail gives visual mode indicator + click target for cycling
- **Approach**: CSS rail with fill div, JS updates fill position/width per mode
- **Result**:
    - Rail renders per-mode: full (every), partial (step), pip (value), segment (range)
    - Click rail cycles mode, drag text adjusts value
    - 52 tests pass, ruff clean, pyright clean
    - Outcome: Success
- **The Delta**: Separated mode-switch (rail) from value-adjust (drag) — cleaner UX than click-on-text cycling
- **Next Step**: Polish rail hover animation, consider adding rail drag for range bounds.
---

### [OK] CRONWIDGET-TANGLE-V3 | 2026-03-16
- **Status**: [X] DISCARDED (replaced by rail version)
- **Objective**: Tangle-style interactive cron with drag/click/scroll
- **Hypothesis**: Click cycles mode, drag adjusts value within mode
- **Approach**: Compound sub-spans per field, pointer events, lightUpdate vs rebuild
- **Result**:
    - Drag works continuously after lightUpdate fix
    - Range sub-values independently draggable
    - Outcome: Functional but mode cycling not discoverable
- **The Delta**: Fixed DOM-rebuild-killing-drag bug by splitting lightUpdate (text only) from rebuildColumn (structure)
- **Next Step**: Replaced by rail approach for better discoverability.
---

### [OK] CRONWIDGET-INIT | 2026-03-16
- **Status**: [OK] ADOPTED
- **Objective**: Create CronBuilder + VirtualJoystick anywidgets for marimo
- **Hypothesis**: Marimo needs cron and joystick widgets
- **Approach**: anywidget + traitlets, CSS vars for dark mode, pointer events
- **Result**:
    - Both widgets render in marimo via mo.ui.anywidget()
    - CronBuilder: expression trait, validation, describe(), next_runs(), fields
    - VirtualJoystick: x/y floats, spring-back, deadzone, angle/magnitude
    - 52 tests, ruff clean, pyright clean
    - Outcome: Success
- **The Delta**: First working prototypes
- **Next Step**: Polish CronBuilder DX, package for distribution.
---
