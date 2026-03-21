"""
ui/tabs/load_tab.py
────────────────────
IS 875 load calculation tab: live loads, wall dead loads, slab dead loads.
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QGroupBox, QLabel,
    QComboBox, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QSizePolicy,
)
from PyQt6.QtCore import Qt
from constants import LIVE_LOAD_DATA
from ui.widgets import UnitLineEdit


class LoadTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wall_inputs:  dict[str, QLineEdit] = {}
        self.slab_inputs:  dict[str, QLineEdit] = {}
        self.slab_outputs: dict[str, QLabel]    = {}
        self._build_ui()
        self._set_defaults()

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(10, 15, 10, 15)
        main.setSpacing(20)
        main.addWidget(self._build_live_load_group())
        main.addWidget(self._build_wall_load_group())
        main.addWidget(self._build_slab_load_group())
        main.addStretch()

    # ── Live Load ─────────────────────────────────────────────────────────────
    def _build_live_load_group(self) -> QGroupBox:
        group = QGroupBox("Live Load Reference (IS 875 Part 2)")
        main  = QVBoxLayout(group)

        input_grp    = QGroupBox("Select Occupancy and Use")
        input_layout = QGridLayout(input_grp)

        self.ll_cat1 = QComboBox()
        self.ll_cat2 = QComboBox()
        input_layout.addWidget(QLabel("1. Main Occupancy Type:"), 0, 0)
        input_layout.addWidget(self.ll_cat1, 0, 1)
        input_layout.addWidget(QLabel("2. Sub-Category:"), 1, 0)
        input_layout.addWidget(self.ll_cat2, 1, 1)
        input_layout.setColumnStretch(1, 1)

        result_grp    = QGroupBox("Available Imposed Loads")
        result_layout = QVBoxLayout(result_grp)
        self.ll_tree  = QTreeWidget()
        self.ll_tree.setAlternatingRowColors(True)
        self.ll_tree.setHeaderLabels(
            ["Specific Use / Area", "UDL [kN/m²]", "Concentrated Load [kN]"]
        )
        self.ll_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ll_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.ll_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.ll_tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        result_layout.addWidget(self.ll_tree)

        main.addWidget(input_grp)
        main.addWidget(result_grp)

        self.ll_cat1.addItems(LIVE_LOAD_DATA.keys())
        self.ll_cat1.currentTextChanged.connect(self._update_ll_cat2)
        self.ll_cat2.currentTextChanged.connect(self._update_ll_results)
        return group

    def _update_ll_cat2(self, text: str) -> None:
        self.ll_cat2.blockSignals(True)
        self.ll_cat2.clear()
        if text in LIVE_LOAD_DATA:
            self.ll_cat2.addItems(LIVE_LOAD_DATA[text].keys())
        self.ll_cat2.blockSignals(False)
        self._update_ll_results(self.ll_cat2.currentText())

    def _update_ll_results(self, sub: str) -> None:
        self.ll_tree.clear()
        cat1 = self.ll_cat1.currentText()
        if not cat1 or not sub:
            return
        try:
            uses = LIVE_LOAD_DATA[cat1][sub]
        except KeyError:
            return
        for use, loads in uses.items():
            udl = loads.get("udl")
            cl  = loads.get("cl")
            udl_t = str(udl) if isinstance(udl, str) else (f"{udl:.2f}" if udl is not None else "--")
            cl_t  = str(cl)  if isinstance(cl,  str) else (f"{cl:.2f}"  if cl  is not None else "--")
            item = QTreeWidgetItem([use, udl_t, cl_t])
            for i in range(3):
                item.setTextAlignment(i, Qt.AlignmentFlag.AlignCenter)
            self.ll_tree.addTopLevelItem(item)
        # Resize tree to content height
        n = self.ll_tree.topLevelItemCount()
        if n > 0:
            rh = self.ll_tree.sizeHintForRow(0)
            hh = self.ll_tree.header().height()
            self.ll_tree.setFixedHeight(hh + rh * n + 4)

    # ── Wall Line Load ────────────────────────────────────────────────────────
    def _build_wall_load_group(self) -> QGroupBox:
        group = QGroupBox("Wall Dead Load (IS 875 Part 1)")
        main  = QVBoxLayout(group)

        input_grp    = QGroupBox("Input Parameters")
        input_layout = QGridLayout(input_grp)
        input_layout.setVerticalSpacing(12)

        def add_entry(label, key, row, col, default, unit=None):
            w = UnitLineEdit(unit, default) if unit else QLineEdit(default)
            self.wall_inputs[key] = w
            input_layout.addWidget(QLabel(label), row, col)
            input_layout.addWidget(w, row, col + 1)

        add_entry("Floor-to-Floor Height [m]:",   "f2f_h",   0, 0, "3.023", "m")
        add_entry("Beam Depth [m]:",               "beam_d",  1, 0, "0.356", "m")
        add_entry("Slab Thickness [m]:",           "slab_t",  2, 0, "0.127", "m")
        add_entry("Parapet Wall Height [m]:",      "parapet", 3, 0, "1.000", "m")
        add_entry("Full Brick Thickness [m]:",     "full_t",  0, 2, "0.230", "m")
        add_entry("Half Brick Thickness [m]:",     "half_t",  1, 2, "0.115", "m")
        add_entry("Unit Weight of Masonry [kN/m³]:", "unit_w", 2, 2, "19.2")
        add_entry("Opening Percentage [%]:",       "opening", 3, 2, "30")

        output_grp    = QGroupBox("Calculated Line Loads")
        output_layout = QVBoxLayout(output_grp)
        self.wall_tree = QTreeWidget()
        self.wall_tree.setAlternatingRowColors(True)
        self.wall_tree.setHeaderLabels(
            ["Wall Description", "Load w/o Opening [kN/m]", "Load with Opening [kN/m]"]
        )
        self.wall_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.wall_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.wall_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.wall_tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        output_layout.addWidget(self.wall_tree)

        main.addWidget(input_grp)
        main.addWidget(output_grp)

        for w in self.wall_inputs.values():
            w.textChanged.connect(self.recalculate_wall_loads)
        return group

    # ── Slab / Misc Dead Loads ─────────────────────────────────────────────────
    def _build_slab_load_group(self) -> QGroupBox:
        group = QGroupBox("Slab & Miscellaneous Dead Loads (IS 875 Part 1)")
        main  = QVBoxLayout(group)

        def make_sub(title: str, entries: list, out_key: str) -> QGroupBox:
            g = QGroupBox(title)
            gl = QGridLayout(g)
            for i, (lbl_text, key, default, *rest) in enumerate(entries):
                unit = rest[0] if rest else None
                w = UnitLineEdit(unit, default) if unit else QLineEdit(default)
                self.slab_inputs[key] = w
                w.textChanged.connect(self._recalculate_slab_loads)
                gl.addWidget(QLabel(lbl_text), i, 0)
                gl.addWidget(w, i, 1)
            out_lbl = QLabel("--")
            out_lbl.setStyleSheet("font-weight: bold;")
            self.slab_outputs[out_key] = out_lbl
            gl.addWidget(QLabel("<b>Equivalent Load [kN/m²]:</b>"), len(entries), 0)
            gl.addWidget(out_lbl, len(entries), 1)
            main.addWidget(g)
            return g

        make_sub("(i) Floor Finish Load", [
            ("Screeding Thickness [mm]:",          "screed_t",  "50",   "mm"),
            ("Ceiling Plaster Thickness [mm]:",    "plaster_t", "12.5", "mm"),
            ("Unit Weight of Screed/Plaster [kN/m³]:", "screed_w", "20"),
            ("Additional Flooring Load [kN/m²]:",  "floor_w",   "0.22"),
        ], "ff_total")

        make_sub("(ii) Water Tank Load", [
            ("Water Tank Capacity [Litres]:",      "tank_cap",  "1000"),
            ("Slab Area Supporting Tank [m²]:",    "tank_area", "9.61", "m"),
        ], "wt_total")

        make_sub("(iii) Partition Wall on Slab", [
            ("Partition Wall Thickness [m]:",      "part_t",    "0.115", "m"),
            ("Partition Wall Height [m]:",         "part_h",    "2.896", "m"),
            ("Partition Wall Length [m]:",         "part_l",    "2.190", "m"),
            ("Slab Area Supporting Wall [m²]:",    "part_area", "8.010", "m"),
            ("Unit Weight of Wall [kN/m³]:",       "part_w",    "19.2"),
        ], "pw_total")

        return group

    # ── Calculations ──────────────────────────────────────────────────────────
    def recalculate_wall_loads(self) -> None:
        try:
            v = {k: float(w.text()) for k, w in self.wall_inputs.items()}
        except ValueError:
            self.wall_tree.clear()
            return

        h_beam  = v["f2f_h"] - v["beam_d"]
        h_slab  = v["f2f_h"] - v["slab_t"]
        op_fac  = 1.0 - v["opening"] / 100.0

        rows = [
            (f"{v['full_t']*1000:.0f}mm Wall on Beam (H={h_beam:.3f}m)",
             h_beam * v["full_t"] * v["unit_w"]),
            (f"{v['half_t']*1000:.0f}mm Wall on Beam (H={h_beam:.3f}m)",
             h_beam * v["half_t"] * v["unit_w"]),
            (f"{v['full_t']*1000:.0f}mm Wall on Slab (H={h_slab:.3f}m)",
             h_slab * v["full_t"] * v["unit_w"]),
            (f"{v['half_t']*1000:.0f}mm Wall on Slab (H={h_slab:.3f}m)",
             h_slab * v["half_t"] * v["unit_w"]),
            (f"Parapet Wall (H={v['parapet']:.2f}m)",
             v["parapet"] * v["half_t"] * v["unit_w"]),
        ]
        self.wall_tree.clear()
        for desc, load in rows:
            with_op = "N/A" if "Parapet" in desc else f"{load * op_fac:.3f}"
            item = QTreeWidgetItem([desc, f"{load:.3f}", with_op])
            for i in range(3):
                item.setTextAlignment(i, Qt.AlignmentFlag.AlignCenter)
            self.wall_tree.addTopLevelItem(item)

        n = self.wall_tree.topLevelItemCount()
        if n:
            rh = self.wall_tree.sizeHintForRow(0)
            hh = self.wall_tree.header().height()
            self.wall_tree.setFixedHeight(hh + rh * n + 4)

    def _recalculate_slab_loads(self) -> None:
        si = self.slab_inputs
        outs = self.slab_outputs

        def _f(k: str) -> float:
            return float(si[k].text())

        # (i) Floor finish
        try:
            ff = (_f("screed_t") / 1000 * _f("screed_w") +
                  _f("plaster_t") / 1000 * _f("screed_w") +
                  _f("floor_w"))
            outs["ff_total"].setText(f"{ff:.3f}")
        except ValueError:
            outs["ff_total"].setText("--")

        # (ii) Water tank
        try:
            wt = (_f("tank_cap") / 1000 * 9.81) / _f("tank_area")
            outs["wt_total"].setText(f"{wt:.3f}")
        except (ValueError, ZeroDivisionError):
            outs["wt_total"].setText("--")

        # (iii) Partition wall
        try:
            pw = (_f("part_t") * _f("part_h") * _f("part_l") * _f("part_w")) / _f("part_area")
            outs["pw_total"].setText(f"{pw:.3f}")
        except (ValueError, ZeroDivisionError):
            outs["pw_total"].setText("--")

    # ── Defaults ──────────────────────────────────────────────────────────────
    def _set_defaults(self) -> None:
        self.ll_cat1.setCurrentText("Residential Buildings")
        self._update_ll_cat2("Residential Buildings")
        self.ll_cat2.setCurrentText("Dwelling houses")
        self.recalculate_wall_loads()
        self._recalculate_slab_loads()
