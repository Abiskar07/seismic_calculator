"""
ui/tabs/beam_tab.py — IS 456:2000 beam design (singly + doubly reinforced).

Fixes in this version:
  • All hardcoded dark colors removed — labels inherit from application palette
  • Doubly-reinforced section: Asc, comp bar layout, fsc shown in UI
  • L/d check: correct limit L*1000/d ≤ basic_ratio
  • UnitLineEdit removed from kN/m force fields
  • Status colors work in both dark and light themes
"""
from __future__ import annotations
import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QCheckBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox,
    QTextEdit, QMessageBox, QFrame,
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
    if bg:
        item.setBackground(QColor(bg))
    if fg:
        item.setForeground(QColor(fg))
    return item


# Colors that work on both themes (dark bg / light bg):
#   OK    → dark green bg + light green text
#   REVISE→ dark red   bg + light red text
#   CHECK → dark amber bg + light amber text
STATUS_PAIRS = {
    "OK":     ("#1B5E20", "#A5D6A7"),
    "REVISE": ("#7F0000", "#EF9A9A"),
    "CHECK":  ("#6D3500", "#FFCC80"),
    "INFO":   ("#0D47A1", "#90CAF9"),
}


def _status_cell(status: str) -> QTableWidgetItem:
    bg, fg = STATUS_PAIRS.get(status, (None, None))
    return _cell(status, bold=True, bg=bg, fg=fg)


