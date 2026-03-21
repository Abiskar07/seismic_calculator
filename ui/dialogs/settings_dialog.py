"""ui/dialogs/settings_dialog.py"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QCheckBox, QPushButton, QHBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(400, 240)
        layout = QVBoxLayout(self)

        theme_group = QGroupBox("Theme")
        tl = QVBoxLayout(theme_group)
        self.dark_mode = QCheckBox("Dark Mode")
        self.dark_mode.setChecked(True)
        tl.addWidget(self.dark_mode)

        calc_group = QGroupBox("Calculation")
        cl = QVBoxLayout(calc_group)
        self.auto_calc      = QCheckBox("Auto-calculate on input change")
        self.show_tooltips  = QCheckBox("Show detailed tooltips")
        self.auto_calc.setChecked(True)
        self.show_tooltips.setChecked(True)
        cl.addWidget(self.auto_calc)
        cl.addWidget(self.show_tooltips)

        export_group = QGroupBox("Export")
        el = QVBoxLayout(export_group)
        self.include_formulas = QCheckBox("Include formulas in export")
        el.addWidget(self.include_formulas)

        btn_layout = QHBoxLayout()
        ok_btn     = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addWidget(theme_group)
        layout.addWidget(calc_group)
        layout.addWidget(export_group)
        layout.addLayout(btn_layout)
