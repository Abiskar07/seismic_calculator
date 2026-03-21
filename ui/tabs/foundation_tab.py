"""
ui/tabs/foundation_tab.py
Isolated Footing — Concentric, Eccentric, Combined
Three sub-modes selectable via radio buttons.
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QRadioButton,
    QButtonGroup, QStackedWidget, QPushButton,
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

STATUS = {
    "OK":   ("#1B5E20","#A5D6A7"),
    "FAIL": ("#7F0000","#EF9A9A"),
    "WARN": ("#6D3500","#FFCC80"),
    "INFO": ("#0D47A1","#90CAF9"),
}

def _lbl(t="--"):
    l = QLabel(t); l.setStyleSheet("font-weight:bold;"); return l


class FoundationTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs: dict = {}
        self._last_result: dict = {}
        self._build_ui()
        self._set_defaults()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 12, 10, 12)
        root.setSpacing(10)

        # ── Mode selector ─────────────────────────────────────────────────────
        mode_grp = QGroupBox("Footing Type")
        mode_lay = QHBoxLayout(mode_grp)
        self._mode_bg = QButtonGroup(self)
        self._rad_conc = QRadioButton("Concentric Isolated")
        self._rad_ecc  = QRadioButton("Eccentric Isolated  (moments present)")
        self._rad_comb = QRadioButton("Combined Footing  (two columns)")
        for i, r in enumerate([self._rad_conc, self._rad_ecc, self._rad_comb]):
            self._mode_bg.addButton(r, i)
            mode_lay.addWidget(r)
        self._rad_ecc.setChecked(True)
        mode_lay.addStretch()
        root.addWidget(mode_grp)
        self._mode_bg.buttonToggled.connect(lambda *_: self._on_mode_changed())

        # ── Stacked input panels ──────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_conc_inputs())   # 0 — concentric
        self._stack.addWidget(self._build_ecc_inputs())    # 1 — eccentric
        self._stack.addWidget(self._build_comb_inputs())   # 2 — combined
        self._stack.setCurrentIndex(1)
        root.addWidget(self._stack)

        # ── Results table ─────────────────────────────────────────────────────
        res_grp = QGroupBox("Design Results")
        res_lay = QVBoxLayout(res_grp)
        self.res_table = QTableWidget()
        self.res_table.setColumnCount(4)
        self.res_table.setHorizontalHeaderLabels(["Check", "Computed", "Limit / Clause", "Status"])
        self.res_table.verticalHeader().setVisible(False)
        self.res_table.setAlternatingRowColors(True)
        self.res_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.res_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        res_lay.addWidget(self.res_table)
        root.addWidget(res_grp)

        # ── Notes ─────────────────────────────────────────────────────────────
        notes_grp = QGroupBox("Design Notes  (IS 456:2000 §34 + NBC 105:2025 §3.8)")
        notes_lay = QVBoxLayout(notes_grp)
        self.notes_edit = QTextEdit(readOnly=True)
        self.notes_edit.setMaximumHeight(150)
        notes_lay.addWidget(self.notes_edit)
        root.addWidget(notes_grp)
        root.addStretch()

    # ── Input panel builders ─────────────────────────────────────────────────

    def _material_row(self, lay, row_start):
        """Add fck/fy/cover/bar rows, return next row."""
        row = row_start
        for lbl, key, opts, r in [
            ("fck [MPa]:", "fck", ["20","25","30","35","40"], 0),
            ("fy [MPa]:",  "fy",  ["250","415","500"],        1),
        ]:
            w = QComboBox(); w.addItems(opts)
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl), row+r, 2); lay.addWidget(w, row+r, 3)
        for lbl, key, r in [("Cover [mm]:", "cover", 2), ("Bar Ø [mm]:", "bar_dia", 3)]:
            w = UnitLineEdit("mm"); self.inputs[key] = w
            lay.addWidget(QLabel(lbl), row+r, 2); lay.addWidget(w, row+r, 3)
        for lbl, key, r in [
            ("Footing D [mm]\n(blank=auto):", "f_D", 4),
            ("Footing L [mm]\n(blank=auto):", "f_L", 5),
            ("Footing B [mm]\n(blank=auto):", "f_B", 6),
        ]:
            w = QLineEdit(); w.setPlaceholderText("auto"); self.inputs[key] = w
            lay.addWidget(QLabel(lbl), row+r, 2); lay.addWidget(w, row+r, 3)
        self.inputs["seismic"] = QCheckBox("Seismic combo (+50% SBC per NBC 105:2025 §3.8)")
        lay.addWidget(self.inputs["seismic"], row+7, 0, 1, 4)
        return row + 8

    def _wire(self):
        for w in self.inputs.values():
            sig = (w.currentTextChanged if isinstance(w, QComboBox)
                   else w.toggled if isinstance(w, QCheckBox)
                   else w.textChanged)
            sig.connect(self.calculate)

    def _build_conc_inputs(self):
        g = QGroupBox("Column & Loads")
        lay = QGridLayout(g); lay.setVerticalSpacing(8)
        for lbl, key, r in [
            ("Col. width b [mm]:", "cc_b", 0),
            ("Col. depth D [mm]:", "cc_D", 1),
            ("Axial P [kN]:",      "cc_P", 2),
            ("SBC [kN/m²]:",       "cc_sbc", 3),
        ]:
            w = UnitLineEdit("mm" if "b" in key or "D" in key else "")
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl), r, 0); lay.addWidget(w, r, 1)
        self._material_row(lay, 0)
        lay.setColumnStretch(1,1); lay.setColumnStretch(3,1)
        self._wire(); return g

    def _build_ecc_inputs(self):
        g = QGroupBox("Column, Loads & Moments")
        lay = QGridLayout(g); lay.setVerticalSpacing(8)
        for lbl, key, r in [
            ("Col. width b [mm]:", "ec_b", 0),
            ("Col. depth D [mm]:", "ec_D", 1),
            ("Axial P [kN]:",      "ec_P", 2),
            ("Moment Mx [kN·m]:",  "ec_Mx",3),
            ("Moment My [kN·m]:",  "ec_My",4),
            ("SBC [kN/m²]:",       "ec_sbc",5),
        ]:
            w = QLineEdit(); w.setPlaceholderText("0" if "M" in key else "")
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl), r, 0); lay.addWidget(w, r, 1)
        self._material_row(lay, 0)
        lay.setColumnStretch(1,1); lay.setColumnStretch(3,1)
        self._wire(); return g

    def _build_comb_inputs(self):
        g = QGroupBox("Two Columns  (left → right)")
        lay = QGridLayout(g); lay.setVerticalSpacing(8)
        for lbl, key, r in [
            ("Col 1 width b [mm]:", "cb1_b", 0),
            ("Col 1 depth D [mm]:", "cb1_D", 1),
            ("Col 1 load P1 [kN]:", "cb_P1", 2),
            ("Col 2 width b [mm]:", "cb2_b", 3),
            ("Col 2 depth D [mm]:", "cb2_D", 4),
            ("Col 2 load P2 [kN]:", "cb_P2", 5),
            ("C/C spacing [m]:",    "cb_sp", 6),
            ("SBC [kN/m²]:",        "cb_sbc",7),
        ]:
            w = QLineEdit()
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl), r, 0); lay.addWidget(w, r, 1)
        self._material_row(lay, 0)
        lay.setColumnStretch(1,1); lay.setColumnStretch(3,1)
        self._wire(); return g

    def _on_mode_changed(self):
        idx = self._mode_bg.checkedId()
        if idx < 0: idx = 1
        self._stack.setCurrentIndex(idx)
        self.calculate()

    def _g(self, key, default="0"):
        w = self.inputs.get(key)
        if w is None: return default
        if isinstance(w, QComboBox): return w.currentText()
        if isinstance(w, QCheckBox): return w.isChecked()
        return w.text().strip() or default

    def _f(self, key, default=0.0):
        try: return float(self._g(key, str(default)))
        except: return default

    def _opt_f(self, key):
        t = self._g(key, "")
        try: return float(t) if t else None
        except: return None

    def _resize(self):
        t = self.res_table
        h = t.horizontalHeader().height()
        h += sum(t.rowHeight(r) for r in range(t.rowCount())) + 4
        t.setFixedHeight(h)

    def _fill_table(self, rows):
        self.res_table.setRowCount(len(rows))
        for i, (chk, val, lim, st) in enumerate(rows):
            self.res_table.setItem(i, 0, _cell(chk, bold=True))
            self.res_table.setItem(i, 1, _cell(val))
            self.res_table.setItem(i, 2, _cell(lim))
            bg, fg = STATUS.get(st, (None, None))
            self.res_table.setItem(i, 3, _cell(st, bold=True, bg=bg, fg=fg))
        self._resize()

    def calculate(self):
        try:
            mode = self._mode_bg.checkedId()
            if mode < 0: mode = 1
            fck = int(self._g("fck","25"))
            fy  = int(self._g("fy", "415"))
            cov = self._f("cover", 50)
            bar = float(self._g("bar_dia","12"))
            fD  = self._opt_f("f_D")
            fL  = self._opt_f("f_L")
            fB  = self._opt_f("f_B")
            seis= bool(self._g("seismic", False))

            if mode == 0:   # Concentric
                P   = self._f("cc_P", 600)
                sbc = self._f("cc_sbc", 150)
                cb  = self._f("cc_b", 300); cD = self._f("cc_D", 400)
                res = design_footing(cb, cD, P, 0, 0, sbc, fck, fy, cov, bar,
                                     fD, fL, fB, seis)
            elif mode == 1:  # Eccentric
                P   = self._f("ec_P", 800)
                Mx  = self._f("ec_Mx", 40)
                My  = self._f("ec_My", 30)
                sbc = self._f("ec_sbc", 150)
                cb  = self._f("ec_b", 300); cD = self._f("ec_D", 400)
                res = design_eccentric_footing(cb, cD, P, Mx, My, sbc, fck, fy,
                                               cov, bar, fD, fL, fB, seis)
            else:            # Combined
                P1  = self._f("cb_P1", 600); P2 = self._f("cb_P2", 700)
                sp  = self._f("cb_sp", 5.0)
                sbc = self._f("cb_sbc", 150)
                b1  = self._f("cb1_b", 300); D1 = self._f("cb1_D", 400)
                b2  = self._f("cb2_b", 300); D2 = self._f("cb2_D", 400)
                res = design_combined_footing(b1, D1, b2, D2, P1, P2, sp,
                                              sbc, fck, fy, cov, bar, fD, seis)

            self._last_result = res

            if mode in (0, 1):
                rows = [
                    ("Footing Plan",
                     f"{res['L_mm']} × {res['B_mm']} mm  (A={res['A_m2']:.2f} m²)",
                     f"Min D={res['D_mm']:.0f}mm  (IS 456 §34.1.3 ≥300mm)",
                     "INFO"),
                    ("q_max (service)",
                     f"{res['q_max_kPa']:.2f} kN/m²",
                     f"≤ {res['SBC_used_kPa']:.0f} kN/m²",
                     "OK" if res['pressure_ok'] else "FAIL"),
                    ("q_min (service)",
                     f"{res['q_min_kPa']:.2f} kN/m²",
                     "≥ 0  (no soil tension)",
                     "OK" if res['q_min_kPa'] >= 0 else "FAIL"),
                ]
                if mode == 1:
                    rows += [
                        ("Eccentricity ex",
                         f"{res['ex_m']:.4f} m",
                         f"Kern limit = {res['L_mm']/1000/6:.3f} m",
                         "OK" if res.get('kern_ok') else "WARN"),
                        ("Eccentricity ey",
                         f"{res['ey_m']:.4f} m",
                         f"Kern limit = {res['B_mm']/1000/6:.3f} m",
                         "OK" if res.get('kern_ok') else "WARN"),
                    ]
                rows += [
                    ("Bending Mu_L",
                     f"{res['Mu_L_kNm']:.2f} kN·m",
                     f"Ast={res['Ast_L_per_m_mm2']:.0f}mm²/m → Ø{int(bar)}@{res['sp_L_mm']}mm",
                     "INFO"),
                    ("Bending Mu_B",
                     f"{res['Mu_B_kNm']:.2f} kN·m",
                     f"Ast={res['Ast_B_per_m_mm2']:.0f}mm²/m → Ø{int(bar)}@{res['sp_B_mm']}mm",
                     "INFO"),
                    ("One-way shear",
                     f"τv_L={res['tau_v_L']:.3f}, τv_B={res['tau_v_B']:.3f} MPa",
                     f"τc={res['tau_c_L']:.3f} MPa  (IS 456 §34.4.2a)",
                     "OK" if res['one_way_ok'] else "FAIL"),
                    ("Punching shear",
                     f"τv={res['tau_v_punch']:.3f} MPa",
                     f"τc=0.25√fck={res['tau_c_punch']:.3f} MPa  (IS 456 §31.6)",
                     "OK" if res['punch_ok'] else "FAIL"),
                    ("Development length",
                     f"Ld={res['Ld_mm']:.0f} mm",
                     f"Available={res.get('avail_L_mm',res.get('avail_m',0)):.0f}mm  (IS 456 §26.2.1)",
                     "OK" if res['dev_ok'] else "WARN"),
                ]
                if 'bear_ok' in res:
                    rows.append(("Col-ftg bearing",
                        f"{res['bear_stress_MPa']:.2f} MPa",
                        f"≤ {res['bear_allow_MPa']:.2f} MPa  (IS 456 §34.4.4)",
                        "OK" if res['bear_ok'] else "WARN"))
            else:  # combined
                rows = [
                    ("Footing Plan",
                     f"{res['L_mm']} × {res['B_mm']} mm (A={res['A_m2']:.2f} m²)",
                     "—", "INFO"),
                    ("Net soil pressure",
                     f"{res['q_net_kPa']:.2f} kN/m²",
                     f"≤ {res['SBC_used_kPa']:.0f} kN/m²",
                     "OK" if res['pressure_ok'] else "FAIL"),
                    ("Resultant position",
                     f"{res['x_resultant_m']*1000:.0f} mm from col 1",
                     "Footing centred on resultant", "INFO"),
                    ("Design moment Mu",
                     f"{res['Mu_design_kNm']:.2f} kN·m",
                     f"Ast_long={res['Ast_long_per_m_mm2']:.0f}mm²/m @ {res['sp_long_mm']}mm",
                     "INFO"),
                    ("Transverse Ast",
                     f"{res['Ast_trans_per_m_mm2']:.0f} mm²/m",
                     f"@ {res['sp_trans_mm']} mm c/c", "INFO"),
                    ("Punching col 1",
                     f"τv={res['tau_v_punch_c1']:.3f} MPa",
                     f"τc={res['tau_c_punch']:.3f} MPa",
                     "OK" if res['punch_col1_ok'] else "FAIL"),
                    ("Punching col 2",
                     f"τv={res['tau_v_punch_c2']:.3f} MPa",
                     f"τc={res['tau_c_punch']:.3f} MPa",
                     "OK" if res['punch_col2_ok'] else "FAIL"),
                    ("Development length",
                     f"Ld={res['Ld_mm']:.0f} mm",
                     f"Available={res['dev_ok'] and 'OK' or 'check'}",
                     "OK" if res['dev_ok'] else "WARN"),
                ]
            self._fill_table(rows)
            self.notes_edit.setPlainText("\n\n".join(res.get("notes", ["—"])))

        except Exception as e:
            self.res_table.setRowCount(1)
            self.res_table.setItem(0, 0, _cell(f"⚠  {e}", fg="#EF9A9A"))
            self.res_table.setSpan(0, 0, 1, 4)

    def _set_defaults(self):
        defaults = {
            "cc_b":"300","cc_D":"400","cc_P":"600","cc_sbc":"150",
            "ec_b":"300","ec_D":"400","ec_P":"800","ec_Mx":"50","ec_My":"35","ec_sbc":"150",
            "cb1_b":"300","cb1_D":"400","cb_P1":"600",
            "cb2_b":"300","cb2_D":"400","cb_P2":"700","cb_sp":"5.0","cb_sbc":"120",
            "cover":"50","bar_dia":"12",
        }
        for k, v in defaults.items():
            if k in self.inputs and hasattr(self.inputs[k], "setText"):
                self.inputs[k].setText(v)
        for key in ("fck", "fy"):
            if key in self.inputs:
                self.inputs[key].setCurrentText("25" if key=="fck" else "415")
        self.calculate()
