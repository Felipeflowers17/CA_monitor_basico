# -*- coding: utf-8 -*-
"""
Ventana Principal de la Aplicación (Modernizada con Fluent Widgets).
"""

import sys
from typing import List

from PySide6.QtCore import QThreadPool, QTimer, Qt, Slot, QSize
from PySide6.QtGui import QAction, QStandardItemModel, QIcon, QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTableView, QLineEdit, QFrame, QHeaderView, QSystemTrayIcon, QMenu, QStyle
)

# --- IMPORTACIONES DE FLUENT WIDGETS ---
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, SubtitleLabel,
    PrimaryPushButton, PushButton, FluentIcon as FIF,
    setTheme, Theme, TableWidget, LineEdit,
    MessageBox, InfoBar, InfoBarPosition, ProgressBar,
    CheckBox, SpinBox, BodyLabel
)

from src.gui.gui_worker import Worker
from src.utils.logger import configurar_logger
from src.utils.settings_manager import SettingsManager
from src.db.session import SessionLocal
from src.db.db_service import DbService
from src.logic.etl_service import EtlService
from src.logic.excel_service import ExcelService
from src.logic.score_engine import ScoreEngine
from src.scraper.scraper_service import ScraperService

# Mixins
from .mixins.threading_mixin import ThreadingMixin
from .mixins.main_slots_mixin import MainSlotsMixin
from .mixins.data_loader_mixin import DataLoaderMixin
from .mixins.context_menu_mixin import ContextMenuMixin
from .mixins.table_manager_mixin import TableManagerMixin, COLUMN_HEADERS_SIMPLE, COLUMN_HEADERS_DETALLADA

logger = configurar_logger(__name__)

# --- CLASE AUXILIAR PARA LAS PESTAÑAS ---
class TableInterface(QWidget):
    """
    Representa el contenido de una 'Pestaña'. 
    Contiene la barra de búsqueda, FILTROS RÁPIDOS y la tabla.
    """
    def __init__(self, object_name, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(object_name)
        
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20) 
        self.vBoxLayout.setSpacing(10)
        
        # 1. Barra de búsqueda moderna
        self.searchBar = LineEdit()
        self.searchBar.setPlaceholderText("Buscar por código, nombre u organismo...")
        self.searchBar.setClearButtonEnabled(True)
        self.vBoxLayout.addWidget(self.searchBar)

        # 2. Barra de Filtros Rápidos
        self.filterLayout = QHBoxLayout()
        
        # Checkbox Simple
        self.chk2doLlamado = CheckBox("Solo 2° Llamado", self)
        
        # Filtro Días (Cierran Pronto)
        self.lblDias = BodyLabel("Cierre en (días):", self)
        self.spinDias = SpinBox(self)
        self.spinDias.setRange(0, 30)
        self.spinDias.setValue(0) # 0 = Desactivado
        self.spinDias.setFixedWidth(140)
        self.spinDias.setToolTip("0 = Sin filtro. 2 = Cierra hoy o mañana.")
        
        # Filtro Monto Mínimo
        self.lblMonto = BodyLabel("Monto Min. ($):", self)
        self.spinMonto = SpinBox(self)
        self.spinMonto.setRange(0, 999999999) # Hasta 999 millones
        self.spinMonto.setValue(0) # 0 = Desactivado
        self.spinMonto.setSingleStep(100000) # Saltos de 100k
        self.spinMonto.setFixedWidth(200)
        
        # Agregar al layout
        self.filterLayout.addWidget(self.chk2doLlamado)
        
        self.filterLayout.addSpacing(20)
        self.filterLayout.addWidget(self.lblDias)
        self.filterLayout.addWidget(self.spinDias)
        
        self.filterLayout.addSpacing(20)
        self.filterLayout.addWidget(self.lblMonto)
        self.filterLayout.addWidget(self.spinMonto)
        
        self.filterLayout.addStretch(1) 
        
        self.vBoxLayout.addLayout(self.filterLayout)
        
        # 3. Contenedor para la tabla
        self.tableContainer = QFrame()
        self.tableLayout = QVBoxLayout(self.tableContainer)
        self.tableLayout.setContentsMargins(0, 5, 0, 0)
        
        self.vBoxLayout.addWidget(self.tableContainer)


