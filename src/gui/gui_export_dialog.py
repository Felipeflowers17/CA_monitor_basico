# -*- coding: utf-8 -*-
"""
Diálogo de Exportación (Moderno).
"""

from PySide6.QtCore import Slot
from qfluentwidgets import MessageBoxBase, SubtitleLabel, RadioButton, BodyLabel

class GuiExportDialog(MessageBoxBase):
    def __init__(self, current_tab_name: str, parent=None):
        super().__init__(parent)
        self.current_tab_name = current_tab_name
        self.titleLabel = SubtitleLabel("Opciones de Exportación", self)
        
        # Widgets
        self.lbl_format = BodyLabel("Formato de Archivo:", self)
        self.radio_excel = RadioButton("Excel (.xlsx)", self)
        self.radio_csv = RadioButton("CSV (.csv)", self)
        self.radio_excel.setChecked(True)
        
        self.lbl_scope = BodyLabel("Alcance:", self)
        self.radio_all = RadioButton("Todas las pestañas", self)
        self.radio_curr = RadioButton(f"Solo actual ({current_tab_name})", self)
        self.radio_all.setChecked(True)
        
        # Layout
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(10)
        
        self.viewLayout.addWidget(self.lbl_format)
        self.viewLayout.addWidget(self.radio_excel)
        self.viewLayout.addWidget(self.radio_csv)
        
        self.viewLayout.addSpacing(15)
        
        self.viewLayout.addWidget(self.lbl_scope)
        self.viewLayout.addWidget(self.radio_all)
        self.viewLayout.addWidget(self.radio_curr)
        
        self.yesButton.setText("Exportar")
        self.cancelButton.setText("Cancelar")
        
    def get_options(self) -> dict:
        return {
            "format": "excel" if self.radio_excel.isChecked() else "csv",
            "scope": "all" if self.radio_all.isChecked() else "current",
            "tab_name": self.current_tab_name
        }