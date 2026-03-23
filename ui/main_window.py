"""
ui/main_window.py — Complete application main window v1.0.0
Fixed: menu actions, tab navigation, all file operations, export pipeline
"""
from __future__ import annotations
import os, sys, subprocess
from datetime import datetime

from PyQt6.QtWidgets import ( # type: ignore
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QScrollArea,
    QStatusBar, QLabel, QMessageBox, QFileDialog, QDialog, QSplitter,
)
from PyQt6.QtCore import QTimer, Qt # type: ignore
from PyQt6.QtGui import QAction, QKeySequence # type: ignore

from core import run_seismic_calculation, SeismicCalcError # type: ignore
from ui.tabs import (SeismicTab, LoadTab, SlabTab, BeamTab, ColumnTab, # type: ignore
                     FoundationTab, StaircaseTab, WindTab, SettingsTab)
from ui.dialogs import HelpDialog, AboutDialog, ExportDialog # type: ignore
from ui.widgets import ProjectInfoBar # type: ignore
from ui.stylesheets import DARK, LIGHT # type: ignore


class MainWindow(QMainWindow):
    from constants import APP_NAME, APP_VERSION # type: ignore
    APP_TITLE = f"{APP_NAME} {APP_VERSION}  ·  NBC 105:2025 · IS 456:2000"
    VERSION   = "1.0.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.APP_TITLE)
        self.setGeometry(40, 40, 1400, 900)
        self.setMinimumSize(900, 600)

        # ── Create tabs ──────────────────────────────────────────────────────
        self.settings_tab   = SettingsTab()
        self.seismic_tab    = SeismicTab()
        self.load_tab       = LoadTab()
        self.slab_tab       = SlabTab()
        self.beam_tab       = BeamTab(seismic_tab_ref=self.seismic_tab)
        self.column_tab     = ColumnTab()
        self.foundation_tab = FoundationTab()
        self.staircase_tab  = StaircaseTab()
        self.wind_tab       = WindTab()

        # Apply persisted settings before rendering
        self._apply_settings()
        self.setStyleSheet(DARK if self.settings_tab.is_dark() else LIGHT)

        # ── Auto-calculate timer ─────────────────────────────────────────────
        self._calc_timer = QTimer(self)
        self._calc_timer.setSingleShot(True)
        self._calc_timer.timeout.connect(self._auto_calc)

        # ── Wire seismic inputs ──────────────────────────────────────────────
        for w in self.seismic_tab.inputs.values():
            if   hasattr(w, "currentTextChanged"): w.currentTextChanged.connect(self._schedule) # type: ignore
            elif hasattr(w, "valueChanged"):        w.valueChanged.connect(self._schedule) # type: ignore
            elif hasattr(w, "textChanged"):         w.textChanged.connect(self._schedule) # type: ignore
        self.seismic_tab.inputs["struct_cat"].currentTextChanged.connect(self._on_struct_cat) # type: ignore
        for key in ("zone", "soil"):
            self.seismic_tab.inputs[key].currentTextChanged.connect(
                lambda _, k=key: self._update_soil_info())

        # ── Wire settings ────────────────────────────────────────────────────
        self.settings_tab.settings_changed.connect(self._apply_settings)
        self.settings_tab.dark_radio.toggled.connect(
            lambda checked: self.setStyleSheet(DARK if self.settings_tab.is_dark() else LIGHT))

        # ── Central layout ───────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        vl = QVBoxLayout(central)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Project info strip
        self.project_info = ProjectInfoBar()
        vl.addWidget(self.project_info)

        # Tab widget — compact tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(False)
        self.tabs.setUsesScrollButtons(True)

        _tab_defs = [
            (self.seismic_tab,    "Base Shear"),
            (self.load_tab,       "Load Calc"),
            (self.slab_tab,       "Slab"),
            (self.beam_tab,       "Beam"),
            (self.column_tab,     "Column"),
            (self.foundation_tab, "Footing"),
            (self.staircase_tab,  "Staircase"),
            (self.wind_tab,       "Wind Load"),
        ]
        for content, title in _tab_defs:
            sc = QScrollArea()
            sc.setWidgetResizable(True)
            sc.setWidget(content)
            self.tabs.addTab(sc, title)

        vl.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # ── Status bar ───────────────────────────────────────────────────────
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._seismic_status = QLabel("")
        self._seismic_status.setStyleSheet("font-family: monospace; padding: 0 6px;")
        sb.addWidget(self._seismic_status)
        dev = QLabel("  Abiskar Acharya  ·  NBC 105:2025 · IS 456:2000 · IS 875  ")
        dev.setStyleSheet("font-weight: bold;")
        sb.addPermanentWidget(dev)
        self._status = sb

        # ── Build menu ───────────────────────────────────────────────────────
        self._build_menu()

        # ── Initial calculation ───────────────────────────────────────────────
        self._set_seismic_defaults()
        self._do_seismic_calc()

    # ══════════════════════════════════════════════════════════════════════════
    # MENU — Fixed: parent passed to QAction, shortcuts use QKeySequence
    # ══════════════════════════════════════════════════════════════════════════
    def _build_menu(self):
        mb = self.menuBar()

        # File menu
        fm = mb.addMenu("&File")
        self._add_action(fm, "New Project",    "Ctrl+N", self._new_project)
        self._add_action(fm, "Open Project…",  "Ctrl+O", self._open_project)
        self._add_action(fm, "Save Project…",  "Ctrl+S", self._save_project)
        fm.addSeparator()
        self._add_action(fm, "Export Report…", "Ctrl+E", self._export_report)
        fm.addSeparator()
        self._add_action(fm, "Exit",           "Ctrl+Q", self.close)

        # View menu — tab navigation
        vm = mb.addMenu("&View")
        tab_shortcuts = ["Ctrl+1","Ctrl+2","Ctrl+3","Ctrl+4",
                         "Ctrl+5","Ctrl+6","Ctrl+7","Ctrl+8"]
        tab_names = ["Base Shear","Load Calc","Slab","Beam",
                     "Column","Footing","Staircase","Wind Load"]
        for i, (name, sc) in enumerate(zip(tab_names, tab_shortcuts)):
            idx = i  # capture by value
            self._add_action(vm, name, sc, lambda _, n=idx: self.tabs.setCurrentIndex(n))

        # Tools menu
        tm = mb.addMenu("&Tools")
        self._add_action(tm, "Run All Calculations", "F5", self._run_all)
        tm.addSeparator()
        self._add_action(tm, "Open System Calculator", "", self._open_calc)
        tm.addSeparator()
        self._add_action(tm, "Preferences…", "Ctrl+P", self._open_settings)

        # Help menu
        hm = mb.addMenu("&Help")
        self._add_action(hm, "Help Documentation", "F1",     lambda: HelpDialog(self).exec())
        self._add_action(hm, "About",              "Ctrl+H", lambda: AboutDialog(self).exec())

    def _add_action(self, menu, text, shortcut, slot):
        """Create and add a QAction with parent=self (required by PyQt6)."""
        a = QAction(text, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(slot)
        menu.addAction(a)
        return a

    # ══════════════════════════════════════════════════════════════════════════
    # SETTINGS
    # ══════════════════════════════════════════════════════════════════════════
    def _apply_settings(self):
        base = self.settings_tab.spacing_round_base()
        self.slab_tab.spacing_round_base = base
        self.beam_tab.spacing_round_base = base
        self.setStyleSheet(DARK if self.settings_tab.is_dark() else LIGHT)

    def _open_settings(self):
        if not hasattr(self, "_settings_window"):
            self._settings_window = QDialog(self)
            self._settings_window.setWindowTitle("Preferences")
            self._settings_window.resize(700, 480)
            from PyQt6.QtWidgets import QHBoxLayout, QPushButton # type: ignore
            vl = QVBoxLayout(self._settings_window)
            vl.addWidget(self.settings_tab)
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self._settings_window.accept)
            btn_row.addWidget(close_btn)
            vl.addLayout(btn_row)
        self._settings_window.exec()

    # ══════════════════════════════════════════════════════════════════════════
    # SEISMIC
    # ══════════════════════════════════════════════════════════════════════════
    def _set_seismic_defaults(self):
        inp = self.seismic_tab.inputs
        inp["zone"].setCurrentText("Lalitpur")
        inp["method"].setCurrentText("Equivalent Static Method")
        inp["importance"].setCurrentText("Residential Building")
        inp["soil"].setCurrentText("D")
        inp["H"].setText("8.534")
        inp["num_stories"].setValue(3)
        inp["struct_cat"].setCurrentText("Moment Resisting Frame Systems")
        self._on_struct_cat("Moment Resisting Frame Systems")
        inp["struct_sub"].setCurrentText("(Reinforced Concrete Moment Resisting Frame)")
        # Default floor weights so story force table shows immediately
        self.seismic_tab._floor_weights_edit.setText("1200, 1200, 1000")

    def _on_struct_cat(self, cat):
        self.seismic_tab.update_subtype_options(cat)
        self._do_seismic_calc()

    def _update_soil_info(self):
        self.seismic_tab.update_soil_info(
            self.seismic_tab.inputs["zone"].currentText(),
            self.seismic_tab.inputs["soil"].currentText())

    def _schedule(self):
        if self.settings_tab.auto_calculate():
            self._calc_timer.start(350)

    def _auto_calc(self):
        if self.tabs.currentIndex() == 0:
            self._do_seismic_calc()

    def _on_tab_changed(self, idx):
        if idx == 0:
            self._do_seismic_calc()

    def _do_seismic_calc(self):
        try:
            p = self.seismic_tab.get_params()
            try:
                p["H"] = float(p["H"]) if p["H"] else 0.0
            except (ValueError, TypeError):
                p["H"] = 0.0
            res = run_seismic_calculation(p)
            self.seismic_tab.populate_results(res)
            self._seismic_status.setText(
                f"T = {res['T']:.3f} s  |  Ch(T) = {res['Ch_T']:.3f}  |  "
                f"Cd(ULS) = {res['Cd_ULS']:.4f}  |  Cd(SLS) = {res['Cd_SLS']:.4f}")
        except SeismicCalcError as e:
            self.seismic_tab.clear_results()
            self._seismic_status.setText(f"Seismic error: {e}")
        except Exception as e:
            self.seismic_tab.clear_results()
            self._seismic_status.setText(f"Error: {e}")

    def _run_all(self):
        self._do_seismic_calc()
        for tab in (self.load_tab, self.slab_tab, self.beam_tab,
                    self.column_tab, self.foundation_tab,
                    self.staircase_tab, self.wind_tab):
            try:
                fn = (getattr(tab, "recalculate_wall_loads", None) or
                      getattr(tab, "calculate", None))
                if fn:
                    fn()
            except Exception:
                pass
        self._status.showMessage("All calculations refreshed", 3000)

    # ══════════════════════════════════════════════════════════════════════════
    # FILE I/O
    # ══════════════════════════════════════════════════════════════════════════
    def _start_dir(self):
        d = self.settings_tab.export_dir()
        return d if d and os.path.isdir(d) else os.path.expanduser("~")

    def _new_project(self):
        reply = QMessageBox.question(
            self, "New Project", "Clear all inputs and start fresh?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._set_seismic_defaults()
            self._do_seismic_calc()
            for tab in (self.slab_tab, self.beam_tab, self.column_tab,
                        self.foundation_tab, self.staircase_tab):
                try:
                    tab._set_defaults()
                except Exception:
                    pass
            self._status.showMessage("New project created", 3000)

    def _open_project(self):
        import json
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", self._start_dir(), "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            # Restore seismic inputs
            inp = self.seismic_tab.inputs
            for key, val in data.get("seismic", {}).items():
                if key not in inp:
                    continue
                w = inp[key]
                try:
                    if   hasattr(w, "setCurrentText"): w.setCurrentText(str(val))
                    elif hasattr(w, "setText"):         w.setText(str(val))
                    elif hasattr(w, "setValue"):        w.setValue(int(val)) # type: ignore
                except Exception:
                    pass
            # Restore project info
            pi = data.get("project_info", {})
            pb = self.project_info
            pb._proj_name.setText(pi.get("project", ""))
            pb._engineer.setText(pi.get("engineer", ""))
            pb._job_no.setText(pi.get("job_no", ""))
            pb._date_edit.setText(pi.get("date", ""))
            pb._checked_by.setText(pi.get("checked_by", ""))
            self._do_seismic_calc()
            self._status.showMessage(f"Opened: {os.path.basename(path)}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Could not open project:\n{e}")

    def _save_project(self):
        import json
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", self._start_dir(), "JSON Files (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            state = {}
            for key, w in self.seismic_tab.inputs.items():
                try:
                    if   hasattr(w, "currentText"): state[key] = w.currentText() # type: ignore
                    elif hasattr(w, "text"):         state[key] = w.text() # type: ignore
                    elif hasattr(w, "value"):        state[key] = w.value() # type: ignore
                except Exception:
                    pass
            data = {
                "version":      self.APP_VERSION,
                "saved_at":     datetime.now().isoformat(),
                "seismic":      state,
                "project_info": self.project_info.get_info(),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._status.showMessage(f"Saved: {os.path.basename(path)}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save:\n{e}")

    # ══════════════════════════════════════════════════════════════════════════
    # EXPORT
    # ══════════════════════════════════════════════════════════════════════════
    def _collect_report_data(self) -> dict:
        """Gather live results from all tabs into export dict."""
        pi   = self.project_info.get_info()
        data = {"project_info": pi}

        # Seismic
        try:
            p = self.seismic_tab.get_params()
            p["H"] = float(p["H"]) if p["H"] else 0.0
            res = run_seismic_calculation(p)
            data["seismic"] = {
                **res,
                "zone_name":   p["zone_name"],
                "H":           p["H"],
                "num_stories": p["num_stories"],
                "struct_sub":  p["struct_sub"],
                "method":      p["method"],
                "lambda_ll":   res.get("lambda_ll", 0.30),
            }
        except Exception:
            pass

        # Beam
        try:
            bt = self.beam_tab
            if bt._last_res:
                data["beam"] = {
                    **bt._last_res,
                    "b":           float(bt._get("width")),
                    "D":           float(bt._get("depth")),
                    "cover":       float(bt._get("cover")),
                    "main_dia":    float(bt._get("dia")),
                    "span_m":      float(bt._get("span_defl") or "0"),
                    "support_type":bt._get("support"),
                    "fck":         int(bt._get("fck")),
                    "fy":          int(bt._get("fy")),
                }
        except Exception:
            pass

        # Slab
        try:
            st = self.slab_tab
            if hasattr(st, 'summary') and st.summary:
                slab_summary = {k: l.text() for k, l in st.summary.items()}
                data["slab"] = {"summary": slab_summary}
        except Exception:
            pass

        # Column
        try:
            ct = self.column_tab
            if ct._last_result:
                data["column"] = ct._last_result
        except Exception:
            pass

        # Foundation
        try:
            ft = self.foundation_tab
            if ft._last_result:
                data["foundation"] = {
                    **ft._last_result,
                    "seismic_used": bool(ft._g("seismic", False)),
                }
        except Exception:
            pass

        return data

    def _export_report(self):
        dlg = ExportDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        sections, fmt, mode = dlg.get_selection()

        ext_map  = {"Excel": ".xlsx", "Word": ".docx", "Text": ".txt"}
        filt_map = {
            "Excel": "Excel Workbook (*.xlsx)",
            "Word":  "Word Document (*.docx)",
            "Text":  "Text File (*.txt)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self, f"Export {fmt} Report", self._start_dir(), filt_map[fmt])
        if not path:
            return
        if not path.lower().endswith(ext_map[fmt]):
            path += ext_map[fmt]

        try:
            self._status.showMessage("Generating report…")
            data = self._collect_report_data()

            # Remove sections user didn't select
            all_keys = ["seismic", "load", "slab", "beam", "column", "foundation"]
            for key in all_keys:
                if key not in sections:
                    data.pop(key, None)

            if fmt == "Excel":
                from export.excel_exporter import generate_excel_report # type: ignore
                generate_excel_report(data, path, mode=mode)
            elif fmt == "Word":
                from export.word_exporter import generate_word_report # type: ignore
                generate_word_report(data, path, mode=mode)
            else:
                self._export_plain_text(data, path)

            sz = os.path.getsize(path)
            self._status.showMessage(
                f"Exported: {os.path.basename(path)}  ({sz:,} bytes)", 5000)
            reply = QMessageBox.question(
                self, "Export Complete",
                f"Report saved:\n{path}\n\nOpen containing folder?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._reveal(path)

        except Exception as e:
            import traceback
            QMessageBox.critical(
                self, "Export Error",
                f"Export failed:\n{e}\n\n"
                "Check that python-docx (pip install python-docx) is installed.\n"
                f"Traceback:\n{traceback.format_exc()}")
            self._status.showMessage("Export failed", 4000)

    def _export_plain_text(self, data: dict, path: str):
        pi = data.get("project_info", {})
        lines = [
            "=" * 70,
            "  STRUCTURAL DESIGN CALCULATIONS",
            "  NBC 105:2025 (Second Revision) · IS 456:2000 · IS 875",
            f"  Project   : {pi.get('project', '')}",
            f"  Engineer  : {pi.get('engineer', '')}   Checked: {pi.get('checked_by', '')}",
            f"  Job No.   : {pi.get('job_no', '')}     Date: {pi.get('date', '')}",
            f"  Generated : {datetime.now().strftime('%Y-%m-%d  %H:%M')}",
            "=" * 70, "",
        ]
        if "seismic" in data:
            s = data["seismic"]
            lines += ["SEISMIC ANALYSIS  —  NBC 105:2025", "-" * 50]
            for k, v in [
                ("Zone", s.get("zone_name", "")),
                ("Z",    f"{s.get('Z', 0):.2f}"),
                ("I",    f"{s.get('I', 0):.2f}"),
                ("T",    f"{s.get('T', 0):.4f} s"),
                ("Ch(T)",f"{s.get('Ch_T', 0):.4f}"),
                ("C(T)", f"{s.get('C_T', 0):.4f}"),
                ("Cd_ULS", f"{s.get('Cd_ULS', 0):.4f}"),
                ("Cd_SLS", f"{s.get('Cd_SLS', 0):.4f}"),
                ("kd",   f"{s.get('kd', 0):.2f}"),
            ]:
                lines.append(f"  {k:<25}: {v}")
            sf = s.get("story_forces", [])
            if sf:
                lines.append("\n  Story Force Distribution (NBC 105:2025 §6.3):")
                lines.append(f"  {'Floor':>5}  {'Wi(kN)':>8}  {'hi(m)':>6}  {'Fi(kN)':>8}  {'Vx(kN)':>10}")
                for f in sf:
                    lines.append(
                        f"  {f['floor']:>5}  {f['W_kN']:>8.1f}  {f['h_m']:>6.2f}"
                        f"  {f['Fi_kN']:>8.2f}  {f['Vx_kN']:>10.2f}")
            lines.append("")
        if "slab" in data:
            s = data["slab"]
            lines += ["SLAB DESIGN  —  IS 456:2000", "-" * 50]
            for k, v in s.get("summary", {}).items():
                lines.append(f"  {k:<35}: {v}")
            lines.append("")

        if "beam" in data:
            b = data["beam"]
            lines += ["BEAM DESIGN  —  IS 456:2000", "-" * 50]
            for k, v in [
                ("Section",   f"{b.get('b','?')}×{b.get('D','?')} mm"),
                ("d",         f"{b.get('d_eff_mm',0):.1f} mm"),
                ("Mu_lim",    f"{b.get('Mu_lim_kNm',0):.3f} kN·m"),
                ("Mu_design", f"{b.get('Mu_design_kNm',0):.3f} kN·m"),
                ("Ast_req",   f"{b.get('Ast_req_mm2',0):.0f} mm²"),
                ("Bars",      f"{b.get('no_of_bars',0)}×Ø{b.get('main_dia','?')}mm"),
                ("Ast_prov",  f"{b.get('Ast_prov_mm2',0):.0f} mm²"),
                ("Shear",     b.get('shear', {}).get('status', '')),
                ("Ld",        f"{b.get('Ld_mm',0):.0f} mm"),
            ]:
                lines.append(f"  {k:<25}: {v}")
            lines.append("")
        if "column" in data:
            c = data["column"]
            lines += ["COLUMN DESIGN  —  IS 456:2000 + NBC 105:2025 Annex A", "-" * 50]
            for k, v in [
                ("Section",     f"{c.get('b_mm','?')}×{c.get('D_mm','?')} mm"),
                ("λx / λy",     f"{c.get('lambda_x',0):.2f} / {c.get('lambda_y',0):.2f}"),
                ("Interaction", f"{c.get('interaction',0):.4f}"),
                ("Steel%",      f"{c.get('steel_pct',0):.2f}%"),
                ("Bars",        f"{c.get('no_of_bars',0)}×Ø{int(c.get('bar_dia_mm',0))}mm"),
                ("Conf. zone",  f"{c.get('conf_zone_mm',0):.0f} mm"),
            ]:
                lines.append(f"  {k:<25}: {v}")
            lines.append("")
        if "foundation" in data:
            f = data["foundation"]
            lines += ["FOUNDATION DESIGN  —  IS 456:2000 §34", "-" * 50]
            for k, v in [
                ("Plan",       f"{f.get('L_mm',0)}×{f.get('B_mm',0)} mm"),
                ("D/d",        f"{f.get('D_mm',0):.0f}/{f.get('d_mm',0):.0f} mm"),
                ("q_max",      f"{f.get('q_max_kPa',0):.2f} kN/m²"),
                ("Punching",   "OK" if f.get('punch_ok') else "FAILS"),
                ("1-way shear","OK" if f.get('one_way_ok') else "FAILS"),
            ]:
                lines.append(f"  {k:<25}: {v}")
            lines.append("")
        with open(path, "w", encoding="utf-8") as fp:
            fp.write("\n".join(lines))

    # ══════════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ══════════════════════════════════════════════════════════════════════════
    @staticmethod
    def _reveal(path: str):
        folder = os.path.dirname(os.path.abspath(path))
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                for cmd in ("xdg-open", "nautilus", "thunar", "pcmanfm"):
                    try:
                        subprocess.Popen([cmd, folder])
                        break
                    except FileNotFoundError:
                        continue
        except Exception:
            pass

    def _open_calc(self):
        try:
            if sys.platform == "win32":
                subprocess.Popen(["calc"])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "Calculator"])
            else:
                for app in ("gnome-calculator", "kcalc", "xcalc", "bc"):
                    try:
                        subprocess.Popen([app])
                        break
                    except FileNotFoundError:
                        continue
        except Exception as e:
            QMessageBox.warning(self, "Calculator", str(e))
