# -*- coding: utf-8 -*-
"""
Mixin para la gestión de las Tablas (crear, poblar, filtrar).
"""

from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QTableView, 
    QAbstractItemView, QHeaderView
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QFont
from PySide6.QtCore import Qt, Slot
from typing import List

from src.utils.logger import configurar_logger
from src.db.db_models import CaLicitacion

logger = configurar_logger(__name__)

# Eliminamos ID Interno de la vista y agregamos Monto
COLUMN_HEADERS_SIMPLE = [
    "Score", "Codigo CA", "Nombre", "Monto", "Organismo", "Direccion de entrega", 
    "Estado", "Fecha publicacion", "Fecha cierre", "Proveedores cotizando"
]

COLUMN_HEADERS_DETALLADA = [
    "Score", "Codigo CA", "Nombre", "Monto", "Descripcion", "Organismo", "Direccion de entrega", 
    "Estado", "Fecha publicacion", "Fecha cierre", "Fecha cierre segundo llamado", 
    "Productos solicitados", "Proveedores cotizando", "Notas"
]

class TableManagerMixin:
    """
    Este Mixin maneja toda la lógica relacionada con las
    QTableView: creación de pestañas, poblado de datos
    y filtrado AVANZADO.
    """

    # El método _crear_pestaña_tabla ya no se usa en la nueva GUI pero se deja por seguridad.
    def _crear_pestaña_tabla(self, placeholder: str, tab_id: str):
        tab = QWidget()
        return tab, None, None, None

    def crear_tabla_view(self, model: QStandardItemModel, tab_id: str) -> QTableView:
        """Configura las propiedades estándar de una QTableView."""
        table_view = QTableView()
        table_view.setModel(model)
        table_view.setSortingEnabled(True)
        table_view.sortByColumn(0, Qt.SortOrder.DescendingOrder) # Col 0 es Score
        table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_view.setAlternatingRowColors(True)
        
        table_view.verticalHeader().setDefaultSectionSize(32)
        table_view.verticalHeader().hide()
        
        header = table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Ajustes de ancho
        target_headers = COLUMN_HEADERS_SIMPLE if tab_id == "tab1_simple" else COLUMN_HEADERS_DETALLADA
        
        if "Nombre" in target_headers:
            header.setSectionResizeMode(target_headers.index("Nombre"), QHeaderView.ResizeMode.Stretch)
        
        if tab_id == "tab1_simple":
            if "Organismo" in target_headers:
                header.setSectionResizeMode(target_headers.index("Organismo"), QHeaderView.ResizeMode.Stretch)
        else:
            if "Descripcion" in target_headers:
                header.setSectionResizeMode(target_headers.index("Descripcion"), QHeaderView.ResizeMode.Stretch)

        return table_view

    def poblar_tabla(self, model: QStandardItemModel, data: List[CaLicitacion]):
        """Llena un QStandardItemModel con datos de la BD."""
        logger.debug(f"Poblando tabla con {len(data)} filas.")
        
        is_simple_view = (model.columnCount() == len(COLUMN_HEADERS_SIMPLE))
        headers = COLUMN_HEADERS_SIMPLE if is_simple_view else COLUMN_HEADERS_DETALLADA
        
        model.clear()
        model.setHorizontalHeaderLabels(headers)
        
        bold_font = QFont()
        bold_font.setBold(True)

        for licitacion in data:
            is_ofertada = licitacion.seguimiento and licitacion.seguimiento.es_ofertada
            is_favorito = licitacion.seguimiento and licitacion.seguimiento.es_favorito

            # --- SCORE (y dato oculto ID) ---
            score_item = QStandardItem()
            score_item.setData(licitacion.puntuacion_final or 0, Qt.ItemDataRole.DisplayRole)
            # IMPORTANTE: Guardamos el ID oculto aquí para el menú contextual
            score_item.setData(licitacion.ca_id, Qt.UserRole)

            # --- MONTO ---
            monto_val = licitacion.monto_clp or 0
            monto_str = f"$ {int(monto_val):,}".replace(",", ".") if monto_val else "N/A"
            monto_item = QStandardItem(monto_str)
            # Guardamos valor numérico real en UserRole para poder FILTRAR por número
            monto_item.setData(monto_val, Qt.UserRole)

            prov_item = QStandardItem()
            prov_item.setData(licitacion.proveedores_cotizando or 0, Qt.ItemDataRole.DisplayRole)
            
            nombre_item = QStandardItem(licitacion.nombre)
            if is_favorito or is_ofertada:
                nombre_item.setFont(bold_font)

            # Formato de Fechas
            try:
                fecha_pub = licitacion.fecha_publicacion.strftime("%Y-%m-%d")
            except Exception:
                fecha_pub = "N/A"
            try:
                fecha_cierre = licitacion.fecha_cierre.strftime("%Y-%m-%d %H:%M")
            except Exception:
                fecha_cierre = "N/A"

            # Visualización de Segundo Llamado
            estado_str = licitacion.estado_ca_texto or "N/A"
            if licitacion.estado_convocatoria == 2:
                estado_str += " (2° Llamado)"
            
            # Notas
            nota_str = ""
            if licitacion.seguimiento and licitacion.seguimiento.notas:
                nota_str = licitacion.seguimiento.notas
            
            nombre_organismo = licitacion.organismo.nombre if licitacion.organismo else "N/A"

            if is_simple_view:
                row_items = [
                    score_item, # 0. Score (contiene ID oculto)
                    QStandardItem(licitacion.codigo_ca),
                    nombre_item,
                    monto_item, # Nueva columna Monto
                    QStandardItem(nombre_organismo),
                    QStandardItem(licitacion.direccion_entrega or "N/A"),
                    QStandardItem(estado_str),
                    QStandardItem(fecha_pub),
                    QStandardItem(fecha_cierre),
                    prov_item,
                ]
            else:
                try:
                    fecha_cierre_2 = licitacion.fecha_cierre_segundo_llamado.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    fecha_cierre_2 = "N/A"
                
                productos_str = "N/A"
                if licitacion.productos_solicitados:
                    nombres_prod = [p.get('nombre', 'Item sin nombre') for p in licitacion.productos_solicitados]
                    productos_str = "; ".join(nombres_prod)
                    if len(productos_str) > 100:
                        productos_str = productos_str[:100] + "..."

                row_items = [
                    score_item, # 0. Score (contiene ID oculto)
                    QStandardItem(licitacion.codigo_ca),
                    nombre_item,
                    monto_item, # Nueva columna Monto
                    QStandardItem(licitacion.descripcion or "N/A"),
                    QStandardItem(nombre_organismo),
                    QStandardItem(licitacion.direccion_entrega or "N/A"),
                    QStandardItem(estado_str),
                    QStandardItem(fecha_pub),
                    QStandardItem(fecha_cierre),
                    QStandardItem(fecha_cierre_2),
                    QStandardItem(productos_str),
                    prov_item,
                    QStandardItem(nota_str),
                ]

            model.appendRow(row_items)

        # Ajuste de columnas post-poblado
        active_table = self.sender() # type: ignore
        if isinstance(active_table, QTableView):
             header = active_table.horizontalHeader()
             header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
             if is_simple_view:
                if "Nombre" in COLUMN_HEADERS_SIMPLE:
                     header.setSectionResizeMode(COLUMN_HEADERS_SIMPLE.index("Nombre"), QHeaderView.ResizeMode.Stretch)
             else:
                if "Nombre" in COLUMN_HEADERS_DETALLADA:
                     header.setSectionResizeMode(COLUMN_HEADERS_DETALLADA.index("Nombre"), QHeaderView.ResizeMode.Stretch)


    def filter_table_view(self, table_view: QTableView, text: str, only_2nd: bool, days_limit: int, min_amount: int):
        """
        Filtra las filas de una tabla con múltiples criterios.
        
        Args:
            table_view: La tabla a filtrar.
            text: Texto de búsqueda.
            only_2nd: Si True, solo muestra "2° Llamado".
            days_limit: Número de días para considerar "Cierra Pronto".
            min_amount: Monto mínimo en CLP.
        """
        model = table_view.model()
        if not model: return

        filter_text = text.lower()
        
        is_simple_view = (model.columnCount() == len(COLUMN_HEADERS_SIMPLE))
        headers = COLUMN_HEADERS_SIMPLE if is_simple_view else COLUMN_HEADERS_DETALLADA
        
        # Índices de columnas
        idx_codigo = headers.index("Codigo CA")
        idx_nombre = headers.index("Nombre")
        idx_org = headers.index("Organismo") if "Organismo" in headers else -1
        idx_estado = headers.index("Estado")
        idx_cierre = headers.index("Fecha cierre")
        idx_monto = headers.index("Monto")

        now = datetime.now()

        for row in range(model.rowCount()):
            should_show = True
            
            # 1. Filtro de Texto
            if filter_text:
                try:
                    codigo_ca = model.item(row, idx_codigo).text().lower()
                    nombre = model.item(row, idx_nombre).text().lower()
                    organismo = model.item(row, idx_org).text().lower() if idx_org != -1 else ""
                    
                    if (filter_text not in codigo_ca and 
                        filter_text not in nombre and 
                        filter_text not in organismo):
                        should_show = False
                except AttributeError:
                    should_show = False

            # 2. Filtro de 2do Llamado
            if should_show and only_2nd:
                estado_val = model.item(row, idx_estado).text()
                if "2° Llamado" not in estado_val:
                    should_show = False
            
            # 3. Filtro de Cierre Pronto (Días dinámicos)
            if should_show and days_limit > 0:
                fecha_str = model.item(row, idx_cierre).text()
                if fecha_str == "N/A":
                    should_show = False 
                else:
                    try:
                        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
                        delta = fecha_dt - now
                        # Si ya pasó (cerrada) o falta más del límite -> Ocultar
                        if delta.total_seconds() < 0 or delta.days >= days_limit:
                             should_show = False
                    except ValueError:
                        should_show = False
            
            # 4. Filtro de Monto Mínimo
            if should_show and min_amount > 0:
                # Recuperamos el valor numérico puro del UserRole
                try:
                    item_monto = model.item(row, idx_monto)
                    monto_val = item_monto.data(Qt.UserRole) # Recuperamos el float/int
                    if monto_val is None: monto_val = 0
                    if float(monto_val) < min_amount:
                        should_show = False
                except Exception:
                    should_show = False

            # APLICAR
            table_view.setRowHidden(row, not should_show)