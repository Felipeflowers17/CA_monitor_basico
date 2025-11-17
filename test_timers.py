# -*- coding: utf-8 -*-
"""
Script de Prueba Rápida para el Piloto Automático (Timers).

Este script crea una 'MainWindow' Falsa que usa los Mixins REALES
(ThreadingMixin, MainSlotsMixin) pero con servicios 'falsos' (Mocks)
para probar la lógica del temporizador y el anti-bloqueo.
"""

import sys
import time
import datetime
from typing import List

# Importaciones Reales de PySide6
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import QThreadPool, QTimer, Slot

# --- Importaciones REALES de tu proyecto ---
# (Asumimos que test_timers.py está en la raíz, junto a 'src')
try:
    from src.gui.gui_worker import Worker
    from src.gui.mixins.threading_mixin import ThreadingMixin
    from src.gui.mixins.main_slots_mixin import MainSlotsMixin
except ImportError:
    print("Error: No se pudieron importar los mixins. Asegúrate de que este script")
    print("esté en la carpeta raíz de tu proyecto (junto a 'run_app.py').")
    sys.exit(1)

# ---
# --- Mocks (Servicios Falsos para la Prueba) ---
# ---

class MockLogger:
    """Logger falso que solo imprime a la consola."""
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")

class MockEtlService:
    """
    Servicio ETL falso. Sus tareas 'duermen' para simular
    un trabajo largo (ej. scraping de 5 segundos).
    """
    def __init__(self, logger):
        self.logger = logger

    def run_etl_live_to_db(self, *args, **kwargs):
        """Simula la TAREA 1 (Búsqueda Diaria)"""
        self.logger.info("--- (TAREA 1 - FASE 1) INICIADA ---")
        self.logger.info("   ... simulando scraping (5 segundos)...")
        time.sleep(5)
        self.logger.info("--- (TAREA 1 - FASE 1) TERMINADA ---")

    def run_fase2_update(self, *args, **kwargs):
        """Simula la TAREA 2 (Actualización de Fichas)"""
        self.logger.info("--- (TAREA 2 - FASE 2) INICIADA ---")
        self.logger.info("   ... simulando scraping (5 segundos)...")
        time.sleep(5)
        self.logger.info("--- (TAREA 2 - FASE 2) TERMINADA ---")


# ---
# --- Ventana de Prueba ---
# ---

class TestWindow(QMainWindow, ThreadingMixin, MainSlotsMixin):
    """
    Una MainWindow falsa que hereda los Mixins REALES de hilos y slots
    para probar la lógica de automatización.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test de Piloto Automático")
        self.setGeometry(300, 300, 500, 200)

        # Configuración del ThreadingMixin REAL
        self.thread_pool = QThreadPool.globalInstance()
        self.running_workers: List['Worker'] = []
        self.is_task_running = False
        self.last_error: Exception | None = None
        
        # Inyectar los Mocks
        self.logger = MockLogger()
        self.etl_service = MockEtlService(self.logger)
        
        # Mocks para funciones que los Mixins esperan que existan
        self.on_progress_update = lambda msg: self.logger.info(f"[UI-Progress] {msg}")
        self.set_ui_busy = lambda busy: self.logger.info(f"[UI-BUSY] {busy}")
        self.on_load_data_thread = lambda: self.logger.info("[UI] Refrescando datos...")

        # Configurar Timers REALES
        self.timer_fase1 = QTimer(self)
        self.timer_fase2 = QTimer(self)
        
        # Conectar Timers a los Slots REALES del MainSlotsMixin
        self.timer_fase1.timeout.connect(self.on_start_full_scraping_auto)
        self.timer_fase2.timeout.connect(self.on_run_fase2_update_thread_auto)

        # UI simple para la prueba
        layout = QVBoxLayout()
        layout.addWidget(QLabel(
            "Revisa la consola.\n"
            "Tarea 1 (Fase 1) se dispara cada 4 segundos.\n"
            "Tarea 2 (Fase 2) se dispara cada 6 segundos.\n"
            "Ambas tareas duran 5 segundos.\n\n"
            "¡Observa cómo una tarea OMITE su ejecución si la otra está activa!"
        ))
        qbtn = QPushButton("Cerrar Prueba", self)
        qbtn.clicked.connect(QApplication.instance().quit)
        layout.addWidget(qbtn)
        
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def start_test_timers(self):
        """Inicia los timers con intervalos rápidos para la prueba."""
        
        # Tarea 1 (Fase 1) se dispara cada 4 segundos
        intervalo_f1 = 4000 
        # Tarea 2 (Fase 2) se dispara cada 6 segundos
        intervalo_f2 = 6000
        # Ambas tareas duran 5 segundos (ver MockEtlService)
        
        print("\n--- INICIANDO SIMULACIÓN (Cerrar ventana para parar) ---")
        self.timer_fase1.start(intervalo_f1)
        self.timer_fase2.start(intervalo_f2)

    # --- Slots Falsos (solo para que los mixins no fallen) ---
    
    def on_task_error(self, ex, title="Error de Tarea"):
        """Callback de error simple."""
        self.logger.error(f"¡ERROR EN HILO! {title}: {ex}")

# ---
# --- Punto de Entrada ---
# ---
if __name__ == "__main__":
    # Necesitamos una QApplication para que los QTimers funcionen
    app = QApplication(sys.argv)
    
    # Crear e iniciar la ventana de prueba
    window = TestWindow()
    window.show()
    
    # Iniciar los timers después de mostrar la ventana
    window.start_test_timers()
    
    # Ejecutar el bucle de la aplicación
    sys.exit(app.exec())