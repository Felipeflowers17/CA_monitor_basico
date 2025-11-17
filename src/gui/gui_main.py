# -*- coding: utf-8 -*-
"""
Ventana Principal de la Aplicación (MainWindow).


"""

import sys
from typing import List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QStatusBar, QTableView, QLineEdit,
    QMenu, QMessageBox, QSystemTrayIcon, QStyle, QProgressBar 
)
from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtGui import QAction, QStandardItemModel, QIcon 
from src.gui.gui_worker import Worker
from src.utils.logger import configurar_logger
from src.utils.settings_manager import SettingsManager
from src.db.session import SessionLocal
from src.db.db_service import DbService
from src.logic.etl_service import EtlService
from src.logic.excel_service import ExcelService
from src.logic.score_engine import ScoreEngine
from src.scraper.scraper_service import ScraperService
from .mixins.threading_mixin import ThreadingMixin
from .mixins.main_slots_mixin import MainSlotsMixin
from .mixins.data_loader_mixin import DataLoaderMixin
from .mixins.context_menu_mixin import ContextMenuMixin
from .mixins.table_manager_mixin import TableManagerMixin

logger = configurar_logger(__name__)

class MainWindow(
    QMainWindow,
    ThreadingMixin,
    MainSlotsMixin,
    DataLoaderMixin,
    ContextMenuMixin,
    TableManagerMixin
):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Compras Ágiles (v3.0 Dinámico)")
        self.setGeometry(100, 100, 1200, 700)
        self.thread_pool = QThreadPool.globalInstance()
        self.running_workers: List['Worker'] = []
        self.is_task_running = False
        self.last_error: Exception | None = None
        self.last_export_path: str | None = None
        try:
            self.settings_manager = SettingsManager()
            self.db_service = DbService(SessionLocal)
            self.scraper_service = ScraperService()
            self.excel_service = ExcelService(self.db_service)
            self.score_engine = ScoreEngine(self.db_service) 
            self.etl_service = EtlService(
                self.db_service, self.scraper_service, self.score_engine
            )
        except Exception as e:
            logger.critical(f"Error al inicializar los servicios: {e}")
            QMessageBox.critical( self, "Error Crítico de Inicialización", f"No se pudieron iniciar los servicios de la aplicación.\nVerifique la configuración (.env) y la conexión a la BD.\n\nError: {e}",)
            sys.exit(1)
        # --- Declaraciones de atributos (para el type-checker) ---
        self.refresh_button: QPushButton | None = None
        self.actions_menu_button: QPushButton | None = None
        self.action_update_fichas: QAction | None = None
        self.action_health_check: QAction | None = None 
        self.action_export_full_db: QAction | None = None
        self.last_health_check_ok: bool = False      
        self.table_tab1: QTableView | None = None
        self.table_tab2: QTableView | None = None
        self.table_tab3: QTableView | None = None
        self.table_tab4: QTableView | None = None
        self.model_tab1: QStandardItemModel | None = None
        self.model_tab2: QStandardItemModel | None = None
        self.model_tab3: QStandardItemModel | None = None
        self.model_tab4: QStandardItemModel | None = None
        self.search_tab1: QLineEdit | None = None
        self.search_tab2: QLineEdit | None = None
        self.search_tab3: QLineEdit | None = None
        self.search_tab4: QLineEdit | None = None
        self.timer_fase1: QTimer | None = None
        self.timer_fase2: QTimer | None = None
        self.tray_icon: QSystemTrayIcon | None = None
        
        self.progress_bar: QProgressBar | None = None
        
        self._setup_ui()
        self._connect_signals()
        self._setup_timers()
        logger.info("Ventana principal (GUI) inicializada.")
        self.on_load_data_thread() 

    def _setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refrescar Datos")
        self.refresh_button.setFixedHeight(40)
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        self.actions_menu_button = QPushButton("Acciones")
        self.actions_menu_button.setFixedHeight(40)
        self.actions_menu = QMenu(self)
        self.action_scrape = QAction("Iniciar Nuevo Scraping...", self)
        self.actions_menu.addAction(self.action_scrape)
        self.action_update_fichas = QAction("Actualizar Fichas (Tabs 2-4)", self)
        self.actions_menu.addAction(self.action_update_fichas)
        

        self.action_export = QAction("Exportar Pestañas a Reporte...", self)
        self.action_export.setToolTip("Exporta el contenido de las pestañas actuales a Excel o CSV.")
        self.actions_menu.addAction(self.action_export)

        
        self.actions_menu.addSeparator()
        self.config_submenu = QMenu("Configuración y Diagnóstico", self) 
        self.action_open_settings = QAction("Configuración y Automatización...", self)
        self.config_submenu.addAction(self.action_open_settings)
        self.action_recalculate = QAction("Recalcular Puntajes", self)
        self.config_submenu.addAction(self.action_recalculate)
        

        self.config_submenu.addSeparator()
        self.action_export_full_db = QAction("Exportar BD Completa a Excel...", self)
        self.action_export_full_db.setToolTip("Exporta todas las tablas de la base de datos a un solo archivo Excel.")
        self.config_submenu.addAction(self.action_export_full_db)
        self.config_submenu.addSeparator()

        
        self.action_health_check = QAction("Probar Conexión (Chequeo de Salud)...", self)
        self.action_health_check.setToolTip("Ejecuta una prueba rápida para verificar la conexión y el formato de datos.")
        self.config_submenu.addAction(self.action_health_check)
        self.actions_menu.addMenu(self.config_submenu)
        self.actions_menu_button.setMenu(self.actions_menu)
        button_layout.addWidget(self.actions_menu_button)
        main_layout.addLayout(button_layout)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        ( self.tab_candidatas, self.search_tab1, self.model_tab1, self.table_tab1, ) = self._crear_pestaña_tabla("Filtrar por Código, Nombre u Organismo...", "tab1_simple")
        self.tabs.addTab(self.tab_candidatas, "CAs Candidatas (Fase 1)")
        ( self.tab_relevantes, self.search_tab2, self.model_tab2, self.table_tab2, ) = self._crear_pestaña_tabla("Filtrar por Código, Nombre u Organismo...", "tab2_detallada")
        self.tabs.addTab(self.tab_relevantes, "CAs Relevantes (Fase 2)")
        ( self.tab_seguimiento, self.search_tab3, self.model_tab3, self.table_tab3, ) = self._crear_pestaña_tabla("Filtrar por Código, Nombre u Organismo...", "tab3_detallada")
        self.tabs.addTab(self.tab_seguimiento, "CAs en Seguimiento (Favoritos)")
        ( self.tab_ofertadas, self.search_tab4, self.model_tab4, self.table_tab4, ) = self._crear_pestaña_tabla("Filtrar por Código, Nombre u Organismo...", "tab4_detallada")
        self.tabs.addTab(self.tab_ofertadas, "CAs Ofertadas")
        self._setup_tray_icon()
        
        self.setStatusBar(QStatusBar(self))
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedSize(200, 18)
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.progress_bar.hide()
        
        self.statusBar().showMessage("Listo.")


    
    def _connect_signals(self):
        self.refresh_button.clicked.connect(self.on_load_data_thread)
        self.action_scrape.triggered.connect(self.on_open_scraping_dialog)
        self.action_update_fichas.triggered.connect(self.on_run_fase2_update_thread)
        
        self.action_export.triggered.connect(self.on_open_export_pestañas_dialog)
        self.action_export_full_db.triggered.connect(self.on_export_full_db_thread)
        
        self.action_open_settings.triggered.connect(self.on_open_settings_dialog)
        self.action_recalculate.triggered.connect(self.on_run_recalculate_thread)
        self.action_health_check.triggered.connect(self.on_run_health_check_thread)
        self.search_tab1.textChanged.connect(self.on_search_tab1_changed)
        self.search_tab2.textChanged.connect(self.on_search_tab2_changed)
        self.search_tab3.textChanged.connect(self.on_search_tab3_changed)
        self.search_tab4.textChanged.connect(self.on_search_tab4_changed)
        self.table_tab1.customContextMenuRequested.connect(self.mostrar_menu_contextual)
        self.table_tab2.customContextMenuRequested.connect(self.mostrar_menu_contextual)
        self.table_tab3.customContextMenuRequested.connect(self.mostrar_menu_contextual)
        self.table_tab4.customContextMenuRequested.connect(self.mostrar_menu_contextual)
    
    def _setup_timers(self):
        logger.info("Configurando timers de automatización...")
        self.timer_fase1 = QTimer(self)
        self.timer_fase1.timeout.connect(self.on_start_full_scraping_auto)
        self.timer_fase2 = QTimer(self)
        self.timer_fase2.timeout.connect(self.on_run_fase2_update_thread_auto)
        self.reload_timers_config()

    def reload_timers_config(self):
        try:
            self.settings_manager.load_settings()
            intervalo_f1_horas = self.settings_manager.get_setting("auto_fase1_intervalo_horas")
            if intervalo_f1_horas > 0:
                intervalo_ms = intervalo_f1_horas * 60 * 60 * 1000 
                self.timer_fase1.start(intervalo_ms)
                logger.info(f"Timer (Fase 1) iniciado. Se ejecutará cada {intervalo_f1_horas} horas.")
            else:
                self.timer_fase1.stop()
                logger.info("Timer (Fase 1) detenido (intervalo 0).")
            intervalo_f2_min = self.settings_manager.get_setting("auto_fase2_intervalo_minutos")
            if intervalo_f2_min > 0:
                intervalo_ms = intervalo_f2_min * 60 * 1000 
                self.timer_fase2.start(intervalo_ms)
                logger.info(f"Timer (Fase 2) iniciado. Se ejecutará cada {intervalo_f2_min} minutos.")
            else:
                self.timer_fase2.stop()
                logger.info("Timer (Fase 2) detenido (intervalo 0).")
        except Exception as e:
            logger.error(f"Error al configurar o (re)iniciar timers: {e}")
            
    def _setup_tray_icon(self):
        icon = QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Monitor de Compras Ágiles")
        tray_menu = QMenu(self)
        quit_action = QAction("Cerrar Aplicación", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        logger.info("Ícono de bandeja del sistema (QSystemTrayIcon) inicializado.")
        
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Aplicación Minimizada",
            "El monitor sigue ejecutándose en segundo plano. "
            "Haz clic derecho en el ícono para cerrar.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

def run_gui():
    logger.info("Iniciando la aplicación Qt...")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) 
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())