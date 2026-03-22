#!/usr/bin/env python3
"""
main.py
────────
Entry point for the Structural Calculator.

Usage:
    python main.py

Requirements:
    PyQt6 >= 6.4
    Python >= 3.10
"""
import sys
import os

# Make sure the project root is on sys.path when running directly
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from ui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Structural Calculator")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Abiskar Acharya")

    # Slightly improved default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
