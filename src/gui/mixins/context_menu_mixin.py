# -*- coding: utf-8 -*-
"""
Mixin para la lógica del Menú Contextual (clic derecho).
"""

import webbrowser
from PySide6.QtWidgets import QTableView, QMenu, QMessageBox, QInputDialog
from PySide6.QtGui import QCursor
from PySide6.QtCore import Slot, QModelIndex, Qt

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
        
        current_note = "" 
        ca_id = None
        codigo_ca = ""

        try:
            # 1. Obtener el ID Interno (Ahora guardado oculto en la columna 0, UserRole)
            # La columna 0 es "Score", usamos esa como ancla para los datos ocultos
            item_score = model.item(row, 0)
            ca_id_data = item_score.data(Qt.UserRole)
            
            if ca_id_data:
                ca_id = int(ca_id_data)
            else:
                logger.error(f"No se encontró ID Interno en UserRole para fila {row}")
                return

            # 2. Obtener Código CA
            # Determinamos índice según la vista
            if model.columnCount() == len(COLUMN_HEADERS_SIMPLE):
                idx_codigo = COLUMN_HEADERS_SIMPLE.index("Codigo CA")
            else:
                idx_codigo = COLUMN_HEADERS_DETALLADA.index("Codigo CA")
                # Intentamos obtener la nota actual si estamos en detallada
                if "Notas" in COLUMN_HEADERS_DETALLADA:
                    idx_notas = COLUMN_HEADERS_DETALLADA.index("Notas")
                    item_nota = model.item(row, idx_notas)
                    if item_nota:
                        current_note = item_nota.text()
            
            codigo_ca = model.item(row, idx_codigo).text()

        except Exception as e:
            logger.error(f"Error al preparar menú contextual fila {row}: {e}", exc_info=True)
            return
            
        logger.debug(f"Menú contextual para CA ID: {ca_id} (Código: {codigo_ca})")
        
        menu = QMenu()
        menu.addAction("Marcar como Favorito").triggered.connect(lambda: self.on_marcar_favorito(ca_id))
        menu.addAction("Eliminar Seguimiento").triggered.connect(lambda: self.on_eliminar_seguimiento(ca_id))
        menu.addSeparator()
        
        menu.addAction("Editar Nota Personal...").triggered.connect(lambda: self.on_editar_nota_dialog(ca_id, current_note))
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
    
    @Slot(int, str)
    def on_editar_nota_dialog(self, ca_id: int, current_note: str):
        text, ok = QInputDialog.getMultiLineText(
            self, 
            "Nota Personal", 
            "Escribe una nota para esta licitación:", 
            current_note
        )
        if ok:
            self._run_context_menu_action(self.db_service.actualizar_nota_seguimiento, ca_id, text)

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