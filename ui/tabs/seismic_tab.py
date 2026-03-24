"""
ui/tabs/seismic_tab.py — NBC 105:2025 Complete Seismic Tab

Panels:
  1. Input Parameters
  2. Elastic Site Spectra & Period
  3. ULS / SLS Coefficients (side by side)
  4. Story Force Distribution (table — enabled when floor weights provided)
  5. Load Combinations (NBC 105:2025 §3.6)
  6. Code References panel
"""
from __future__ import annotations
from PyQt6.QtWidgets import (  # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QSpinBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QTextEdit, QScrollArea,
)
from PyQt6.QtCore import Qt  # type: ignore
from PyQt6.QtGui import QFont, QColor  # type: ignore
from constants import (  # type: ignore
    ZONE_FACTOR_DATA, IMPORTANCE_FACTORS, SOIL_PARAMS,
    STRUCTURAL_SYSTEMS, KTM_VALLEY_SOIL_D,
)
from ui.widgets import UnitLineEdit  # type: ignore


def _res_lbl(text="--"):
    l = QLabel(text); l.setStyleSheet("font-weight:bold; font-size:10pt;")
    return l

def _cell(text, bold=False, bg=None, fg=None):
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    if bold: f=QFont(); f.setBold(True); item.setFont(f)
    if bg:   item.setBackground(QColor(bg))
    if fg:   item.setForeground(QColor(fg))
    return item

STATUS_COLORS = {
    "OK":        ("#1B5E20","#A5D6A7"),
    "IRREGULAR": ("#6D3500","#FFCC80"),
    "EXTREME":   ("#7F0000","#EF9A9A"),
}


class SeismicTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)  # type: ignore
        self.inputs:  dict = {}
        self.outputs: dict = {}
        self._build_ui()

    def _build_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(14,14,14,14); main.setSpacing(10)
        main.addWidget(self._build_input_group())
        main.addWidget(self._build_soil_info_label())

        # Spectra + coefficients side by side
        row1 = QHBoxLayout(); row1.setSpacing(10)
        row1.addWidget(self._build_spectra_group(), stretch=3)
        row1.addWidget(self._build_uls_sls_group(), stretch=2)
        main.addLayout(row1)

        main.addWidget(self._build_story_force_group())
        main.addWidget(self._build_load_combo_group())
        main.addWidget(self._build_code_ref_group())
        main.addStretch()

    # ── Input ──────────────────────────────────────────────────────────────────
    def _build_input_group(self) -> QGroupBox:
        g = QGroupBox("Input Parameters  —  NBC 105:2025")
        lay = QGridLayout(g); lay.setVerticalSpacing(9); lay.setHorizontalSpacing(12)

        self.inputs["zone"]        = QComboBox()
        self.inputs["method"]      = QComboBox()
        self.inputs["importance"]  = QComboBox()
        self.inputs["soil"]        = QComboBox()
        self.inputs["H"]           = UnitLineEdit("m")
        self.inputs["num_stories"] = QSpinBox()
        self.inputs["num_stories"].setRange(1, 100); self.inputs["num_stories"].setValue(3)
        self.inputs["num_stories"].setToolTip(
            "Number of stories — used for deflection scale factor kd (Table 6-1)")
        self.inputs["struct_cat"]  = QComboBox()
        self.inputs["struct_sub"]  = QComboBox()
        
        self.inputs["sys_orient"]  = QComboBox()
        self.inputs["snow_load"]   = QComboBox()

        self.inputs["zone"].addItems(sorted(ZONE_FACTOR_DATA.keys()))
        self.inputs["method"].addItems(
            ["Equivalent Static Method", "Response Spectrum Method"])
        self.inputs["importance"].addItems(IMPORTANCE_FACTORS.keys())
        self.inputs["soil"].addItems(SOIL_PARAMS.keys())
        self.inputs["struct_cat"].addItems(STRUCTURAL_SYSTEMS.keys())
        self.inputs["sys_orient"].addItems(["Parallel (§3.6.1)", "Non-Parallel (§3.6.2)"])
        self.inputs["snow_load"].addItems(["No", "Yes"])

        # Soil type tooltips
        for s, d in SOIL_PARAMS.items():
            idx = self.inputs["soil"].findText(s)
            if idx >= 0:
                self.inputs["soil"].setItemData(idx, d["description"],
                                                Qt.ItemDataRole.ToolTipRole)

        rows_left = [
            ("Zone / Municipality:",         "zone"),
            ("Analysis Method:",             "method"),
            ("Importance Category:",         "importance"),
            ("Soil Type  (Vs,30 basis):",    "soil"),
            ("Building Height H [m]:",       "H"),
            ("Number of Stories:",           "num_stories"),
            ("Structural System Category:",  "struct_cat"),
            ("Structural System Sub-Type:",  "struct_sub"),
            ("System Orientation:",          "sys_orient"),
            ("Include Snow Load:",           "snow_load"),
        ]
        for r, (lbl_txt, key) in enumerate(rows_left):
            lay.addWidget(QLabel(lbl_txt), r, 0)
            lay.addWidget(self.inputs[key], r, 1)

        # Floor-by-floor weight input (for story force distribution)
        lay.addWidget(QLabel("Floor Weights [kN] (comma-separated,\nbottom→top for Fi calc):"),
                      len(rows_left), 0)
        self._floor_weights_edit = QLineEdit()
        self._floor_weights_edit.setPlaceholderText(
            "e.g. 1200, 1200, 1200  (one per floor, bottom→top)")
        self._floor_weights_edit.setToolTip(
            "Optional: enter per-floor seismic weights (kN) separated by commas. "
            "Enables story force distribution table (NBC 105:2025 §6.3).")
        self.inputs["floor_weights_str"] = self._floor_weights_edit
        lay.addWidget(self._floor_weights_edit, len(rows_left), 1)

        lay.setColumnStretch(1, 1)
        return g

    def _build_soil_info_label(self) -> QLabel:
        self._soil_info = QLabel("")
        self._soil_info.setWordWrap(True)
        self._soil_info.setStyleSheet("color: #D97706; font-style:italic; padding:2px 4px;")
        return self._soil_info

    # ── Spectra & period ───────────────────────────────────────────────────────
    def _build_spectra_group(self) -> QGroupBox:
        g = QGroupBox("Elastic Site Spectra & Fundamental Period  —  NBC 105:2025 §4–§5")
        lay = QGridLayout(g); lay.setVerticalSpacing(7)
        self._add_outputs(lay, [
            ("Zone Factor (Z)",               "Z"),
            ("Importance Factor (I)",         "I"),
            ("Period kt coefficient",         "kt"),
            ("T_approx = kt·H^(3/4)  [s]",   "T_approx"),
            ("Time Period T (×1.25)  [s]",    "T"),
            ("Lateral force exponent k",      "k"),
            ("Spectral Shape Factor Ch(T)",   "Ch_T"),
            ("Elastic Site Spectra C(T)  ULS","C_T"),
            ("Elastic Site Spectra Cs(T) SLS","Cs_T"),
            ("Vertical Spectra Cv(T)",        "Cv_T"),
            ("Deflection Scale Factor kd",    "kd"),
        ])
        lay.setColumnStretch(1, 1)
        return g

    def _build_uls_sls_group(self) -> QGroupBox:
        g = QGroupBox("Base Shear Coefficients")
        lay = QVBoxLayout(g)

        uls = QGroupBox("ULS  —  NBC 105:2025 §6.1.1")
        ul  = QGridLayout(uls)
        self._add_outputs(ul, [
            ("Ductility Factor Rμ",             "Ru"),
            ("Overstrength Ωu",                 "O_u"),
            ("Cd(T) ULS",                       "Cd_ULS"),
            ("Cd(T) ULS (min check)",           "Cd_ULS_governed"),
            ("Allowable Drift  (ULS)",          "Drift_ULS"),
            ("Max. Displacement ULS  [mm]",     "Disp_ULS_mm"),
        ])
        ul.setColumnStretch(1,1)

        sls = QGroupBox("SLS  —  NBC 105:2025 §6.1.2")
        sl  = QGridLayout(sls)
        self._add_outputs(sl, [
            ("Overstrength Ωs",                 "O_s"),
            ("Cd(T) SLS",                       "Cd_SLS"),
            ("Allowable Drift  (SLS)",          "Drift_SLS"),
            ("Max. Displacement SLS  [mm]",     "Disp_SLS_mm"),
        ])
        sl.setColumnStretch(1,1)

        lay.addWidget(uls); lay.addWidget(sls)
        return g

    def _add_outputs(self, layout, pairs):
        for i, (label_text, key) in enumerate(pairs):
            layout.addWidget(QLabel(label_text + ":"), i, 0)
            lbl = _res_lbl(); self.outputs[key] = lbl
            layout.addWidget(lbl, i, 1)

    # ── Story force distribution ───────────────────────────────────────────────
    def _build_story_force_group(self) -> QGroupBox:
        g = QGroupBox(
            "Story Force Distribution  Fi = V·Wi·hi^k / Σ(Wj·hj^k)  —  NBC 105:2025 §6.3")
        self._story_group = g
        lay = QVBoxLayout(g)
        self._story_table = QTableWidget()
        self._story_table.setColumnCount(6)
        self._story_table.setHorizontalHeaderLabels(
            ["Floor", "Wi  [kN]", "hi  [m]", "Wi·hi^k", "Fi  [kN]", "Story Shear Vx  [kN]"])
        self._story_table.verticalHeader().setVisible(False)
        self._story_table.setAlternatingRowColors(True)
        hdr = self._story_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._story_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._story_table.setMinimumHeight(100)
        lay.addWidget(self._story_table)

        # Summary row
        sum_row = QHBoxLayout()
        self._base_shear_lbl = QLabel("Base Shear V:  --  kN")
        self._base_shear_lbl.setStyleSheet("font-weight:bold; font-size:11pt;")
        self._seismic_wt_lbl = QLabel("Seismic Weight W:  --  kN")
        self._seismic_wt_lbl.setStyleSheet("font-weight:bold;")
        sum_row.addWidget(self._seismic_wt_lbl)
        sum_row.addWidget(self._base_shear_lbl)
        sum_row.addStretch()
        lay.addLayout(sum_row)
        g.setVisible(False)
        return g

    # ── Load combinations ──────────────────────────────────────────────────────
    def _build_load_combo_group(self) -> QGroupBox:
        g = QGroupBox(
            "Load Combinations  —  NBC 105:2025 §3.6  (Limit State Method)")
        lay = QVBoxLayout(g)

        # DL / LL input for actual factored forces
        inp = QHBoxLayout()
        inp.addWidget(QLabel("DL per floor [kN/m²]:"))
        self._dl_edit = QLineEdit(); self._dl_edit.setFixedWidth(90)
        self._dl_edit.setPlaceholderText("e.g. 8.0")
        self.inputs["dl_combo_edit"] = self._dl_edit
        inp.addWidget(self._dl_edit)
        inp.addWidget(QLabel("LL [kN/m²]:"))
        self._ll_edit = QLineEdit(); self._ll_edit.setFixedWidth(90)
        self._ll_edit.setPlaceholderText("e.g. 3.0")
        self.inputs["ll_combo_edit"] = self._ll_edit
        inp.addWidget(self._ll_edit)
        inp.addWidget(QLabel("λ (live load factor):"))
        self._lambda_lbl = QLabel("0.30")
        self._lambda_lbl.setStyleSheet("font-weight:bold;")
        inp.addWidget(self._lambda_lbl)
        inp.addStretch()
        lay.addLayout(inp)

        self._combo_table = QTableWidget()
        self._combo_table.setColumnCount(5)
        self._combo_table.setHorizontalHeaderLabels(
            ["Combination", "Formula", "DL factor", "LL factor", "E / W factor"])
        self._combo_table.verticalHeader().setVisible(False)
        self._combo_table.setAlternatingRowColors(True)
        self._combo_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._combo_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lay.addWidget(self._combo_table)

        note = QLabel(
            "<small>E_ULS = Cd(T)·W (ULS),  E_SLS = Cd(T)·W/Ωs (SLS).  "
            "For seismic combos: λ = 0.30 (general) or 0.60 (storage).  "
            "WSM combos per NBC 105:2025 §3.7 use 0.7×E (not SLS spectra). "
            "SBC increase: +50% per §3.8.</small>"
        )
        note.setWordWrap(True); lay.addWidget(note)
        return g

    # ── Code references ────────────────────────────────────────────────────────
    def _build_code_ref_group(self) -> QGroupBox:
        g = QGroupBox("Key Code References  —  NBC 105:2025")
        lay = QVBoxLayout(g)
        refs = QTextEdit(readOnly=True); refs.setMinimumHeight(100)
        refs.setHtml("""
        <small>
        <b>§4.1.2</b> Spectral shape factor Ch(T): 3-zone formula (flat → velocity → displacement)<br>
        <b>§4.2</b> SLS spectra: Cs(T) = 0.20·C(T)  |  <b>§4.3</b> Vertical spectra: Cv(Tv) = 2/3·Z<br>
        <b>§5.1.3</b> Period amplification ×1.25  |  <b>§5.3</b> Structural systems: Rμ, Ωu, Ωs (Table 5-2)<br>
        <b>§5.4</b> Irregularity: weak/soft/mass story; torsional (>1.5× = irregular; >2.5× = not permitted)<br>
        <b>§5.5.2</b> Building separation: Δgap = √(Δ1²+Δ2²) (SRSS)  |  <b>§5.6</b> Accidental eccentricity ±0.05b<br>
        <b>§6.3</b> Story force Fi = V·Wi·hi^k/Σ(Wj·hj^k)  |  <b>§6.5</b> Deflection scale kd (Table 6-1)<br>
        <b>§3.6</b> LSM combos: 1.2DL+1.5LL; DL+λLL±E; 0.9DL±E  |  <b>§3.7</b> WSM: DL+λLL±0.7E  |  <b>§3.8</b> SBC +50%<br>
        <b>§10</b> Parts: Fp = Cd(T)·Cp·(1+z/H)·Ip/μp·Wp  |  Annex A: Ductile RC detailing
        </small>
        """)
        lay.addWidget(refs)
        return g

    # ── Public API ─────────────────────────────────────────────────────────────
    def get_params(self) -> dict:
        # Parse floor weights
        fw_text = self._floor_weights_edit.text().strip()
        floor_weights = []
        if fw_text:
            try:
                floor_weights = [float(x.strip()) for x in fw_text.split(",") if x.strip()]
            except ValueError:
                pass
        return {
            "zone_name":     self.inputs["zone"].currentText(),
            "method":        self.inputs["method"].currentText(),
            "imp_name":      self.inputs["importance"].currentText(),
            "soil_type":     self.inputs["soil"].currentText(),
            "H":             self.inputs["H"].text(),
            "num_stories":   self.inputs["num_stories"].value(),
            "struct_cat":    self.inputs["struct_cat"].currentText(),
            "struct_sub":    self.inputs["struct_sub"].currentText(),
            "is_parallel":   self.inputs["sys_orient"].currentText().startswith("Parallel"),
            "include_snow":  self.inputs["snow_load"].currentText() == "Yes",
            "floor_weights": floor_weights,
        }

    def populate_results(self, res: dict) -> None:
        fmt = {
            "Z":              f"{res['Z']:.2f}",
            "I":              f"{res['I']:.2f}",
            "kt":             f"{res['kt']:.4f}",
            "T_approx":       f"{res['T_approx']:.4f}",
            "T":              f"{res['T']:.4f}",
            "k":              f"{res['k']:.4f}",
            "Ch_T":           f"{res['Ch_T']:.4f}",
            "C_T":            f"{res['C_T']:.4f}",
            "Cs_T":           f"{res['Cs_T']:.4f}",
            "Cv_T":           f"{res['Cv_T']:.4f}",
            "kd":             f"{res['kd']:.2f}",
            "Ru":             f"{res['Ru']:.2f}",
            "O_u":            f"{res['O_u']:.2f}",
            "Cd_ULS":         f"{res['Cd_ULS']:.4f}",
            "Cd_ULS_governed":f"{res['Cd_ULS_governed']:.4f}" + (" ← min governs" if res.get("min_governed") else ""),
            "Drift_ULS":      f"0.025  (inter-story limit)",
            "Disp_ULS_mm":    f"{res['Disp_ULS_mm']:.2f}",
            "O_s":            f"{res['O_s']:.2f}",
            "Cd_SLS":         f"{res['Cd_SLS']:.4f}",
            "Drift_SLS":      f"0.006  (inter-story limit)",
            "Disp_SLS_mm":    f"{res['Disp_SLS_mm']:.2f}",
        }
        for key, val in fmt.items():
            if key in self.outputs:
                self.outputs[key].setText(val)

        # Story force table
        sf = res.get("story_forces", [])
        if sf:
            self._story_group.setVisible(True)
            t = self._story_table
            t.setRowCount(len(sf))
            for r, f in enumerate(sf):
                t.setItem(r, 0, _cell(f["floor"], bold=True))
                t.setItem(r, 1, _cell(f"{f['W_kN']:.1f}"))
                t.setItem(r, 2, _cell(f"{f['h_m']:.2f}"))
                t.setItem(r, 3, _cell(f"{f['Wh_k']:.1f}"))
                t.setItem(r, 4, _cell(f"{f['Fi_kN']:.2f}"))
                t.setItem(r, 5, _cell(f"{f['Vx_kN']:.2f}", bold=True))
            self._base_shear_lbl.setText(f"Base Shear V = {res['V_base_kN']:.1f} kN")
            self._seismic_wt_lbl.setText(f"Total Seismic Weight W = {res['W_seismic_kN']:.1f} kN")
        else:
            self._story_group.setVisible(False)

        # Load combination table
        combos = res.get("load_combos", [])
        if combos:
            self._lambda_lbl.setText(f"{res.get('lambda_ll', 0.30):.2f}")
            t = self._combo_table
            t.setRowCount(len(combos))
            for r, c in enumerate(combos):
                e_info = ""
                if "EX_ULS_fac" in c and (c["EX_ULS_fac"] != 0 or c["EY_ULS_fac"] != 0):
                    parts = []
                    ex, ey = c["EX_ULS_fac"], c["EY_ULS_fac"]
                    if ex != 0: parts.append(f"{ex:+.2f}EX")  # type: ignore
                    if ey != 0: parts.append(f"{ey:+.2f}EY")  # type: ignore
                    e_info = " ".join(parts)
                elif c.get("E_ULS_fac", 0) != 0:
                    e_info = f"{c['E_ULS_fac']:+.1f}×E_ULS"
                elif c.get("E_SLS_fac", 0) != 0:
                    e_info = f"{c['E_SLS_fac']:+.1f}×E_SLS"
                ll_show = f"{c['LL_fac']:.2f}" if isinstance(c['LL_fac'],float) else str(c['LL_fac'])
                t.setItem(r, 0, _cell(c["label"], bold=True))  # type: ignore
                t.setItem(r, 1, _cell(c["formula"]))  # type: ignore
                t.setItem(r, 2, _cell(f"{c['DL_fac']:.1f}"))
                t.setItem(r, 3, _cell(ll_show))
                t.setItem(r, 4, _cell(e_info))
            # Resize table to content
            pass  # combo table auto-sizes

    def clear_results(self) -> None:
        for lbl in self.outputs.values():
            lbl.setText("--")
        self._story_group.setVisible(False)

    def update_subtype_options(self, category: str) -> None:
        current = self.inputs["struct_sub"].currentText()
        self.inputs["struct_sub"].blockSignals(True)
        self.inputs["struct_sub"].clear()
        if category in STRUCTURAL_SYSTEMS:
            items = list(STRUCTURAL_SYSTEMS[category].keys())
            self.inputs["struct_sub"].addItems(items)
            if current in items:
                self.inputs["struct_sub"].setCurrentText(current)
        self.inputs["struct_sub"].blockSignals(False)

    def update_soil_info(self, zone: str, soil_type: str) -> None:
        # Check if any KTM Valley municipality name partially matches the zone
        ktm_match = any(
            muni.split()[0].lower() in zone.lower()
            for muni in KTM_VALLEY_SOIL_D.keys()
        )
        if ktm_match and soil_type != "D":
            self._soil_info.setText(
                f"⚠  NBC 105:2025 Table 4-3: '{zone}' may be in Kathmandu Valley "
                "Soil Type D zone — verify with Vs,30 field testing.")
        else:
            self._soil_info.setText("")

    def get_ct_value(self) -> float | None:
        try:
            return float(self.outputs["C_T"].text().split()[0])
        except (ValueError, TypeError, IndexError):
            return None
