"""
ui/tabs/beam_tab.py — IS 456:2000 Beam Design
Fixed: layout overlap (Tu/span at row 7, comp_grp at row 6),
       wu displayed inline, status cell colours correct,
       stirrup spacing user-override with safety check.
"""
from __future__ import annotations
import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QCheckBox, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QSpinBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from constants import BEAM_MOMENT_COEFFICIENTS
from core import design_beam_section
from ui.widgets import UnitLineEdit


def _cell(text, bold=False, bg=None, fg=None):
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    if bold:
        f = QFont(); f.setBold(True); item.setFont(f)
    if bg:  item.setBackground(QColor(bg))
    if fg:  item.setForeground(QColor(fg))
    return item


def _status_cell(status: str) -> QTableWidgetItem:
    COLOURS = {
        "OK":     ("#1B5E20", "#A5D6A7"),
        "REVISE": ("#7F0000", "#EF9A9A"),
        "INFO":   ("#0D47A1", "#90CAF9"),
        "WARN":   ("#6D3500", "#FFCC80"),
        "CHECK":  ("#6D3500", "#FFCC80"),
    }
    fg, bg = COLOURS.get(status, ("#000000", "#F5F5F5"))
    return _cell(status, bold=True, bg=bg, fg=fg)


class BeamTab(QWidget):
    spacing_round_base: int = 25

    def __init__(self, parent=None, seismic_tab_ref=None):
        super().__init__(parent)
        self._seismic_ref = seismic_tab_ref
        self.inputs:       dict = {}
        self.rein_labels:  dict = {}
        self.rein_inputs:  dict = {}
        self.comp_labels:  dict = {}
        self._last_res: dict | None = None
        self._build_ui()
        self._set_defaults()

    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 12, 10, 12)
        root.setSpacing(8)

        top = QWidget()
        tl  = QHBoxLayout(top); tl.setContentsMargins(0,0,0,0); tl.setSpacing(10)
        tl.addWidget(self._build_input_group(),  stretch=3)
        tl.addWidget(self._build_seismic_group(), stretch=2)
        root.addWidget(top)
        root.addWidget(self._build_results_group())
        root.addWidget(self._build_rein_group())
        root.addWidget(self._build_doubly_group())
        root.addWidget(self._build_defl_group())
        root.addWidget(self._build_notes_group(), stretch=1)

    # ── Input group ───────────────────────────────────────────────────────────
    def _build_input_group(self) -> QGroupBox:
        g = QGroupBox("Section & Loading")
        lay = QGridLayout(g)
        lay.setVerticalSpacing(9); lay.setHorizontalSpacing(10)

        def irow(label, key, widget, r, c=0):
            self.inputs[key] = widget
            lay.addWidget(QLabel(label), r, c)
            lay.addWidget(widget, r, c+1)

        irow("Span L [m]:",           "span",  UnitLineEdit("m"),  0)
        irow("Width b [mm]:",         "width", UnitLineEdit("mm"), 1)
        irow("Overall Depth D [mm]:", "depth", UnitLineEdit("mm"), 2)

        ll_w = QLineEdit(); ll_w.setPlaceholderText("kN/m")
        irow("Live Load wL [kN/m]:", "ll", ll_w, 3)

        dl_w = QLineEdit(); dl_w.setPlaceholderText("kN/m")
        auto_chk = QCheckBox("Auto self-wt")
        auto_chk.setToolTip("Self-weight = b × D × 25 kN/m³")
        auto_chk.setChecked(True)
        self.inputs["dl"] = dl_w
        self._auto_dl_chk = auto_chk
        lay.addWidget(QLabel("Dead Load wD [kN/m]:"), 4, 0)
        dl_row = QHBoxLayout(); dl_row.setContentsMargins(0,0,0,0)
        dl_row.addWidget(dl_w); dl_row.addWidget(auto_chk)
        lay.addLayout(dl_row, 4, 1)

        fck_w = QComboBox(); fck_w.addItems(["20","25","30","35","40"])
        fy_w  = QComboBox(); fy_w.addItems(["250","415","500"])
        cov_w = UnitLineEdit("mm")
        dia_w = QComboBox(); dia_w.addItems(["10","12","16","20","25","32"])
        sup_w = QComboBox(); sup_w.addItems(list(BEAM_MOMENT_COEFFICIENTS.keys()))

        for lbl_txt, key, w, r in [
            ("Grade fck [MPa]:",  "fck",   fck_w, 0),
            ("Grade fy [MPa]:",   "fy",    fy_w,  1),
            ("Cover [mm]:",       "cover", cov_w, 2),
            ("Main Bar Ø [mm]:", "dia",   dia_w, 3),
        ]:
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl_txt), r, 2)
            lay.addWidget(w, r, 3)

        lay.addWidget(QLabel("Support Condition:"), 5, 0)
        lay.addWidget(sup_w, 5, 1, 1, 3)
        self.inputs["support"] = sup_w

        # Compression steel sub-group — row 6
        comp_grp = QGroupBox("Compression Steel (Doubly-Reinforced)")
        cgl = QGridLayout(comp_grp); cgl.setVerticalSpacing(8)
        self._allow_doubly_chk = QCheckBox("Auto-design compression steel if Mu > Mu,lim")
        self._allow_doubly_chk.setChecked(True)
        comp_dia_w = QComboBox(); comp_dia_w.addItems(["10","12","16","20","25"])
        comp_dia_w.setCurrentText("16")
        cgl.addWidget(self._allow_doubly_chk, 0, 0, 1, 3)
        cgl.addWidget(QLabel("Comp. bar Ø [mm]:"), 1, 0)
        cgl.addWidget(comp_dia_w, 1, 1)
        self.inputs["comp_dia"] = comp_dia_w
        lay.addWidget(comp_grp, 6, 0, 1, 4)

        # Torsion + deflection span — row 7 (FIXED: was row 6, clashed with comp_grp)
        tu_w   = QLineEdit(); tu_w.setPlaceholderText("0.0  (blank = none)")
        span_w = UnitLineEdit("m")
        tu_w.setToolTip("Factored torsional moment Tu (kN·m). IS 456:2000 §41")
        span_w.setToolTip("Clear span for deflection check. IS 456:2000 §23.2")
        self.inputs["Tu"]        = tu_w
        self.inputs["span_defl"] = span_w
        lay.addWidget(QLabel("Torsion Tu [kN·m]:"),      7, 0); lay.addWidget(tu_w,   7, 1)
        lay.addWidget(QLabel("Span for Deflection [m]:"), 7, 2); lay.addWidget(span_w, 7, 3)

        sug = QPushButton("Suggest Bar Layout")
        sug.clicked.connect(self._suggest_bars)
        lay.addWidget(sug, 8, 0, 1, 4)
        lay.setColumnStretch(1, 1); lay.setColumnStretch(3, 1)

        # Signals
        auto_chk.toggled.connect(self._on_auto_dl)
        self._allow_doubly_chk.toggled.connect(self._on_changed)
        tu_w.textChanged.connect(self._on_changed)
        span_w.textChanged.connect(self._on_changed)
        for key, w in self.inputs.items():
            if isinstance(w, QComboBox):
                w.currentTextChanged.connect(self._on_changed)
            elif isinstance(w, QCheckBox):
                w.toggled.connect(self._on_changed)
            elif key not in ("width", "depth", "dl"):
                # width/depth handled separately below; dl is read-only in auto mode
                w.textChanged.connect(self._on_changed)
        # width and depth must refresh the auto self-weight first
        for dep in ("width", "depth"):
            self.inputs[dep].textChanged.connect(
                lambda _, c=auto_chk: self._on_auto_dl(c.isChecked()))
        return g

    # ── Seismic coupling ──────────────────────────────────────────────────────
    def _build_seismic_group(self) -> QGroupBox:
        g = QGroupBox("NBC 105 Seismic Demands  (optional)")
        lay = QGridLayout(g); lay.setVerticalSpacing(9)
        s_mu = QLineEdit(); s_mu.setPlaceholderText("kN·m — blank = ignore")
        s_vu = QLineEdit(); s_vu.setPlaceholderText("kN  — blank = ignore")
        use_s   = QCheckBox("Include seismic demands in design")
        pop_btn = QPushButton("Pull C(T) from Seismic Tab")
        pop_btn.clicked.connect(self._populate_from_seismic)
        lay.addWidget(QLabel("Seismic Mu [kN·m]:"), 0, 0); lay.addWidget(s_mu, 0, 1)
        lay.addWidget(QLabel("Seismic Vu [kN]:"),   1, 0); lay.addWidget(s_vu, 1, 1)
        lay.addWidget(use_s,    2, 0, 1, 2)
        lay.addWidget(pop_btn,  3, 0, 1, 2)
        self.inputs["seismic_mu"]  = s_mu
        self.inputs["seismic_vu"]  = s_vu
        self.inputs["use_seismic"] = use_s
        s_mu.textChanged.connect(self._on_changed)
        s_vu.textChanged.connect(self._on_changed)
        use_s.toggled.connect(self._on_changed)
        lay.setColumnStretch(1, 1)
        return g

    # ── Results table ─────────────────────────────────────────────────────────
    def _build_results_group(self) -> QGroupBox:
        g = QGroupBox("Loading & Section Checks  (IS 456:2000)")
        lay = QVBoxLayout(g)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(
            ["Parameter", "Value", "Unit", "Formula / Note", "Clause", "Status"])
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setAlternatingRowColors(True)
        hdr = self.results_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lay.addWidget(self.results_table)
        return g

    # ── Reinforcement panel ───────────────────────────────────────────────────
    def _build_rein_group(self) -> QGroupBox:
        g = QGroupBox("Tension Reinforcement  —  User-adjustable")
        outer = QHBoxLayout(g); outer.setSpacing(20)

        left = QGridLayout(); left.setVerticalSpacing(8)
        for i, (key, label, unit) in enumerate([
            ("Ast_req",  "Ast required",  "mm²"),
            ("Ast_min",  "Ast minimum",   "mm²"),
            ("Ast_max",  "Ast maximum",   "mm²"),
            ("Ast_prov", "Ast provided",  "mm²"),
        ]):
            lbl = QLabel("--"); lbl.setStyleSheet("font-weight:bold; font-size:11pt;")
            self.rein_labels[key] = lbl
            left.addWidget(QLabel(f"{label}:"), i, 0)
            left.addWidget(lbl, i, 1)
            left.addWidget(QLabel(unit), i, 2)
        left.setColumnStretch(1, 1)

        div = QFrame(); div.setFrameShape(QFrame.Shape.VLine); div.setFrameShadow(QFrame.Shadow.Sunken)

        right = QGridLayout(); right.setVerticalSpacing(8)

        right.addWidget(QLabel("No. of bars (0=auto):"), 0, 0)
        nb_spin = QSpinBox(); nb_spin.setRange(0, 24); nb_spin.setFixedWidth(70)
        nb_spin.setToolTip("Override bar count (0 = auto-select)")
        nb_spin.valueChanged.connect(self._on_nbars_changed)
        self.rein_inputs["num_bars"] = nb_spin; right.addWidget(nb_spin, 0, 1)

        right.addWidget(QLabel("Bar spacing [mm]:"), 1, 0)
        sp_edit = QLineEdit("--"); sp_edit.setFixedWidth(70)
        sp_edit.setToolTip("Override bar spacing. Press Enter to validate safety.")
        sp_edit.editingFinished.connect(lambda: self._on_spacing_edited(sp_edit))
        self.rein_inputs["spacing"] = sp_edit; right.addWidget(sp_edit, 1, 1)
        right.addWidget(QLabel("mm c/c"), 1, 2)

        right.addWidget(QLabel("Stirrup spacing [mm]:"), 2, 0)
        sv_edit = QLineEdit("--"); sv_edit.setFixedWidth(70)
        sv_edit.setToolTip("Override stirrup spacing. Press Enter to validate.")
        sv_edit.editingFinished.connect(lambda: self._on_stirrup_edited(sv_edit))
        self.rein_inputs["stir_sp"] = sv_edit; right.addWidget(sv_edit, 2, 1)
        right.addWidget(QLabel("mm c/c"), 2, 2)

        right.addWidget(QLabel("Stirrup legs:"), 3, 0)
        leg_cb = QComboBox(); leg_cb.addItems(["2","3","4"])
        leg_cb.setFixedWidth(70)
        leg_cb.currentTextChanged.connect(self._on_changed)
        self.rein_inputs["stir_legs"] = leg_cb; right.addWidget(leg_cb, 3, 1)

        right.addWidget(QLabel("Shear status:"), 4, 0)
        sh_lbl = QLabel("--"); sh_lbl.setStyleSheet("font-weight:bold;")
        self.rein_labels["Shear"] = sh_lbl; right.addWidget(sh_lbl, 4, 1, 1, 2)

        right.setColumnStretch(1, 1)
        outer.addLayout(left, 1); outer.addWidget(div); outer.addLayout(right, 1)
        return g

    # ── Compression steel panel ───────────────────────────────────────────────
    def _build_doubly_group(self) -> QGroupBox:
        self._doubly_group = QGroupBox("Compression Reinforcement  (Doubly-Reinforced  —  IS 456:2000 Annex G)")
        self._doubly_group.setVisible(False)
        lay = QGridLayout(self._doubly_group); lay.setVerticalSpacing(8)
        params = [
            ("Asc_req",   "Asc required",         "mm²"),
            ("Asc_prov",  "Asc provided",          "mm²"),
            ("comp_bars", "Bars provided",         ""),
            ("fsc",       "Bar stress fsc",        "MPa"),
            ("d_prime",   "Cover to comp. bars d'","mm"),
            ("Ast1",      "Ast,1 (balanced)",      "mm²"),
            ("Ast2",      "Ast,2 (extra tens.)",   "mm²"),
        ]
        for i, (key, label, unit) in enumerate(params):
            lbl = QLabel("--"); lbl.setStyleSheet("font-weight:bold;")
            self.comp_labels[key] = lbl
            lay.addWidget(QLabel(f"{label}:"), i, 0)
            lay.addWidget(lbl, i, 1)
            if unit: lay.addWidget(QLabel(unit), i, 2)
        lay.setColumnStretch(1, 1)
        return self._doubly_group

    # ── Deflection panel ──────────────────────────────────────────────────────
    def _build_defl_group(self) -> QGroupBox:
        self._defl_group = QGroupBox("Deflection Check  (IS 456:2000 §23.2)")
        self._defl_group.setVisible(False)
        lay = QGridLayout(self._defl_group); lay.setVerticalSpacing(8)
        self._defl_labels = {}
        params = [
            ("ld_basic",  "Basic L/d ratio",    ""),
            ("fs",        "Service steel stress fs", "MPa"),
            ("kt",        "Modification factor kt",  ""),
            ("kc",        "Compression factor kc",   ""),
            ("ld_allow",  "Allowable L/d",       ""),
            ("ld_prov",   "Provided L/d",        ""),
        ]
        for i, (key, label, unit) in enumerate(params):
            r, c = i // 3, (i % 3) * 3
            lbl = QLabel("--"); lbl.setStyleSheet("font-weight:bold;")
            self._defl_labels[key] = lbl
            lay.addWidget(QLabel(f"{label}:"), r, c)
            lay.addWidget(lbl, r, c+1)
            if unit: lay.addWidget(QLabel(unit), r, c+2)

        self._defl_status_lbl = QLabel("—")
        self._defl_status_lbl.setStyleSheet("font-weight:bold; font-size:11pt;")
        lay.addWidget(QLabel("Result:"), 2, 0)
        lay.addWidget(self._defl_status_lbl, 2, 1, 1, 5)
        return self._defl_group

    # ── Notes ─────────────────────────────────────────────────────────────────
    def _build_notes_group(self) -> QGroupBox:
        g = QGroupBox("Development Length & Design Notes  (IS 456:2000)")
        lay = QVBoxLayout(g)
        self._ld_lbl = QLabel("Development length Ld: —")
        self._ld_lbl.setStyleSheet("font-weight:bold; padding:2px 4px;")
        lay.addWidget(self._ld_lbl)
        self.notes_edit = QTextEdit(readOnly=True)
        self.notes_edit.setMinimumHeight(130)
        lay.addWidget(self.notes_edit)
        return g

    # ══════════════════════════════════════════════════════════════════════════
    # CALCULATIONS
    # ══════════════════════════════════════════════════════════════════════════
    def _get(self, key: str) -> str:
        w = self.inputs[key]
        return w.currentText() if isinstance(w, QComboBox) else w.text().strip()

    def _on_auto_dl(self, checked: bool):
        """Update self-weight field, then recalculate. Does NOT call _on_changed."""
        w = self.inputs["dl"]
        w.setReadOnly(checked)
        if checked:
            try:
                b = float(self._get("width") or "0") / 1000
                D = float(self._get("depth") or "0") / 1000
                w.setText(f"{b * D * 25:.3f}")
            except ValueError:
                pass
        self.calculate()

    def _on_changed(self):
        """Any input changed — just recalculate. Does NOT call _on_auto_dl."""
        self.calculate()

    def _on_nbars_changed(self, val: int):
        self.rein_inputs["spacing"].setReadOnly(val > 0)
        self.calculate()

    def _on_spacing_edited(self, edit: QLineEdit):
        """User typed a custom spacing — re-run & check safety."""
        self.calculate()

    def _on_stirrup_edited(self, edit: QLineEdit):
        """User overrode stirrup spacing — validate and re-display."""
        if not self._last_res:
            return
        try:
            sv_user = float(edit.text().strip())
        except ValueError:
            return
        shear = self._last_res.get("shear", {})
        sv_auto = shear.get("Sv_mm")
        legs    = int(self.rein_inputs["stir_legs"].currentText())
        b_mm    = float(self._get("width") or "0")
        d_mm    = self._last_res.get("d_eff_mm", 1)
        fy      = float(self._get("fy") or "415")
        Vus     = self._last_res.get("Vu_design_kN", 0) * 1e3 - \
                  self._last_res["shear"]["tau_c"] * b_mm * d_mm
        # Capacity with user spacing
        asv = legs * math.pi * 8**2 / 4  # assume 8mm dia stirrups
        Vus_cap = 0.87 * fy * asv * d_mm / sv_user if sv_user > 0 else 0
        ok = Vus_cap >= max(Vus, 0)
        col = "#2E7D32" if ok else "#C62828"
        self.rein_labels["Shear"].setText(
            f"Ø8-{legs}leg @{sv_user:.0f}mm  {'OK ✓' if ok else 'UNSAFE ✗ (auto:{sv_auto}mm)'}")
        self.rein_labels["Shear"].setStyleSheet(f"font-weight:bold; color:{col};")

    def _resize_results(self) -> None:
        t = self.results_table
        h = t.horizontalHeader().height()
        h += sum(t.rowHeight(r) for r in range(t.rowCount())) + 6
        t.setFixedHeight(h)

    def calculate(self):
        try:
            b       = float(self._get("width"))
            D       = float(self._get("depth"))
            cover   = float(self._get("cover"))
            fck     = int(self._get("fck"))
            fy      = int(self._get("fy"))
            dia     = float(self._get("dia"))
            comp_dia= float(self._get("comp_dia"))
            support = self._get("support")
            L       = float(self._get("span"))
            wdl     = float(self._get("dl") or "0")
            wll     = float(self._get("ll") or "0")

            coeff = BEAM_MOMENT_COEFFICIENTS.get(support, {})
            wu    = 1.5 * (wdl + wll)
            Mu_design = coeff.get("max_moment", 0.125) * wu * L**2
            Vu_design = coeff.get("max_shear",  0.5)   * wu * L

            # Seismic coupling
            use_seis = self.inputs["use_seismic"].isChecked()
            try:
                seis_mu = float(self._get("seismic_mu"))
                seis_vu = float(self._get("seismic_vu"))
                if use_seis:
                    Mu_design = max(Mu_design, seis_mu)
                    Vu_design = max(Vu_design, seis_vu)
            except ValueError:
                pass

            Tu_t   = self._get("Tu"); Tu = float(Tu_t) if Tu_t else 0.0
            span_v = float(self._get("span_defl")) if self._get("span_defl") else 0.0
            allow_doubly = self._allow_doubly_chk.isChecked()

            user_sp = None
            try:
                t = self.rein_inputs["spacing"].text().strip()
                if t and t != "--": user_sp = float(t)
            except ValueError: pass
            user_nb = None
            try:
                v = int(self.rein_inputs["num_bars"].value())
                if v > 0: user_nb = v
            except ValueError: pass

            res = design_beam_section(
                b_mm=b, D_mm=D, cover_mm=cover,
                main_bar_dia_mm=dia, fck=float(fck), fy=float(fy),
                Mu_kNm=Mu_design, Vu_kN=Vu_design,
                spacing_round_base=self.spacing_round_base,
                user_spacing_mm=user_sp, user_no_of_bars=user_nb,
                allow_doubly=allow_doubly, comp_bar_dia_mm=comp_dia,
                Tu_kNm=Tu, span_m=span_v, support_type=support,
                wdl_kNm=wdl, wll_kNm=wll,
            )
            self._last_res = res
            Mu_lim = res["Mu_lim_kNm"]
            d_eff  = res["d_eff_mm"]

            # ── Results table — clear, readable rows ──────────────────────────
            ld_limits = {"Simply Supported":20,"Cantilever":7,"Fixed-Fixed":26,"Propped Cantilever":20}
            ld_limit  = ld_limits.get(support, 20)
            ld_ratio  = L * 1000 / d_eff
            ld_ok     = ld_ratio <= ld_limit

            rows = [
                ("Factored wu",       f"{wu:.3f}", "kN/m",   "1.5×(wD+wL)",              "IS 456 §5.3",  "OK"),
                ("Design Mu",         f"{Mu_design:.3f}", "kN·m",
                 f"{coeff.get('max_moment',0.125)}×wu×L²",  "IS 456 §22.2",
                 "OK" if Mu_design<=Mu_lim else ("INFO" if res["is_doubly"] else "REVISE")),
                ("Limiting Mu,lim",   f"{Mu_lim:.3f}", "kN·m",
                 "0.36fck·b·xu,max·(d−0.42xu,max)",         "IS 456 §38.1",  "OK"),
                ("Design Vu",         f"{res['Vu_design_kN']:.3f}", "kN",
                 f"{coeff.get('max_shear',0.5)}×wu×L",      "IS 456 §22.5",  "OK"),
                ("Effective depth d", f"{d_eff:.1f}", "mm",  "D−cover−Ø/2",  "IS 456 §26.3","OK"),
                ("Basic L/d check",   f"{ld_ratio:.1f}", "—",
                 f"≤ {ld_limit} (basic, without mods)",      "IS 456 §23.2",
                 "OK" if ld_ok else "CHECK"),
            ]

            self.results_table.setRowCount(len(rows))
            for r_idx, (param, val, unit, note, ref, status) in enumerate(rows):
                for c_idx, txt in enumerate([param, val, unit, note, ref]):
                    self.results_table.setItem(r_idx, c_idx, _cell(txt, bold=(c_idx==0)))
                self.results_table.setItem(r_idx, 5, _status_cell(status))
            self._resize_results()

            # ── Tension reinforcement ─────────────────────────────────────────
            self.rein_labels["Ast_req"].setText(f"{res['Ast_req_mm2']:.1f}")
            self.rein_labels["Ast_min"].setText(f"{res['Ast_min_mm2']:.1f}")
            self.rein_labels["Ast_max"].setText(f"{res['Ast_max_mm2']:.1f}")
            self.rein_labels["Ast_prov"].setText(f"{res['Ast_prov_mm2']:.1f}")
            ok_s   = "font-weight:bold; font-size:11pt; color:#2E7D32;"
            fail_s = "font-weight:bold; font-size:11pt; color:#C62828;"
            self.rein_labels["Ast_prov"].setStyleSheet(
                ok_s if res["Ast_prov_mm2"] >= res["Ast_req_mm2"] else fail_s)

            nb_val = int(self.rein_inputs["num_bars"].value())
            if nb_val == 0:   # auto
                self.rein_inputs["spacing"].setText(str(int(res["spacing_mm"])))

            shear  = res["shear"]
            sv     = shear.get("Sv_mm")
            # Only update shear display if user hasn't overridden stirrup spacing
            stir_txt = self.rein_inputs["stir_sp"].text().strip()
            if not stir_txt or stir_txt == "--":
                self.rein_inputs["stir_sp"].setText(str(int(sv)) if sv else "--")
            legs_stored = int(self.rein_inputs["stir_legs"].currentText())
            self.rein_labels["Shear"].setText(
                shear["status"] + (f"  —  Ø8×{legs_stored}@{sv}mm" if sv else ""))

            # ── Compression steel ─────────────────────────────────────────────
            dr = res.get("doubly")
            if dr:
                self._doubly_group.setVisible(True)
                self.comp_labels["Asc_req"].setText(f"{dr['Asc_req_mm2']:.1f}")
                self.comp_labels["Asc_prov"].setText(f"{dr['Asc_prov_mm2']:.1f}")
                self.comp_labels["comp_bars"].setText(
                    f"{dr['no_comp_bars']} × Ø{int(dr['comp_bar_dia'])} mm")
                self.comp_labels["fsc"].setText(
                    f"{dr['fsc_MPa']:.0f}  (εsc={dr['eps_sc']:.4f})")
                self.comp_labels["d_prime"].setText(f"{dr['d_prime_mm']:.1f}")
                self.comp_labels["Ast1"].setText(f"{dr['Ast1_mm2']:.1f}")
                self.comp_labels["Ast2"].setText(f"{dr['Ast2_mm2']:.1f}")
            else:
                self._doubly_group.setVisible(False)

            # ── Deflection ────────────────────────────────────────────────────
            dd = res.get("deflection")
            if dd:
                self._defl_group.setVisible(True)
                self._defl_labels["ld_basic"].setText(str(dd["ld_basic"]))
                self._defl_labels["fs"].setText(f"{dd['fs_serv']:.0f}")
                self._defl_labels["kt"].setText(f"{dd['kt']:.3f}")
                self._defl_labels["kc"].setText(f"{dd['kc']:.3f}")
                self._defl_labels["ld_allow"].setText(f"{dd['ld_allow']:.1f}")
                self._defl_labels["ld_prov"].setText(f"{dd['ld_prov']:.1f}")
                col_d = "#2E7D32" if dd["ok"] else "#C62828"
                self._defl_status_lbl.setText("OK ✓" if dd["ok"] else "Increase span/depth ✗")
                self._defl_status_lbl.setStyleSheet(f"font-weight:bold; color:{col_d};")
            else:
                self._defl_group.setVisible(False)

            # ── Development length & notes ────────────────────────────────────
            if "Ld_mm" in res:
                self._ld_lbl.setText(
                    f"Development length Ld = {res['Ld_mm']:.0f} mm  "
                    f"(0.87·fy·Ø / 4·τbd,  IS 456:2000 §26.2.1)")
            self.notes_edit.setPlainText("\n\n".join(res.get("notes", ["—"])))

        except Exception as e:
            self.results_table.setRowCount(1)
            self.results_table.setItem(0, 0, _cell(f"⚠  {e}", fg="#EF9A9A"))
            self.results_table.setSpan(0, 0, 1, 6)
            self._resize_results()

    # ══════════════════════════════════════════════════════════════════════════
    def _suggest_bars(self):
        if not self._last_res: return
        Ast = self._last_res["Ast_req_mm2"]
        b   = float(self._get("width") or "300")
        cov = float(self._get("cover") or "25")
        for dia in [10,12,16,20,25,32]:
            ab = math.pi * dia**2 / 4
            for n in range(2, 12):
                if ab * n >= Ast:
                    sp = (b - 2*cov - dia) / max(1, n-1)
                    if sp >= max(dia, 25):
                        self.rein_inputs["num_bars"].setValue(n)
                        self.inputs["dia"].setCurrentText(str(dia))
                        return

    def _populate_from_seismic(self):
        if not self._seismic_ref: return
        try:
            ct = self._seismic_ref.get_ct_value()
            L  = float(self._get("span") or "0")
            support = self._get("support")
            coeff = BEAM_MOMENT_COEFFICIENTS.get(support, {})
            wdl = float(self._get("dl") or "0")
            wll = float(self._get("ll") or "0")
            wu  = 1.5 * (wdl + wll)
            self.inputs["seismic_mu"].setText(
                f"{coeff.get('max_moment',0.125)*wu*L**2*ct:.3f}")
            self.inputs["seismic_vu"].setText(
                f"{coeff.get('max_shear',0.5)*wu*L*ct:.3f}")
        except Exception:
            pass

    def _set_defaults(self):
        for key, val in [("span","6.0"),("width","300"),("depth","500"),
                         ("ll","20"),("cover","25"),("span_defl","6.0")]:
            self.inputs[key].setText(val)
        self.inputs["fck"].setCurrentText("25")
        self.inputs["fy"].setCurrentText("415")
        self.inputs["dia"].setCurrentText("16")
        self.inputs["comp_dia"].setCurrentText("16")
        self.inputs["support"].setCurrentText("Simply Supported")
        self._auto_dl_chk.setChecked(True)
        self._on_auto_dl(True)
