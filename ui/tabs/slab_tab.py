"""
ui/tabs/slab_tab.py
────────────────────
IS 456:2000 two-way slab design tab.
"""
from __future__ import annotations
import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QGroupBox, QLabel,
    QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QMessageBox,
)


from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from constants import SLAB_MOMENT_COEFFICIENTS, SHEAR_STRENGTH_CONCRETE, DEFLECTION_KT_DATA
from ui.widgets import UnitLineEdit


def _interp(x: float, xs: list, ys: list) -> float:
    if x <= xs[0]:  return ys[0]
    if x >= xs[-1]: return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            return ys[i] + (ys[i+1] - ys[i]) * (x - xs[i]) / (xs[i+1] - xs[i])
    return ys[-1]


class SlabTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.inputs: dict = {}
        self.summary: dict = {}
        # cached calc state
        self._d_x = self._d_y = self._wu = self._ast_min = 0.0
        self._dia = 8
        self._fck = 20
        self._fy  = 500
        self._lx  = 3.5
        self._D   = 125.0
        self.ast_results: dict = {}
        self.spacing_round_base: int = 5
        self._input_warning_state: str = ""

        self._build_ui()
        self._set_defaults()

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(10, 15, 10, 15)
        main.setSpacing(12)
        main.addWidget(self._build_input_group())
        main.addWidget(self._build_summary_group())
        main.addWidget(self._build_results_group())
        main.addWidget(self._build_checks_group())
        main.addWidget(self._build_notes_group())
        main.addStretch()


    def _build_input_group(self) -> QGroupBox:
        group  = QGroupBox("Input Parameters")
        layout = QGridLayout(group)
        layout.setVerticalSpacing(12)

        def add(label, key, widget, row, col):
            self.inputs[key] = widget
            layout.addWidget(QLabel(label), row, col)
            layout.addWidget(widget, row, col + 1)

        add("Short Span Lx [m]:",        "lx",      UnitLineEdit("m"),  0, 0)
        add("Long Span Ly [m]:",         "ly",      UnitLineEdit("m"),  1, 0)
        add("Live Load [kN/m²]:",        "ll",      QLineEdit(),        2, 0)
        add("Floor Finish [kN/m²]:",     "ff",      QLineEdit(),        3, 0)
        add("Trial Overall Depth D [mm]:","d_trial", UnitLineEdit("mm"), 4, 0)

        fck_w = QComboBox(); fck_w.addItems(["20","25","30","35"])
        fy_w  = QComboBox(); fy_w.addItems(["250","415","500"])
        dia_w = QComboBox(); dia_w.addItems(["8","10","12","16"])
        sup_w = QComboBox(); sup_w.addItems(list(SLAB_MOMENT_COEFFICIENTS.keys()))
        cov_w = UnitLineEdit("mm")

        add("Concrete Grade fck [MPa]:", "fck",     fck_w, 0, 2)
        add("Steel Grade fy [MPa]:",     "fy",      fy_w,  1, 2)
        add("Clear Cover [mm]:",         "cover",   cov_w, 2, 2)
        add("Main Bar Diameter [mm]:",   "dia",     dia_w, 3, 2)
        layout.addWidget(QLabel("Support Condition:"), 5, 0)
        layout.addWidget(sup_w, 5, 1, 1, 3)
        self.inputs["support"] = sup_w

        for w in self.inputs.values():
            sig = w.currentTextChanged if isinstance(w, QComboBox) else w.textChanged
            sig.connect(self._on_input_changed)
        return group

    def _build_summary_group(self) -> QGroupBox:
        group  = QGroupBox("Design Summary")
        layout = QGridLayout(group)
        for col, (key, text) in enumerate([
            ("ratio",  "Ly/Lx Ratio:"),
            ("d_eff",  "Effective Depth d [mm]:"),
            ("wu",     "Factored Load wu [kN/m²]:"),
            ("astmin", "Ast,min [mm²]:"),
        ]):
            layout.addWidget(QLabel(text), 0, col * 2)
            lbl = QLabel("--")
            lbl.setStyleSheet("font-weight: bold;")
            self.summary[key] = lbl
            layout.addWidget(lbl, 0, col * 2 + 1)
        return group

    def _build_results_group(self) -> QGroupBox:
        group  = QGroupBox("Moment and Reinforcement")
        layout = QVBoxLayout(group)
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(11)
        self.result_table.setHorizontalHeaderLabels([
            "Span", "Moment Type", "α", "Mu\nkN·m", "Mu/bd²\nN/mm²",
            "Pt%", "Ast req\nmm²", "Ast min\nmm²", "Dia\nmm", "Spacing\nmm", "Ast prov\nmm²",
        ])
        self.result_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.result_table.cellChanged.connect(self._on_spacing_changed)
        layout.addWidget(self.result_table)
        return group

    def _build_checks_group(self) -> QGroupBox:
        group  = QGroupBox("Final Safety Checks")
        layout = QVBoxLayout(group)
        self.checks_table = QTableWidget()
        self.checks_table.setColumnCount(3)
        self.checks_table.setHorizontalHeaderLabels(["Check", "Detail", "Status"])
        self.checks_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.checks_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.checks_table)
        return group

    def _build_notes_group(self) -> QGroupBox:
        group = QGroupBox("Design Notes & Recommendations")
        layout = QVBoxLayout(group)
        self.notes_box = QTextEdit()
        self.notes_box.setReadOnly(True)
        self.notes_box.setMinimumHeight(110)
        self.notes_box.setHtml("<small>Enter slab inputs to generate detailing recommendations.</small>")
        layout.addWidget(self.notes_box)
        return group


    # ── Defaults ──────────────────────────────────────────────────────────────
    def _set_defaults(self) -> None:
        self.inputs["lx"].setText("3.5")
        self.inputs["ly"].setText("4.5")
        self.inputs["ll"].setText("2.0")
        self.inputs["ff"].setText("1.5")
        self.inputs["d_trial"].setText("125")
        self.inputs["cover"].setText("20")
        self.inputs["fck"].setCurrentText("20")
        self.inputs["fy"].setCurrentText("500")
        self.inputs["dia"].setCurrentText("8")
        self.inputs["support"].setCurrentText("Two adjacent edges discontinuous")
        self.calculate()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_text(self, key: str) -> str:
        w = self.inputs[key]
        return w.currentText() if isinstance(w, QComboBox) else w.text()

    def _set_cell(self, table: QTableWidget, row: int, col: int,
                  text: str, bold: bool = False, color: str | None = None) -> None:
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        if bold:
            f = QFont(); f.setBold(True); item.setFont(f)
        if color:
            item.setForeground(QColor(color))
        table.setItem(row, col, item)

    def _resize(self, table: QTableWidget) -> None:
        table.resizeRowsToContents()
        h = table.horizontalHeader().height()
        h += sum(table.rowHeight(r) for r in range(table.rowCount())) + (table.frameWidth() * 2) + 4
        table.setFixedHeight(max(70, h))


    def _get_coeffs(self, support: str, ratio: float) -> dict:
        data = SLAB_MOMENT_COEFFICIENTS.get(support, {})

        def resolve(key):
            v = data.get(key)
            if v is None:
                return None
            if isinstance(v, dict):
                xs = [k for k, val in v.items() if val is not None]
                ys = [val for val in v.values() if val is not None]
                return _interp(ratio, xs, ys)
            return float(v)

        return {
            "ax_neg": resolve("alpha_x_neg"),
            "ax_pos": resolve("alpha_x_pos"),
            "ay_neg": resolve("alpha_y_neg"),
            "ay_pos": resolve("alpha_y_pos"),
        }

    # ── Main Calculation ──────────────────────────────────────────────────────
    def _on_input_changed(self) -> None:
        self.calculate()

    def calculate(self) -> None:
        self.result_table.blockSignals(True)
        try:
            lx      = float(self._get_text("lx"))
            ly      = float(self._get_text("ly"))
            D       = float(self._get_text("d_trial"))
            fck     = int(self._get_text("fck"))
            fy      = int(self._get_text("fy"))
            ll      = float(self._get_text("ll"))
            ff      = float(self._get_text("ff"))
            cover   = float(self._get_text("cover"))
            dia     = int(self._get_text("dia"))
            support = self._get_text("support")

            # Input validity for two-way slab tab
            ratio = ly / lx
            invalid_reason = ""
            if lx > ly:
                invalid_reason = "Lx should be the shorter span. Please enter values with Lx ≤ Ly."
            elif ratio > 2.0:
                invalid_reason = "Ly/Lx > 2.0 indicates one-way slab behavior. This tab is for two-way slabs only."

            if invalid_reason:
                self.summary["ratio"].setText(f"{ratio:.3f}")
                self.summary["d_eff"].setText("--")
                self.summary["wu"].setText("--")
                self.summary["astmin"].setText("--")
                self.result_table.setRowCount(0)
                self.checks_table.setRowCount(0)
                self.notes_box.setHtml(f"<small><b>Warning:</b> {invalid_reason}</small>")
                if self._input_warning_state != invalid_reason:
                    QMessageBox.warning(self, "Slab Input Warning", invalid_reason)
                    self._input_warning_state = invalid_reason
                return

            self._input_warning_state = ""

            # Cache
            self._lx, self._D, self._fck, self._fy, self._dia = lx, D, fck, fy, dia

            d_x = D - cover - dia / 2.0

            d_y = d_x - dia
            wu  = 1.5 * (D / 1000 * 25.0 + ff + ll)
            ast_min = (0.0012 if fy > 250 else 0.0015) * 1000 * D
            # IS 456 §38.1: xu_max/d = 0.48 for Fe415/Fe500, 0.53 for Fe250
            xu_frac = 0.53 if fy <= 250 else 0.48
            mu_lim_x = 0.36 * fck * 1000 * (xu_frac * d_x) * (d_x - 0.42 * xu_frac * d_x) / 1e6
            mu_lim_y = 0.36 * fck * 1000 * (xu_frac * d_y) * (d_y - 0.42 * xu_frac * d_y) / 1e6

            self._d_x, self._d_y = d_x, d_y
            self._wu, self._ast_min = wu, ast_min

            self.summary["ratio"].setText(f"{ly/lx:.3f}")
            self.summary["d_eff"].setText(f"{d_x:.1f}")
            self.summary["wu"].setText(f"{wu:.2f}")
            self.summary["astmin"].setText(f"{ast_min:.2f}")

            coeffs = self._get_coeffs(support, ly / lx)
            self.result_table.setRowCount(4)

            # Span label spanning 2 rows
            for span_text, row_start in [("Shorter (Main)", 0), ("Longer (Dist.)", 2)]:
                item = QTableWidgetItem(span_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                f = QFont(); f.setBold(True); item.setFont(f)
                self.result_table.setSpan(row_start, 0, 2, 1)
                self.result_table.setItem(row_start, 0, item)

            self.ast_results = {}
            cases = [
                ("x_neg", 0, "Support (−ve)", coeffs["ax_neg"], d_x, mu_lim_x, False),
                ("x_pos", 1, "Mid-span (+ve)", coeffs["ax_pos"], d_x, mu_lim_x, False),
                ("y_neg", 2, "Support (−ve)", coeffs["ay_neg"], d_y, mu_lim_y, True),
                ("y_pos", 3, "Mid-span (+ve)", coeffs["ay_pos"], d_y, mu_lim_y, True),
            ]

            for key, row, m_type, alpha, d_eff, mu_lim, is_dist in cases:
                self._set_cell(self.result_table, row, 1, m_type)
                if alpha is None:
                    for c in range(2, 11):
                        self._set_cell(self.result_table, row, c, "–")
                    self.ast_results[key] = {"req": 0.0, "prov": 0.0}
                    continue

                mu     = alpha * wu * lx**2
                mu_bd2 = (mu * 1e6) / (1000 * d_eff**2)

                if mu > mu_lim:
                    self._set_cell(self.result_table, row, 2, f"{alpha:.3f}")
                    self._set_cell(self.result_table, row, 3, f"{mu:.2f}")
                    for c in range(4, 11):
                        self._set_cell(self.result_table, row, c, "Revise Depth", color="#C62828")
                    self.ast_results[key] = {"req": 0.0, "prov": 0.0}
                    continue

                # Quadratic for xu
                Mu_Nmm = mu * 1e6
                a_q = -0.36 * 0.42 * fck * 1000
                b_q =  0.36 * fck * 1000 * d_eff
                c_q = -Mu_Nmm
                disc = b_q**2 - 4*a_q*c_q
                if disc < 0:
                    self.ast_results[key] = {"req": 0.0, "prov": 0.0}
                    continue
                candidates = [x for x in ((-b_q + disc**0.5)/(2*a_q),
                                           (-b_q - disc**0.5)/(2*a_q)) if x > 0]
                xu = min(candidates) if candidates else 0.48 * d_eff
                xu = min(xu, 0.48 * d_eff)
                z  = d_eff - 0.42 * xu
                ast_req = max(Mu_Nmm / (0.87 * fy * z), ast_min) if z > 0 else ast_min

                area_bar  = math.pi * dia**2 / 4.0
                max_sp    = min(5*d_eff, 450) if is_dist else min(3*d_eff, 300)
                sp_raw    = min((area_bar * 1000) / ast_req, max_sp)
                sp_prov   = self._round_spacing(sp_raw)
                sp_prov   = max(75, sp_prov)
                ast_prov  = (area_bar * 1000) / sp_prov

                self.ast_results[key] = {"req": ast_req, "prov": ast_prov}

                self._set_cell(self.result_table, row, 2, f"{alpha:.3f}")
                self._set_cell(self.result_table, row, 3, f"{mu:.2f}")
                self._set_cell(self.result_table, row, 4, f"{mu_bd2:.2f}")
                self._set_cell(self.result_table, row, 5, f"{100*ast_req/(1000*d_eff):.3f}%")
                self._set_cell(self.result_table, row, 6, f"{ast_req:.2f}")
                self._set_cell(self.result_table, row, 7, f"{ast_min:.2f}")
                self._set_cell(self.result_table, row, 8, str(dia))

                sp_item = QTableWidgetItem(str(sp_prov))
                sp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                sp_item.setFlags(Qt.ItemFlag.ItemIsSelectable |
                                  Qt.ItemFlag.ItemIsEnabled |
                                  Qt.ItemFlag.ItemIsEditable)
                sp_item.setToolTip(f"Max allowed: {int(max_sp)} mm")
                self.result_table.setItem(row, 9, sp_item)
                self._set_cell(self.result_table, row, 10, f"{ast_prov:.2f}")

            self._run_checks(support, ly/lx, lx, wu, fck, fy, d_x, D)

        except (ValueError, ZeroDivisionError, TypeError, KeyError):
            self.result_table.setRowCount(0)
            self.checks_table.setRowCount(0)
            self.notes_box.setHtml("<small>Enter valid slab inputs to generate design notes.</small>")
        finally:

            self.result_table.blockSignals(False)
            self._resize(self.result_table)
            self._resize(self.checks_table)

    def _on_spacing_changed(self, row: int, col: int) -> None:
        if col != 9:
            return
        self.result_table.blockSignals(True)
        try:
            key  = ["x_neg", "x_pos", "y_neg", "y_pos"][row]
            is_dist = row >= 2
            d_eff   = self._d_y if is_dist else self._d_x
            sp      = int(self.result_table.item(row, 9).text())
            max_sp  = int(min(5*d_eff, 450) if is_dist else min(3*d_eff, 300))
            sp      = min(max(sp, 75), max_sp)
            self.result_table.item(row, 9).setText(str(sp))
            area_bar = math.pi * self._dia**2 / 4.0
            ast_prov = (area_bar * 1000) / sp
            self.ast_results.setdefault(key, {})["prov"] = ast_prov
            self._set_cell(self.result_table, row, 5,
                           f"{100*ast_prov/(1000*d_eff):.3f}%")
            self._set_cell(self.result_table, row, 10, f"{ast_prov:.2f}")
            self._run_checks(
                self._get_text("support"),
                float(self._get_text("ly")) / float(self._get_text("lx")),
                float(self._get_text("lx")), self._wu,
                self._fck, self._fy, self._d_x, self._D,
            )
        except (ValueError, KeyError, TypeError):
            pass
        finally:
            self.result_table.blockSignals(False)

    def _spacing_value(self, row: int) -> int | None:
        it = self.result_table.item(row, 9)
        if not it:
            return None
        try:
            return int(float(it.text()))
        except (ValueError, TypeError):
            return None

    def _update_design_notes(self, ratio: float, support: str) -> None:
        dia = self._dia
        main_support_sp = self._spacing_value(0)
        main_mid_sp = self._spacing_value(1)
        dist_support_sp = self._spacing_value(2)
        dist_mid_sp = self._spacing_value(3)

        deflection_status = self.checks_table.item(3, 2).text() if self.checks_table.item(3, 2) else ""
        span_status = self.checks_table.item(4, 2).text() if self.checks_table.item(4, 2) else ""
        twoway_status = self.checks_table.item(5, 2).text() if self.checks_table.item(5, 2) else ""

        lines = [
            "<b>Recommended reinforcement layout (two-way slab):</b>",
            "<ul>",
            f"<li><b>Main bar (short span / Lx):</b> Ø{dia} mm @ {main_mid_sp or '—'} mm c/c at mid-span, and Ø{dia} mm @ {main_support_sp or '—'} mm c/c over supports.</li>",
            f"<li><b>Longitudinal / distribution bar (long span / Ly):</b> Ø{dia} mm @ {dist_mid_sp or '—'} mm c/c at mid-span, and Ø{dia} mm @ {dist_support_sp or '—'} mm c/c over supports.</li>",
            f"<li><b>Support condition considered:</b> {support}</li>",
            f"<li><b>Span ratio check:</b> Ly/Lx = {ratio:.3f} (valid two-way range: 1.0 to 2.0)</li>",
            "</ul>",
        ]

        if "Increase D to" in deflection_status:
            lines.append(f"<p><b>Deflection recommendation:</b> {deflection_status}</p>")
        if "⚠" in span_status:
            lines.append(f"<p><b>Input warning:</b> {span_status}</p>")
        if "⚠" in twoway_status:
            lines.append(f"<p><b>Applicability warning:</b> {twoway_status}</p>")

        lines.append("<p><small>Detailing and anchorage must satisfy IS 456 ductility and spacing provisions.</small></p>")
        self.notes_box.setHtml("".join(lines))

    def _run_checks(self, support: str, ratio: float, lx: float,
                    wu: float, fck: int, fy: int, d_x: float, D: float) -> None:
        self.checks_table.setRowCount(6)


        # 1 Moment capacity

        mus = [float(self.result_table.item(r, 3).text())
               for r in range(4)
               if self.result_table.item(r, 3)
               and self.result_table.item(r, 3).text() not in ("–", "Revise Depth", "--")]
        max_mu  = max(mus, default=0.0)
        xu_frac = 0.53 if fck <= 250 else 0.48   # use fy not fck
        xu_frac = 0.53 if fy <= 250 else 0.48
        mu_lim  = 0.36 * fck * 1000 * (xu_frac * d_x) * (d_x - 0.42 * xu_frac * d_x) / 1e6
        ok      = max_mu <= mu_lim
        self._set_cell(self.checks_table, 0, 0, "Moment Capacity")
        self._set_cell(self.checks_table, 0, 1, f"Mu,max={max_mu:.2f} ≤ Mu,lim={mu_lim:.2f} kN·m")
        self._set_cell(self.checks_table, 0, 2, "✓ OK" if ok else "✗ Revise Section",
                        color="#2E7D32" if ok else "#C62828")

        # 2 Minimum steel
        ax = self.ast_results.get("x_pos", {}).get("prov", 0.0)
        ay = self.ast_results.get("y_pos", {}).get("prov", 0.0)
        ok2 = min(ax, ay) >= self._ast_min
        self._set_cell(self.checks_table, 1, 0, "Minimum Steel")
        self._set_cell(self.checks_table, 1, 1,
                        f"Ast,min={self._ast_min:.1f}, Ast,x={ax:.1f}, Ast,y={ay:.1f} mm²")
        self._set_cell(self.checks_table, 1, 2, "✓ OK" if ok2 else "✗ Increase Steel",
                        color="#2E7D32" if ok2 else "#C62828")

        # 3 Shear
        Vu    = 0.5 * wu * lx
        tau_v = (Vu * 1000) / (1000 * d_x)
        pt    = min(100 * ax / (1000 * d_x), 3.0)
        tc_d  = SHEAR_STRENGTH_CONCRETE.get(fck, SHEAR_STRENGTH_CONCRETE[20])
        tau_c = _interp(pt, list(tc_d.keys()), list(tc_d.values()))
        k_fac = 1.3 if D <= 150 else max(1.0, 1.3 - 0.6*(D-150)/150) if D <= 300 else 1.0
        ok3   = tau_v <= k_fac * tau_c
        self._set_cell(self.checks_table, 2, 0, "Shear Check")
        self._set_cell(self.checks_table, 2, 1,
                        f"τv={tau_v:.3f} ≤ k·τc={k_fac*tau_c:.3f} MPa (k={k_fac:.2f})")
        self._set_cell(self.checks_table, 2, 2, "✓ OK" if ok3 else "✗ Shear Critical",
                        color="#2E7D32" if ok3 else "#C62828")

        # 4 Deflection
        disc_flag = "discontinuous" in support.lower()
        try:
            cover = float(self._get_text("cover"))
        except (ValueError, TypeError):
            cover = 20.0

        if lx <= 3.5:
            basic = 35 if disc_flag else 40
            mf    = 0.8 if fy > 250 else 1.0
            ld_max  = basic * mf
            ld_prov = (lx * 1000) / D
            ok4   = ld_prov <= ld_max
            detail = f"L/D = {ld_prov:.1f} ≤ {ld_max:.1f}"
            req_D = (lx * 1000) / ld_max if ld_max > 0 else D
        else:
            req   = self.ast_results.get("x_pos", {}).get("req", ax)
            fs    = min(0.58 * fy * req / ax, 0.58 * fy) if ax > 0 else 0.58 * fy
            fs_keys = sorted(DEFLECTION_KT_DATA.keys())
            kt = _interp(
                pt,
                list(DEFLECTION_KT_DATA[
                    min(fs_keys, key=lambda k: abs(k - fs))
                ].keys()),
                list(DEFLECTION_KT_DATA[
                    min(fs_keys, key=lambda k: abs(k - fs))
                ].values()),
            )
            base    = 20 if disc_flag else 26
            ld_max  = base * min(kt, 2.0)
            ld_prov = (lx * 1000) / d_x
            ok4     = ld_prov <= ld_max
            detail  = f"L/d = {ld_prov:.1f} ≤ {ld_max:.1f} (kt={min(kt,2.0):.2f})"
            req_d = (lx * 1000) / ld_max if ld_max > 0 else d_x
            req_D = req_d + cover + (self._dia / 2.0)

        req_D_rounded = int(math.ceil(max(req_D, D) / 5.0) * 5)

        self._set_cell(self.checks_table, 3, 0, "Deflection Check")
        self._set_cell(self.checks_table, 3, 1, detail)
        self._set_cell(self.checks_table, 3, 2,
                        "✓ OK" if ok4 else f"✗ Increase D to {req_D_rounded} mm",
                        color="#2E7D32" if ok4 else "#E65100")

        # 5 Span input order validity (Lx must be shorter span)
        ok5 = ratio >= 1.0
        self._set_cell(self.checks_table, 4, 0, "Span Input Order")
        self._set_cell(self.checks_table, 4, 1,
                        f"Ly/Lx = {ratio:.3f}; expected Ly ≥ Lx for two-way slab input")
        self._set_cell(self.checks_table, 4, 2,
                        "✓ OK" if ok5 else "⚠ Lx should be shorter span (enter Lx ≤ Ly)",
                        color="#2E7D32" if ok5 else "#E65100")

        # 6 Applicability check (this tab is for two-way slabs only)
        ok6 = ratio <= 2.0 and ratio >= 1.0
        self._set_cell(self.checks_table, 5, 0, "Two-Way Slab Applicability")
        self._set_cell(self.checks_table, 5, 1,
                        f"Two-way slab condition: 1.0 ≤ Ly/Lx ≤ 2.0; current Ly/Lx = {ratio:.3f}")
        self._set_cell(self.checks_table, 5, 2,
                        "✓ OK" if ok6 else "⚠ One-way behavior or invalid span order; use one-way slab design",
                        color="#2E7D32" if ok6 else "#E65100")

        self._resize(self.checks_table)
        self._update_design_notes(ratio, support)


    def _round_spacing(self, sp: float) -> int:

        base = self.spacing_round_base
        return int(round(sp / base) * base)
