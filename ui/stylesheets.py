"""
ui/stylesheets.py — Theme-aware stylesheets.
Result labels use the application palette (no hardcoded colors) so they
remain readable in both dark and light mode.
"""

DARK = """
QWidget {
    background-color: #2E3440;
    color: #ECEFF4;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}
QMainWindow, QDialog { background-color: #2E3440; }
QScrollArea { background-color: #2E3440; border: none; }
QScrollArea > QWidget > QWidget { background-color: #2E3440; }

QTabWidget::pane {
    border: 1px solid #4C566A;
    border-radius: 5px;
    background-color: #3B4252;
}
QTabBar::tab {
    background-color: #434C5E; color: #D8DEE9;
    padding: 10px 22px;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
    border: 1px solid #4C566A; border-bottom: none; margin-right: 2px;
    font-size: 10pt;
}
QTabBar::tab:selected { background-color: #5E81AC; color: #ECEFF4; font-weight: bold; }
QTabBar::tab:!selected:hover { background-color: #4C566A; }

QGroupBox {
    font-weight: bold; color: #88C0D0;
    border: 1px solid #4C566A; border-radius: 6px; margin-top: 14px;
    padding-top: 6px;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 2px 10px; margin-left: 10px;
    background-color: #3B4252; border-radius: 3px; color: #88C0D0;
}
QLabel { color: #ECEFF4; }
QLabel[class="result"] { color: #ECEFF4; font-weight: bold; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #434C5E; border: 1px solid #4C566A;
    border-radius: 4px; padding: 5px 7px; min-height: 22px; color: #ECEFF4;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #88C0D0; }
QLineEdit:disabled { background-color: #3B4252; color: #4C566A; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #434C5E; selection-background-color: #5E81AC;
    color: #ECEFF4; border: 1px solid #4C566A; outline: none;
}
QPushButton {
    background-color: #5E81AC; color: #ECEFF4; font-weight: bold;
    border: none; border-radius: 5px; padding: 7px 16px; min-width: 90px;
}
QPushButton:hover   { background-color: #81A1C1; }
QPushButton:pressed { background-color: #4C6F96; }
QPushButton:disabled{ background-color: #3B4252; color: #616E82; }

QTreeWidget, QTableWidget {
    background-color: #3B4252; border: 1px solid #4C566A;
    border-radius: 4px; color: #D8DEE9;
    alternate-background-color: #434C5E; gridline-color: #4C566A;
}
QTableWidget::item { color: #D8DEE9; padding: 2px 4px; }
QTableWidget::item:selected { background-color: #5E81AC; color: #ECEFF4; }
QHeaderView::section {
    background-color: #4C566A; color: #ECEFF4;
    padding: 5px; border: 1px solid #3B4252; font-weight: bold;
}
QCheckBox, QRadioButton { color: #ECEFF4; spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator { width: 17px; height: 17px; }
QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
    border: 2px solid #4C566A; background-color: #434C5E; border-radius: 3px;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    border: 2px solid #5E81AC; background-color: #5E81AC; border-radius: 3px;
}
QScrollBar:vertical { border:none; background:#434C5E; width:10px; }
QScrollBar::handle:vertical { background:#5E81AC; min-height:20px; border-radius:5px; }
QScrollBar::handle:vertical:hover { background:#81A1C1; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
QScrollBar:horizontal { border:none; background:#434C5E; height:10px; }
QScrollBar::handle:horizontal { background:#5E81AC; min-width:20px; border-radius:5px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0px; }
QToolTip { background-color:#434C5E; color:#ECEFF4; border:1px solid #5E81AC; padding:5px; border-radius:3px; }
QStatusBar { background-color:#3B4252; color:#D8DEE9; border-top:1px solid #4C566A; }
QStatusBar::item { border:none; }
QMenuBar { background-color:#3B4252; color:#ECEFF4; border-bottom:1px solid #4C566A; }
QMenuBar::item { background:transparent; padding:4px 10px; border-radius:3px; margin:2px; }
QMenuBar::item:selected { background-color:#5E81AC; }
QMenu { background-color:#3B4252; color:#ECEFF4; border:1px solid #4C566A; padding:2px; }
QMenu::item { padding:5px 22px; border-radius:3px; margin:1px; }
QMenu::item:selected { background-color:#5E81AC; }
QMenu::separator { height:1px; background:#4C566A; margin:2px 8px; }
QTextEdit { background-color:#3B4252; color:#ECEFF4; border:1px solid #4C566A; border-radius:4px; }
QMessageBox { background-color:#3B4252; }
QMessageBox QLabel { color:#ECEFF4; }
QFrame[frameShape="4"], QFrame[frameShape="5"] { color: #4C566A; }
"""

