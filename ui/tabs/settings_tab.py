"""
ui/tabs/settings_tab.py — Fully-working settings with persistence to JSON.
"""
from __future__ import annotations
import json, os
from PyQt6.QtWidgets import ( # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QCheckBox, QRadioButton, QButtonGroup, QComboBox,
    QSpinBox, QPushButton, QTextEdit, QLineEdit, QFileDialog,
)
from PyQt6.QtCore import pyqtSignal # type: ignore

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".struct_calc_settings.json")

DEFAULTS = {
    "auto_calculate":        True,
    "show_tooltips":         True,
    "include_formulas_export": False,
    "theme":                 "dark",
    "spacing_rounding":      "Nearest 5 mm",
    "moment_lookup":         "Interpolate",
    "decimal_places":        3,
    "concrete_unit_wt":      25.0,
    "steel_unit_wt":         78.5,
    "last_export_dir":       "",
}


class SettingsTab(QWidget):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent) # type: ignore
        self._settings: dict = dict(DEFAULTS)
        self._load_from_disk()
        self._build_ui()
        self._apply_to_ui()

    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(14)

        # Two-column layout
        cols = QHBoxLayout(); cols.setSpacing(14)
        left  = QVBoxLayout(); left.setSpacing(14)
        right = QVBoxLayout(); right.setSpacing(14)

        left.addWidget(self._build_general_group())
        left.addWidget(self._build_theme_group())
        left.addWidget(self._build_units_group())
        right.addWidget(self._build_calc_group())
        right.addWidget(self._build_export_group())
        right.addWidget(self._build_about_group())

        cols.addLayout(left,  stretch=1)
        cols.addLayout(right, stretch=1)
        root.addLayout(cols)

        root.addStretch()

    # ── General ───────────────────────────────────────────────────────────────
    def _build_general_group(self) -> QGroupBox:
        g = QGroupBox("General")
        lay = QVBoxLayout(g); lay.setSpacing(8)
        self.auto_calc_chk     = QCheckBox("Auto-calculate on input change  (400 ms debounce)")
        self.show_tips_chk     = QCheckBox("Show detailed field tooltips")
        self.incl_formulas_chk = QCheckBox("Include formulas in exported reports")
        for chk in (self.auto_calc_chk, self.show_tips_chk, self.incl_formulas_chk):
            chk.stateChanged.connect(self._on_any_change)
            lay.addWidget(chk)
        return g

    # ── Theme ──────────────────────────────────────────────────────────────────
    def _build_theme_group(self) -> QGroupBox:
        g = QGroupBox("Theme")
        lay = QVBoxLayout(g); lay.setSpacing(8)
        self._theme_grp  = QButtonGroup(self)
        self.dark_radio  = QRadioButton("🌙  Dark  (Nord Polar Night)")
        self.light_radio = QRadioButton("☀   Light (High-Contrast)")
        self._theme_grp.addButton(self.dark_radio,  0)
        self._theme_grp.addButton(self.light_radio, 1)
        self.dark_radio.toggled.connect(self._on_any_change)
        lay.addWidget(self.dark_radio)
        lay.addWidget(self.light_radio)
        return g

    # ── Unit weights ──────────────────────────────────────────────────────────
    def _build_units_group(self) -> QGroupBox:
        g = QGroupBox("Material Unit Weights  (kN/m³)")
        lay = QGridLayout(g); lay.setSpacing(8)
        self.conc_wt_spin = QSpinBox()
        self.conc_wt_spin.setRange(20, 30); self.conc_wt_spin.setSuffix(" kN/m³")
        self.steel_wt_spin = QSpinBox()
        self.steel_wt_spin.setRange(70, 85); self.steel_wt_spin.setSuffix(" kN/m³")
        lay.addWidget(QLabel("Concrete:"), 0, 0)
        lay.addWidget(self.conc_wt_spin,   0, 1)
        lay.addWidget(QLabel("Steel:"),    1, 0)
        lay.addWidget(self.steel_wt_spin,  1, 1)
        self.conc_wt_spin.valueChanged.connect(self._on_any_change)
        self.steel_wt_spin.valueChanged.connect(self._on_any_change)
        return g

    # ── Calculation ────────────────────────────────────────────────────────────
    def _build_calc_group(self) -> QGroupBox:
        g = QGroupBox("Calculation")
        lay = QGridLayout(g); lay.setSpacing(8)

        lay.addWidget(QLabel("Decimal places in output:"), 0, 0)
        self.decimal_spin = QSpinBox()
        self.decimal_spin.setRange(1, 6); self.decimal_spin.setFixedWidth(80)
        lay.addWidget(self.decimal_spin, 0, 1)

        lay.addWidget(QLabel("Bar spacing rounding:"), 1, 0)
        self.spacing_combo = QComboBox()
        self.spacing_combo.addItems([
            "Nearest 5 mm", "Nearest 10 mm",
            "Round Down to 5 mm", "Round Up to 5 mm", "No Rounding",
        ])
        lay.addWidget(self.spacing_combo, 1, 1)

        lay.addWidget(QLabel("Moment coefficient lookup:"), 2, 0)
        self.moment_combo = QComboBox()
        self.moment_combo.addItems(["Interpolate", "Nearest Table Value"])
        lay.addWidget(self.moment_combo, 2, 1)

        self.decimal_spin.valueChanged.connect(self._on_any_change)
        self.spacing_combo.currentTextChanged.connect(self._on_any_change)
        self.moment_combo.currentTextChanged.connect(self._on_any_change)
        lay.setColumnStretch(1, 1)
        return g

    # ── Export ─────────────────────────────────────────────────────────────────
    def _build_export_group(self) -> QGroupBox:
        g = QGroupBox("Export")
        lay = QGridLayout(g); lay.setSpacing(8)

        lay.addWidget(QLabel("Default export folder:"), 0, 0)
        self.export_dir_edit = QLineEdit()
        self.export_dir_edit.setPlaceholderText("(ask each time)")
        self.export_dir_edit.setReadOnly(True)
        lay.addWidget(self.export_dir_edit, 1, 0, 1, 2)
        browse = QPushButton("Browse…")
        browse.setFixedWidth(90)
        browse.clicked.connect(self._browse_export_dir)
        lay.addWidget(browse, 0, 1)

        clear = QPushButton("Clear")
        clear.setFixedWidth(90)
        clear.clicked.connect(lambda: (self.export_dir_edit.clear(), self._on_any_change()))
        lay.addWidget(clear, 2, 1)
        lay.setColumnStretch(0, 1)
        return g

    # ── About ──────────────────────────────────────────────────────────────────
    def _build_about_group(self) -> QGroupBox:
        from constants import APP_NAME, APP_VERSION  # type: ignore
        g = QGroupBox("About")
        lay = QVBoxLayout(g)
        txt = QTextEdit(readOnly=True)
        txt.setMaximumHeight(110)
        txt.setHtml(
            f"<p><b>{APP_NAME} {APP_VERSION}</b></p>"
            "<p><b>Standards:</b> NBC 105:2025 (2nd Revision) · IS 456:2000 · IS 875 Pt 1&2</p>"
            "<p><b>Developer:</b> Abiskar Acharya</p>"
            "<p style='color: #1565C0;font-size:9pt;'>"
            "For educational use.  Not a substitute for professional judgement.</p>"
        )
        lay.addWidget(txt)
        return g

    # ══════════════════════════════════════════════════════════════════════════
    # Public API — read by MainWindow
    # ══════════════════════════════════════════════════════════════════════════
    def is_dark(self) -> bool:
        return self.dark_radio.isChecked()

    def spacing_round_base(self) -> int:
        mode = self.spacing_combo.currentText()
        return 10 if "10" in mode else 5

    def auto_calculate(self) -> bool:
        return self.auto_calc_chk.isChecked()

    def decimal_places(self) -> int:
        return self.decimal_spin.value()

    def concrete_unit_weight(self) -> float:
        return float(self.conc_wt_spin.value())

    def export_dir(self) -> str:
        return self.export_dir_edit.text().strip()

    def get_all(self) -> dict:
        return {
            "auto_calculate":          self.auto_calc_chk.isChecked(),
            "show_tooltips":           self.show_tips_chk.isChecked(),
            "include_formulas_export": self.incl_formulas_chk.isChecked(),
            "theme":                   "dark" if self.dark_radio.isChecked() else "light",
            "spacing_rounding":        self.spacing_combo.currentText(),
            "moment_lookup":           self.moment_combo.currentText(),
            "decimal_places":          self.decimal_spin.value(),
            "concrete_unit_wt":        float(self.conc_wt_spin.value()),
            "steel_unit_wt":           float(self.steel_wt_spin.value()),
            "last_export_dir":         self.export_dir_edit.text(),
        }

    # ══════════════════════════════════════════════════════════════════════════
    # Persistence
    # ══════════════════════════════════════════════════════════════════════════
    def _load_from_disk(self) -> None:
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, encoding="utf-8") as f:
                    saved = json.load(f)
                self._settings.update(saved)
        except Exception:
            pass

    def _save_to_disk(self) -> None:
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
        except Exception:
            pass

    def _apply_to_ui(self) -> None:
        s = self._settings
        self.auto_calc_chk.setChecked(s.get("auto_calculate", True))
        self.show_tips_chk.setChecked(s.get("show_tooltips", True))
        self.incl_formulas_chk.setChecked(s.get("include_formulas_export", False))
        self.dark_radio.setChecked(s.get("theme", "dark") == "dark")
        self.light_radio.setChecked(s.get("theme", "dark") == "light")
        idx = self.spacing_combo.findText(s.get("spacing_rounding", "Nearest 5 mm"))
        if idx >= 0: self.spacing_combo.setCurrentIndex(idx)
        idx = self.moment_combo.findText(s.get("moment_lookup", "Interpolate"))
        if idx >= 0: self.moment_combo.setCurrentIndex(idx)
        self.decimal_spin.setValue(s.get("decimal_places", 3))
        self.conc_wt_spin.setValue(int(s.get("concrete_unit_wt", 25)))
        self.steel_wt_spin.setValue(int(s.get("steel_unit_wt", 78)))
        self.export_dir_edit.setText(s.get("last_export_dir", ""))

    # ── Slots ──────────────────────────────────────────────────────────────────
    def _on_any_change(self) -> None:
        self._settings.update(self.get_all())
        self._save_to_disk()
        self.settings_changed.emit()

    def _browse_export_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Select Default Export Folder",
            self.export_dir_edit.text() or os.path.expanduser("~")
        )
        if d:
            self.export_dir_edit.setText(d)
            self._on_any_change()
