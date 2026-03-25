"""
ui/tabs/beam_tab.py — Professional Beam Design UI (NBC 105:2025 priority)
"""
from __future__ import annotations

import math
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QSpinBox,
    QMessageBox,
)

from constants import BEAM_MOMENT_COEFFICIENTS
from core import design_beam_section
from ui.widgets import UnitLineEdit


def _cell(text, bold: bool = False, bg: str | None = None, fg: str | None = None) -> QTableWidgetItem:
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    if bold:
        f = QFont()
        f.setBold(True)
        item.setFont(f)
    if bg:
        item.setBackground(QColor(bg))
    if fg:
        item.setForeground(QColor(fg))
    return item


def _status_cell(status: str) -> QTableWidgetItem:
    colors = {
        "OK":     ("#1B5E20", "#A5D6A7"),
        "CHECK":  ("#6D3500", "#FFCC80"),
        "WARN":   ("#6D3500", "#FFCC80"),
        "INFO":   ("#0D47A1", "#90CAF9"),
        "FAIL":   ("#7F0000", "#EF9A9A"),
        "REVISE": ("#7F0000", "#EF9A9A"),
    }
    fg, bg = colors.get(status, ("#000000", "#F5F5F5"))
    icon = ""
    if status == "OK": icon = " ✓"
    elif status in ("FAIL", "REVISE"): icon = " ✗"
    elif status in ("WARN", "CHECK"): icon = " ⚠"
    elif status == "INFO": icon = " ℹ"
    
    return _cell(f"{status}{icon}", bold=True, bg=bg, fg=fg)


