"""
ui/tabs/foundation_tab.py — IS 456:2000 Isolated Footing Design
Fixed: shared input key conflict between panels, _wire() triple-connection bug,
       enlarged notes area, responsive layout
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QRadioButton, QButtonGroup,
    QStackedWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from core import design_footing, design_eccentric_footing, design_combined_footing
from ui.widgets import UnitLineEdit





def _cell(text, bold=False, bg=None, fg=None):
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    if bold:
        f = QFont(); f.setBold(True); item.setFont(f)
    if bg: item.setBackground(QColor(bg))
    if fg: item.setForeground(QColor(fg))
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

class FoundationTab(QWidget):
    """
    Three footing types via radio buttons and a QStackedWidget.
    CRITICAL FIX: each panel uses UNIQUE input key prefixes so no shared keys.
    Material properties (fck, fy, cover, bar_dia) are SHARED but belong to
    a single material widget group shown at the top, NOT duplicated per panel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # All input widgets in one flat dict with unique keys
        self.inputs: dict = {}
        self._last_result: dict = {}
        self._build_ui()
        self._set_defaults()

    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 12, 10, 12)
        root.setSpacing(8)

        # ── Type selector ────────────────────────────────────────────────────
        mode_grp = QGroupBox("Footing Type")
        mode_lay = QHBoxLayout(mode_grp)
        self._mode_bg = QButtonGroup(self)
        self._rad_conc = QRadioButton("Concentric Isolated")
        self._rad_ecc  = QRadioButton("Eccentric Isolated  (moments present)")
        self._rad_comb = QRadioButton("Combined  (two columns)")
        for i, r in enumerate([self._rad_conc, self._rad_ecc, self._rad_comb]):
            self._mode_bg.addButton(r, i)
            mode_lay.addWidget(r)
        self._rad_ecc.setChecked(True)
        mode_lay.addStretch()
        root.addWidget(mode_grp)
        self._mode_bg.buttonToggled.connect(lambda *_: self._on_mode_changed())

        # ── Material / geometry strip (shared, always visible) ────────────────
        mat_grp = QGroupBox("Material Properties & Footing Depth")
        mat_lay = QGridLayout(mat_grp)
        mat_lay.setVerticalSpacing(7)
        mat_lay.setHorizontalSpacing(12)

        fck_w = QComboBox(); fck_w.addItems(["20","25","30","35","40"])
        fy_w  = QComboBox(); fy_w.addItems(["250","415","500"])
        self.inputs["fck"]     = fck_w
        self.inputs["fy"]      = fy_w
        self.inputs["cover"]   = UnitLineEdit("mm")
        self.inputs["bar_dia"] = QComboBox()
        self.inputs["bar_dia"].addItems(["10","12","16","20"])
        self.inputs["f_D"]     = QLineEdit()
        self.inputs["f_D"].setPlaceholderText("auto")
        self.inputs["f_L"]     = QLineEdit()
        self.inputs["f_L"].setPlaceholderText("auto")
        self.inputs["f_B"]     = QLineEdit()
        self.inputs["f_B"].setPlaceholderText("auto")
        self.inputs["seismic"] = QCheckBox(
            "Seismic combo — SBC × 1.5  (NBC 105:2025 §3.8)")

        for col, (lbl, key) in enumerate([
            ("fck [MPa]:", "fck"), ("fy [MPa]:", "fy"),
            ("Cover [mm]:", "cover"), ("Bar Ø [mm]:", "bar_dia"),
        ]):
            mat_lay.addWidget(QLabel(lbl), 0, col*2)
            mat_lay.addWidget(self.inputs[key], 0, col*2+1)
        for col, (lbl, key) in enumerate([
            ("Depth D [mm] (auto):", "f_D"),
            ("Length L [mm] (auto):", "f_L"),
            ("Breadth B [mm] (auto):", "f_B"),
        ]):
            mat_lay.addWidget(QLabel(lbl), 1, col*2)
            mat_lay.addWidget(self.inputs[key], 1, col*2+1)
        mat_lay.addWidget(self.inputs["seismic"], 2, 0, 1, 8)
        for i in range(8): mat_lay.setColumnStretch(i, 1)
        root.addWidget(mat_grp)

        # ── Stacked input panels (column/load only, no material duplication) ─
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_conc_panel())
        self._stack.addWidget(self._build_ecc_panel())
        self._stack.addWidget(self._build_comb_panel())
        self._stack.setCurrentIndex(1)
        root.addWidget(self._stack)

        # ── Results table ────────────────────────────────────────────────────
        res_grp = QGroupBox("Design Results  —  IS 456:2000 §34 + NBC 105:2025 §3.8")
        res_lay = QVBoxLayout(res_grp)
        self.res_table = QTableWidget()
        self.res_table.setColumnCount(4)
        self.res_table.setHorizontalHeaderLabels(
            ["Check", "Computed", "Limit / Clause", "Status"])
        self.res_table.verticalHeader().setVisible(False)
        self.res_table.setAlternatingRowColors(True)
        self.res_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.res_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        res_lay.addWidget(self.res_table)
        root.addWidget(res_grp)

        # ── Notes ────────────────────────────────────────────────────────────
        notes_grp = QGroupBox("Design Notes")
        notes_lay = QVBoxLayout(notes_grp)
        self.notes_edit = QTextEdit(readOnly=True)
        self.notes_edit.setMinimumHeight(120)
        notes_lay.addWidget(self.notes_edit)
        root.addWidget(notes_grp, stretch=1)

        # Wire material controls
        for key in ("fck","fy","cover","bar_dia","f_D","f_L","f_B"):
            w = self.inputs[key]
            sig = w.currentTextChanged if isinstance(w, QComboBox) else w.textChanged
            sig.connect(self.calculate)
        self.inputs["seismic"].toggled.connect(self.calculate)

    # ── Panel builders — UNIQUE KEY PREFIXES per panel ────────────────────────
    def _build_conc_panel(self) -> QGroupBox:
        g = QGroupBox("Concentric Footing — Column & Load")
        lay = QGridLayout(g); lay.setVerticalSpacing(8)
        for r, (lbl, key) in enumerate([
            ("Column width b [mm]:", "cc_b"),
            ("Column depth D [mm]:", "cc_D"),
            ("Service Axial P [kN]:", "cc_P"),
            ("SBC [kN/m²]:",          "cc_sbc"),
        ]):
            w = UnitLineEdit("mm") if "b" in key or "D" in key else QLineEdit()
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl), r, 0); lay.addWidget(w, r, 1)
            w.editingFinished.connect(self.calculate)
        lay.setColumnStretch(1, 1)
        return g

    def _build_ecc_panel(self) -> QGroupBox:
        g = QGroupBox("Eccentric Footing — Column, Loads & Moments")
        lay = QGridLayout(g); lay.setVerticalSpacing(8)
        for r, (lbl, key, ph) in enumerate([
            ("Column width b [mm]:",   "ec_b",   "mm"),
            ("Column depth D [mm]:",   "ec_D",   "mm"),
            ("Service Axial P [kN]:",  "ec_P",   "kN"),
            ("Moment Mx [kN·m]:",      "ec_Mx",  "0"),
            ("Moment My [kN·m]:",      "ec_My",  "0"),
            ("SBC [kN/m²]:",           "ec_sbc", "150"),
        ]):
            if "b" in key or "D" in key:
                w = UnitLineEdit("mm")
            else:
                w = QLineEdit(); w.setPlaceholderText(ph)
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl), r, 0); lay.addWidget(w, r, 1)
            w.editingFinished.connect(self.calculate)
        lay.setColumnStretch(1, 1)
        return g

    def _build_comb_panel(self) -> QGroupBox:
        g = QGroupBox("Combined Footing — Two Columns (Left → Right)")
        lay = QGridLayout(g); lay.setVerticalSpacing(8)
        for r, (lbl, key, ph) in enumerate([
            ("Col 1 width b [mm]:",  "cb1_b",  "300"),
            ("Col 1 depth D [mm]:",  "cb1_D",  "400"),
            ("Col 1 load P1 [kN]:",  "cb_P1",  "600"),
            ("Col 2 width b [mm]:",  "cb2_b",  "300"),
            ("Col 2 depth D [mm]:",  "cb2_D",  "400"),
            ("Col 2 load P2 [kN]:",  "cb_P2",  "700"),
            ("C/C spacing [m]:",     "cb_sp",  "5.0"),
            ("SBC [kN/m²]:",         "cb_sbc", "120"),
        ]):
            w = QLineEdit(); w.setPlaceholderText(ph)
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl), r, 0); lay.addWidget(w, r, 1)
            w.editingFinished.connect(self.calculate)
        lay.setColumnStretch(1, 1)
        return g

    # ══════════════════════════════════════════════════════════════════════════
    def _on_mode_changed(self):
        idx = self._mode_bg.checkedId()
        if idx < 0: idx = 1
        self._stack.setCurrentIndex(idx)
        self.calculate()

    def _g(self, key: str, default="0"):
        w = self.inputs.get(key)
        if w is None: return default
        if isinstance(w, QComboBox):  return w.currentText()
        if isinstance(w, QCheckBox):  return w.isChecked()
        return w.text().strip() or default

    def _f(self, key: str, default=0.0) -> float:
        try:
            return float(self._g(key, str(default)))
        except (ValueError, TypeError):
            return default

    def _opt_f(self, key: str):
        t = self._g(key, "")
        try:
            return float(t) if t else None
        except (ValueError, TypeError):
            return None

    def _resize(self):
        t = self.res_table
        h = t.horizontalHeader().height()
        h += sum(t.rowHeight(r) for r in range(t.rowCount())) + 6
        t.setFixedHeight(h)

    def _fill_table(self, rows):
        self.res_table.setRowCount(len(rows))
        for i, (chk, val, lim, st) in enumerate(rows):
            self.res_table.setItem(i, 0, _cell(chk, bold=True))
            self.res_table.setItem(i, 1, _cell(val))
            self.res_table.setItem(i, 2, _cell(lim))
            self.res_table.setItem(i, 3, _status_cell(st))
        self._resize()

    def calculate(self):
        try:
            mode = self._mode_bg.checkedId()
            if mode < 0: mode = 1

            fck  = int(self._g("fck", "25"))
            fy   = int(self._g("fy",  "415"))
            cov  = self._f("cover", 50)
            bar  = float(self._g("bar_dia", "12"))
            fD   = self._opt_f("f_D")
            fL   = self._opt_f("f_L")
            fB   = self._opt_f("f_B")
            seis = bool(self._g("seismic", False))
            
            if cov <= 0 or bar <= 0:
                raise ValueError("Cover and Bar diameter must be > 0.")
            if fD is not None and fD <= 0:
                raise ValueError("Footing Depth D must be > 0.")
            if fL is not None and fL <= 0:
                raise ValueError("Footing Length L must be > 0.")
            if fB is not None and fB <= 0:
                raise ValueError("Footing Breadth B must be > 0.")

            if mode == 0:   # Concentric
                res = design_footing(
                    self._f("cc_b", 300), self._f("cc_D", 400),
                    self._f("cc_P", 600), 0, 0,
                    self._f("cc_sbc", 150), fck, fy, cov, bar, fD, fL, fB, seis)
            elif mode == 1:  # Eccentric
                res = design_eccentric_footing(
                    self._f("ec_b", 300), self._f("ec_D", 400),
                    self._f("ec_P", 800),
                    self._f("ec_Mx", 0), self._f("ec_My", 0),
                    self._f("ec_sbc", 150), fck, fy, cov, bar, fD, fL, fB, seis)
            else:            # Combined
                res = design_combined_footing(
                    self._f("cb1_b", 300), self._f("cb1_D", 400),
                    self._f("cb2_b", 300), self._f("cb2_D", 400),
                    self._f("cb_P1", 600), self._f("cb_P2", 700),
                    self._f("cb_sp", 5.0),
                    self._f("cb_sbc", 120), fck, fy, cov, bar, fD, seis)

            # Store footing type and input parameters for export
            self._last_result = {
                **res,
                "footing_type": ["Concentric Isolated", "Eccentric Isolated", "Combined"][mode],
                "footing_type_id": mode,
                "fck": fck,
                "fy": fy,
                "cover_mm": cov,
                "bar_dia_mm": bar,
                "seismic_used": seis,
            }
            
            # Add type-specific inputs to _last_result
            if mode == 0:  # Concentric
                self._last_result.update({
                    "cc_b_mm": self._f("cc_b", 300),
                    "cc_D_mm": self._f("cc_D", 400),
                    "cc_P_kN": self._f("cc_P", 600),
                    "cc_sbc_kPa": self._f("cc_sbc", 150),
                })
            elif mode == 1:  # Eccentric
                self._last_result.update({
                    "ec_b_mm": self._f("ec_b", 300),
                    "ec_D_mm": self._f("ec_D", 400),
                    "ec_P_kN": self._f("ec_P", 800),
                    "ec_Mx_kNm": self._f("ec_Mx", 0),
                    "ec_My_kNm": self._f("ec_My", 0),
                    "ec_sbc_kPa": self._f("ec_sbc", 150),
                })
            else:  # Combined
                self._last_result.update({
                    "cb1_b_mm": self._f("cb1_b", 300),
                    "cb1_D_mm": self._f("cb1_D", 400),
                    "cb2_b_mm": self._f("cb2_b", 300),
                    "cb2_D_mm": self._f("cb2_D", 400),
                    "cb_P1_kN": self._f("cb_P1", 600),
                    "cb_P2_kN": self._f("cb_P2", 700),
                    "cb_sp_m": self._f("cb_sp", 5.0),
                    "cb_sbc_kPa": self._f("cb_sbc", 120),
                })

            if mode in (0, 1):
                rows = [
                    ("Footing Plan",
                     f"{res['L_mm']} × {res['B_mm']} mm  (A = {res['A_m2']:.2f} m²)",
                     f"Depth D = {res['D_mm']:.0f} mm  (IS 456 §34.1.3 ≥ 300 mm)",
                     "INFO"),
                    ("Soil Pressure q_max",
                     f"{res['q_max_kPa']:.2f} kN/m²",
                     f"SBC = {res['SBC_used_kPa']:.0f} kN/m²  (IS 456 §34.2)",
                     "OK" if res['pressure_ok'] else "FAIL"),
                    ("Soil Pressure q_min",
                     f"{res['q_min_kPa']:.2f} kN/m²",
                     "≥ 0  (IS 456 §34.2.4 — no uplift)",
                     "OK" if res['q_min_kPa'] >= 0 else "WARN"),
                ]
                if mode == 1:
                    rows += [
                        ("Eccentricity ex  (from My)",
                         f"{res['ex_m']:.4f} m",
                         f"Kern = {res['L_mm']/1000/6:.3f} m  (IS 456 §34.2.4)",
                         "OK" if res.get('kern_ok') else "WARN"),
                        ("Eccentricity ey  (from Mx)",
                         f"{res['ey_m']:.4f} m",
                         f"Kern = {res['B_mm']/1000/6:.3f} m",
                         "OK" if res.get('kern_ok') else "WARN"),
                    ]
                rows += [
                    ("Moment Mu,L  (long dir.)",
                     f"{res['Mu_L_kNm']:.2f} kN·m",
                     f"Ast = {res['Ast_L_per_m_mm2']:.0f} mm²/m  → "
                     f"Ø{int(bar)} @ {res['sp_L_mm']} mm c/c",
                     "INFO"),
                    ("Moment Mu,B  (short dir.)",
                     f"{res['Mu_B_kNm']:.2f} kN·m",
                     f"Ast = {res['Ast_B_per_m_mm2']:.0f} mm²/m  → "
                     f"Ø{int(bar)} @ {res['sp_B_mm']} mm c/c",
                     "INFO"),
                    ("One-way Shear",
                     f"τv,L = {res['tau_v_L']:.3f},  τv,B = {res['tau_v_B']:.3f} MPa",
                     f"τc = {res['tau_c_L']:.3f} MPa  (IS 456 §34.4.2a)",
                     "OK" if res['one_way_ok'] else "FAIL"),
                    ("Punching Shear",
                     f"τv = {res['tau_v_punch']:.3f} MPa",
                     f"τc = 0.25√fck = {res['tau_c_punch']:.3f} MPa  (IS 456 §31.6)",
                     "OK" if res['punch_ok'] else "FAIL"),
                    ("Development Length Ld",
                     f"{res['Ld_mm']:.0f} mm",
                     f"Available = {res.get('avail_L_mm', res.get('avail_m',0)):.0f} mm  "
                     f"(IS 456 §34.4.3)",
                     "OK" if res['dev_ok'] else "FAIL"),
                ]
                if 'bear_ok' in res:
                    rows.append((
                        "Col-Ftg Bearing",
                        f"{res['bear_stress_MPa']:.3f} MPa",
                        f"≤ {res['bear_allow_MPa']:.3f} MPa  (IS 456 §34.4.4)",
                        "OK" if res['bear_ok'] else "FAIL"))
            else:  # Combined
                rows = [
                    ("Footing Plan",
                     f"{res['L_mm']} × {res['B_mm']} mm  (A = {res['A_m2']:.2f} m²)",
                     f"Depth D = {res['D_mm']:.0f} mm",
                     "INFO"),
                    ("Net Soil Pressure",
                     f"{res['q_net_kPa']:.2f} kN/m²",
                     f"SBC = {res['SBC_used_kPa']:.0f} kN/m²",
                     "OK" if res['pressure_ok'] else "FAIL"),
                    ("Resultant Location",
                     f"{res['x_resultant_m']*1000:.0f} mm from col 1",
                     "Footing centred on resultant",
                     "INFO"),
                    ("Design Moment Mu",
                     f"{res['Mu_design_kNm']:.2f} kN·m",
                     f"Long. Ast = {res['Ast_long_per_m_mm2']:.0f} mm²/m  "
                     f"@ {res['sp_long_mm']} mm",
                     "INFO"),
                    ("Transverse Ast",
                     f"{res['Ast_trans_per_m_mm2']:.0f} mm²/m",
                     f"@ {res['sp_trans_mm']} mm c/c",
                     "INFO"),
                    ("Punching — Col 1",
                     f"τv = {res['tau_v_punch_c1']:.3f} MPa",
                     f"τc = {res['tau_c_punch']:.3f} MPa  (IS 456 §31.6)",
                     "OK" if res['punch_col1_ok'] else "FAIL"),
                    ("Punching — Col 2",
                     f"τv = {res['tau_v_punch_c2']:.3f} MPa",
                     f"τc = {res['tau_c_punch']:.3f} MPa",
                     "OK" if res['punch_col2_ok'] else "FAIL"),
                    ("Development Length",
                     f"Ld = {res['Ld_mm']:.0f} mm",
                     f"Available = ok  (IS 456 §26.2.1)",
                     "OK" if res['dev_ok'] else "FAIL"),
                ]
            self._fill_table(rows)
            self.notes_edit.setPlainText("\n\n".join(res.get("notes", ["—"])))

        except Exception as e:
            self.res_table.setRowCount(1)
            err = _cell(f"⚠  {e}", fg="#EF9A9A")
            self.res_table.setItem(0, 0, err)
            self.res_table.setSpan(0, 0, 1, 4)
            self._resize()

    def _set_defaults(self):
        d = {
            "cc_b":"300","cc_D":"400","cc_P":"600","cc_sbc":"150",
            "ec_b":"300","ec_D":"400","ec_P":"800",
            "ec_Mx":"50","ec_My":"35","ec_sbc":"150",
            "cb1_b":"300","cb1_D":"400","cb_P1":"600",
            "cb2_b":"300","cb2_D":"400","cb_P2":"700",
            "cb_sp":"5.0","cb_sbc":"120",
            "cover":"50",
        }
        for k, v in d.items():
            w = self.inputs.get(k)
            if w and hasattr(w, "setText"):
                w.setText(v)
        self.inputs["fck"].setCurrentText("25")
        self.inputs["fy"].setCurrentText("415")
        self.inputs["bar_dia"].setCurrentText("12")
        self.calculate()
