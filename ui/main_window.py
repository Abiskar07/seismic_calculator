"""ui/main_window.py — Complete application main window v4.0."""
from __future__ import annotations
import os, sys, subprocess
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QScrollArea,
    QStatusBar, QLabel, QMessageBox, QFileDialog, QDialog,
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction

from core import run_seismic_calculation, SeismicCalcError
from ui.tabs    import SeismicTab, LoadTab, SlabTab, BeamTab, ColumnTab, FoundationTab, StaircaseTab, WindTab, SettingsTab
from ui.dialogs import HelpDialog, AboutDialog, ExportDialog
from ui.widgets import ProjectInfoBar
from ui.stylesheets import DARK, LIGHT


class MainWindow(QMainWindow):
    APP_TITLE = "Structural Calculator v4.0  ·  NBC 105:2025 · IS 456:2000"
    VERSION   = "4.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.APP_TITLE)
        self.setGeometry(60, 60, 1380, 980)

        self.settings_tab   = SettingsTab()
        self.seismic_tab    = SeismicTab()
        self.load_tab       = LoadTab()
        self.slab_tab       = SlabTab()
        self.beam_tab       = BeamTab(seismic_tab_ref=self.seismic_tab)
        self.column_tab     = ColumnTab()
        self.foundation_tab = FoundationTab()
        self.staircase_tab  = StaircaseTab()
        self.wind_tab       = WindTab()

        self._apply_settings()
        self.setStyleSheet(DARK if self.settings_tab.is_dark() else LIGHT)

        self._calc_timer = QTimer(singleShot=True)
        self._calc_timer.timeout.connect(self._auto_calc)

        # wire seismic inputs
        for w in self.seismic_tab.inputs.values():
            if   hasattr(w,"currentTextChanged"): w.currentTextChanged.connect(self._schedule)
            elif hasattr(w,"valueChanged"):        w.valueChanged.connect(self._schedule)
            elif hasattr(w,"textChanged"):         w.textChanged.connect(self._schedule)
        self.seismic_tab.inputs["struct_cat"].currentTextChanged.connect(self._on_struct_cat)
        for key in ("zone","soil"):
            self.seismic_tab.inputs[key].currentTextChanged.connect(
                lambda _,k=key: self._update_soil_info())

        self.settings_tab.settings_changed.connect(self._apply_settings)
        self.settings_tab.dark_radio.toggled.connect(
            lambda _: self.setStyleSheet(DARK if self.settings_tab.is_dark() else LIGHT))

        # Central layout
        central = QWidget(); self.setCentralWidget(central)
        vl = QVBoxLayout(central); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)

        self.project_info = ProjectInfoBar()
        vl.addWidget(self.project_info)

        self.tabs = QTabWidget()
        for content, title in [
            (self.seismic_tab,    "🌍  Base Shear (NBC 105)"),
            (self.load_tab,       "📦  Load Calc"),
            (self.slab_tab,       "▦  Slab Design"),
            (self.beam_tab,       "━  Beam Design"),
            (self.column_tab,     "⬛  Column Design"),
            (self.foundation_tab, "⬛  Footing Design"),
            (self.staircase_tab,  "🪜  Staircase Design"),
            (self.wind_tab,       "💨  Wind Load (IS 875)"),
            (self.settings_tab,   "⚙  Settings"),
        ]:
            sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(content)
            self.tabs.addTab(sc, title)
        vl.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        sb = QStatusBar(); self.setStatusBar(sb)
        sb.addPermanentWidget(QLabel("  Abiskar Acharya  ·  NBC 105:2025 · IS 456:2000 · IS 875  "))
        self._status = sb
        self._build_menu()
        self._set_seismic_defaults()
        self._do_seismic_calc()

    # ── Menu ──────────────────────────────────────────────────────────────────
    def _build_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu("File")
        self._act(fm,"New Project",    "Ctrl+N", self._new_project)
        self._act(fm,"Open Project…",  "Ctrl+O", self._open_project)
        self._act(fm,"Save Project…",  "Ctrl+S", self._save_project)
        fm.addSeparator()
        self._act(fm,"Export Report…", "Ctrl+E", self._export_report)
        fm.addSeparator()
        self._act(fm,"Exit",           "Ctrl+Q", self.close)
        vm = mb.addMenu("View")
        for i,t in enumerate(["Base Shear","Load Calc","Slab","Beam","Column","Footing","Settings"]):
            self._act(vm,t,f"Ctrl+{i+1}",lambda _,n=i: self.tabs.setCurrentIndex(n))
        tm = mb.addMenu("Tools")
        self._act(tm,"Run All Calculations","F5",   self._run_all)
        self._act(tm,"Open Calculator",     "",     self._open_calc)
        hm = mb.addMenu("Help")
        self._act(hm,"Help","F1",     lambda: HelpDialog(self).exec())
        self._act(hm,"About","Ctrl+H",lambda: AboutDialog(self).exec())

    @staticmethod
    def _act(menu,text,shortcut,slot):
        a=QAction(text); a.triggered.connect(slot)
        if shortcut: a.setShortcut(shortcut)
        menu.addAction(a); return a

    # ── Settings ──────────────────────────────────────────────────────────────
    def _apply_settings(self):
        base = self.settings_tab.spacing_round_base()
        self.slab_tab.spacing_round_base = base
        self.beam_tab.spacing_round_base = base
        self.setStyleSheet(DARK if self.settings_tab.is_dark() else LIGHT)

    # ── Seismic ───────────────────────────────────────────────────────────────
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

    def _on_struct_cat(self,cat):
        self.seismic_tab.update_subtype_options(cat); self._do_seismic_calc()
    def _update_soil_info(self):
        self.seismic_tab.update_soil_info(
            self.seismic_tab.inputs["zone"].currentText(),
            self.seismic_tab.inputs["soil"].currentText())
    def _schedule(self):
        if self.settings_tab.auto_calculate(): self._calc_timer.start(400)
    def _auto_calc(self):
        if self.tabs.currentIndex()==0: self._do_seismic_calc()
    def _on_tab_changed(self,idx):
        if idx==0: self._do_seismic_calc()

    def _do_seismic_calc(self):
        try:
            p = self.seismic_tab.get_params()
            p["H"] = float(p["H"]) if p["H"] else 0.0
            res = run_seismic_calculation(p)
            self.seismic_tab.populate_results(res)
            self._status.showMessage(
                f"T={res['T']:.3f}s  Ch={res['Ch_T']:.3f}  "
                f"Cd(ULS)={res['Cd_ULS']:.4f}  Cd(SLS)={res['Cd_SLS']:.4f}",4000)
        except (SeismicCalcError, Exception) as e:
            self.seismic_tab.clear_results()
            self._status.showMessage(f"Seismic error: {e}",5000)

    def _run_all(self):
        self._do_seismic_calc()
        for tab in (self.load_tab, self.slab_tab, self.beam_tab,
                    self.column_tab, self.foundation_tab,
                    self.staircase_tab, self.wind_tab):
            try:
                fn = getattr(tab, "recalculate_wall_loads", None) or getattr(tab, "calculate", None)
                if fn: fn()
            except: pass
        self._status.showMessage("All calculations refreshed",3000)

    # ── File I/O ──────────────────────────────────────────────────────────────
    def _start_dir(self):
        d = self.settings_tab.export_dir()
        return d if d and os.path.isdir(d) else os.path.expanduser("~")

    def _new_project(self):
        if QMessageBox.question(self,"New Project","Clear all inputs?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
        )==QMessageBox.StandardButton.Yes:
            self._set_seismic_defaults(); self._do_seismic_calc()
            for tab in (self.slab_tab, self.beam_tab, self.column_tab,
                    self.foundation_tab, self.staircase_tab):
                try: tab._set_defaults()
                except: pass
            self._status.showMessage("New project",3000)

    def _open_project(self):
        import json
        path,_ = QFileDialog.getOpenFileName(self,"Open Project",self._start_dir(),"JSON (*.json)")
        if not path: return
        try:
            with open(path,encoding="utf-8") as f: data=json.load(f)
            for key,val in data.get("seismic",{}).items():
                w = self.seismic_tab.inputs.get(key)
                if not w: continue
                if   hasattr(w,"setCurrentText"): w.setCurrentText(str(val))
                elif hasattr(w,"setText"):         w.setText(str(val))
                elif hasattr(w,"setValue"):        w.setValue(int(val))
            pi = data.get("project_info",{})
            pb = self.project_info
            pb._proj_name.setText(pi.get("project",""))
            pb._engineer.setText(pi.get("engineer",""))
            pb._job_no.setText(pi.get("job_no",""))
            pb._date_edit.setText(pi.get("date",""))
            pb._checked_by.setText(pi.get("checked_by",""))
            self._do_seismic_calc()
            self._status.showMessage(f"Loaded: {os.path.basename(path)}",3000)
        except Exception as e:
            QMessageBox.critical(self,"Open Error",str(e))

    def _save_project(self):
        import json
        path,_ = QFileDialog.getSaveFileName(self,"Save Project",self._start_dir(),"JSON (*.json)")
        if not path: return
        if not path.lower().endswith(".json"): path+=".json"
        try:
            state={}
            for key,w in self.seismic_tab.inputs.items():
                if   hasattr(w,"currentText"): state[key]=w.currentText()
                elif hasattr(w,"text"):         state[key]=w.text()
                elif hasattr(w,"value"):        state[key]=w.value()
            data={"version":self.VERSION,"saved_at":datetime.now().isoformat(),
                  "seismic":state,"project_info":self.project_info.get_info()}
            with open(path,"w",encoding="utf-8") as f: json.dump(data,f,indent=2)
            self._status.showMessage(f"Saved: {os.path.basename(path)}",3000)
        except Exception as e:
            QMessageBox.critical(self,"Save Error",str(e))

    # ── Export ────────────────────────────────────────────────────────────────
    def _collect_report_data(self) -> dict:
        """Gather all live calculation results into one dict for export."""
        pi = self.project_info.get_info()
        data = {"project_info": pi}

        # Seismic
        try:
            p = self.seismic_tab.get_params()
            p["H"] = float(p["H"]) if p["H"] else 0.0
            res = run_seismic_calculation(p)
            data["seismic"] = {
                **res,
                "zone_name": p["zone_name"],
                "H":         p["H"],
                "num_stories": p["num_stories"],
                "struct_sub":  p["struct_sub"],
                "method":      p["method"],
                "lambda_ll":   res.get("lambda_ll", 0.30),
            }
        except: pass

        # Beam
        try:
            bt = self.beam_tab
            if bt._last_res:
                res = bt._last_res
                data["beam"] = {
                    **res,
                    "b":    float(bt._get("width")),
                    "D":    float(bt._get("depth")),
                    "cover":float(bt._get("cover")),
                    "main_dia": float(bt._get("dia")),
                    "span_m":   float(bt._get("span_defl") or "0"),
                    "support_type": bt._get("support"),
                    "fck":  int(bt._get("fck")),
                    "fy":   int(bt._get("fy")),
                }
        except: pass

        # Column
        try:
            ct = self.column_tab
            if hasattr(ct, "_last_result") and ct._last_result:
                data["column"] = ct._last_result
            else:
                # trigger a fresh calc and grab
                ct.calculate()
                # store last result on calculate
        except: pass

        # Foundation
        try:
            ft = self.foundation_tab
            if ft._last_result:
                data["foundation"] = {**ft._last_result, "seismic_used": bool(ft._g("seismic",False))}
        except: pass

        return data

    def _export_report(self):
        dlg = ExportDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        sections, fmt, mode = dlg.get_selection()

        ext_map  = {"Excel":".xlsx","Word":".docx","Text":".txt"}
        filt_map = {"Excel":"Excel Workbook (*.xlsx)",
                    "Word": "Word Document (*.docx)",
                    "Text": "Text File (*.txt)"}
        path,_ = QFileDialog.getSaveFileName(
            self, f"Export {fmt} Report", self._start_dir(), filt_map[fmt])
        if not path: return
        if not path.lower().endswith(ext_map[fmt]):
            path += ext_map[fmt]

        try:
            self._status.showMessage("Collecting results…")
            data = self._collect_report_data()

            # Filter to requested sections
            for key in ("seismic","load","slab","beam","column","foundation"):
                if key not in sections and key in data:
                    del data[key]

            if fmt == "Excel":
                from export.excel_exporter import generate_excel_report
                generate_excel_report(data, path, mode=mode)
            elif fmt == "Word":
                from export.word_exporter import generate_word_report
                generate_word_report(data, path, mode=mode)
            else:
                self._export_plain_text(data, path, mode)

            sz = os.path.getsize(path)
            self._status.showMessage(f"Exported: {os.path.basename(path)}  ({sz:,} bytes)",5000)

            if QMessageBox.question(
                self,"Export Complete",
                f"Report saved:\n{path}\n\nOpen containing folder?",
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self._reveal(path)

        except Exception as e:
            QMessageBox.critical(self,"Export Error",
                f"Export failed:\n{e}\n\n"
                "Ensure PyQt6, openpyxl, and Node.js (docx package) are installed.")
            self._status.showMessage("Export failed",4000)

    def _export_plain_text(self, data: dict, path: str, mode: str):
        pi = data.get("project_info",{})
        lines = [
            "="*70,
            "  STRUCTURAL DESIGN CALCULATIONS",
            "  NBC 105:2025 (Second Revision) · IS 456:2000 · IS 875",
            f"  Project   : {pi.get('project','')}",
            f"  Engineer  : {pi.get('engineer','')}    Checked: {pi.get('checked_by','')}",
            f"  Job No.   : {pi.get('job_no','')}     Date: {pi.get('date','')}",
            f"  Generated : {datetime.now().strftime('%Y-%m-%d  %H:%M')}",
            "="*70, "",
        ]
        if "seismic" in data:
            s = data["seismic"]
            lines += ["SEISMIC ANALYSIS  —  NBC 105:2025","-"*50]
            for k,v in [
                ("Zone",s.get("zone_name","")),("Z",f"{s.get('Z',0):.2f}"),
                ("I",f"{s.get('I',0):.2f}"),("T",f"{s.get('T',0):.4f} s"),
                ("Ch(T)",f"{s.get('Ch_T',0):.4f}"),("C(T)",f"{s.get('C_T',0):.4f}"),
                ("Cd_ULS",f"{s.get('Cd_ULS',0):.4f}"),("Cd_SLS",f"{s.get('Cd_SLS',0):.4f}"),
                ("kd",f"{s.get('kd',0):.2f}"),
            ]: lines.append(f"  {k:<25}: {v}")
            sf = s.get("story_forces",[])
            if sf:
                lines.append(f"\n  Story Force Distribution (NBC 105:2025 §6.3):")
                lines.append(f"  {'Floor':>5}  {'Wi(kN)':>8}  {'hi(m)':>6}  {'Fi(kN)':>8}  {'Vx(kN)':>10}")
                for f in sf:
                    lines.append(f"  {f['floor']:>5}  {f['W_kN']:>8.1f}  {f['h_m']:>6.2f}  {f['Fi_kN']:>8.2f}  {f['Vx_kN']:>10.2f}")
            lines.append("")
        if "beam" in data:
            b = data["beam"]
            lines += ["BEAM DESIGN  —  IS 456:2000","-"*50]
            for k,v in [
                ("Section",f"{b.get('b','?')}×{b.get('D','?')} mm"),
                ("d",f"{b.get('d_eff_mm',0):.1f} mm"),
                ("Mu_lim",f"{b.get('Mu_lim_kNm',0):.3f} kN·m"),
                ("Mu_design",f"{b.get('Mu_design_kNm',0):.3f} kN·m"),
                ("Ast_req",f"{b.get('Ast_req_mm2',0):.0f} mm²"),
                ("Bars",f"{b.get('no_of_bars',0)}×Ø{b.get('main_dia','?')}mm"),
                ("Ast_prov",f"{b.get('Ast_prov_mm2',0):.0f} mm²"),
                ("Shear",b.get('shear',{}).get('status','')),
                ("Ld",f"{b.get('Ld_mm',0):.0f} mm"),
            ]: lines.append(f"  {k:<25}: {v}")
            lines.append("")
        if "column" in data:
            c = data["column"]
            lines += ["COLUMN DESIGN  —  IS 456:2000 + NBC 105:2025 Annex A","-"*50]
            for k,v in [
                ("Section",f"{c.get('b_mm','?')}×{c.get('D_mm','?')} mm"),
                ("λx / λy",f"{c.get('lambda_x',0):.2f} / {c.get('lambda_y',0):.2f}"),
                ("Interaction",f"{c.get('interaction',0):.4f}"),
                ("Steel%",f"{c.get('steel_pct',0):.2f}%"),
                ("Bars",f"{c.get('no_of_bars',0)}×Ø{int(c.get('bar_dia_mm',0))}mm"),
                ("Conf. zone",f"{c.get('conf_zone_mm',0):.0f} mm (NBC 105 Annex A)"),
            ]: lines.append(f"  {k:<25}: {v}")
            lines.append("")
        if "foundation" in data:
            f = data["foundation"]
            lines += ["FOUNDATION DESIGN  —  IS 456:2000 §34","-"*50]
            for k,v in [
                ("Plan",f"{f.get('L_mm',0)}×{f.get('B_mm',0)} mm"),
                ("D/d",f"{f.get('D_mm',0):.0f}/{f.get('d_mm',0):.0f} mm"),
                ("q_max",f"{f.get('q_max_kPa',0):.2f} kN/m²"),
                ("Punching","OK" if f.get('punch_ok') else "FAILS"),
                ("1-way shear","OK" if f.get('one_way_ok') else "FAILS"),
                ("Rein L",f"Ø{int(f.get('bar_dia_mm',12))}@{f.get('sp_L_mm',0)}mm"),
            ]: lines.append(f"  {k:<25}: {v}")
            lines.append("")
        with open(path,"w",encoding="utf-8") as fp:
            fp.write("\n".join(lines))

    @staticmethod
    def _reveal(path):
        folder = os.path.dirname(os.path.abspath(path))
        try:
            if sys.platform=="win32": os.startfile(folder)
            elif sys.platform=="darwin": subprocess.Popen(["open",folder])
            else:
                for cmd in ("xdg-open","nautilus","thunar"):
                    try: subprocess.Popen([cmd,folder]); break
                    except FileNotFoundError: continue
        except: pass

    def _open_calc(self):
        try:
            if sys.platform=="win32": subprocess.Popen(["calc"])
            elif sys.platform=="darwin": subprocess.Popen(["open","-a","Calculator"])
            else:
                for a in ("gnome-calculator","kcalc","xcalc"):
                    try: subprocess.Popen([a]); break
                    except FileNotFoundError: continue
        except Exception as e:
            QMessageBox.warning(self,"Error",str(e))
