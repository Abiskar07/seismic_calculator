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
    QCompleter,
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
        self._setup_zone_combo()
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

        # Floor seismic weight table (NBC Table 5-1): Wi = DL + λ·LL
        lay.addWidget(QLabel("Story seismic weights Wi [kN] (auto: Wi = DL + λ·LL):"),
                      len(rows_left), 0)
        self._floor_weights_input = QTableWidget()
        self._floor_weights_input.setColumnCount(5)
        self._floor_weights_input.setHorizontalHeaderLabels(
            ["Level", "DL [kN]", "LL [kN]", "λ", "Wi [kN]"])

        self._floor_weights_input.verticalHeader().setVisible(False)
        self._floor_weights_input.setAlternatingRowColors(True)
        self._floor_weights_input.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._floor_weights_input.setMinimumHeight(160)
        self._floor_weights_input.setToolTip(
            "Enter DL and LL for each story. Wi is auto-calculated as Wi = DL + λ·LL, with λ=0.30 for all stories and λ=0.00 for top story.")

        lay.addWidget(self._floor_weights_input, len(rows_left), 1)

        self._floor_weights_input.itemChanged.connect(self._on_floor_weight_item_changed)
        self.inputs["num_stories"].valueChanged.connect(self._sync_floor_weight_rows)
        self._sync_floor_weight_rows(self.inputs["num_stories"].value())



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

    def _fit_table_height_to_rows(self, table: QTableWidget) -> None:
        table.resizeRowsToContents()
        header_h = table.horizontalHeader().height() if table.horizontalHeader().isVisible() else 0
        rows_h = sum(table.rowHeight(r) for r in range(table.rowCount()))
        h = header_h + rows_h + (table.frameWidth() * 2) + 6
        table.setMinimumHeight(max(70, h))
        table.setMaximumHeight(max(70, h))


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

        info = QLabel(
            "<small>Seismic weight Wi is computed in the story table as Wi = DL + λ·LL "
            "(NBC 105:2025 Table 5-1). App rule: λ=0.30 for all stories, top story λ=0.00.</small>")

        info.setWordWrap(True)
        lay.addWidget(info)


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
            "In this app: λ = 0.30 for seismic combinations; top-story LL participation for Wi is taken as 0.00.  "
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
        ref_lines = [
            "<b>§4.1.2</b> Spectral shape factor Ch(T): 3-zone formula (flat → velocity → displacement)",
            "<b>§4.2</b> SLS spectra: Cs(T) = 0.20·C(T)  |  <b>§4.3</b> Vertical spectra: Cv(Tv) = 2/3·Z",
            "<b>§5.1.3</b> Period amplification ×1.25  |  <b>§5.3</b> Structural systems: Rμ, Ωu, Ωs (Table 5-2)",
            "<b>§5.4</b> Irregularity: weak/soft/mass story; torsional (>1.5× = irregular; >2.5× = not permitted)",
            "<b>§5.5.2</b> Building separation: Δgap = √(Δ1²+Δ2²) (SRSS)  |  <b>§5.6</b> Accidental eccentricity ±0.05b",
            "<b>§6.3</b> Story force Fi = V·Wi·hi^k/Σ(Wj·hj^k)  |  <b>§6.5</b> Deflection scale kd (Table 6-1)",
            "<b>§3.6</b> LSM combos: 1.2DL+1.5LL; DL+λLL±E; 0.9DL±E  |  <b>§3.7</b> WSM: DL+λLL±0.7E  |  <b>§3.8</b> SBC +50%",
            "<b>Design note (app)</b> Story seismic weight input uses Wi = DL + λ·LL with λ=0.30 for all stories and λ=0.00 at top story.",
            "<b>§10</b> Parts: Fp = Cd(T)·Cp·(1+z/H)·Ip/μp·Wp  |  Annex A: Ductile RC detailing",
        ]
        refs.setHtml("<small>" + "<br>".join(ref_lines) + "</small>")

        lay.addWidget(refs)
        return g

    def _safe_float(self, item: QTableWidgetItem | None) -> float:
        if item is None:
            return 0.0
        txt = item.text().strip()
        if not txt:
            return 0.0
        try:
            return max(float(txt), 0.0)
        except ValueError:
            return 0.0

    def _live_load_factor_from_row(self, row: int) -> float:
        # App rule per user requirement:
        # all stories λ = 0.30, top story λ = 0.00
        last_story_row = self._floor_weights_input.rowCount() - 1
        return 0.00 if row == last_story_row else 0.30

    def _normalize_numeric_input(self, row: int, col: int) -> None:
        item = self._floor_weights_input.item(row, col)
        if item is None:
            return
        txt = item.text().strip()
        if not txt:
            return
        try:
            value = max(float(txt), 0.0)
            item.setText(f"{value:g}")
        except ValueError:
            item.setText("")

    def _update_floor_weight_row(self, row: int) -> None:
        t = self._floor_weights_input
        if row <= 0 or row >= t.rowCount():
            return

        dl = self._safe_float(t.item(row, 1))
        ll = self._safe_float(t.item(row, 2))
        lam = self._live_load_factor_from_row(row)
        wi = dl + lam * ll

        t.blockSignals(True)
        lam_item = t.item(row, 3)
        if lam_item is None:
            lam_item = QTableWidgetItem(f"{lam:.2f}")
            lam_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            lam_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            t.setItem(row, 3, lam_item)
        else:
            lam_item.setText(f"{lam:.2f}")

        wi_item = t.item(row, 4)
        if wi_item is None:
            wi_item = QTableWidgetItem(f"{wi:.2f}")
            wi_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            wi_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            t.setItem(row, 4, wi_item)
        else:
            wi_item.setText(f"{wi:.2f}")
        t.blockSignals(False)

    def _on_floor_weight_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() not in (1, 2):
            return
        row = item.row()
        self._floor_weights_input.blockSignals(True)
        self._normalize_numeric_input(row, item.column())
        self._floor_weights_input.blockSignals(False)
        self._update_floor_weight_row(row)

    def _sync_floor_weight_rows(self, num_stories: int) -> None:
        t = self._floor_weights_input

        existing_rows: list[tuple[str, str]] = []
        for r in range(1, t.rowCount()):
            dl_item = t.item(r, 1)
            ll_item = t.item(r, 2)
            existing_rows.append((
                dl_item.text().strip() if dl_item else "",
                ll_item.text().strip() if ll_item else "",
            ))

        t.blockSignals(True)
        t.setRowCount(num_stories + 1)  # +1 for Ground Floor row

        # Ground floor: fixed blank and unwritable
        gf_level = QTableWidgetItem("Ground Floor")
        gf_level.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        gf_level.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        t.setItem(0, 0, gf_level)

        for c in (1, 2, 3, 4):
            gf_item = QTableWidgetItem("")
            gf_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            t.setItem(0, c, gf_item)

        for r in range(1, num_stories + 1):
            prev_dl, prev_ll = (existing_rows[r - 1] if (r - 1) < len(existing_rows)
                                else ("", ""))

            level_item = QTableWidgetItem(f"Story {r}")
            level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            level_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            t.setItem(r, 0, level_item)

            dl_item = QTableWidgetItem(prev_dl)
            dl_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setItem(r, 1, dl_item)

            ll_item = QTableWidgetItem(prev_ll)
            ll_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setItem(r, 2, ll_item)

            lam_item = QTableWidgetItem("0.30")
            lam_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            lam_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            t.setItem(r, 3, lam_item)

            wi_item = QTableWidgetItem("0.00")
            wi_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            wi_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            t.setItem(r, 4, wi_item)

        t.blockSignals(False)
        for r in range(1, num_stories + 1):
            self._update_floor_weight_row(r)

    def set_floor_weights(self, weights: list[float]) -> None:
        t = self._floor_weights_input
        for r in range(1, t.rowCount()):
            wi = float(weights[r - 1]) if (r - 1) < len(weights) else 0.0
            dl_item = t.item(r, 1)
            if dl_item is None:
                dl_item = QTableWidgetItem("")
                dl_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                t.setItem(r, 1, dl_item)
            dl_item.setText(f"{max(wi, 0.0):g}")

            ll_item = t.item(r, 2)
            if ll_item is None:
                ll_item = QTableWidgetItem("")
                ll_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                t.setItem(r, 2, ll_item)
            ll_item.setText("0")

            self._update_floor_weight_row(r)


    def _setup_zone_combo(self) -> None:

        zone_combo: QComboBox = self.inputs["zone"]
        zone_combo.setEditable(True)
        zone_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        zone_combo.lineEdit().setPlaceholderText("Search municipality (e.g., Lalitpur)")
        zone_combo.setToolTip("Type to search municipality/local unit (case-insensitive).")

        completer = QCompleter(zone_combo.model(), zone_combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        zone_combo.setCompleter(completer)

        default_zone = "Lalitpur Mahanagarpalika"
        default_idx = zone_combo.findText(default_zone, Qt.MatchFlag.MatchFixedString)
        if default_idx >= 0:
            zone_combo.setCurrentIndex(default_idx)

    def _resolve_zone_name(self, text: str) -> str:
        zone_combo: QComboBox = self.inputs["zone"]
        query = text.strip()

        if not query:
            return zone_combo.currentText()

        # Exact (case-sensitive) match
        idx = zone_combo.findText(query, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            zone_combo.setCurrentIndex(idx)
            return zone_combo.itemText(idx)

        # Exact (case-insensitive) match
        ql = query.lower()
        for i in range(zone_combo.count()):
            item = zone_combo.itemText(i)
            if item.lower() == ql:
                zone_combo.setCurrentIndex(i)
                return item

        # Prefix and contains fallback for typed search text
        for i in range(zone_combo.count()):
            item = zone_combo.itemText(i)
            if item.lower().startswith(ql):
                zone_combo.setCurrentIndex(i)
                return item

        for i in range(zone_combo.count()):
            item = zone_combo.itemText(i)
            if ql in item.lower():
                zone_combo.setCurrentIndex(i)
                return item

        return zone_combo.currentText()

    # ── Public API ─────────────────────────────────────────────────────────────
    def get_params(self) -> dict:
        # Parse seismic floor weights Wi from auto-calculated table column
        floor_weights: list[float] = []
        num_stories = self.inputs["num_stories"].value()

        for r in range(1, self._floor_weights_input.rowCount()):
            self._update_floor_weight_row(r)
            wi_item = self._floor_weights_input.item(r, 4)

            floor_weights.append(self._safe_float(wi_item))

        if len(floor_weights) < num_stories:
            floor_weights.extend([0.0] * (num_stories - len(floor_weights)))

        return {
            "zone_name":     self._resolve_zone_name(self.inputs["zone"].currentText()),
            "method":        self.inputs["method"].currentText(),
            "imp_name":      self.inputs["importance"].currentText(),
            "soil_type":     self.inputs["soil"].currentText(),
            "H":             self.inputs["H"].text(),
            "num_stories":   num_stories,
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
            self._fit_table_height_to_rows(t)


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