class BeamTab(QWidget):
    spacing_round_base: int = 25

    def __init__(self, parent=None, seismic_tab_ref=None):
        super().__init__(parent)
        self._seismic_ref = seismic_tab_ref

        self.inputs: dict = {}
        self.rein_inputs: dict = {}
        self.rein_labels: dict = {}
        self.comp_labels: dict = {}
        self.summary_labels: dict = {}

        self._last_res: dict | None = None
        self._bar_spacing_warn_state = ""
        self._ui_ready = False

        self._build_ui()
        self._set_defaults()
        self._ui_ready = True

    # ──────────────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 12, 10, 12)
        root.setSpacing(8)

        top = QWidget()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(10)
        top_lay.addWidget(self._build_input_group(), stretch=3)
        top_lay.addWidget(self._build_seismic_group(), stretch=2)
        root.addWidget(top)

        root.addWidget(self._build_summary_group())
        root.addWidget(self._build_checks_group())
        root.addWidget(self._build_reinforcement_group())
        root.addWidget(self._build_doubly_group())
        root.addWidget(self._build_deflection_group())
        root.addWidget(self._build_notes_group(), stretch=1)

    def _build_input_group(self) -> QGroupBox:
        g = QGroupBox("Section, Material & Loads")
        lay = QGridLayout(g)
        lay.setVerticalSpacing(9)
        lay.setHorizontalSpacing(10)

        def add_input(label: str, key: str, widget, row: int, col: int = 0):
            self.inputs[key] = widget
            lay.addWidget(QLabel(label), row, col)
            lay.addWidget(widget, row, col + 1)

        add_input("Span L [m]:", "span", UnitLineEdit("m"), 0)
        add_input("Width b [mm]:", "width", UnitLineEdit("mm"), 1)
        add_input("Overall depth D [mm]:", "depth", UnitLineEdit("mm"), 2)

        ll = QLineEdit()
        ll.setPlaceholderText("kN/m")
        add_input("Live load wL [kN/m]:", "ll", ll, 3)

        dl = QLineEdit()
        dl.setPlaceholderText("kN/m")
        self.inputs["dl"] = dl
        self._auto_dl_chk = QCheckBox("Auto self-weight")
        self._auto_dl_chk.setToolTip("Self-weight = b × D × 25 kN/m³")
        self._auto_dl_chk.setChecked(True)

        lay.addWidget(QLabel("Dead load wD [kN/m]:"), 4, 0)
        dl_row = QHBoxLayout()
        dl_row.setContentsMargins(0, 0, 0, 0)
        dl_row.addWidget(dl)
        dl_row.addWidget(self._auto_dl_chk)
        lay.addLayout(dl_row, 4, 1)

        fck = QComboBox()
        fck.addItems(["20", "25", "30", "35", "40"])
        fy = QComboBox()
        fy.addItems(["250", "415", "500"])
        cover = UnitLineEdit("mm")
        dia = QComboBox()
        dia.addItems(["10", "12", "16", "20", "25", "32"])
        support = QComboBox()
        support.addItems(list(BEAM_MOMENT_COEFFICIENTS.keys()))

        for label, key, w, row in [
            ("Grade fck [MPa]:", "fck", fck, 0),
            ("Grade fy [MPa]:", "fy", fy, 1),
            ("Cover [mm]:", "cover", cover, 2),
            ("Main bar Ø [mm]:", "dia", dia, 3),
        ]:
            self.inputs[key] = w
            lay.addWidget(QLabel(label), row, 2)
            lay.addWidget(w, row, 3)

        self.inputs["support"] = support
        lay.addWidget(QLabel("Support condition:"), 5, 0)
        lay.addWidget(support, 5, 1, 1, 3)

        comp_grp = QGroupBox("Doubly-reinforced settings")
        cgl = QGridLayout(comp_grp)
        cgl.setVerticalSpacing(8)
        self._allow_doubly_chk = QCheckBox("Auto-design compression steel when Mu > Mu,lim")
        self._allow_doubly_chk.setChecked(True)
        comp_dia = QComboBox()
        comp_dia.addItems(["10", "12", "16", "20", "25"])
        comp_dia.setCurrentText("16")
        self.inputs["comp_dia"] = comp_dia
        cgl.addWidget(self._allow_doubly_chk, 0, 0, 1, 3)
        cgl.addWidget(QLabel("Compression bar Ø [mm]:"), 1, 0)
        cgl.addWidget(comp_dia, 1, 1)
        lay.addWidget(comp_grp, 6, 0, 1, 4)

        Tu = QLineEdit()
        Tu.setPlaceholderText("0.0 (blank = none)")
        span_defl = UnitLineEdit("m")
        self.inputs["Tu"] = Tu
        self.inputs["span_defl"] = span_defl
        lay.addWidget(QLabel("Torsion Tu [kN·m]:"), 7, 0)
        lay.addWidget(Tu, 7, 1)
        lay.addWidget(QLabel("Span for deflection [m]:"), 7, 2)
        lay.addWidget(span_defl, 7, 3)

        lay.setColumnStretch(1, 1)
        lay.setColumnStretch(3, 1)

        # Signals
        self._auto_dl_chk.toggled.connect(self._on_auto_dl)
        self._allow_doubly_chk.toggled.connect(self._on_changed)

        for key, w in self.inputs.items():
            if isinstance(w, QComboBox):
                w.currentTextChanged.connect(self._on_changed)
            elif isinstance(w, QLineEdit) and key not in ("dl", "width", "depth"):
                w.editingFinished.connect(self._on_changed)

        # Width/depth must update dead load first
        self.inputs["width"].editingFinished.connect(lambda: self._on_auto_dl(self._auto_dl_chk.isChecked()))
        self.inputs["depth"].editingFinished.connect(lambda: self._on_auto_dl(self._auto_dl_chk.isChecked()))

        return g

    def _build_seismic_group(self) -> QGroupBox:
        g = QGroupBox("NBC 105 Seismic Coupling (Optional)")
        lay = QGridLayout(g)
        lay.setVerticalSpacing(9)

        s_mu = QLineEdit()
        s_mu.setPlaceholderText("kN·m")
        s_vu = QLineEdit()
        s_vu.setPlaceholderText("kN")
        use = QCheckBox("Use seismic demand envelope")
        pull = QPushButton("Pull from Seismic Tab")
        pull.clicked.connect(self._populate_from_seismic)

        self.inputs["seismic_mu"] = s_mu
        self.inputs["seismic_vu"] = s_vu
        self.inputs["use_seismic"] = use

        lay.addWidget(QLabel("Seismic Mu [kN·m]:"), 0, 0)
        lay.addWidget(s_mu, 0, 1)
        lay.addWidget(QLabel("Seismic Vu [kN]:"), 1, 0)
        lay.addWidget(s_vu, 1, 1)
        lay.addWidget(use, 2, 0, 1, 2)
        lay.addWidget(pull, 3, 0, 1, 2)
        lay.setColumnStretch(1, 1)

        s_mu.editingFinished.connect(self._on_changed)
        s_vu.editingFinished.connect(self._on_changed)
        use.toggled.connect(self._on_changed)

        return g

    def _build_summary_group(self) -> QGroupBox:
        g = QGroupBox("Design Summary")
        lay = QGridLayout(g)
        lay.setVerticalSpacing(8)
        lay.setHorizontalSpacing(16)

        fields = [
            ("mu", "Mu (design):"),
            ("vu", "Vu (design):"),
            ("d", "Effective depth d:"),
            ("ast", "Ast provided:"),
            ("bars", "Bars:"),
            ("spacing", "Main spacing:"),
        ]

        for i, (key, title) in enumerate(fields):
            r = i // 3
            c = (i % 3) * 2
            lay.addWidget(QLabel(title), r, c)
            v = QLabel("--")
            v.setStyleSheet("font-weight:bold; font-size:11pt;")
            self.summary_labels[key] = v
            lay.addWidget(v, r, c + 1)

        return g

    def _build_checks_group(self) -> QGroupBox:
        g = QGroupBox("Primary Checks (NBC 105:2025 priority, IS 456 fallback)")
        lay = QVBoxLayout(g)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(
            ["Parameter", "Value", "Unit", "Formula / Note", "Clause", "Status"]
        )
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        hdr = self.results_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.results_table)
        return g

    def _build_reinforcement_group(self) -> QGroupBox:
        g = QGroupBox("Reinforcement Controls")
        out = QHBoxLayout(g)
        out.setSpacing(20)

        left = QGridLayout()
        left.setVerticalSpacing(8)
        for i, (key, title, unit) in enumerate([
            ("Ast_req", "Ast required", "mm²"),
            ("Ast_min", "Ast minimum", "mm²"),
            ("Ast_max", "Ast maximum", "mm²"),
            ("Ast_prov", "Ast provided", "mm²"),
        ]):
            v = QLabel("--")
            v.setStyleSheet("font-weight:bold; font-size:11pt;")
            self.rein_labels[key] = v
            left.addWidget(QLabel(f"{title}:"), i, 0)
            left.addWidget(v, i, 1)
            left.addWidget(QLabel(unit), i, 2)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)

        right = QGridLayout()
        right.setVerticalSpacing(8)

        mode = QComboBox()
        mode.addItems([
            "Auto",
            "Override number of bars",
            "Override spacing (c/c)",
        ])
        mode.currentTextChanged.connect(self._on_rebar_mode_changed)
        self.rein_inputs["mode"] = mode
        right.addWidget(QLabel("Main bar mode:"), 0, 0)
        right.addWidget(mode, 0, 1, 1, 2)

        nb = QSpinBox()
        nb.setRange(2, 30)
        nb.setMinimumHeight(30)
        nb.setMinimumWidth(90)
        nb.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        nb.setStyleSheet(
            "QSpinBox { padding-right: 20px; }"
            "QSpinBox::up-button, QSpinBox::down-button { width: 20px; }"
        )
        nb.editingFinished.connect(self._on_changed)
        self.rein_inputs["num_bars"] = nb
        right.addWidget(QLabel("No. of bars:"), 1, 0)
        right.addWidget(nb, 1, 1)

        sp = QLineEdit()
        sp.setPlaceholderText("mm c/c")
        sp.editingFinished.connect(self._on_changed)
        self.rein_inputs["spacing"] = sp
        right.addWidget(QLabel("Bar spacing [mm]:"), 2, 0)
        right.addWidget(sp, 2, 1)
        right.addWidget(QLabel("mm c/c"), 2, 2)

        sv_end = QLineEdit()
        sv_end.setPlaceholderText("auto")
        sv_end.editingFinished.connect(self._on_stirrup_edited)
        self.rein_inputs["stir_sp_end"] = sv_end
        right.addWidget(QLabel("Stirrup spacing @ support [mm]:"), 3, 0)
        right.addWidget(sv_end, 3, 1)
        right.addWidget(QLabel("mm c/c"), 3, 2)

        sv_mid = QLineEdit()
        sv_mid.setPlaceholderText("auto")
        sv_mid.editingFinished.connect(self._on_stirrup_edited)
        self.rein_inputs["stir_sp_mid"] = sv_mid
        right.addWidget(QLabel("Stirrup spacing @ main/mid [mm]:"), 4, 0)
        right.addWidget(sv_mid, 4, 1)
        right.addWidget(QLabel("mm c/c"), 4, 2)

        legs = QComboBox()
        legs.addItems(["2", "3", "4"])
        legs.currentTextChanged.connect(self._on_changed)
        self.rein_inputs["stir_legs"] = legs
        right.addWidget(QLabel("Stirrup legs:"), 5, 0)
        right.addWidget(legs, 5, 1)

        shear = QLabel("--")
        shear.setStyleSheet("font-weight:bold;")
        self.rein_labels["Shear"] = shear
        right.addWidget(QLabel("Shear status:"), 6, 0)
        right.addWidget(shear, 6, 1, 1, 2)

        out.addLayout(left, 1)
        out.addWidget(line)
        out.addLayout(right, 1)

        self._on_rebar_mode_changed(mode.currentText())
        return g

    def _build_doubly_group(self) -> QGroupBox:
        self._doubly_group = QGroupBox("Compression Reinforcement (Annex G)")
        self._doubly_group.setVisible(False)
        lay = QGridLayout(self._doubly_group)
        lay.setVerticalSpacing(8)

        params = [
            ("Asc_req", "Asc required", "mm²"),
            ("Asc_prov", "Asc provided", "mm²"),
            ("comp_bars", "Bars provided", ""),
            ("fsc", "Compression steel stress fsc", "MPa"),
            ("d_prime", "d'", "mm"),
            ("Ast1", "Ast,1", "mm²"),
            ("Ast2", "Ast,2", "mm²"),
        ]
        for i, (key, title, unit) in enumerate(params):
            v = QLabel("--")
            v.setStyleSheet("font-weight:bold;")
            self.comp_labels[key] = v
            lay.addWidget(QLabel(f"{title}:"), i, 0)
            lay.addWidget(v, i, 1)
            if unit:
                lay.addWidget(QLabel(unit), i, 2)

        lay.setColumnStretch(1, 1)
        return self._doubly_group

    def _build_deflection_group(self) -> QGroupBox:
        self._defl_group = QGroupBox("Deflection Check (IS 456 fallback §23.2)")
        self._defl_group.setVisible(False)
        lay = QGridLayout(self._defl_group)
        lay.setVerticalSpacing(8)

        self._defl_labels = {}
        items = [
            ("ld_basic", "Basic L/d"),
            ("fs", "fs [MPa]"),
            ("kt", "kt"),
            ("kc", "kc"),
            ("ld_allow", "Allowable L/d"),
            ("ld_prov", "Provided L/d"),
        ]
        for i, (key, title) in enumerate(items):
            r = i // 3
            c = (i % 3) * 3
            lay.addWidget(QLabel(f"{title}:"), r, c)
            v = QLabel("--")
            v.setStyleSheet("font-weight:bold;")
            self._defl_labels[key] = v
            lay.addWidget(v, r, c + 1)

        self._defl_status = QLabel("—")
        self._defl_status.setStyleSheet("font-weight:bold; font-size:11pt;")
        lay.addWidget(QLabel("Result:"), 2, 0)
        lay.addWidget(self._defl_status, 2, 1, 1, 5)

        return self._defl_group

    def _build_notes_group(self) -> QGroupBox:
        g = QGroupBox("Code Basis, Development Length & Design Notes")
        lay = QVBoxLayout(g)
        self._ld_lbl = QLabel("Development length Ld: —")
        self._ld_lbl.setStyleSheet("font-weight:bold; padding:2px 4px;")
        lay.addWidget(self._ld_lbl)
        self.notes_edit = QTextEdit(readOnly=True)
        self.notes_edit.setMinimumHeight(130)
        lay.addWidget(self.notes_edit)
        return g

    # ──────────────────────────────────────────────────────────────────────────
    # Logic
    # ──────────────────────────────────────────────────────────────────────────
    def _get(self, key: str) -> str:
        w = self.inputs[key]
        return w.currentText() if isinstance(w, QComboBox) else w.text().strip()

    def _resize_results(self) -> None:
        t = self.results_table
        t.resizeRowsToContents()
        header_h = t.horizontalHeader().height() if t.horizontalHeader().isVisible() else 0
        rows_h = sum(t.rowHeight(r) for r in range(t.rowCount()))
        h = header_h + rows_h + (t.frameWidth() * 2) + 6
        t.setMinimumHeight(max(70, h))
        t.setMaximumHeight(max(70, h))

    def _on_auto_dl(self, checked: bool) -> None:
        dl = self.inputs["dl"]
        dl.setReadOnly(checked)
        if checked:
            try:
                b_m = float(self._get("width") or "0") / 1000.0
                D_m = float(self._get("depth") or "0") / 1000.0
                dl.setText(f"{b_m * D_m * 25.0:.3f}")
            except Exception:
                pass
        self.calculate()

    def _on_rebar_mode_changed(self, mode: str) -> None:
        nb = self.rein_inputs["num_bars"]
        sp = self.rein_inputs["spacing"]

        if mode == "Auto":
            nb.setEnabled(False)
            sp.setEnabled(False)
        elif mode == "Override number of bars":
            nb.setEnabled(True)
            sp.setEnabled(False)
        else:
            nb.setEnabled(False)
            sp.setEnabled(True)

        self.calculate()

    def _on_changed(self) -> None:
        self.calculate()

    def _handle_bar_spacing_warning(self, res: dict) -> bool:
        if not self._ui_ready:
            return False
        
        if "clear_spacing_mm" not in res or "min_clear_spacing_mm" not in res:
            return False
            
        clear_sp = float(res.get("clear_spacing_mm", 0.0))
        min_clear = float(res.get("min_clear_spacing_mm", 0.0))
        
        if min_clear <= 0:
            return False
            
        state = "unsafe" if clear_sp < min_clear else "safe"

        if state == "unsafe" and self._bar_spacing_warn_state != "unsafe":
            self._bar_spacing_warn_state = state  # Set state before any reset to prevent recursive popups
            QMessageBox.warning(
                self,
                "Main Bar Spacing Warning",
                (
                    f"Clear spacing = {clear_sp:.1f} mm is below code minimum {min_clear:.1f} mm.\n\n"
                    "Recommendation:\n"
                    "• Increase beam width, or\n"
                    "• Increase bar diameter and reduce bar count, or\n"
                    "• Return to Auto mode."
                ),
            )
            
            # Block signals to prevent intermediate recalculations
            self.rein_inputs["mode"].blockSignals(True)
            self.inputs["ll"].blockSignals(True)
            self._auto_dl_chk.blockSignals(True)
            
            # Reset values back to auto or default
            self.rein_inputs["mode"].setCurrentText("Auto")
            self.inputs["ll"].setText("3")
            self._auto_dl_chk.setChecked(True)
            self.inputs["dl"].setReadOnly(True)
            
            # Auto DL calc
            try:
                b_m = float(self._get("width") or "0") / 1000.0
                D_m = float(self._get("depth") or "0") / 1000.0
                self.inputs["dl"].setText(f"{b_m * D_m * 25.0:.3f}")
            except Exception:
                pass
                
            # Unblock signals
            self.rein_inputs["mode"].blockSignals(False)
            self.inputs["ll"].blockSignals(False)
            self._auto_dl_chk.blockSignals(False)
            
            # Perform single clean recalculation
            self.calculate()
            return True
        else:
            self._bar_spacing_warn_state = state
            return False

    def _on_stirrup_edited(self) -> None:
        if not self._last_res:
            return

        shear = self._last_res.get("shear", {})
        sv_end_auto = shear.get("Sv_end_zone_mm") or shear.get("Sv_mm")
        sv_mid_auto = shear.get("Sv_mid_zone_mm") or shear.get("Sv_mm")

        end_txt = self.rein_inputs["stir_sp_end"].text().strip()
        mid_txt = self.rein_inputs["stir_sp_mid"].text().strip()

        try:
            sv_end_user = float(end_txt) if end_txt else None
            sv_mid_user = float(mid_txt) if mid_txt else None
            if sv_end_user is not None and sv_end_user < 25:
                raise ValueError
            if sv_mid_user is not None and sv_mid_user < 25:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Stirrup Spacing", "Enter valid stirrup spacing values (must be ≥ 25 mm).")
            self.rein_inputs["stir_sp_end"].clear()
            self.rein_inputs["stir_sp_mid"].clear()
            self.calculate()
            return

        sv_end_use = sv_end_user if sv_end_user is not None else sv_end_auto
        sv_mid_use = sv_mid_user if sv_mid_user is not None else sv_mid_auto

        end_ok = True if not sv_end_auto else (25 <= sv_end_use <= float(sv_end_auto))
        mid_ok = True if not sv_mid_auto else (25 <= sv_mid_use <= float(sv_mid_auto))
        ok = end_ok and mid_ok

        self.rein_labels["Shear"].setStyleSheet(
            f"font-weight:bold; color:{'#2E7D32' if ok else '#C62828'};"
        )
        self.rein_labels["Shear"].setText(
            f"{shear.get('status', '--')}  —  support@{int(sv_end_use) if sv_end_use else '--'}mm, "
            f"mid@{int(sv_mid_use) if sv_mid_use else '--'}mm"
        )

        if not ok:
            QMessageBox.warning(
                self,
                "Stirrup Spacing Unsafe",
                (
                    f"Entered spacing is larger than safe auto detailing.\n"
                    f"Support-zone limit: {int(float(sv_end_auto)) if sv_end_auto else '--'} mm\n"
                    f"Mid/main-zone limit: {int(float(sv_mid_auto)) if sv_mid_auto else '--'} mm"
                ),
            )
            self.rein_inputs["stir_sp_end"].clear()
            self.rein_inputs["stir_sp_mid"].clear()
            self.calculate()
            return

    def _collect_rebar_overrides(self) -> tuple[int | None, float | None]:
        mode = self.rein_inputs["mode"].currentText()
        user_nb = None
        user_sp = None

        if mode == "Override number of bars":
            user_nb = int(self.rein_inputs["num_bars"].value())
        elif mode == "Override spacing (c/c)":
            txt = self.rein_inputs["spacing"].text().strip()
            if txt:
                user_sp = float(txt)

        return user_nb, user_sp

    def calculate(self) -> None:
        try:
            b = float(self._get("width"))
            D = float(self._get("depth"))
            cover = float(self._get("cover"))
            fck = float(self._get("fck"))
            fy = float(self._get("fy"))
            dia = float(self._get("dia"))
            comp_dia = float(self._get("comp_dia"))
            span = float(self._get("span"))
            support = self._get("support")
            wdl = float(self._get("dl") or "0")
            wll = float(self._get("ll") or "0")

            coeff = BEAM_MOMENT_COEFFICIENTS.get(support, {})
            wu = 1.5 * (wdl + wll)
            gravity_mu = coeff.get("max_moment", 0.125) * wu * span**2
            Mu_design = gravity_mu
            gravity_vu = coeff.get("max_shear", 0.5) * wu * span
            Vu_design = gravity_vu

            mu_note = f"{coeff.get('max_moment', 0.125)} × wu × L²"
            vu_note = f"{coeff.get('max_shear', 0.5)} × wu × L"

            use_seismic = self.inputs["use_seismic"].isChecked()
            if use_seismic:
                try:
                    s_mu = float(self._get("seismic_mu"))
                    if s_mu > Mu_design:
                        Mu_design = s_mu
                        mu_note = "Seismic envelope governs"
                except ValueError:
                    pass
                try:
                    s_vu = float(self._get("seismic_vu"))
                    if s_vu > Vu_design:
                        Vu_design = s_vu
                        vu_note = "Seismic envelope governs"
                except ValueError:
                    pass

            Tu_txt = self._get("Tu")
            Tu = float(Tu_txt) if Tu_txt else 0.0
            span_defl_txt = self._get("span_defl")
            span_defl = float(span_defl_txt) if span_defl_txt else 0.0

            user_nb, user_sp = self._collect_rebar_overrides()
            legs = int(self.rein_inputs["stir_legs"].currentText())

            res = design_beam_section(
                b_mm=b,
                D_mm=D,
                cover_mm=cover,
                main_bar_dia_mm=dia,
                fck=fck,
                fy=fy,
                Mu_kNm=Mu_design,
                Vu_kN=Vu_design,
                Tu_kNm=Tu,
                span_m=span_defl,
                support_type=support,
                wdl_kNm=wdl,
                wll_kNm=wll,
                spacing_round_base=self.spacing_round_base,
                user_spacing_mm=user_sp,
                user_no_of_bars=user_nb,
                allow_doubly=self._allow_doubly_chk.isChecked(),
                comp_bar_dia_mm=comp_dia,
                stir_legs=legs,
            )

            self._last_res = res

            # Summary
            self.summary_labels["mu"].setText(f"{res['Mu_design_kNm']:.2f} kN·m")
            self.summary_labels["vu"].setText(f"{res['Vu_design_kN']:.2f} kN")
            self.summary_labels["d"].setText(f"{res['d_eff_mm']:.1f} mm")
            self.summary_labels["ast"].setText(f"{res['Ast_prov_mm2']:.1f} mm²")
            self.summary_labels["bars"].setText(f"{res['no_of_bars']} × Ø{int(dia)}")
            self.summary_labels["spacing"].setText(f"{res['spacing_cc_mm']:.1f} mm c/c")

            # Checks table
            Mu_lim = float(res["Mu_lim_kNm"])
            d_eff = float(res["d_eff_mm"])
            ld_limits = {
                "Simply Supported": 20,
                "Cantilever": 7,
                "Fixed-Fixed": 26,
                "Propped Cantilever": 20,
                "Continuous": 26,
            }
            ld_limit = ld_limits.get(support, 20)
            ld_ratio = span * 1000.0 / d_eff if d_eff > 0 else 999

            res_mu = float(res['Mu_design_kNm'])
            res_vu = float(res['Vu_design_kN'])

            rows = [
                ("Factored load wu", f"{wu:.3f}", "kN/m", "1.5 × (wD + wL)", "NBC 105 §3.6", "OK"),
                (
                    "Design moment Mu",
                    f"{res_mu:.3f}",
                    "kN·m",
                    mu_note if not float(Tu) else f"{mu_note} + torsion equiv",
                    "IS 456 / NBC 105",
                    "OK" if res_mu <= Mu_lim else ("INFO" if res.get("is_doubly") else "REVISE"),
                ),
                (
                    "Limiting moment Mu,lim",
                    f"{Mu_lim:.3f}",
                    "kN·m",
                    "Section moment capacity",
                    "IS 456 fallback §38",
                    "OK",
                ),
                (
                    "Design shear Vu",
                    f"{res_vu:.3f}",
                    "kN",
                    vu_note if not float(Tu) else f"{vu_note} + torsion equiv",
                    "IS 456 / NBC 105",
                    "OK",
                ),
                (
                    "Effective depth d",
                    f"{d_eff:.1f}",
                    "mm",
                    "D - cover - Ø/2",
                    "IS 456 fallback §26.3",
                    "OK",
                ),
                (
                    "Basic L/d",
                    f"{ld_ratio:.1f}",
                    "—",
                    f"≤ {ld_limit} (basic)",
                    "IS 456 fallback §23.2",
                    "OK" if ld_ratio <= ld_limit else "CHECK",
                ),
            ]

            self.results_table.clearSpans()
            self.results_table.setRowCount(len(rows))
            for r, (p, v, u, n, c, s) in enumerate(rows):
                self.results_table.setItem(r, 0, _cell(p, bold=True))
                self.results_table.setItem(r, 1, _cell(v))
                self.results_table.setItem(r, 2, _cell(u))
                self.results_table.setItem(r, 3, _cell(n))
                self.results_table.setItem(r, 4, _cell(c))
                self.results_table.setItem(r, 5, _status_cell(s))
            self._resize_results()

            # Reinforcement summary
            self.rein_labels["Ast_req"].setText(f"{res['Ast_req_mm2']:.1f}")
            self.rein_labels["Ast_min"].setText(f"{res['Ast_min_mm2']:.1f}")
            self.rein_labels["Ast_max"].setText(f"{res['Ast_max_mm2']:.1f}")
            self.rein_labels["Ast_prov"].setText(f"{res['Ast_prov_mm2']:.1f}")

            ast_ok = float(res["Ast_prov_mm2"]) >= float(res["Ast_req_mm2"])
            self.rein_labels["Ast_prov"].setStyleSheet(
                "font-weight:bold; font-size:11pt; color:#2E7D32;" if ast_ok
                else "font-weight:bold; font-size:11pt; color:#C62828;"
            )

            mode = self.rein_inputs["mode"].currentText()
            if mode != "Override number of bars":
                self.rein_inputs["num_bars"].blockSignals(True)
                self.rein_inputs["num_bars"].setValue(int(res["no_of_bars"]))
                self.rein_inputs["num_bars"].blockSignals(False)

            self.rein_inputs["spacing"].setText(f"{res['spacing_cc_mm']:.1f}")
            if self._handle_bar_spacing_warning(res):
                return

            shear = res.get("shear", {})
            sv = shear.get("Sv_mm")
            sv_end = shear.get("Sv_end_zone_mm") or sv
            sv_mid = shear.get("Sv_mid_zone_mm") or sv

            end_txt = self.rein_inputs["stir_sp_end"].text().strip()
            mid_txt = self.rein_inputs["stir_sp_mid"].text().strip()

            if not end_txt and sv_end:
                self.rein_inputs["stir_sp_end"].setText(str(int(sv_end)))
            if not mid_txt and sv_mid:
                self.rein_inputs["stir_sp_mid"].setText(str(int(sv_mid)))

            try:
                sv_end_use = float(self.rein_inputs["stir_sp_end"].text().strip()) if self.rein_inputs["stir_sp_end"].text().strip() else sv_end
            except ValueError:
                sv_end_use = sv_end
            try:
                sv_mid_use = float(self.rein_inputs["stir_sp_mid"].text().strip()) if self.rein_inputs["stir_sp_mid"].text().strip() else sv_mid
            except ValueError:
                sv_mid_use = sv_mid

            shear["Sv_end_zone_user_mm"] = round(float(sv_end_use), 1) if sv_end_use else None
            shear["Sv_mid_zone_user_mm"] = round(float(sv_mid_use), 1) if sv_mid_use else None

            end_ok = True if not sv_end else (25 <= sv_end_use <= float(sv_end))
            mid_ok = True if not sv_mid else (25 <= sv_mid_use <= float(sv_mid))
            ok = end_ok and mid_ok

            self.rein_labels["Shear"].setStyleSheet(f"font-weight:bold; color:{'#2E7D32' if ok else '#C62828'};")
            self.rein_labels["Shear"].setText(
                f"{shear.get('status', '--')}  —  support@{int(sv_end_use) if sv_end_use else '--'}mm, "
                f"mid@{int(sv_mid_use) if sv_mid_use else '--'}mm"
            )

            # Doubly reinforcement
            dr = res.get("doubly")
            if dr:
                self._doubly_group.setVisible(True)
                self.comp_labels["Asc_req"].setText(f"{dr['Asc_req_mm2']:.1f}")
                self.comp_labels["Asc_prov"].setText(f"{dr['Asc_prov_mm2']:.1f}")
                self.comp_labels["comp_bars"].setText(f"{dr['no_comp_bars']} × Ø{int(dr['comp_bar_dia'])}")
                self.comp_labels["fsc"].setText(f"{dr['fsc_MPa']:.0f}")
                self.comp_labels["d_prime"].setText(f"{dr['d_prime_mm']:.1f}")
                self.comp_labels["Ast1"].setText(f"{dr['Ast1_mm2']:.1f}")
                self.comp_labels["Ast2"].setText(f"{dr['Ast2_mm2']:.1f}")
            else:
                self._doubly_group.setVisible(False)

            # Deflection
            dd = res.get("deflection")
            if dd:
                self._defl_group.setVisible(True)
                self._defl_labels["ld_basic"].setText(str(dd.get("ld_basic", "--")))
                self._defl_labels["fs"].setText(f"{dd.get('fs_serv', 0):.1f}")
                self._defl_labels["kt"].setText(f"{dd.get('kt', 0):.3f}")
                self._defl_labels["kc"].setText(f"{dd.get('kc', 0):.3f}")
                self._defl_labels["ld_allow"].setText(f"{dd.get('ld_allow', 0):.1f}")
                self._defl_labels["ld_prov"].setText(f"{dd.get('ld_prov', 0):.1f}")
                ok = bool(dd.get("ok"))
                self._defl_status.setText("OK ✓" if ok else "Increase section depth/span ratio ✗")
                self._defl_status.setStyleSheet(f"font-weight:bold; color:{'#2E7D32' if ok else '#C62828'};")
            else:
                self._defl_group.setVisible(False)

            # Notes
            if "Ld_mm" in res:
                basis = res.get("code_design_basis", "NBC priority + IS fallback")
                self._ld_lbl.setText(
                    f"{basis}  |  Development length Ld = {res['Ld_mm']:.0f} mm (IS 456 fallback §26.2.1)"
                )
            self.notes_edit.setPlainText("\n\n".join(res.get("notes", ["—"])))

        except Exception as e:
            self._last_res = None
            self.results_table.setRowCount(1)
            self.results_table.setItem(0, 0, _cell(f"⚠ {e}", fg="#EF9A9A"))
            self.results_table.setSpan(0, 0, 1, 6)
            self._resize_results()

    def _populate_from_seismic(self) -> None:
        if not self._seismic_ref:
            return
        try:
            ct = self._seismic_ref.get_ct_value()
            L = float(self._get("span") or "0")
            support = self._get("support")
            coeff = BEAM_MOMENT_COEFFICIENTS.get(support, {})
            wdl = float(self._get("dl") or "0")
            wll = float(self._get("ll") or "0")
            wu = 1.5 * (wdl + wll)

            self.inputs["seismic_mu"].setText(f"{coeff.get('max_moment', 0.125) * wu * L**2 * ct:.3f}")
            self.inputs["seismic_vu"].setText(f"{coeff.get('max_shear', 0.5) * wu * L * ct:.3f}")
        except Exception:
            pass

    def _set_defaults(self) -> None:
        defaults = [
            ("span", "6.0"),
            ("width", "230"),
            ("depth", "355"),
            ("ll", "3"),
            ("cover", "25"),
            ("span_defl", "6.0"),
        ]
        for k, v in defaults:
            self.inputs[k].setText(v)

        self.inputs["fck"].setCurrentText("20")
        self.inputs["fy"].setCurrentText("500")
        self.inputs["dia"].setCurrentText("12")
        self.inputs["comp_dia"].setCurrentText("12")
        self.inputs["support"].setCurrentText("Simply Supported")

        self.rein_inputs["mode"].setCurrentText("Auto")
        self.rein_inputs["num_bars"].setValue(4)
        self.rein_inputs["spacing"].clear()
        self.rein_inputs["stir_sp_end"].clear()
        self.rein_inputs["stir_sp_mid"].clear()
        self.rein_inputs["stir_legs"].setCurrentText("2")

        self._auto_dl_chk.setChecked(True)
        self._on_auto_dl(True)
