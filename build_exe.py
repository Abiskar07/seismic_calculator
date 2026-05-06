"""
PyInstaller build script with proper data files and hidden imports
"""
import PyInstaller.__main__
import sys

# List of data files to include (source:destination in exe)
datas = [
    ('Building codes', 'Building codes'),  # Include the Building codes folder
    ('constants', 'constants'),             # Include constants folder resources
]

# Hidden imports that PyInstaller might miss
hidden_imports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'openpyxl',
    'docx',
    'constants.is456_data',
    'constants.nbc105_2025_data',
    'constants.structural_systems',
    'constants.load_data',
]

# Build command
PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--windowed',
    '--name=Seismic Calculator',
    '--icon=NONE',
    *[f'--add-data={src}{":"}{dest}' for src, dest in datas],
    *[f'--hidden-import={imp}' for imp in hidden_imports],
])