LIGHT = """
QWidget {
    background-color: #F2F4F8;
    color: #1A1E2E;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}
QMainWindow, QDialog { background-color: #F2F4F8; }
QScrollArea { background-color: #F2F4F8; border: none; }
QScrollArea > QWidget > QWidget { background-color: #F2F4F8; }

QTabWidget::pane { background-color: #FFFFFF; border: 1px solid #C8D0DC; border-radius:5px; }
QTabBar::tab {
    background-color: #E4E8F0; color: #1A1E2E;
    padding: 10px 22px; border-top-left-radius:6px; border-top-right-radius:6px;
    border:1px solid #C8D0DC; border-bottom:none; margin-right:2px;
}
QTabBar::tab:selected { background-color: #1565C0; color: #FFFFFF; font-weight:bold; }
QTabBar::tab:!selected:hover { background-color: #D0D8E8; }

QGroupBox {
    font-weight: bold; color: #1565C0;
    border: 1px solid #B0BAD0; border-radius:6px; margin-top:14px; padding-top:6px;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 2px 10px; margin-left: 10px;
    background-color: #E4E8F0; border-radius:3px; color:#1565C0;
}
QLabel { color: #1A1E2E; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF; border: 1px solid #B0BAD0;
    border-radius: 4px; padding: 5px 7px; min-height: 22px; color: #1A1E2E;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #1565C0; }
QLineEdit:disabled { background-color: #E8ECF4; color: #909AAA; }
QComboBox::drop-down { border:none; width:20px; }
QComboBox QAbstractItemView {
    background-color: #FFFFFF; selection-background-color: #1565C0;
    color: #1A1E2E; border: 1px solid #B0BAD0; outline:none;
}
QPushButton {
    background-color: #1565C0; color: #FFFFFF; font-weight: bold;
    border: none; border-radius: 5px; padding: 7px 16px; min-width: 90px;
}
QPushButton:hover   { background-color: #1976D2; }
QPushButton:pressed { background-color: #0D47A1; }
QPushButton:disabled{ background-color: #C8D0DC; color: #909AAA; }

QTreeWidget, QTableWidget {
    background-color: #FFFFFF; border: 1px solid #B0BAD0;
    border-radius: 4px; color: #1A1E2E;
    alternate-background-color: #F0F3FA; gridline-color: #D0D8E8;
}
QTableWidget::item { color: #1A1E2E; padding: 2px 4px; }
QTableWidget::item:selected { background-color: #1565C0; color: #FFFFFF; }
QHeaderView::section {
    background-color: #2E5FA3; color: #FFFFFF;
    padding: 5px; border: 1px solid #B0BAD0; font-weight: bold;
}
QCheckBox, QRadioButton { color: #1A1E2E; spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator { width: 17px; height: 17px; }
QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
    border: 2px solid #B0BAD0; background-color: #FFFFFF; border-radius: 3px;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    border: 2px solid #1565C0; background-color: #1565C0; border-radius: 3px;
}
QScrollBar:vertical { border:none; background:#E4E8F0; width:10px; }
QScrollBar::handle:vertical { background:#1565C0; min-height:20px; border-radius:5px; }
QScrollBar::handle:vertical:hover { background:#1976D2; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
QScrollBar:horizontal { border:none; background:#E4E8F0; height:10px; }
QScrollBar::handle:horizontal { background:#1565C0; min-width:20px; border-radius:5px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0px; }
QToolTip { background-color:#FFFFFF; color:#1A1E2E; border:1px solid #1565C0; padding:5px; border-radius:3px; }
QStatusBar { background-color:#E4E8F0; color:#1A1E2E; border-top:1px solid #B0BAD0; }
QStatusBar::item { border:none; }
QMenuBar { background-color:#E4E8F0; color:#1A1E2E; border-bottom:1px solid #B0BAD0; }
QMenuBar::item { background:transparent; padding:4px 10px; border-radius:3px; margin:2px; }
QMenuBar::item:selected { background-color:#1565C0; color:#FFFFFF; }
QMenu { background-color:#FFFFFF; color:#1A1E2E; border:1px solid #B0BAD0; padding:2px; }
QMenu::item { padding:5px 22px; border-radius:3px; margin:1px; }
QMenu::item:selected { background-color:#1565C0; color:#FFFFFF; }
QMenu::separator { height:1px; background:#B0BAD0; margin:2px 8px; }
QTextEdit { background-color:#FFFFFF; color:#1A1E2E; border:1px solid #B0BAD0; border-radius:4px; }
QMessageBox { background-color:#F2F4F8; }
QMessageBox QLabel { color:#1A1E2E; }
QFrame[frameShape="4"], QFrame[frameShape="5"] { color: #B0BAD0; }
"""