class BeamTab(QWidget):
    def __init__(self, seismic_tab_ref=None, parent=None):
        super().__init__(parent)
        self._seismic_tab = seismic_tab_ref
        self.inputs:       dict = {}
        self.rein_labels:  dict = {}
        self.rein_inputs:  dict = {}
        self.comp_labels:  dict = {}   # compression steel results
        self.spacing_round_base: int = 5
        self._last_res: dict | None = None
        self._build_ui()
        self._set_defaults()

    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 12, 10, 12)
        root.setSpacing(10)

        top = QWidget()
        tl  = QHBoxLayout(top); tl.setContentsMargins(0,0,0,0); tl.setSpacing(10)
        tl.addWidget(self._build_input_group(), stretch=3)
        tl.addWidget(self._build_seismic_group(), stretch=2)
        root.addWidget(top)
        root.addWidget(self._build_results_group())
        root.addWidget(self._build_rein_group())
        root.addWidget(self._build_doubly_group())
        root.addWidget(self._build_notes_group())
        root.addWidget(self._build_defl_group())
        root.addWidget(self._build_devlen_group())
        root.addStretch()

    # ── Input group ────────────────────────────────────────────────────────────
    def _build_input_group(self) -> QGroupBox:
        g = QGroupBox("Section & Loading")
        lay = QGridLayout(g)
        lay.setVerticalSpacing(9); lay.setHorizontalSpacing(10)

        def irow(label, key, widget, r):
            self.inputs[key] = widget
            lay.addWidget(QLabel(label), r, 0)
            lay.addWidget(widget, r, 1)

        irow("Span L [m]:",           "span",  UnitLineEdit("m"),   0)
        irow("Width b [mm]:",         "width", UnitLineEdit("mm"),  1)
        irow("Overall Depth D [mm]:", "depth", UnitLineEdit("mm"),  2)

        ll_w = QLineEdit(); ll_w.setPlaceholderText("kN/m")
        irow("Live Load wL [kN/m]:",  "ll",    ll_w,  3)

        dl_w = QLineEdit(); dl_w.setPlaceholderText("kN/m")
        auto_chk = QCheckBox("Auto self-wt")
        auto_chk.setToolTip("Self-weight = b × D × 25 kN/m³ (concrete unit weight)")
        auto_chk.setChecked(True)
        self.inputs["dl"]  = dl_w
        self._auto_dl_chk  = auto_chk
        lay.addWidget(QLabel("Dead Load wD [kN/m]:"), 4, 0)
        dl_row = QHBoxLayout(); dl_row.setContentsMargins(0,0,0,0)
        dl_row.addWidget(dl_w); dl_row.addWidget(auto_chk)
        lay.addLayout(dl_row, 4, 1)

        fck_w = QComboBox(); fck_w.addItems(["20","25","30","35","40"])
        fy_w  = QComboBox(); fy_w.addItems(["250","415","500"])
        cov_w = UnitLineEdit("mm")
        dia_w = QComboBox(); dia_w.addItems(["10","12","16","20","25"])
        sup_w = QComboBox(); sup_w.addItems(list(BEAM_MOMENT_COEFFICIENTS.keys()))

        for lbl_txt, key, w, r in [
            ("Grade fck [MPa]:", "fck",   fck_w, 0),
            ("Grade fy [MPa]:",  "fy",    fy_w,  1),
            ("Cover [mm]:",      "cover", cov_w, 2),
            ("Main Bar Ø [mm]:","dia",   dia_w, 3),
        ]:
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl_txt), r, 2)
            lay.addWidget(w, r, 3)

        lay.addWidget(QLabel("Support Condition:"), 5, 0)
        lay.addWidget(sup_w, 5, 1, 1, 3)
        self.inputs["support"] = sup_w

        # Compression steel options
        comp_grp = QGroupBox("Compression Steel (Doubly-Reinforced)")
        cgl = QGridLayout(comp_grp); cgl.setVerticalSpacing(8)
        self._allow_doubly_chk = QCheckBox("Auto-design compression steel if Mu > Mu,lim")
        self._allow_doubly_chk.setChecked(True)
        self._allow_doubly_chk.setToolTip(
            "When Mu exceeds the limiting moment, compression bars are designed "
            "per IS 456:2000 Annex G instead of just flagging an error.")
        comp_dia_w = QComboBox(); comp_dia_w.addItems(["10","12","16","20","25"])
        comp_dia_w.setCurrentText("16")
        comp_dia_w.setToolTip("Diameter of compression bar")
        cgl.addWidget(self._allow_doubly_chk, 0, 0, 1, 3)
        cgl.addWidget(QLabel("Comp. bar Ø [mm]:"), 1, 0)
        cgl.addWidget(comp_dia_w, 1, 1)
        self.inputs["comp_dia"] = comp_dia_w
        lay.addWidget(comp_grp, 6, 0, 1, 4)

        # Extra fields for deflection check and torsion
        tu_w = QLineEdit(); tu_w.setPlaceholderText("0.0  (blank = none)")
        tu_w.setToolTip("Factored torsional moment Tu (kN·m). Activates IS 456 Cl. 41 torsion design.")
        span_w = UnitLineEdit("m"); span_w.setToolTip("Clear span (m). Used for deflection check IS 456 §23.2.")
        self.inputs["Tu"]   = tu_w
        self.inputs["span_defl"] = span_w
        lay.addWidget(QLabel("Torsion Tu [kN·m] (opt):"), 6, 0); lay.addWidget(tu_w, 6, 1)
        lay.addWidget(QLabel("Span for Deflection [m]:"), 6, 2); lay.addWidget(span_w, 6, 3)
        tu_w.textChanged.connect(self._on_changed)
        span_w.textChanged.connect(self._on_changed)

        sug = QPushButton("💡 Suggest Bar Layout")
        sug.clicked.connect(self._suggest_bars)
        lay.addWidget(sug, 7, 0, 1, 4)
        lay.setColumnStretch(1, 1); lay.setColumnStretch(3, 1)

        # Signals
        auto_chk.toggled.connect(self._on_auto_dl)
        self._allow_doubly_chk.toggled.connect(self._on_changed)
        for key, w in self.inputs.items():
            if isinstance(w, QComboBox):
                w.currentTextChanged.connect(self._on_changed)
            elif isinstance(w, QCheckBox):
                w.toggled.connect(self._on_changed)
            else:
                w.textChanged.connect(self._on_changed)
        for dep in ("width", "depth"):
            self.inputs[dep].textChanged.connect(
                lambda _, c=auto_chk: self._on_auto_dl(c.isChecked()))
        return g

    # ── Seismic coupling ───────────────────────────────────────────────────────
    def _build_seismic_group(self) -> QGroupBox:
        g = QGroupBox("NBC 105 Seismic Demands  (optional)")
        lay = QGridLayout(g); lay.setVerticalSpacing(9)
        s_mu = QLineEdit(); s_mu.setPlaceholderText("kN·m — blank = ignore")
        s_vu = QLineEdit(); s_vu.setPlaceholderText("kN  — blank = ignore")
        use_s = QCheckBox("Include seismic demands in design")
        pop_btn = QPushButton("↙ Pull C(T) from Seismic Tab")
        pop_btn.setToolTip("Scale static beam demands by elastic site spectra C(T)")
        pop_btn.clicked.connect(self._populate_from_seismic)
        lay.addWidget(QLabel("Seismic Mu [kN·m]:"), 0, 0); lay.addWidget(s_mu, 0, 1)
        lay.addWidget(QLabel("Seismic Vu [kN]:"),   1, 0); lay.addWidget(s_vu, 1, 1)
        lay.addWidget(use_s,    2, 0, 1, 2)
        lay.addWidget(pop_btn,  3, 0, 1, 2)
        self.inputs["seismic_mu"]  = s_mu
        self.inputs["seismic_vu"]  = s_vu
        self.inputs["use_seismic"] = use_s
        use_s.toggled.connect(self._on_changed)
        s_mu.textChanged.connect(self._on_changed)
        s_vu.textChanged.connect(self._on_changed)
        lay.setColumnStretch(1, 1)
        return g

    # ── Results table ──────────────────────────────────────────────────────────
    def _build_results_group(self) -> QGroupBox:
        g = QGroupBox("Design Results Summary")
        lay = QVBoxLayout(g)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(
            ["Parameter","Value","Units","Formula / Note","Ref.","Status"])
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lay.addWidget(self.results_table)
        return g

    # ── Reinforcement panel ────────────────────────────────────────────────────
    def _build_rein_group(self) -> QGroupBox:
        g = QGroupBox("Tension Reinforcement")
        outer = QHBoxLayout(g); outer.setSpacing(20)

        left = QGridLayout(); left.setVerticalSpacing(8)
        for i, (key, label, unit) in enumerate([
            ("Ast_req",  "Ast required",  "mm²"),
            ("Ast_min",  "Ast minimum",   "mm²"),
            ("Ast_max",  "Ast maximum",   "mm²"),
            ("Ast_prov", "Ast provided",  "mm²"),
        ]):
            lbl = QLabel("--")
            lbl.setStyleSheet("font-weight: bold; font-size: 11pt;")
            self.rein_labels[key] = lbl
            left.addWidget(QLabel(f"{label}:"), i, 0)
            left.addWidget(lbl, i, 1)
            left.addWidget(QLabel(unit), i, 2)
        left.setColumnStretch(1, 1)

        div = QFrame(); div.setFrameShape(QFrame.Shape.VLine)
        div.setFrameShadow(QFrame.Shadow.Sunken)

        right = QGridLayout(); right.setVerticalSpacing(8)
        right.addWidget(QLabel("No. of bars:"),      0, 0)
        nb_lbl = QLabel("--"); nb_lbl.setStyleSheet("font-weight:bold;")
        self.rein_labels["No_bars"] = nb_lbl; right.addWidget(nb_lbl, 0, 1)

        right.addWidget(QLabel("Spacing c/c:"),  1, 0)
        sp_edit = QLineEdit("--"); sp_edit.setFixedWidth(80)
        sp_edit.editingFinished.connect(lambda: self._on_spacing_edited(sp_edit))
        self.rein_inputs["spacing"] = sp_edit
        right.addWidget(sp_edit, 1, 1)
        right.addWidget(QLabel("mm"), 1, 2)

        right.addWidget(QLabel("Shear links:"),  2, 0)
        sh_lbl = QLabel("--"); sh_lbl.setStyleSheet("font-weight:bold;")
        self.rein_labels["Shear"] = sh_lbl; right.addWidget(sh_lbl, 2, 1, 1, 2)

        right.addWidget(QLabel("Override bar count (0=auto):"), 3, 0)
        nb_spin = QSpinBox(); nb_spin.setRange(0, 24); nb_spin.setFixedWidth(80)
        nb_spin.valueChanged.connect(self._on_nbars_changed)
        self.rein_inputs["num_bars"] = nb_spin; right.addWidget(nb_spin, 3, 1)
        right.setColumnStretch(1, 1)

        outer.addLayout(left, 1); outer.addWidget(div); outer.addLayout(right, 1)
        return g

    # ── Compression steel panel ────────────────────────────────────────────────
    def _build_doubly_group(self) -> QGroupBox:
        self._doubly_group = QGroupBox("Compression Reinforcement  (Doubly-Reinforced)")
        self._doubly_group.setVisible(False)   # hidden when singly is sufficient
        lay = QGridLayout(self._doubly_group); lay.setVerticalSpacing(8)

        params = [
            ("Asc_req",      "Asc required",       "mm²"),
            ("Asc_prov",     "Asc provided",        "mm²"),
            ("comp_bars",    "Compression bars",    ""),
            ("fsc",          "Bar stress fsc",      "MPa"),
            ("d_prime",      "Cover to comp. bars d'","mm"),
            ("Ast1",         "Ast,1 (balanced)",    "mm²"),
            ("Ast2",         "Ast,2 (extra tens.)",  "mm²"),
        ]
        for i, (key, label, unit) in enumerate(params):
            lbl = QLabel("--"); lbl.setStyleSheet("font-weight:bold;")
            self.comp_labels[key] = lbl
            lay.addWidget(QLabel(f"{label}:"), i//2*1 if False else i, 0)
            lay.addWidget(lbl, i, 1)
            if unit: lay.addWidget(QLabel(unit), i, 2)
        lay.setColumnStretch(1, 1)
        return self._doubly_group

    # ── Notes ──────────────────────────────────────────────────────────────────
    def _build_notes_group(self) -> QGroupBox:
        g = QGroupBox("Design Notes  (IS 456:2000)")
        lay = QVBoxLayout(g)
        self.notes_edit = QTextEdit(readOnly=True)
        self.notes_edit.setMaximumHeight(130)
        self.notes_edit.setPlainText("—")
        lay.addWidget(self.notes_edit)
        return g

    # ══════════════════════════════════════════════════════════════════════════
    def _get(self, key: str) -> str:
        w = self.inputs[key]
        return w.currentText() if isinstance(w, QComboBox) else w.text().strip()

    def _resize_results(self) -> None:
        t = self.results_table
        h = t.horizontalHeader().height()
        h += sum(t.rowHeight(r) for r in range(t.rowCount())) + 6
        t.setFixedHeight(h)

    # ══════════════════════════════════════════════════════════════════════════
    def _on_changed(self) -> None:
        self.calculate()

    def _on_auto_dl(self, checked: bool) -> None:
        try:
            if checked:
                b = float(self._get("width")); D = float(self._get("depth"))
                self.inputs["dl"].setText(f"{b/1000*D/1000*25.0:.2f}")
                self.inputs["dl"].setEnabled(False)
            else:
                self.inputs["dl"].setEnabled(True)
        except (ValueError, TypeError):
            self.inputs["dl"].setEnabled(True)

    def calculate(self) -> None:
        try:
            L       = float(self._get("span"))
            b       = float(self._get("width"))
            D       = float(self._get("depth"))
            fck     = int(self._get("fck"))
            fy      = int(self._get("fy"))
            wll_t   = self._get("ll");  wll = float(wll_t) if wll_t else 0.0
            wdl_t   = self._get("dl");  wdl = float(wdl_t) if wdl_t else b/1000*D/1000*25.0
            cover   = float(self._get("cover"))
            dia     = int(self._get("dia"))
            comp_dia = int(self._get("comp_dia"))
            support = self._get("support")
            allow_doubly = self._allow_doubly_chk.isChecked()

            wu    = 1.5 * (wdl + wll)
            coeff = BEAM_MOMENT_COEFFICIENTS[support]
            Mu_st = coeff["max_moment"] * wu * L**2
            Vu_st = coeff["max_shear"]  * wu * L

            Mu_design, Vu_design = Mu_st, Vu_st
            if self.inputs["use_seismic"].isChecked():
                for field, is_mu in (("seismic_mu", True), ("seismic_vu", False)):
                    try:
                        v = float(self._get(field))
                        if is_mu and v > Mu_design: Mu_design = v
                        elif not is_mu and v > Vu_design: Vu_design = v
                    except (ValueError, TypeError): pass

            user_sp = None
            try:
                t = self.rein_inputs["spacing"].text().strip()
                if t and t != "--": user_sp = float(t)
            except (ValueError, TypeError): pass
            user_nb = None
            try:
                v = int(self.rein_inputs["num_bars"].value())
                if v > 0: user_nb = v
            except (ValueError, TypeError): pass

            Tu_t    = self._get("Tu");   Tu   = float(Tu_t)   if Tu_t   else 0.0
            sp_t    = self._get("span_defl"); span_v = float(sp_t) if sp_t else 0.0
            res = design_beam_section(
                b_mm=b, D_mm=D, cover_mm=cover,
                main_bar_dia_mm=float(dia), fck=float(fck), fy=float(fy),
                Mu_kNm=Mu_design, Vu_kN=Vu_design,
                spacing_round_base=self.spacing_round_base,
                user_spacing_mm=user_sp, user_no_of_bars=user_nb,
                allow_doubly=allow_doubly, comp_bar_dia_mm=float(comp_dia),
                Tu_kNm=Tu, span_m=span_v, support_type=support,
                wdl_kNm=wdl, wll_kNm=wll,
            )
            self._last_res = res
            Mu_lim = res["Mu_lim_kNm"]
            d_eff  = res["d_eff_mm"]

            # L/d check per IS 456 §23.2
            ld_limits = {"Simply Supported":20,"Cantilever":7,
                         "Fixed-Fixed":26,"Propped Cantilever":20}
            ld_limit = ld_limits.get(support, 20)
            ld_ratio = L * 1000 / d_eff
            ld_ok    = ld_ratio <= ld_limit

            rows = [
                ("Factored Load wu",      f"{wu:.3f}",        "kN/m",
                 "1.5×(wD+wL)",              "IS 456 §5.3",  "OK"),
                ("Design Moment Mu",      f"{Mu_design:.3f}", "kN·m",
                 f"{coeff['max_moment']}×wu×L²", "IS 456 §22.2",
                 "OK" if Mu_design<=Mu_lim else ("INFO" if res["is_doubly"] else "REVISE")),
                ("Limiting Moment Mu,lim",f"{Mu_lim:.3f}",    "kN·m",
                 "0.36fck·b·xu,max·(d−0.42xu,max)","IS 456 §38.1","OK"),
                ("Design Shear Vu",       f"{Vu_design:.3f}", "kN",
                 f"{coeff['max_shear']}×wu×L",  "IS 456 §22.5","OK"),
                ("Effective Depth d",     f"{d_eff:.1f}",     "mm",
                 "D−cover−Ø/2",             "IS 456 §26.3", "OK"),
                ("L/d Ratio",             f"{ld_ratio:.1f}",  "—",
                 f"≤ {ld_limit} (basic)",   "IS 456 §23.2", "OK" if ld_ok else "CHECK"),
            ]

            self.results_table.setRowCount(len(rows))
            for r, (param, val, unit, note, ref, status) in enumerate(rows):
                for c, txt in enumerate([param, val, unit, note, ref]):
                    self.results_table.setItem(r, c, _cell(txt, bold=(c==0)))
                self.results_table.setItem(r, 5, _status_cell(status))
            self._resize_results()

            # Tension reinforcement
            self.rein_labels["Ast_req"].setText(f"{res['Ast_req_mm2']:.1f}")
            self.rein_labels["Ast_min"].setText(f"{res['Ast_min_mm2']:.1f}")
            self.rein_labels["Ast_max"].setText(f"{res['Ast_max_mm2']:.1f}")
            self.rein_labels["Ast_prov"].setText(f"{res['Ast_prov_mm2']:.1f}")
            self.rein_labels["No_bars"].setText(str(int(res["no_of_bars"])))
            self.rein_inputs["spacing"].setText(str(int(res["spacing_mm"])))
            shear = res["shear"]; sv = shear.get("Sv_mm")
            self.rein_labels["Shear"].setText(
                shear["status"] + (f" — Ø8@{sv}mm" if sv else ""))

            # Color Ast_prov
            prov = res["Ast_prov_mm2"]; req = res["Ast_req_mm2"]
            # Use named colors that work on both themes
            ok_style   = "font-weight:bold; font-size:11pt; color:#2E7D32;"
            fail_style = "font-weight:bold; font-size:11pt; color:#C62828;"
            self.rein_labels["Ast_prov"].setStyleSheet(
                ok_style if prov >= req else fail_style)

            # Compression steel panel
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

            self.notes_edit.setPlainText("\n\n".join(res.get("notes", ["—"])))
            # Deflection check panel
            dr = res.get("deflection")
            if dr:
                self._defl_group.setVisible(True)
                self._defl_labels["ld_basic"].setText(str(dr["ld_basic"]))
                self._defl_labels["fs"].setText(f"{dr['fs_serv']:.0f}")
                self._defl_labels["kt"].setText(f"{dr['kt']:.3f}")
                self._defl_labels["kc"].setText(f"{dr['kc']:.3f}")
                self._defl_labels["ld_allow"].setText(f"{dr['ld_allow']:.1f}")
                self._defl_labels["ld_prov"].setText(f"{dr['ld_prov']:.1f}")
                ok_defl = dr["ok"]
                col_d = "#2E7D32" if ok_defl else "#C62828"
                self._defl_status_lbl.setText("✓ OK" if ok_defl else "✗ Increase depth")
                self._defl_status_lbl.setStyleSheet(f"font-weight:bold; color:{col_d};")
            else:
                self._defl_group.setVisible(False)
            # Development length
            if "Ld_mm" in res:
                self._ld_lbl.setText(f"{int(res['Ld_mm'])}")

        except Exception as e:
            self.results_table.setRowCount(1)
            err = _cell(f"⚠  {e}", fg="#EF9A9A")
            self.results_table.setItem(0, 0, err)
            self.results_table.setSpan(0, 0, 1, 6)
            self._doubly_group.setVisible(False)

    # ── Seismic coupling ──────────────────────────────────────────────────────
    def _populate_from_seismic(self) -> None:
        if self._seismic_tab is None:
            QMessageBox.information(self,"Not Connected","Seismic tab ref not available."); return
        ct = self._seismic_tab.get_ct_value()
        if ct is None:
            QMessageBox.information(self,"No Data","Run the seismic calculation first."); return
        try:
            L = float(self._get("span"))
            wll = float(self._get("ll")) if self._get("ll") else 0.0
            wdl = float(self._get("dl")) if self._get("dl") else 0.0
            c = BEAM_MOMENT_COEFFICIENTS[self._get("support")]
            wu = 1.5*(wdl+wll)
            self.inputs["seismic_mu"].setText(f"{c['max_moment']*wu*L**2*ct:.3f}")
            self.inputs["seismic_vu"].setText(f"{c['max_shear'] *wu*L   *ct:.3f}")
            self.inputs["use_seismic"].setChecked(True)
        except Exception as e:
            QMessageBox.warning(self,"Error",f"Failed: {e}")

    def _on_spacing_edited(self, edit: QLineEdit) -> None:
        try: float(edit.text()); self.calculate()
        except ValueError: pass

    def _on_nbars_changed(self, value: int) -> None:
        try:
            if value > 0:
                b = float(self._get("width")); c = float(self._get("cover"))
                d = int(self._get("dia"))
                sp = (b-2*c-d)/(value-1) if value>1 else b-2*c-d
                self.rein_inputs["spacing"].setText(
                    str(max(50,int(round(sp/self.spacing_round_base)*self.spacing_round_base))))
            self.calculate()
        except (ValueError, ZeroDivisionError): pass

    def _suggest_bars(self) -> None:
        try:
            self.calculate()
            if not self._last_res: return
            res     = self._last_res
            ast_req = max(res["Ast_req_mm2"], res["Ast_min_mm2"])
            b, cover, dia = (float(self._get("width")),
                              float(self._get("cover")), int(self._get("dia")))
            support  = self._get("support")
            area_bar = math.pi*dia**2/4.0
            n        = max(2, math.ceil(ast_req/area_bar))
            sp       = (b-2*cover)/n
            sp_r     = max(50, int(round(sp/self.spacing_round_base)*self.spacing_round_base))
            top_note = ""
            if "Fixed" in support:
                top_note = f"\n\nProvide {max(1,math.ceil(0.3*n))} top bar(s) for hogging."
            doubly_note = ""
            if res.get("is_doubly") and res.get("doubly"):
                dr = res["doubly"]
                doubly_note = (
                    f"\n\nCompression steel: {dr['no_comp_bars']} × Ø{int(dr['comp_bar_dia'])} mm\n"
                    f"Asc,prov = {dr['Asc_prov_mm2']:.0f} mm²  (fsc={dr['fsc_MPa']:.0f} MPa)"
                )
            QMessageBox.information(
                self, "Suggested Bar Layout",
                f"Required Ast  = {ast_req:.0f} mm²\n"
                f"─────────────────────────────\n"
                f"Provide : {n} × Ø{dia} mm\n"
                f"Spacing ≈ {sp_r} mm c/c\n"
                f"Ast,prov = {area_bar*n:.0f} mm²"
                f"{doubly_note}{top_note}")
        except Exception as e:
            QMessageBox.warning(self,"Error",str(e))

    def _build_defl_group(self) -> QGroupBox:
        g = QGroupBox("Deflection Check  (IS 456 §23.2 with modification factors)")
        g.setVisible(False)
        self._defl_group = g
        lay = QGridLayout(g); lay.setVerticalSpacing(6); lay.setHorizontalSpacing(10)
        self._defl_labels = {}
        items = [
            ("ld_basic","Basic L/d limit"), ("fs","Service steel stress fs","MPa"),
            ("kt","Mod. factor kt",""),     ("kc","Comp. mod. factor kc",""),
            ("ld_allow","Allowed L/d",""),  ("ld_prov","Provided L/d",""),
        ]
        for i,(key,lbl,*unit) in enumerate(items):
            r,c = divmod(i,2)
            lay.addWidget(QLabel(f"{lbl}:"), r, c*3)
            lb = QLabel("--"); lb.setStyleSheet("font-weight:bold;")
            self._defl_labels[key] = lb
            lay.addWidget(lb, r, c*3+1)
            if unit: lay.addWidget(QLabel(unit[0]), r, c*3+2)
        lay.addWidget(QLabel("Status:"), 3, 0)
        self._defl_status_lbl = QLabel("--"); self._defl_status_lbl.setStyleSheet("font-weight:bold;")
        lay.addWidget(self._defl_status_lbl, 3, 1, 1, 3)
        return g

    def _build_devlen_group(self) -> QGroupBox:
        g = QGroupBox("Development Length  (IS 456 Cl. 26.2.1)")
        lay = QGridLayout(g); lay.setVerticalSpacing(6); lay.setHorizontalSpacing(10)
        lay.addWidget(QLabel("Ld (tension, straight bar):"), 0, 0)
        self._ld_lbl = QLabel("--"); self._ld_lbl.setStyleSheet("font-weight:bold;")
        lay.addWidget(self._ld_lbl, 0, 1); lay.addWidget(QLabel("mm"), 0, 2)
        lay.setColumnStretch(3, 1)
        return g

    def _set_defaults(self) -> None:
        self.inputs["span"].setText("5.0")
        self.inputs["width"].setText("230")
        self.inputs["depth"].setText("450")
        self.inputs["ll"].setText("15.0")
        self.inputs["fck"].setCurrentText("25")
        self.inputs["fy"].setCurrentText("415")
        self.inputs["cover"].setText("25")
        self.inputs["dia"].setCurrentText("16")
        self.inputs["comp_dia"].setCurrentText("16")
        self.inputs["support"].setCurrentText("Simply Supported")
        self.inputs["span_defl"].setText("5.0")
        self._on_auto_dl(True)
        self.calculate()

