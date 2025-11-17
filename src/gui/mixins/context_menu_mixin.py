# -*- coding: utf-8 -*-
"""
Mixin para la lógica del Menú Contextual (clic derecho).

"""

import webbrowser
from PySide6.QtWidgets import QTableView, QMenu, QMessageBox
from PySide6.QtGui import QCursor
from PySide6.QtCore import Slot, QModelIndex

from src.utils.logger import configurar_logger
from src.scraper.url_builder import construir_url_ficha

from .table_manager_mixin import COLUMN_HEADERS_SIMPLE, COLUMN_HEADERS_DETALLADA


logger = configurar_logger(__name__)


class ContextMenuMixin:
    @Slot(QModelIndex)
    def mostrar_menu_contextual(self, position):
        """Muestra el menú de clic derecho."""
        active_table = self.sender()
        if not isinstance(active_table, QTableView): 
            return
            
        index: QModelIndex = active_table.indexAt(position)
        if not index.isValid(): 
            return
            
        model = active_table.model()
        row = index.row()
        
        try:
            # Determinamos en qué tipo de tabla estamos
            num_columnas = model.columnCount()
            
            if num_columnas == len(COLUMN_HEADERS_SIMPLE):
                # Estamos en la Pestaña 1 (Simple)
                idx_id = COLUMN_HEADERS_SIMPLE.index("ID Interno")
                idx_codigo = COLUMN_HEADERS_SIMPLE.index("Codigo CA") 
            elif num_columnas == len(COLUMN_HEADERS_DETALLADA):
                # Estamos en Pestañas 2, 3, o 4 (Detallada)
                idx_id = COLUMN_HEADERS_DETALLADA.index("ID Interno")
                idx_codigo = COLUMN_HEADERS_DETALLADA.index("Codigo CA") 
            else:
                # Caso inesperado, no podemos continuar
                logger.error(f"Error de menú contextual: número de columnas desconocido ({num_columnas})")
                return

            ca_id = int(model.item(row, idx_id).text())
            codigo_ca = model.item(row, idx_codigo).text()


        except Exception as e:
            logger.error(f"Error al obtener ID de la fila {row}: {e}")
            return
            
        logger.debug(f"Menú contextual para CA ID: {ca_id} (Código: {codigo_ca})")
        
        menu = QMenu()
        menu.addAction("Marcar como Favorito").triggered.connect(lambda: self.on_marcar_favorito(ca_id))
        menu.addAction("Eliminar Seguimiento").triggered.connect(lambda: self.on_eliminar_seguimiento(ca_id))
        menu.addSeparator()
        menu.addAction("Marcar como Ofertada").triggered.connect(lambda: self.on_marcar_ofertada(ca_id))
        menu.addAction("Quitar marca de Ofertada").triggered.connect(lambda: self.on_quitar_ofertada(ca_id))
        menu.addSeparator()
        menu.addAction("Eliminar Definitivamente (BD)").triggered.connect(lambda: self.on_eliminar_definitivo(ca_id))
        menu.addSeparator()
        menu.addAction("Ver Ficha Web").triggered.connect(lambda: self.on_ver_ficha_web(codigo_ca))
        
        menu.exec_(QCursor.pos())

    def _run_context_menu_action(self, task: callable, *args):
        if self.is_task_running:
            return
            
        self.start_task(
            task=task,
            on_result=lambda: logger.debug(f"Acción {task.__name__} OK"),
            on_error=self.on_task_error,
            on_finished=self.on_load_data_thread,
            task_args=args,
        )

    @Slot(int)
    def on_marcar_favorito(self, ca_id: int):
        self._run_context_menu_action(self.db_service.gestionar_favorito, ca_id, True)

    @Slot(int)
    def on_eliminar_seguimiento(self, ca_id: int):
        self._run_context_menu_action(self.db_service.gestionar_favorito, ca_id, False)

    @Slot(int)
    def on_marcar_ofertada(self, ca_id: int):
        self._run_context_menu_action(self.db_service.gestionar_ofertada, ca_id, True)

    @Slot(int)
    def on_quitar_ofertada(self, ca_id: int):
        self._run_context_menu_action(self.db_service.gestionar_ofertada, ca_id, False)

    @Slot(int)
    def on_eliminar_definitivo(self, ca_id: int):
        confirm = QMessageBox.warning(
            self, "Confirmación de Eliminación",
            "¿Estás seguro de que quieres eliminar esta CA permanentemente?\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._run_context_menu_action(self.db_service.eliminar_ca_definitivamente, ca_id)

    @Slot(str)
    def on_ver_ficha_web(self, codigo_ca: str):
        url = construir_url_ficha(codigo_ca)
        webbrowser.open_new_tab(url)