class MainWindow(FluentWindow, ThreadingMixin, MainSlotsMixin, DataLoaderMixin, ContextMenuMixin, TableManagerMixin):
    """
    Ventana Principal estilo Windows 11.
    """
    def __init__(self):
        super().__init__()
        
        # 1. Configuración Inicial
        self.setWindowTitle("Monitor CA") # <-- Título actualizado
        self.resize(1200, 800)
        
        # Bandera para controlar el cierre real vs minimizado
        self.force_close = False 

        # Inicializar Servicios
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
            self.etl_service = EtlService(self.db_service, self.scraper_service, self.score_engine)
        except Exception as e:
            logger.critical(f"Error servicios: {e}")
            sys.exit(1)

        # Variables de UI
        self.timer_fase1: QTimer | None = None
        self.timer_fase2: QTimer | None = None
        self.progress_bar: ProgressBar | None = None
        self.tray_icon: QSystemTrayIcon | None = None

        # 2. Crear Interfaces (Pestañas)
        self.homeInterface = TableInterface("tab1_simple", self)
        self.relevantesInterface = TableInterface("tab2_detallada", self)
        self.seguimientoInterface = TableInterface("tab3_detallada", self)
        self.ofertadasInterface = TableInterface("tab4_detallada", self)
        
        # Inicializar componentes de tabla
        # Pestaña 1
        self.model_tab1 = QStandardItemModel(0, len(COLUMN_HEADERS_SIMPLE))
        self.model_tab1.setHorizontalHeaderLabels(COLUMN_HEADERS_SIMPLE)
        self.table_tab1 = self.crear_tabla_view(self.model_tab1, "tab1_simple")
        self.homeInterface.tableLayout.addWidget(self.table_tab1)
        self.search_tab1 = self.homeInterface.searchBar 

        # Pestaña 2
        self.model_tab2 = QStandardItemModel(0, len(COLUMN_HEADERS_DETALLADA))
        self.model_tab2.setHorizontalHeaderLabels(COLUMN_HEADERS_DETALLADA)
        self.table_tab2 = self.crear_tabla_view(self.model_tab2, "tab2_detallada")
        self.relevantesInterface.tableLayout.addWidget(self.table_tab2)
        self.search_tab2 = self.relevantesInterface.searchBar

        # Pestaña 3
        self.model_tab3 = QStandardItemModel(0, len(COLUMN_HEADERS_DETALLADA))
        self.model_tab3.setHorizontalHeaderLabels(COLUMN_HEADERS_DETALLADA)
        self.table_tab3 = self.crear_tabla_view(self.model_tab3, "tab3_detallada")
        self.seguimientoInterface.tableLayout.addWidget(self.table_tab3)
        self.search_tab3 = self.seguimientoInterface.searchBar

        # Pestaña 4
        self.model_tab4 = QStandardItemModel(0, len(COLUMN_HEADERS_DETALLADA))
        self.model_tab4.setHorizontalHeaderLabels(COLUMN_HEADERS_DETALLADA)
        self.table_tab4 = self.crear_tabla_view(self.model_tab4, "tab4_detallada")
        self.ofertadasInterface.tableLayout.addWidget(self.table_tab4)
        self.search_tab4 = self.ofertadasInterface.searchBar

        # 3. Configurar Navegación Lateral
        self.initNavigation()
        
        self._setup_tray_icon() 
        self._connect_signals()
        self._setup_timers()
        
        # Cargar datos iniciales
        QTimer.singleShot(500, self.on_load_data_thread)
        QTimer.singleShot(3000, self.iniciar_limpieza_silenciosa)

    def initNavigation(self):
        """Configura el menú lateral izquierdo."""
        
        self.addSubInterface(self.homeInterface, FIF.HOME, "Candidatas", NavigationItemPosition.TOP)
        self.addSubInterface(self.relevantesInterface, FIF.FILTER, "Relevantes", NavigationItemPosition.TOP)
        self.addSubInterface(self.seguimientoInterface, FIF.HEART, "Seguimiento", NavigationItemPosition.TOP)
        self.addSubInterface(self.ofertadasInterface, FIF.SHOPPING_CART, "Ofertadas", NavigationItemPosition.TOP)
        
        self.navigationInterface.addSeparator()
        
        self.navigationInterface.addItem(routeKey="scraping", icon=FIF.DOWNLOAD, text="Nuevo Scraping", onClick=self.on_open_scraping_dialog, position=NavigationItemPosition.SCROLL)
        self.navigationInterface.addItem(routeKey="update", icon=FIF.SYNC, text="Actualizar Fichas", onClick=self.on_run_fase2_update_thread, position=NavigationItemPosition.SCROLL)
        self.navigationInterface.addItem(routeKey="recalculate", icon=FIF.EDIT, text="Recalcular Puntajes", onClick=self.on_run_recalculate_thread, position=NavigationItemPosition.SCROLL)
        self.navigationInterface.addItem(routeKey="refresh", icon=FIF.UPDATE, text="Refrescar Tablas", onClick=self.on_load_data_thread, position=NavigationItemPosition.SCROLL)
        
        self.navigationInterface.addItem(routeKey="settings", icon=FIF.SETTING, text="Configuración", onClick=self.on_open_settings_dialog, position=NavigationItemPosition.BOTTOM)

    def _connect_signals(self):
        # --- CONECTORES PESTAÑA 1 ---
        self.homeInterface.searchBar.textChanged.connect(self.on_filters_changed_tab1)
        self.homeInterface.chk2doLlamado.stateChanged.connect(self.on_filters_changed_tab1)
        self.homeInterface.spinDias.valueChanged.connect(self.on_filters_changed_tab1)
        self.homeInterface.spinMonto.valueChanged.connect(self.on_filters_changed_tab1)
        
        # --- CONECTORES PESTAÑA 2 ---
        self.relevantesInterface.searchBar.textChanged.connect(self.on_filters_changed_tab2)
        self.relevantesInterface.chk2doLlamado.stateChanged.connect(self.on_filters_changed_tab2)
        self.relevantesInterface.spinDias.valueChanged.connect(self.on_filters_changed_tab2)
        self.relevantesInterface.spinMonto.valueChanged.connect(self.on_filters_changed_tab2)
        
        # --- CONECTORES PESTAÑA 3 ---
        self.seguimientoInterface.searchBar.textChanged.connect(self.on_filters_changed_tab3)
        self.seguimientoInterface.chk2doLlamado.stateChanged.connect(self.on_filters_changed_tab3)
        self.seguimientoInterface.spinDias.valueChanged.connect(self.on_filters_changed_tab3)
        self.seguimientoInterface.spinMonto.valueChanged.connect(self.on_filters_changed_tab3)
        
        # --- CONECTORES PESTAÑA 4 ---
        self.ofertadasInterface.searchBar.textChanged.connect(self.on_filters_changed_tab4)
        self.ofertadasInterface.chk2doLlamado.stateChanged.connect(self.on_filters_changed_tab4)
        self.ofertadasInterface.spinDias.valueChanged.connect(self.on_filters_changed_tab4)
        self.ofertadasInterface.spinMonto.valueChanged.connect(self.on_filters_changed_tab4)
        
        # Menú contextual
        self.table_tab1.customContextMenuRequested.connect(self.mostrar_menu_contextual)
        self.table_tab2.customContextMenuRequested.connect(self.mostrar_menu_contextual)
        self.table_tab3.customContextMenuRequested.connect(self.mostrar_menu_contextual)
        self.table_tab4.customContextMenuRequested.connect(self.mostrar_menu_contextual)

    # --- SLOTS PARA FILTRADO COMBINADO ---
    @Slot()
    def on_filters_changed_tab1(self):
        text = self.homeInterface.searchBar.text()
        only_2nd = self.homeInterface.chk2doLlamado.isChecked()
        days = self.homeInterface.spinDias.value()
        amount = self.homeInterface.spinMonto.value()
        self.filter_table_view(self.table_tab1, text, only_2nd, days, amount)

    @Slot()
    def on_filters_changed_tab2(self):
        text = self.relevantesInterface.searchBar.text()
        only_2nd = self.relevantesInterface.chk2doLlamado.isChecked()
        days = self.relevantesInterface.spinDias.value()
        amount = self.relevantesInterface.spinMonto.value()
        self.filter_table_view(self.table_tab2, text, only_2nd, days, amount)

    @Slot()
    def on_filters_changed_tab3(self):
        text = self.seguimientoInterface.searchBar.text()
        only_2nd = self.seguimientoInterface.chk2doLlamado.isChecked()
        days = self.seguimientoInterface.spinDias.value()
        amount = self.seguimientoInterface.spinMonto.value()
        self.filter_table_view(self.table_tab3, text, only_2nd, days, amount)

    @Slot()
    def on_filters_changed_tab4(self):
        text = self.ofertadasInterface.searchBar.text()
        only_2nd = self.ofertadasInterface.chk2doLlamado.isChecked()
        days = self.ofertadasInterface.spinDias.value()
        amount = self.ofertadasInterface.spinMonto.value()
        self.filter_table_view(self.table_tab4, text, only_2nd, days, amount)

    def _setup_timers(self):
        logger.info("Configurando timers...")
        self.timer_fase1 = QTimer(self)
        self.timer_fase1.timeout.connect(self.on_start_full_scraping_auto)
        self.timer_fase2 = QTimer(self)
        self.timer_fase2.timeout.connect(self.on_run_fase2_update_thread_auto)
        self.reload_timers_config()

    def _show_task_completion_notification(self, title: str, message: str, is_auto: bool = False, is_error: bool = False):
        if is_auto:
            logger.info(f"AUTO NOTIFICACION: {title} - {message}")
            return

        pos = InfoBarPosition.TOP_RIGHT
        if is_error:
            InfoBar.error(title=title, content=message, orient=Qt.Horizontal, isClosable=True, position=pos, duration=5000, parent=self)
        else:
            InfoBar.success(title=title, content=message, orient=Qt.Horizontal, isClosable=True, position=pos, duration=3000, parent=self)

    def set_ui_busy(self, busy: bool):
        self.is_task_running = busy
        if busy:
            self.setCursor(Qt.WaitCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    @Slot()
    def iniciar_limpieza_silenciosa(self):
        if self.is_task_running: return
        self.start_task(
            task=self.etl_service.run_limpieza_automatica,
            on_result=lambda: logger.debug("Fin de limpieza."),
            on_error=lambda e: logger.warning(f"Error limpieza: {e}"),
            on_finished=lambda: None
        )

    def reload_timers_config(self):
        try:
            self.settings_manager.load_settings()
            intervalo_f1_horas = self.settings_manager.get_setting("auto_fase1_intervalo_horas")
            if intervalo_f1_horas > 0:
                intervalo_ms = intervalo_f1_horas * 60 * 60 * 1000 
                self.timer_fase1.start(intervalo_ms)
            else:
                self.timer_fase1.stop()
            intervalo_f2_min = self.settings_manager.get_setting("auto_fase2_intervalo_minutos")
            if intervalo_f2_min > 0:
                intervalo_ms = intervalo_f2_min * 60 * 1000 
                self.timer_fase2.start(intervalo_ms)
            else:
                self.timer_fase2.stop()
        except Exception as e:
            logger.error(f"Error timers: {e}")
            
    def _setup_tray_icon(self):
        """Configura el icono de la bandeja del sistema."""
        icon = QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Monitor CA")
        
        tray_menu = QMenu()
        
        restore_action = QAction("Abrir Monitor", self)
        restore_action.triggered.connect(self.showNormal)
        tray_menu.addAction(restore_action)
        
        tray_menu.addSeparator()
        
        # Acción para cerrar totalmente
        quit_action = QAction("Cerrar Aplicación", self)
        quit_action.triggered.connect(self.force_quit) # <-- Conectamos a método personalizado
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        logger.info("Ícono de bandeja (Tray Icon) inicializado.")

    @Slot()
    def force_quit(self):
        """Fuerza el cierre de la aplicación desde la bandeja."""
        self.force_close = True
        self.close() # Esto dispara closeEvent, que ahora permitirá el cierre
        QApplication.instance().quit() # Asegura matar el proceso

    def _on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def closeEvent(self, event):
        """Sobrescribe el evento de cerrar para minimizar a la bandeja."""
        if self.force_close:
            event.accept() # Permite cerrar de verdad
        else:
            event.ignore() # Ignora el cierre real
            self.hide() # Oculta la ventana
            
            self._show_task_completion_notification(
                "Aplicación Minimizada",
                "El monitor sigue ejecutándose en segundo plano.",
                is_auto=False,
                is_error=False
            )


def run_gui():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())