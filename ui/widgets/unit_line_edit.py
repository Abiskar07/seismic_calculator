"""
ui/widgets/unit_line_edit.py
─────────────────────────────
A QLineEdit that transparently converts ft'in" input to metric on focus-out.
"""
from __future__ import annotations
import re
from PyQt6.QtWidgets import QLineEdit


class UnitLineEdit(QLineEdit):
    """
    Drop-in replacement for QLineEdit that understands imperial ft'in" entry.

    target_unit : 'm'  → stores value in metres    (3 d.p.)
                  'mm' → stores value in millimetres (1 d.p.)

    Anything that doesn't match the ft-in pattern is left untouched so that
    normal numeric entry keeps working.
    """

    _FT_IN_PATTERN = re.compile(
        r"""^                     # start
            (?:(\d*\.?\d+)')?     # optional feet  group 1
            \s*
            (?:(\d*\.?\d+)\")?    # optional inches group 2
            $                     # end
        """,
        re.VERBOSE,
    )

    def __init__(self, target_unit: str = "m", default_text: str = "", *args, **kwargs):
        super().__init__(default_text, *args, **kwargs)
        self.target_unit = target_unit
        self._set_tooltip()
        self.editingFinished.connect(self._process_input)

    # ── Private ───────────────────────────────────────────────────────────────
    def _set_tooltip(self) -> None:
        if self.target_unit == "m":
            self.setToolTip("Enter value in metres or use ft′in″ format (e.g. 5′6″)")
        elif self.target_unit == "mm":
            self.setToolTip("Enter value in mm or use ft′in″ format (e.g. 0′6.5″)")

    def _parse_feet_inches(self, text: str) -> float | None:
        """Return total metres, or None if the text is not a valid ft-in expression."""
        text = text.strip()
        if not ("'" in text or '"' in text):
            return None
        match = self._FT_IN_PATTERN.match(text)
        if not match or not any(match.groups()):
            return None
        feet_str, inches_str = match.groups()
        try:
            total_inches = (float(feet_str) * 12 if feet_str else 0.0) + \
                           (float(inches_str)     if inches_str else 0.0)
            return total_inches * 0.0254  # → metres
        except (ValueError, TypeError):
            return None

    def _process_input(self) -> None:
        """Convert ft-in input to the target metric unit on editing-finished."""
        metres = self._parse_feet_inches(self.text())
        if metres is None:
            return
        if self.target_unit == "mm":
            self.setText(f"{metres * 1000:.1f}")
        else:
            self.setText(f"{metres:.3f}")
