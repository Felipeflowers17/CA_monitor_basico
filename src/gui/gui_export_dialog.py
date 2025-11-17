# -*- coding: utf-8 -*-
"""
Diálogo para configurar las opciones de exportación.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QRadioButton, 
    QDialogButtonBox, QFormLayout
)
from PySide6.QtCore import Slot

class GuiExportDialog(QDialog):
    def __init__(self, current_tab_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opciones de Exportación")
        self.setMinimumWidth(350)
        
        self.current_tab_name = current_tab_name

        # Layout principal
        layout = QVBoxLayout(self)

        # Grupo de Formato
        format_group = QGroupBox("Formato de Archivo")
        format_layout = QVBoxLayout()
        self.radio_excel = QRadioButton("Excel (.xlsx)")
        self.radio_csv = QRadioButton("CSV (.csv)")
        self.radio_excel.setChecked(True)
        format_layout.addWidget(self.radio_excel)
        format_layout.addWidget(self.radio_csv)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # Grupo de Alcance
        scope_group = QGroupBox("Alcance de la Exportación")
        scope_layout = QVBoxLayout()
        self.radio_all_tabs = QRadioButton("Exportar todas las pestañas")
        self.radio_current_tab = QRadioButton(f"Exportar solo pestaña actual ({current_tab_name})")
        self.radio_all_tabs.setChecked(True)
        scope_layout.addWidget(self.radio_all_tabs)
        scope_layout.addWidget(self.radio_current_tab)
        scope_group.setLayout(scope_layout)
        layout.addWidget(scope_group)

        # Botones de Aceptar/Cancelar
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_options(self) -> dict:
        """Devuelve un diccionario con las opciones seleccionadas."""
        return {
            "format": "excel" if self.radio_excel.isChecked() else "csv",
            "scope": "all" if self.radio_all_tabs.isChecked() else "current",
            "tab_name": self.current_tab_name
        }