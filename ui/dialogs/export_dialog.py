"""ui/dialogs/export_dialog.py — Professional export dialog with format/mode selection."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
    QComboBox, QLabel, QPushButton, QRadioButton, QButtonGroup, QTextEdit,
)
from PyQt6.QtCore import Qt


class ExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Design Report")
        self.setModal(True)
        self.resize(460, 500)
        if parent and hasattr(parent, "styleSheet"):
            self.setStyleSheet(parent.styleSheet())
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        # ── Export mode ────────────────────────────────────────────────────────
        mode_grp = QGroupBox("Report Type")
        mode_lay = QVBoxLayout(mode_grp)
        self._mode_bg = QButtonGroup(self)
        self._radio_detailed = QRadioButton(
            "📋  Detailed Report — Full calculations with all formulas, clause references,\n"
            "     derivations and design notes (manual-style, suitable for submission)")
        self._radio_summary = QRadioButton(
            "📄  Summary Report — Key results at a glance, suitable for\n"
            "     quick review or project records")
        self._radio_detailed.setChecked(True)
        self._mode_bg.addButton(self._radio_detailed, 0)
        self._mode_bg.addButton(self._radio_summary, 1)
        mode_lay.addWidget(self._radio_detailed)
        mode_lay.addWidget(self._radio_summary)
        lay.addWidget(mode_grp)

        # ── Format ────────────────────────────────────────────────────────────
        fmt_grp = QGroupBox("Output Format")
        fmt_lay = QHBoxLayout(fmt_grp)
        fmt_lay.addWidget(QLabel("Export as:"))
        self._fmt = QComboBox()
        self._fmt.addItems([
            "📊  Excel (.xlsx)  —  Formatted spreadsheet with live formulas",
            "📝  Word (.docx)   —  Professional document with headings & tables",
            "📄  Text (.txt)    —  Plain-text report",
        ])
        self._fmt.currentIndexChanged.connect(self._on_fmt_changed)
        fmt_lay.addWidget(self._fmt, 1)
        lay.addWidget(fmt_grp)

        # ── Sections ──────────────────────────────────────────────────────────
        sec_grp = QGroupBox("Include Sections")
        sec_lay = QVBoxLayout(sec_grp)
        self._chk = {}
        sections = [
            ("seismic",   "🌍  Seismic Analysis  (NBC 105:2025 §4–6)"),
            ("load",      "📦  Load Calculations  (IS 875 Part 1 & 2)"),
            ("slab",      "▦   Slab Design  (IS 456:2000)"),
            ("beam",      "━   Beam Design  (IS 456:2000 §23, §38–41)"),
            ("column",    "⬛  Column Design  (IS 456:2000 §39 + NBC 105 Annex A)"),
            ("footing",   "⬛  Footing Design  (IS 456:2000 §34 + NBC 105:2025 §3.8)"),
        ]
        for key, label in sections:
            chk = QCheckBox(label)
            chk.setChecked(True)
            self._chk[key] = chk
            sec_lay.addWidget(chk)
        lay.addWidget(sec_grp)

        # ── Format note ───────────────────────────────────────────────────────
        self._note = QLabel("")
        self._note.setWordWrap(True)
        self._note.setStyleSheet("color: #595959; font-size: 9pt; padding: 4px 8px;")
        lay.addWidget(self._note)
        self._on_fmt_changed(0)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_lay = QHBoxLayout()
        ok = QPushButton("Export…")
        ok.setDefault(True)
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btn_lay.addStretch()
        btn_lay.addWidget(ok)
        btn_lay.addWidget(cancel)
        lay.addLayout(btn_lay)

    def _on_fmt_changed(self, idx):
        notes = [
            "Excel: Multi-sheet workbook — Summary, Seismic calculations with story force table, "
            "Beam design with all IS 456 checks, Column biaxial interaction, Foundation design, "
            "Load combinations. Live Excel formulas where applicable.",
            "Word: Professional A4 document with cover page, project info header/footer, "
            "table of contents (detailed mode), all calculations with formula derivations "
            "and clause references. Suitable for design report submission.",
            "Text: Simple plain-text report for quick reference or archiving.",
        ]
        self._note.setText(notes[idx])

    def get_selection(self):
        """Returns (sections: list[str], format: str, mode: str)."""
        sections = [k for k, c in self._chk.items() if c.isChecked()]
        idx = self._fmt.currentIndex()
        fmt = ["Excel", "Word", "Text"][idx]
        mode = "summary" if self._mode_bg.checkedId() == 1 else "detailed"
        return sections, fmt, mode
