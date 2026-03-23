"""ui/dialogs/about_dialog.py"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        from constants import APP_NAME, APP_VERSION # type: ignore
        self.setWindowTitle(f"About — {APP_NAME}")
        self.setModal(True); self.resize(440, 320)
        if parent and hasattr(parent, "styleSheet"):
            self.setStyleSheet(parent.styleSheet())
        lay = QVBoxLayout(self)
        txt = QTextEdit(readOnly=True)
        txt.setHtml(f"""
        <style>body{{font-family:'Segoe UI',Arial;font-size:10pt;}}
        h2{{color:#5E81AC;}}p{{margin:4px 0;}}</style>
        <h2>{APP_NAME} {APP_VERSION}</h2>
        <p><b>Standards:</b></p>
        <ul>
          <li>NBC 105:2025 — Seismic Design of Buildings in Nepal (2nd Revision)</li>
          <li>IS 456:2000 — Plain and Reinforced Concrete</li>
          <li>IS 875 Part 1 &amp; 2 — Dead and Imposed Loads</li>
        </ul>
        <p><b>Developer:</b> Abiskar Acharya</p>
        <p><b>Features:</b> Seismic ESM/MRSM · Two-way slab design · Beam design ·
           ft′in″ unit conversion · Dark/Light theme · Export to CSV/PDF/Text ·
           Save/Load JSON projects · Persistent settings</p>
        <p style="color:#BF616A;font-size:9pt;margin-top:12px;">
        For educational and reference use only.  Not a substitute for professional
        structural engineering judgement.  Always verify against current code provisions.</p>
        """)
        lay.addWidget(txt)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        lay.addWidget(close)
