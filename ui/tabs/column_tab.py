"""
ui/tabs/column_tab.py — IS 456:2000 Column Design Tab
Covers: slenderness, biaxial bending, bar layout, ties, ductile detailing
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from core import check_column
from ui.widgets import UnitLineEdit


def _lbl(text="--"):
    l = QLabel(text); l.setStyleSheet("font-weight:bold;"); return l


def _cell(text, bold=False, bg=None, fg=None):
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    if bold:
        f = QFont(); f.setBold(True); item.setFont(f)
    if bg: item.setBackground(QColor(bg))
    if fg: item.setForeground(QColor(fg))
    return item


STATUS = {"OK": ("#1B5E20","#A5D6A7"), "FAIL": ("#7F0000","#EF9A9A"),
          "WARN": ("#6D3500","#FFCC80"), "INFO": ("#0D47A1","#90CAF9")}


class ColumnTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs: dict = {}
        self._last_result: dict = {}
        self.results: dict = {}
        self._build_ui()
        self._set_defaults()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10,12,10,12); root.setSpacing(10)
        top = QWidget(); tl = QHBoxLayout(top)
        tl.setContentsMargins(0,0,0,0); tl.setSpacing(10)
        tl.addWidget(self._build_input_group(), stretch=2)
        tl.addWidget(self._build_load_group(),  stretch=1)
        root.addWidget(top)
        root.addWidget(self._build_results_group())
        root.addWidget(self._build_rein_group())
        root.addWidget(self._build_notes_group())
        root.addStretch()

    def _build_input_group(self):
        g = QGroupBox("Column Section & Slenderness")
        lay = QGridLayout(g); lay.setVerticalSpacing(9); lay.setHorizontalSpacing(10)
        def ir(lbl, key, w, r, c=0):
            self.inputs[key]=w
            lay.addWidget(QLabel(lbl),r,c); lay.addWidget(w,r,c+1)
        ir("Width b [mm]:",           "b",      UnitLineEdit("mm"), 0)
        ir("Depth D [mm]:",           "D",      UnitLineEdit("mm"), 1)
        ir("Eff. Length lex [mm]:",   "lex",    UnitLineEdit("mm"), 2)
        ir("Eff. Length ley [mm]:",   "ley",    UnitLineEdit("mm"), 3)
        ir("Clear Cover [mm]:",       "cover",  UnitLineEdit("mm"), 4)
        fck_w=QComboBox(); fck_w.addItems(["20","25","30","35","40"])
        fy_w =QComboBox(); fy_w.addItems(["250","415","500"])
        dia_w=QComboBox(); dia_w.addItems(["12","16","20","25","32"])
        tie_w=QComboBox(); tie_w.addItems(["8","10","12"])
        ir("Grade fck [MPa]:", "fck",     fck_w, 0, 2)
        ir("Grade fy [MPa]:",  "fy",      fy_w,  1, 2)
        ir("Main Bar Ø [mm]:","main_dia", dia_w, 2, 2)
        ir("Tie Ø [mm]:",     "tie_dia",  tie_w, 3, 2)
        lay.setColumnStretch(1,1); lay.setColumnStretch(3,1)
        for w in self.inputs.values():
            sig = w.currentTextChanged if isinstance(w,QComboBox) else w.textChanged
            sig.connect(self.calculate)
        return g

    def _build_load_group(self):
        g = QGroupBox("Factored Loads")
        lay = QGridLayout(g); lay.setVerticalSpacing(9)
        def lr(lbl,key,placeholder,r):
            self.inputs[key]=QLineEdit(); self.inputs[key].setPlaceholderText(placeholder)
            lay.addWidget(QLabel(lbl),r,0); lay.addWidget(self.inputs[key],r,1)
            self.inputs[key].textChanged.connect(self.calculate)
        lr("Axial Load Pu [kN]:",    "Pu",  "kN",  0)
        lr("Moment Mux [kN·m]:",     "Mux", "kN·m",1)
        lr("Moment Muy [kN·m]:",     "Muy", "kN·m",2)
        lay.setColumnStretch(1,1)
        return g

    def _build_results_group(self):
        g = QGroupBox("Design Summary")
        lay = QVBoxLayout(g)
        self.res_table = QTableWidget()
        self.res_table.setColumnCount(4)
        self.res_table.setHorizontalHeaderLabels(["Check","Value","Limit / Formula","Status"])
        self.res_table.verticalHeader().setVisible(False)
        self.res_table.setAlternatingRowColors(True)
        self.res_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.res_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lay.addWidget(self.res_table)
        return g

    def _build_rein_group(self):
        g = QGroupBox("Reinforcement Details")
        outer = QHBoxLayout(g); outer.setSpacing(20)
        left = QGridLayout(); left.setVerticalSpacing(8)
        for i,(key,lbl,unit) in enumerate([
            ("Ast_req","Ast required","mm²"),("Ast_prov","Ast provided","mm²"),
            ("steel_pct","Steel %","% of Ag"),("no_bars","No. of bars",""),
        ]):
            l=_lbl(); self.results[key]=l
            left.addWidget(QLabel(f"{lbl}:"),i,0); left.addWidget(l,i,1)
            if unit: left.addWidget(QLabel(unit),i,2)
        left.setColumnStretch(1,1)
        div=QFrame(); div.setFrameShape(QFrame.Shape.VLine); div.setFrameShadow(QFrame.Shadow.Sunken)
        right=QGridLayout(); right.setVerticalSpacing(8)
        for i,(key,lbl,unit) in enumerate([
            ("tie_sp","Tie spacing","mm"),("conf_zone","Confinement zone","mm"),
            ("conf_sp","Confinement tie sp.","mm"),("interaction","Interaction ratio",""),
        ]):
            l=_lbl(); self.results[key]=l
            right.addWidget(QLabel(f"{lbl}:"),i,0); right.addWidget(l,i,1)
            if unit: right.addWidget(QLabel(unit),i,2)
        right.setColumnStretch(1,1)
        outer.addLayout(left,1); outer.addWidget(div); outer.addLayout(right,1)
        return g

    def _build_notes_group(self):
        g = QGroupBox("Design Notes  (IS 456:2000 + NBC 105 Annex A Ductile Detailing)")
        lay = QVBoxLayout(g)
        self.notes_edit = QTextEdit(readOnly=True); self.notes_edit.setMaximumHeight(140)
        lay.addWidget(self.notes_edit); return g

    def _get(self, key):
        w=self.inputs[key]
        return w.currentText() if isinstance(w,QComboBox) else w.text().strip()

    def _resize(self):
        t=self.res_table
        h=t.horizontalHeader().height()
        h+=sum(t.rowHeight(r) for r in range(t.rowCount()))+6
        t.setFixedHeight(h)

    def calculate(self):
        try:
            b   = float(self._get("b"));    D   = float(self._get("D"))
            lex = float(self._get("lex"));  ley = float(self._get("ley"))
            fck = int(self._get("fck"));    fy  = int(self._get("fy"))
            cov = float(self._get("cover"))
            dia = float(self._get("main_dia")); tie = float(self._get("tie_dia"))
            Pu  = float(self._get("Pu") or "0")
            Mux = float(self._get("Mux") or "0")
            Muy = float(self._get("Muy") or "0")
            res = check_column(b,D,lex,ley,fck,fy,Pu,Mux,Muy,
                                cover_mm=cov,tie_dia_mm=tie,main_dia_mm=dia)
            # Results table
            rows = [
                ("Slenderness λx",f"{res['lambda_x']:.2f}","≤ 12 short","OK" if res['lambda_x']<=12 else "WARN"),
                ("Slenderness λy",f"{res['lambda_y']:.2f}","≤ 12 short","OK" if res['lambda_y']<=12 else "WARN"),
                ("Design Mux",f"{res['Mux_design_kNm']:.2f} kN·m",
                 f"incl. Madd={res['Ma_x_kNm']:.2f}","INFO"),
                ("Design Muy",f"{res['Muy_design_kNm']:.2f} kN·m",
                 f"incl. Madd={res['Ma_y_kNm']:.2f}","INFO"),
                ("Biaxial Interaction",f"{res['interaction']:.4f}","≤ 1.0",
                 "OK" if res['interaction']<=1.0 else "FAIL"),
                ("Short Column Pu,max",f"{res['Pu_short_kN']:.1f} kN",
                 "IS 456 Cl.39.3","OK" if res['Pu_short_kN']>=Pu else "WARN"),
                ("Steel %",f"{res['steel_pct']:.2f}%","0.8% – 4.0%",
                 "OK" if 0.8<=res['steel_pct']<=4.0 else "WARN"),
            ]
            self.res_table.setRowCount(len(rows))
            for r,(chk,val,lim,st) in enumerate(rows):
                self.res_table.setItem(r,0,_cell(chk,bold=True))
                self.res_table.setItem(r,1,_cell(val))
                self.res_table.setItem(r,2,_cell(lim))
                bg,fg=STATUS.get(st,(None,None))
                self.res_table.setItem(r,3,_cell(st,bold=True,bg=bg,fg=fg))
            self._resize()
            # Rein labels
            self.results["Ast_req"].setText(f"{res['Ast_req_mm2']:.1f}")
            self.results["Ast_prov"].setText(f"{res['Ast_prov_mm2']:.1f}")
            self.results["steel_pct"].setText(f"{res['steel_pct']:.2f}")
            self.results["no_bars"].setText(
                f"{res['no_of_bars']} × Ø{int(res['bar_dia_mm'])} mm")
            self.results["tie_sp"].setText(str(int(res['tie_spacing_mm'])))
            self.results["conf_zone"].setText(f"{int(res['conf_zone_mm'])}")
            self.results["conf_sp"].setText(str(int(res['conf_tie_sp_mm'])))
            self.results["interaction"].setText(f"{res['interaction']:.4f}")
            self._last_result = res
            self.notes_edit.setPlainText("\n\n".join(res["notes"]))
        except Exception as e:
            self.res_table.setRowCount(1)
            self.res_table.setItem(0,0,_cell(f"⚠ {e}",fg="#EF9A9A"))
            self.res_table.setSpan(0,0,1,4)

    def _set_defaults(self):
        for k,v in [("b","300"),("D","400"),("lex","3500"),("ley","3500"),
                    ("cover","40"),("Pu","900"),("Mux","60"),("Muy","40")]:
            self.inputs[k].setText(v)
        self.inputs["fck"].setCurrentText("25")
        self.inputs["fy"].setCurrentText("415")
        self.inputs["main_dia"].setCurrentText("16")
        self.inputs["tie_dia"].setCurrentText("8")
        self.calculate()
