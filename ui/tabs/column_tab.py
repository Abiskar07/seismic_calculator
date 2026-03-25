"""
ui/tabs/column_tab.py — IS 456:2000 Column Design
Fixed: Pu_short_kN → Pu_max_kN key, enlarged notes area, responsive layout
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QSplitter, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from core import check_column
from ui.widgets import UnitLineEdit


def _lbl(t="--"):
    l = QLabel(t)
    l.setStyleSheet("font-weight: bold;")
    return l


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

class ColumnTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs: dict = {}
        self.results: dict = {}
        self._last_result: dict = {}
        self._build_ui()
        self._set_defaults()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 12, 10, 12)
        root.setSpacing(8)

        # Top: inputs side by side
        top = QWidget()
        tl = QHBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(10)
        tl.addWidget(self._build_section_group(), stretch=3)
        tl.addWidget(self._build_load_group(), stretch=2)
        root.addWidget(top)

        # Results table
        root.addWidget(self._build_results_group())

        # Reinforcement details
        root.addWidget(self._build_rein_group())

        # Notes — expanded, no max height cap
        root.addWidget(self._build_notes_group(), stretch=1)

    def _build_section_group(self) -> QGroupBox:
        g = QGroupBox("Section Geometry & Slenderness")
        lay = QGridLayout(g)
        lay.setVerticalSpacing(8)
        lay.setHorizontalSpacing(10)

        def _ir(lbl, key, widget, row, col=0):
            self.inputs[key] = widget
            lay.addWidget(QLabel(lbl), row, col)
            lay.addWidget(widget, row, col + 1)

        _ir("Width b [mm]:",           "b",   UnitLineEdit("mm"), 0)
        _ir("Depth D [mm]:",           "D",   UnitLineEdit("mm"), 1)
        _ir("Eff. Length lex [mm]:",   "lex", UnitLineEdit("mm"), 2)
        _ir("Eff. Length ley [mm]:",   "ley", UnitLineEdit("mm"), 3)
        _ir("Clear Cover [mm]:",       "cover", UnitLineEdit("mm"), 4)

        fck_w = QComboBox(); fck_w.addItems(["20","25","30","35","40"])
        fy_w  = QComboBox(); fy_w.addItems(["250","415","500"])
        dia_w = QComboBox(); dia_w.addItems(["12","16","20","25","32"])
        tie_w = QComboBox(); tie_w.addItems(["8","10","12"])

        _ir("fck [MPa]:", "fck",      fck_w, 0, 2)
        _ir("fy [MPa]:",  "fy",       fy_w,  1, 2)
        _ir("Main Ø [mm]:","main_dia", dia_w, 2, 2)
        _ir("Tie Ø [mm]:","tie_dia",  tie_w, 3, 2)

        lay.setColumnStretch(1, 1)
        lay.setColumnStretch(3, 1)

        # Wire all inputs
        for w in self.inputs.values():
            sig = w.currentTextChanged if isinstance(w, QComboBox) else w.editingFinished
            sig.connect(self.calculate)
        return g

    def _build_load_group(self) -> QGroupBox:
        g = QGroupBox("Factored Loads")
        lay = QGridLayout(g)
        lay.setVerticalSpacing(8)

        for r, (lbl, key, ph) in enumerate([
            ("Axial Pu [kN]:",    "Pu",  "kN"),
            ("Moment Mux [kN·m]:","Mux", "kN·m"),
            ("Moment Muy [kN·m]:","Muy", "kN·m"),
        ]):
            w = QLineEdit()
            w.setPlaceholderText(ph)
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl), r, 0)
            lay.addWidget(w, r, 1)
            w.editingFinished.connect(self.calculate)

        lay.setColumnStretch(1, 1)
        return g

    def _build_results_group(self) -> QGroupBox:
        g = QGroupBox("Design Checks  —  IS 456:2000 §39 + NBC 105:2025 Annex A")
        lay = QVBoxLayout(g)
        self.res_table = QTableWidget()
        self.res_table.setColumnCount(4)
        self.res_table.setHorizontalHeaderLabels(
            ["Check", "Value", "Limit / Clause", "Status"])
        # DEBUG: Show vertical header to display row numbers (1-based)
        self.res_table.verticalHeader().setVisible(True)
        self.res_table.setAlternatingRowColors(True)
        hdr = self.res_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.res_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lay.addWidget(self.res_table)
        return g

    def _build_rein_group(self) -> QGroupBox:
        g = QGroupBox("Reinforcement Details")
        outer = QHBoxLayout(g)
        outer.setSpacing(20)

        left = QGridLayout()
        left.setVerticalSpacing(6)
        for i, (key, lbl, unit) in enumerate([
            ("Ast_req",    "Ast required",    "mm²"),
            ("Ast_prov",   "Ast provided",    "mm²"),
            ("steel_pct",  "Steel %",         "%"),
            ("no_bars",    "Bars provided",   ""),
        ]):
            l = _lbl()
            self.results[key] = l
            left.addWidget(QLabel(f"{lbl}:"), i, 0)
            left.addWidget(l, i, 1)
            if unit:
                left.addWidget(QLabel(unit), i, 2)
        left.setColumnStretch(1, 1)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFrameShadow(QFrame.Shadow.Sunken)

        right = QGridLayout()
        right.setVerticalSpacing(6)
        for i, (key, lbl, unit) in enumerate([
            ("tie_sp",    "Tie spacing",      "mm c/c"),
            ("conf_zone", "Confinement zone", "mm"),
            ("conf_sp",   "Confinement ties", "mm c/c"),
            ("interaction","Interaction ratio",""),
        ]):
            l = _lbl()
            self.results[key] = l
            right.addWidget(QLabel(f"{lbl}:"), i, 0)
            right.addWidget(l, i, 1)
            if unit:
                right.addWidget(QLabel(unit), i, 2)
        right.setColumnStretch(1, 1)

        outer.addLayout(left, 1)
        outer.addWidget(div)
        outer.addLayout(right, 1)
        return g

    def _build_notes_group(self) -> QGroupBox:
        g = QGroupBox(
            "Design Notes  (IS 456:2000 §25, §39 + NBC 105:2025 Annex A Ductile Detailing)")
        lay = QVBoxLayout(g)
        self.notes_edit = QTextEdit(readOnly=True)
        self.notes_edit.setMinimumHeight(120)
        self.notes_edit.setSizePolicy(
            self.notes_edit.sizePolicy().horizontalPolicy(),
            __import__('PyQt6.QtWidgets', fromlist=['QSizePolicy']).QSizePolicy.Policy.Expanding)
        lay.addWidget(self.notes_edit)
        return g

    def _get(self, key: str) -> str:
        w = self.inputs[key]
        return w.currentText() if isinstance(w, QComboBox) else w.text().strip()

    def _resize_table(self):
        t = self.res_table
        h = t.horizontalHeader().height()
        h += sum(t.rowHeight(r) for r in range(t.rowCount())) + 6
        t.setFixedHeight(h)

    def calculate(self):
        try:
            b   = float(self._get("b"))
            D   = float(self._get("D"))
            lex = float(self._get("lex"))
            ley = float(self._get("ley"))
            fck = int(self._get("fck"))
            fy  = int(self._get("fy"))
            cov = float(self._get("cover"))
            dia = float(self._get("main_dia"))
            tie = float(self._get("tie_dia"))
            Pu  = float(self._get("Pu")  or "0")
            Mux = float(self._get("Mux") or "0")
            Muy = float(self._get("Muy") or "0")

            if b <= 0 or D <= 0:
                raise ValueError("Dimensions b and D must be > 0.")
            if lex <= 0 or ley <= 0:
                raise ValueError("Effective lengths lex and ley must be > 0.")
            if cov <= 0:
                raise ValueError("Clear cover must be > 0.")

            res = check_column(b, D, lex, ley, fck, fy, Pu, Mux, Muy,
                               cover_mm=cov, tie_dia_mm=tie, main_dia_mm=dia)

            # Fixed key: engine returns Pu_max_kN, not Pu_short_kN
            # DEBUG: Print rows to console
            print("DEBUG: Building rows for results table...")
            import sys; sys.stdout.flush()
            rows = [
                ("Slenderness λx",
                 f"{res['lambda_x']:.2f}",
                 "≤ 12 → short column",
                 "OK" if res['lambda_x'] <= 12 else "WARN"),
                ("Slenderness λy",
                 f"{res['lambda_y']:.2f}",
                 "≤ 12 → short column",
                 "OK" if res['lambda_y'] <= 12 else "WARN"),
                ("Min. eccentricity ex",
                 f"{res['emin_x_mm']:.1f} mm",
                 "max(L/500 + D/30, 20mm)  IS 456 §25.4",
                 "INFO"),
                ("Design Mux  (incl. Madd)",
                 f"{res['Mux_design_kNm']:.2f} kN·m",
                 f"Madd,x = {res['Ma_x_kNm']:.2f} kN·m  (IS 456 §39.7)",
                 "INFO"),
                ("Design Muy  (incl. Madd)",
                 f"{res['Muy_design_kNm']:.2f} kN·m",
                 f"Madd,y = {res['Ma_y_kNm']:.2f} kN·m  (IS 456 §39.7)",
                 "INFO"),
                ("Biaxial Interaction",
                 f"{res['interaction']:.4f}",
                 "≤ 1.0  (IS 456 §39.6)",
                 "OK" if res['interaction'] <= 1.0 else "FAIL"),
                ("Pure Axial Capacity Pu,max",
                 f"{res['Pu_max_kN']:.1f} kN",       # FIXED: was Pu_short_kN
                 "0.40·fck·(Ag−Ast) + 0.67·fy·Ast  IS 456 §39.3",
                 "OK" if res['Pu_max_kN'] >= Pu else "FAIL"),
                ("Steel percentage",
                 f"{res['steel_pct']:.2f}%",
                 "0.8% – 4.0%  (IS 456 §26.5.3 / NBC 105 Annex A)",
                 "OK" if 0.8 <= res['steel_pct'] <= 4.0 else "FAIL"),
                ("Confinement hoop Ash",
                 f"req={res['Ash_req_mm2']:.1f} mm²  prov={res['Ash_prov_mm2']:.1f} mm²",
                 "≥ 0.09·s·h\"·fck/fy  (NBC 105 Annex A §A.4.4.4)",
                 "OK" if res['hoop_ok'] else "FAIL"),
            ]

            # DEBUG: Print all rows
            print("DEBUG: Rows data:")
            for i, row in enumerate(rows):
                print(f"  Row {i}: {row}")
            print(f"DEBUG: Total rows: {len(rows)}")
            import sys; sys.stdout.flush()

            #self.res_table.setRowCount(len(rows))
            self.res_table.clearSpans()          # ← add this line
            self.res_table.setRowCount(len(rows))
            # DEBUG: Set 1-based row numbers in vertical header
            for r in range(len(rows)):
                self.res_table.setVerticalHeaderItem(r, QTableWidgetItem(str(r + 1)))
            for r, (chk, val, lim, st) in enumerate(rows):
                self.res_table.setItem(r, 0, _cell(chk, bold=True))
                self.res_table.setItem(r, 1, _cell(val))
                self.res_table.setItem(r, 2, _cell(lim))
                self.res_table.setItem(r, 3, _status_cell(st))
            self._resize_table()

            # Reinforcement detail labels
            self.results["Ast_req"].setText(f"{res['Ast_req_mm2']:.1f}")
            self.results["Ast_prov"].setText(f"{res['Ast_prov_mm2']:.1f}")
            self.results["steel_pct"].setText(f"{res['steel_pct']:.2f}")
            self.results["no_bars"].setText(
                f"{res['no_of_bars']} × Ø{int(res['bar_dia_mm'])} mm  "
                f"(Ast = {res['Ast_prov_mm2']:.0f} mm²)")
            self.results["tie_sp"].setText(str(int(res['tie_spacing_mm'])))
            self.results["conf_zone"].setText(f"{int(res['conf_zone_mm'])}")
            self.results["conf_sp"].setText(str(int(res['conf_tie_sp_mm'])))
            # Color interaction ratio
            inter = res['interaction']
            col = "#2E7D32" if inter <= 1.0 else "#C62828"
            self.results["interaction"].setText(f"{inter:.4f}")
            self.results["interaction"].setStyleSheet(f"font-weight:bold; color:{col};")

            self._last_result = res
            self.notes_edit.setPlainText("\n\n".join(res.get("notes", ["—"])))

        except Exception as e:
            self.res_table.setRowCount(1)
            err = _cell(f"⚠  {e}", fg="#EF9A9A")
            self.res_table.setItem(0, 0, err)
            self.res_table.setSpan(0, 0, 1, 4)
            self._resize_table()

    def _set_defaults(self):
        defaults = {
            "b": "300", "D": "400",
            "lex": "3500", "ley": "3500",
            "cover": "40",
            "Pu": "900", "Mux": "60", "Muy": "40",
        }
        for k, v in defaults.items():
            if k in self.inputs:
                self.inputs[k].setText(v)
        self.inputs["fck"].setCurrentText("25")
        self.inputs["fy"].setCurrentText("415")
        self.inputs["main_dia"].setCurrentText("16")
        self.inputs["tie_dia"].setCurrentText("8")
        self.calculate()
