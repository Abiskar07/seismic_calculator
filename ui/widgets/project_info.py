"""ui/widgets/project_info.py — Project header bar shown across all exports."""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox,
)
from datetime import date


class ProjectInfoBar(QWidget):
    """Compact project info strip — shown at top of main window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(12)

        g = QGroupBox("Project Information")
        gl = QGridLayout(g); gl.setVerticalSpacing(4); gl.setHorizontalSpacing(8)

        self._proj_name  = QLineEdit(); self._proj_name.setPlaceholderText("Project name / address")
        self._engineer   = QLineEdit(); self._engineer.setPlaceholderText("Engineer name")
        self._job_no     = QLineEdit(); self._job_no.setPlaceholderText("Job / Ref no.")
        self._date_edit  = QLineEdit(date.today().strftime("%Y-%m-%d"))
        self._checked_by = QLineEdit(); self._checked_by.setPlaceholderText("Checked by")

        for i, (lbl, w) in enumerate([
            ("Project:",   self._proj_name),
            ("Engineer:",  self._engineer),
            ("Job No.:",   self._job_no),
            ("Date:",      self._date_edit),
            ("Checked by:",self._checked_by),
        ]):
            gl.addWidget(QLabel(lbl), 0, i*2)
            gl.addWidget(w,           0, i*2+1)

        for col in range(1, 10, 2):
            gl.setColumnStretch(col, 1)
        lay.addWidget(g)

    def get_info(self) -> dict:
        return {
            "project":    self._proj_name.text().strip(),
            "engineer":   self._engineer.text().strip(),
            "job_no":     self._job_no.text().strip(),
            "date":       self._date_edit.text().strip(),
            "checked_by": self._checked_by.text().strip(),
        }
