"""ui/tabs/wind_tab.py — IS 875 Part 3:2015 Wind Load Tab"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from core import calculate_wind_loads
from core.wind_engine import (
    BASIC_WIND_SPEED, K1_FACTORS, K3_TABLE, K4_TABLE
)
from ui.widgets import UnitLineEdit

def _cell(text, bold=False, bg=None, fg=None):
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setFlags(Qt.ItemFlag.ItemIsSelectable|Qt.ItemFlag.ItemIsEnabled)
    if bold: f=QFont(); f.setBold(True); item.setFont(f)
    if bg: item.setBackground(QColor(bg))
    if fg: item.setForeground(QColor(fg))
    return item


class WindTab(QWidget):
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
        tl.addWidget(self._build_site_group(), stretch=2)
        tl.addWidget(self._build_bldg_group(), stretch=1)
        root.addWidget(top)
        root.addWidget(self._build_results_group())
        root.addWidget(self._build_story_group())
        root.addWidget(self._build_notes_group())
        root.addStretch()

    def _build_site_group(self):
        g = QGroupBox("Site Parameters  —  IS 875 Part 3:2015")
        lay = QGridLayout(g); lay.setVerticalSpacing(9); lay.setHorizontalSpacing(10)

        loc_w = QComboBox(); loc_w.addItems(sorted(BASIC_WIND_SPEED.keys()))
        k1_w  = QComboBox(); k1_w.addItems(list(K1_FACTORS.keys()))
        k3_w  = QComboBox(); k3_w.addItems(list(K3_TABLE.keys()))
        k4_w  = QComboBox(); k4_w.addItems(list(K4_TABLE.keys()))
        tc_w  = QComboBox(); tc_w.addItems(["1 (Open sea/flat)","2 (Open terrain)","3 (Suburban)","4 (Urban dense)"])
        vb_w  = QLineEdit(); vb_w.setPlaceholderText("Override (blank=use table)")
        vb_w.setToolTip("Override basic wind speed in m/s. Leave blank to use table value.")

        self.inputs.update({"location":loc_w,"k1":k1_w,"k3":k3_w,"k4":k4_w,
                            "terrain":tc_w,"Vb_override":vb_w})
        for r,(lbl,key) in enumerate([
            ("Location:",           "location"),
            ("Risk / Return Period (k1):","k1"),
            ("Topography factor (k3):", "k3"),
            ("Importance factor (k4):","k4"),
            ("Terrain Category:",   "terrain"),
            ("Override Vb [m/s]:",  "Vb_override"),
        ]):
            lay.addWidget(QLabel(lbl), r, 0)
            lay.addWidget(self.inputs[key], r, 1)

        for w in self.inputs.values():
            sig = w.currentTextChanged if isinstance(w,QComboBox) else w.textChanged
            sig.connect(self.calculate)
        lay.setColumnStretch(1,1)
        return g

    def _build_bldg_group(self):
        g = QGroupBox("Building Dimensions")
        lay = QGridLayout(g); lay.setVerticalSpacing(9)
        for r,(lbl,key) in enumerate([
            ("Height H [m]:", "H"),
            ("Width B [m] (⊥ wind):", "B"),
            ("Depth D [m] (∥ wind):", "D"),
            ("Floor heights [m]\n(comma sep. for story forces):", "floors"),
        ]):
            w = QLineEdit() if key=="floors" else UnitLineEdit("m")
            w.setPlaceholderText("optional" if key=="floors" else "")
            self.inputs[key] = w
            lay.addWidget(QLabel(lbl), r, 0); lay.addWidget(w, r, 1)
            w.textChanged.connect(self.calculate)
        lay.setColumnStretch(1,1)
        return g

    def _build_results_group(self):
        g = QGroupBox("Wind Pressure & Base Shear  —  IS 875 Pt 3:2015")
        lay = QVBoxLayout(g)
        self.res_table = QTableWidget()
        self.res_table.setColumnCount(3)
        self.res_table.setHorizontalHeaderLabels(["Parameter","Value","Clause / Formula"])
        self.res_table.verticalHeader().setVisible(False)
        self.res_table.setAlternatingRowColors(True)
        self.res_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.res_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lay.addWidget(self.res_table)
        return g

    def _build_story_group(self):
        self._story_grp = QGroupBox("Story Wind Forces")
        self._story_grp.setVisible(False)
        lay = QVBoxLayout(self._story_grp)
        self._story_table = QTableWidget()
        self._story_table.setColumnCount(4)
        self._story_table.setHorizontalHeaderLabels(
            ["Floor","Height h (m)","pz (kPa)","Fi (kN)"])
        self._story_table.verticalHeader().setVisible(False)
        self._story_table.setAlternatingRowColors(True)
        self._story_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._story_table.setMaximumHeight(200)
        lay.addWidget(self._story_table)
        return self._story_grp

    def _build_notes_group(self):
        g = QGroupBox("Design Notes")
        lay = QVBoxLayout(g)
        self.notes_edit = QTextEdit(readOnly=True)
        self.notes_edit.setMaximumHeight(100)
        lay.addWidget(self.notes_edit)
        return g

    def _g(self, key, default=""):
        w = self.inputs.get(key)
        if w is None: return default
        return w.currentText() if isinstance(w,QComboBox) else w.text().strip()

    def _resize(self, t):
        h = t.horizontalHeader().height()
        h += sum(t.rowHeight(r) for r in range(t.rowCount())) + 4
        t.setFixedHeight(h)

    def calculate(self):
        try:
            loc = self._g("location","Generic Nepal")
            k1_label = self._g("k1", list(K1_FACTORS.keys())[0])
            k3_label = self._g("k3", list(K3_TABLE.keys())[0])
            k4_label = self._g("k4", list(K4_TABLE.keys())[0])
            tc_text  = self._g("terrain","2 (Open terrain)")
            tc       = int(tc_text[0])
            Vb_ov    = self._g("Vb_override","")
            Vb       = float(Vb_ov) if Vb_ov else None
            H   = float(self._g("H","10") or "10")
            B   = float(self._g("B","10") or "10")
            D   = float(self._g("D","10") or "10")
            fl_t = self._g("floors","")
            floors = [float(x.strip()) for x in fl_t.split(",") if x.strip()] if fl_t else None

            res = calculate_wind_loads(loc, Vb, H, B, D, tc,
                                       k1_label, k3_label, k4_label, floors)
            self._last_result = res

            rows = [
                ("Location",        res['location'],          "—"),
                ("Basic Wind Speed Vb", f"{res['Vb_ms']:.0f} m/s", "IS 875 Pt 3 §5.2 Fig.1"),
                ("k1 (risk factor)",f"{res['k1']:.2f}",       "Table 1"),
                ("k2 (height+terrain)",f"{res['k2']:.3f}",   "Table 2 (power law)"),
                ("k3 (topography)", f"{res['k3']:.2f}",       "§6.3.3"),
                ("k4 (importance)", f"{res['k4']:.2f}",       "§6.3.4"),
                ("Design Wind Speed Vz", f"{res['Vz_ms']:.2f} m/s","Vb·k1·k2·k3·k4"),
                ("Wind Pressure pz", f"{res['pz_kPa']:.4f} kPa","0.6·Vz² (IS 875 Pt 3 §6.2)"),
                ("Kd (directionality)", f"{res['Kd']:.2f}",   "§7.3.1"),
                ("Ka (area averaging)", f"{res['Ka']:.3f}",   "§7.3.2 Table 4"),
                ("Kc (combination)",f"{res['Kc']:.2f}",       "§7.3.3"),
                ("Design Pressure pd",f"{res['pd_kPa']:.4f} kPa","pz·Kd·Ka·Kc"),
                ("Cpe windward",    f"{res['Cpe_windward']:.1f}",  "Table 5 (h/d={:.2f})".format(res['h_d_ratio'])),
                ("Cpe leeward",     f"{res['Cpe_leeward']:.1f}",   "Table 5"),
                ("Net wall pressure",f"{res['p_net_kPa']:.4f} kPa","(Cpe,ww−Cpe,lw)·pd"),
                ("Base Shear V_wind",f"{res['V_wind_kN']:.2f} kN", "Sum of story forces"),
            ]
            self.res_table.setRowCount(len(rows))
            for i,(p,v,f) in enumerate(rows):
                self.res_table.setItem(i,0,_cell(p,bold=True))
                self.res_table.setItem(i,1,_cell(v))
                self.res_table.setItem(i,2,_cell(f))
            self._resize(self.res_table)

            sf = res.get("story_forces",[])
            if sf:
                self._story_grp.setVisible(True)
                t = self._story_table
                t.setRowCount(len(sf))
                for i,f in enumerate(sf):
                    t.setItem(i,0,_cell(f["floor"],bold=True))
                    t.setItem(i,1,_cell(f"{f['h_m']:.2f}"))
                    t.setItem(i,2,_cell(f"{f['pz_kPa']:.4f}"))
                    t.setItem(i,3,_cell(f"{f['Fi_kN']:.2f}"))
                t.setMaximumHeight(min(250,(t.rowCount()+1)*30+10))
            else:
                self._story_grp.setVisible(False)

            self.notes_edit.setPlainText("\n".join(res.get("notes",["—"])))

        except Exception as e:
            self.res_table.setRowCount(1)
            self.res_table.setItem(0,0,_cell(f"⚠ {e}",fg="#EF9A9A"))
            self.res_table.setSpan(0,0,1,3)

    def _set_defaults(self):
        for k,v in [("H","12.0"),("B","10.0"),("D","15.0")]:
            self.inputs[k].setText(v)
        self.inputs["location"].setCurrentText("Kathmandu")
        self.calculate()
