"""ui/tabs/staircase_tab.py — Staircase Design (IS 456:2000 §33)"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from core import design_staircase
from ui.widgets import UnitLineEdit

STATUS = {"OK":("#1B5E20","#A5D6A7"),"FAIL":("#7F0000","#EF9A9A"),
          "WARN":("#6D3500","#FFCC80"),"INFO":("#0D47A1","#90CAF9")}

def _cell(text, bold=False, bg=None, fg=None):
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    if bold: f=QFont(); f.setBold(True); item.setFont(f)
    if bg: item.setBackground(QColor(bg))
    if fg: item.setForeground(QColor(fg))
    return item


class StaircaseTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs: dict = {}
        self._last_result: dict = {}
        self._build_ui()
        self._set_defaults()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10,12,10,12); root.setSpacing(10)

        top = QWidget(); tl = QHBoxLayout(top)
        tl.setContentsMargins(0,0,0,0); tl.setSpacing(10)
        tl.addWidget(self._build_geom_group(), stretch=2)
        tl.addWidget(self._build_mat_group(),  stretch=1)
        root.addWidget(top)
        root.addWidget(self._build_results_group())
        root.addWidget(self._build_notes_group())
        root.addStretch()

    def _build_geom_group(self):
        g = QGroupBox("Staircase Geometry & Loading  (Dog-legged, IS 456:2000 §33)")
        lay = QGridLayout(g); lay.setVerticalSpacing(9); lay.setHorizontalSpacing(10)
        def ir(lbl, key, w, r, c=0):
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl), r, c); lay.addWidget(w, r, c+1)
        ir("Floor-to-floor height H [m]:", "H",     UnitLineEdit("m"),  0)
        ir("Stair width [m]:",              "width", UnitLineEdit("m"),  1)
        ir("Tread (going) T [mm]:",         "tread", UnitLineEdit("mm"), 2)
        ir("Riser R [mm]:",                 "riser", UnitLineEdit("mm"), 3)
        ir("Live load LL [kN/m²]:",         "LL",    QLineEdit(),        4)
        sup_w = QComboBox()
        sup_w.addItems(["SS","One end fixed"])
        self.inputs["support"] = sup_w
        lay.addWidget(QLabel("Support condition:"), 5, 0)
        lay.addWidget(sup_w, 5, 1)
        for w in self.inputs.values():
            sig = w.currentTextChanged if isinstance(w,QComboBox) else w.textChanged
            sig.connect(self.calculate)
        lay.setColumnStretch(1,1)
        return g

    def _build_mat_group(self):
        g = QGroupBox("Material & Reinforcement")
        lay = QGridLayout(g); lay.setVerticalSpacing(9)
        def ir(lbl, key, items, r):
            w = QComboBox(); w.addItems(items)
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl), r, 0); lay.addWidget(w, r, 1)
            w.currentTextChanged.connect(self.calculate)
        ir("fck [MPa]:", "fck", ["20","25","30"], 0)
        ir("fy [MPa]:",  "fy",  ["250","415","500"], 1)
        ir("Main bar Ø [mm]:", "main_dia", ["8","10","12","16"], 2)
        ir("Dist. bar Ø [mm]:","dist_dia", ["6","8","10"],  3)
        for lbl,key,r in [("Cover [mm]:","cover",4)]:
            w = QLineEdit(); self.inputs[key]=w
            lay.addWidget(QLabel(lbl),r,0); lay.addWidget(w,r,1)
            w.editingFinished.connect(self.calculate)
        lay.setColumnStretch(1,1)
        return g

    def _build_results_group(self):
        g = QGroupBox("Design Results  —  IS 456:2000 §33 (Waist-Slab Method)")
        lay = QVBoxLayout(g)
        self.res_table = QTableWidget()
        self.res_table.setColumnCount(4)
        self.res_table.setHorizontalHeaderLabels(["Parameter","Value","Formula / Clause","Status"])
        self.res_table.verticalHeader().setVisible(False)
        self.res_table.setAlternatingRowColors(True)
        self.res_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.res_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lay.addWidget(self.res_table)
        return g

    def _build_notes_group(self):
        g = QGroupBox("Design Notes")
        lay = QVBoxLayout(g)
        self.notes_edit = QTextEdit(readOnly=True)
        self.notes_edit.setMinimumHeight(120)
        lay.addWidget(self.notes_edit)
        return g

    def _resize(self):
        t = self.res_table
        h = t.horizontalHeader().height()
        h += sum(t.rowHeight(r) for r in range(t.rowCount())) + 4
        t.setFixedHeight(h)

    def _g(self, key, default=""):
        w = self.inputs.get(key)
        if w is None: return default
        return w.currentText() if isinstance(w,QComboBox) else w.text().strip()

    def calculate(self):
        try:
            H    = float(self._g("H","3.0") or "3.0")
            wid  = float(self._g("width","1.2") or "1.2")
            T    = float(self._g("tread","250") or "250")
            R    = float(self._g("riser","150") or "150")
            LL   = float(self._g("LL","3.0") or "3.0")
            fck  = int(self._g("fck","20"))
            fy   = int(self._g("fy","415"))
            cov  = float(self._g("cover","15") or "15")
            mdia = float(self._g("main_dia","10"))
            ddia = float(self._g("dist_dia","8"))
            sup  = self._g("support","SS")

            res = design_staircase(H, wid, T, R, fck, fy, LL, cov, mdia, ddia, support_type=sup)
            self._last_result = res

            rows = [
                ("Riser (actual)", f"{res['riser_actual_mm']:.0f} mm",
                 f"H×1000/{res['n_risers']} risers", "OK"),
                ("2R + T comfort check", f"{res['comfort_check']:.0f} mm",
                 "600–650 mm (IS 456 §33)", "OK" if res['comfort_ok'] else "WARN"),
                ("Slope α", f"{res['alpha_deg']:.1f}°",
                 "tan⁻¹(R/T)", "INFO"),
                ("Effective span", f"{res['L_eff_m']:.3f} m",
                 "(n−1)×T + landing  (IS 456 §33.1)", "INFO"),
                ("Waist slab D", f"{res['D_waist_mm']:.0f} mm",
                 f"L×1000/{20 if sup=='SS' else 26} (IS 456 §23.2)", "INFO"),
                ("Effective depth d", f"{res['d_waist_mm']:.1f} mm",
                 "D − cover − Ø/2", "INFO"),
                ("Factored load wu", f"{res['wu_kNm2']:.3f} kN/m²",
                 f"1.5×(DL+LL) = 1.5×({res['w_DL_kNm2']:.2f}+{res['w_LL_kNm2']:.2f})", "INFO"),
                ("Design Moment Mu", f"{res['Mu_kNm_m']:.3f} kN·m/m",
                 f"wu×L²/{8 if sup=='SS' else 10}", "INFO"),
                ("Ast required", f"{res['Ast_req_mm2_m']:.0f} mm²/m",
                 "Mu/(0.87×fy×z)", "OK"),
                ("Main bars", f"Ø{int(mdia)} @ {res['sp_main_mm']} mm c/c",
                 f"Ast,prov={res['ast_main_prov']:.0f} mm²/m  (IS 456 §26.3)", "OK"),
                ("Distribution bars", f"Ø{int(ddia)} @ {res['sp_dist_mm']} mm c/c",
                 f"{0.12 if fy>=415 else 0.15:.2f}% bD  (IS 456 §26.5.2)", "INFO"),
                ("Shear check", f"τv={res['tau_v']:.3f} MPa",
                 f"τc={res['tau_c']:.3f} MPa", "OK" if res['shear_ok'] else "FAIL"),
                ("Deflection L/d", f"{res['ld_prov']:.1f}",
                 f"≤ {res['ld_allow']:.1f} (IS 456 §23.2)", "OK" if res['defl_ok'] else "FAIL"),
                ("Development length Ld", f"{res['Ld_main_mm']:.0f} mm",
                 "0.87fy×Ø/(4τbd)  (IS 456 §26.2.1)", "INFO"),
            ]

            self.res_table.setRowCount(len(rows))
            for i,(p,v,f,st) in enumerate(rows):
                self.res_table.setItem(i,0,_cell(p,bold=True))
                self.res_table.setItem(i,1,_cell(v))
                self.res_table.setItem(i,2,_cell(f))
                bg,fg = STATUS.get(st,(None,None))
                self.res_table.setItem(i,3,_cell(st,bold=True,bg=bg,fg=fg))
            self._resize()
            self.notes_edit.setPlainText("\n\n".join(res.get("notes",["—"])))

        except Exception as e:
            self.res_table.setRowCount(1)
            self.res_table.setItem(0,0,_cell(f"⚠ {e}",fg="#EF9A9A"))
            self.res_table.setSpan(0,0,1,4)

    def _set_defaults(self):
        for k,v in [("H","3.0"),("width","1.2"),("tread","250"),
                    ("riser","150"),("LL","3.0"),("cover","15")]:
            self.inputs[k].setText(v)
        self.inputs["fck"].setCurrentText("20")
        self.inputs["fy"].setCurrentText("415")
        self.inputs["main_dia"].setCurrentText("10")
        self.inputs["dist_dia"].setCurrentText("8")
        self.calculate()
