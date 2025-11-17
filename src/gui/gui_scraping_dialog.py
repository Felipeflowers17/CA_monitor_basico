# -*- coding: utf-8 -*-
"""
Diálogo de Configuración de Scraping.

Este archivo define el QDialog (ventana emergente) que permite
al usuario configurar y lanzar una nueva tarea de scraping.

"""

from datetime import date

from PySide6.QtCore import QDate, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)


class ScrapingDialog(QDialog):
    """
    Ventana de diálogo modal para configurar los parámetros
    de un nuevo proceso de scraping.
    """

    # Esta señal se emitirá cuando el usuario haga clic en "Ejecutar".
    # Enviará un diccionario (dict) con la configuración.
    start_scraping = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        """
        Inicializa el diálogo.

        """
        super().__init__(parent)
        self.setWindowTitle("Configurar Nuevo Scraping")
        self.setModal(True)  # Bloquea la ventana principal
        self.setMinimumWidth(400)

        # --- Layout Principal ---
        layout = QVBoxLayout(self)

        # --- 1. Rango de Fechas ---
        layout.addWidget(QLabel("Seleccione el rango de fechas a buscar:"))
        fechas_layout = QHBoxLayout()

        # Fecha Desde
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(
            QDate.currentDate().addDays(-7)
        )  # Por defecto: 7 días atrás
        fechas_layout.addWidget(QLabel("Desde:"))
        fechas_layout.addWidget(self.date_from)

        # Fecha Hasta
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())  # Por defecto: hoy
        fechas_layout.addWidget(QLabel("Hasta:"))
        fechas_layout.addWidget(self.date_to)

        layout.addLayout(fechas_layout)

        # --- 2. Límite de Páginas ---
        layout.addSpacing(10)
        layout.addWidget(QLabel("Límite de páginas a scrapear (0 = sin límite):"))
        self.limit_pages = QSpinBox()
        self.limit_pages.setMinimum(0)
        self.limit_pages.setMaximum(1000)
        self.limit_pages.setValue(0)  # Por defecto: sin límite
        layout.addWidget(self.limit_pages)

        # --- 3. Modo de Ejecución ---
        layout.addSpacing(10)
        layout.addWidget(QLabel("Modo de ejecución:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem(
            "Procesar y Guardar en Base de Datos (Recomendado)", "to_db"
        )
        self.mode_combo.addItem(
            "Solo Guardar Datos Crudos en JSON (Para depuración)", "to_json"
        )
        layout.addWidget(self.mode_combo)

        # --- Separador ---
        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(linea)

        # --- 4. Botones (Aceptar / Cancelar) ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Ejecutar")

        # Conectar las señales de los botones
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)  # self.reject cierra el diálogo

        layout.addWidget(button_box)

    @Slot()
    def on_accept(self):
        """
        Se llama cuando el usuario hace clic en "Ejecutar".
        Recopila los datos, los emite en la señal y cierra el diálogo.
        """
        logger.debug("Diálogo de scraping aceptado por el usuario.")

        # 1. Recopilar los datos de los widgets
        date_from: date = self.date_from.date().toPython()
        date_to: date = self.date_to.date().toPython()
        max_paginas: int = self.limit_pages.value()
        mode: str = self.mode_combo.currentData()

        # 2. Crear el diccionario de configuración
        config = {
            "date_from": date_from,
            "date_to": date_to,
            "max_paginas": max_paginas,
            "mode": mode,
        }

        logger.info(f"Configuración de scraping generada: {config}")

        # 3. Emitir la señal con el diccionario
        self.start_scraping.emit(config)

        # 4. Aceptar y cerrar el diálogo
        self.accept()


# --- Prueba rápida (se ejecuta solo si corres este archivo directamente) ---
if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication, QMainWindow

    # Se necesita una App y una Ventana para probar un Diálogo
    app = QApplication(sys.argv)
    ventana_prueba = QMainWindow()
    ventana_prueba.show()

    dialog = ScrapingDialog(ventana_prueba)

    # Conectar la señal a una función de prueba (lambda)
    dialog.start_scraping.connect(lambda config: print(f"SEÑAL RECIBIDA: {config}"))

    dialog.exec()  # Mostrar el diálogo

    logger.info("Diálogo cerrado.")
    sys.exit(app.exec())
