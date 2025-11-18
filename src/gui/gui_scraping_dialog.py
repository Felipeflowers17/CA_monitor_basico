# -*- coding: utf-8 -*-
"""
Diálogo de Configuración de Scraping (Moderno y Funcional).
"""

from datetime import date
from PySide6.QtCore import QDate, Signal, Slot, Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QWidget

# FLUENT WIDGETS
from qfluentwidgets import (
    SubtitleLabel, BodyLabel, CalendarPicker, 
    SpinBox, ComboBox, PrimaryPushButton, PushButton
)

from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)


class ScrapingDialog(QDialog):
    """
    Ventana de diálogo moderna para configurar scraping.
    Usa QDialog estándar para evitar conflictos de eventos con los popups,
    pero implementa widgets de Fluent UI para el estilo.
    """

    start_scraping = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Nuevo Scraping")
        self.resize(450, 400)
        
        # Fondo blanco/oscuro según tema (Fluent style)
        self.setObjectName("ScrapingDialog")
        # Estilo básico para que no se vea gris antiguo (Qt StyleSheet)
        self.setStyleSheet("""
            QDialog {
                background-color: palette(window);
            }
        """)

        # Layout Principal
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(24, 24, 24, 24)
        self.mainLayout.setSpacing(16)

        # Título
        self.titleLabel = SubtitleLabel("Parámetros de Búsqueda", self)
        self.mainLayout.addWidget(self.titleLabel)

        # --- SECCIÓN FECHAS ---
        
        # Contenedor de fechas
        self.datesContainer = QWidget()
        self.datesLayout = QHBoxLayout(self.datesContainer)
        self.datesLayout.setContentsMargins(0, 0, 0, 0)
        
        # Desde
        self.vboxFrom = QVBoxLayout()
        self.lblFrom = BodyLabel("Desde:", self)
        self.dateFromPicker = CalendarPicker(self)
        self.dateFromPicker.setDate(QDate.currentDate().addDays(-7))
        self.dateFromPicker.setDateFormat(Qt.ISODate) # Formato yyyy-MM-dd
        self.vboxFrom.addWidget(self.lblFrom)
        self.vboxFrom.addWidget(self.dateFromPicker)
        
        # Hasta
        self.vboxTo = QVBoxLayout()
        self.lblTo = BodyLabel("Hasta:", self)
        self.dateToPicker = CalendarPicker(self)
        self.dateToPicker.setDate(QDate.currentDate())
        self.dateToPicker.setDateFormat(Qt.ISODate)
        self.vboxTo.addWidget(self.lblTo)
        self.vboxTo.addWidget(self.dateToPicker)
        
        self.datesLayout.addLayout(self.vboxFrom)
        self.datesLayout.addSpacing(20)
        self.datesLayout.addLayout(self.vboxTo)
        
        self.mainLayout.addWidget(self.datesContainer)

        # --- SECCIÓN LÍMITE ---
        self.vboxLimit = QVBoxLayout()
        self.lblLimit = BodyLabel("Límite de páginas (0 = Todo):", self)
        self.pageLimitSpin = SpinBox(self)
        self.pageLimitSpin.setRange(0, 1000)
        self.pageLimitSpin.setValue(0)
        self.vboxLimit.addWidget(self.lblLimit)
        self.vboxLimit.addWidget(self.pageLimitSpin)
        
        self.mainLayout.addLayout(self.vboxLimit)

        # --- SECCIÓN MODO (GUARDAR EN) ---
        self.vboxMode = QVBoxLayout()
        self.lblMode = BodyLabel("Guardar en:", self) # Texto corregido
        self.modeCombo = ComboBox(self)
        self.modeCombo.addItem("En la BD")          # Opción 1
        self.modeCombo.addItem("En formato json")   # Opción 2
        self.modeCombo.setCurrentIndex(0)
        self.vboxMode.addWidget(self.lblMode)
        self.vboxMode.addWidget(self.modeCombo)
        
        self.mainLayout.addLayout(self.vboxMode)

        self.mainLayout.addStretch(1) # Empujar botones al fondo

        # --- BOTONES ---
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.addStretch(1)
        
        self.btnCancel = PushButton("Cancelar", self)
        self.btnRun = PrimaryPushButton("Ejecutar", self)
        
        self.buttonLayout.addWidget(self.btnCancel)
        self.buttonLayout.addWidget(self.btnRun)
        
        self.mainLayout.addLayout(self.buttonLayout)

        # Conexiones
        self.btnRun.clicked.connect(self.on_accept)
        self.btnCancel.clicked.connect(self.reject)

    @Slot()
    def on_accept(self):
        logger.debug("Diálogo scraping aceptado.")
        
        # Recopilar datos
        try:
            # .date devuelve un QDate, usamos toPython() para obtener datetime.date
            date_from = self.dateFromPicker.date.toPython()
            date_to = self.dateToPicker.date.toPython()
        except Exception:
            # Fallback por si la versión de la librería cambia comportamiento
            date_from = self.dateFromPicker.getDate().toPython()
            date_to = self.dateToPicker.getDate().toPython()

        max_paginas = self.pageLimitSpin.value()
        
        # Mapeo del índice seleccionado al código interno
        mode_idx = self.modeCombo.currentIndex()
        mode = "to_db" if mode_idx == 0 else "to_json"

        config = {
            "date_from": date_from,
            "date_to": date_to,
            "max_paginas": max_paginas,
            "mode": mode,
        }
        
        self.start_scraping.emit(config)
        self.accept()