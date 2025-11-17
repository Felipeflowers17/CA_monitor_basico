# -*- coding: utf-8 -*-
"""
Mixin para la gestión de las Tablas (crear, poblar, filtrar).

"""

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


COLUMN_HEADERS_SIMPLE = [
    "Score", "Codigo CA", "Nombre", "Organismo", "Direccion de entrega", 
    "Estado", "Fecha publicacion", "Fecha cierre", "Proveedores cotizando", "ID Interno"
]
COLUMN_HEADERS_DETALLADA = [
    "Score", "Codigo CA", "Nombre", "Descripcion", "Organismo", "Direccion de entrega", 
    "Estado", "Fecha publicacion", "Fecha cierre", "Fecha cierre segundo llamado", 
    "Productos solicitados", "Proveedores cotizando", "ID Interno"
]



COL_HEADERS_DET = COLUMN_HEADERS_DETALLADA
COL_IDX_DET_CODIGO_CA = COL_HEADERS_DET.index("Codigo CA") 
COL_IDX_DET_ID_INTERNO = COL_HEADERS_DET.index("ID Interno") 




class TableManagerMixin:
    """
    Este Mixin maneja toda la lógica relacionada con las
    QTableView: creación de pestañas, poblado de datos
    y filtrado de búsqueda.
    """

    def _crear_pestaña_tabla(self, placeholder: str, tab_id: str):
        """Crea un widget de pestaña (Tab) con una barra y una tabla."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        search_bar = QLineEdit()
        search_bar.setPlaceholderText(placeholder)
        layout.addWidget(search_bar)
        
        headers = COLUMN_HEADERS_SIMPLE if tab_id == "tab1_simple" else COLUMN_HEADERS_DETALLADA
        model = QStandardItemModel(0, len(headers))
        model.setHorizontalHeaderLabels(headers)
        
        table_view = self.crear_tabla_view(model, tab_id)
        layout.addWidget(table_view)
        
        return tab, search_bar, model, table_view

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
        

        if tab_id == "tab1_simple":
            header.setSectionResizeMode(COLUMN_HEADERS_SIMPLE.index("Nombre"), QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(COLUMN_HEADERS_SIMPLE.index("Organismo"), QHeaderView.ResizeMode.Stretch)
            table_view.setColumnHidden(COLUMN_HEADERS_SIMPLE.index("ID Interno"), True)
        else:
            header.setSectionResizeMode(COLUMN_HEADERS_DETALLADA.index("Nombre"), QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(COLUMN_HEADERS_DETALLADA.index("Descripcion"), QHeaderView.ResizeMode.Stretch)
            table_view.setColumnHidden(COLUMN_HEADERS_DETALLADA.index("ID Interno"), True)

        
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

            nombre_organismo = "N/A"
            if licitacion.organismo:
                nombre_organismo = licitacion.organismo.nombre

            score_item = QStandardItem()
            score_item.setData(licitacion.puntuacion_final or 0, Qt.ItemDataRole.DisplayRole)

            prov_item = QStandardItem()
            prov_item.setData(licitacion.proveedores_cotizando or 0, Qt.ItemDataRole.DisplayRole)
            
            nombre_item = QStandardItem(licitacion.nombre)
            if is_favorito or is_ofertada:
                nombre_item.setFont(bold_font)

            try:
                fecha_pub = licitacion.fecha_publicacion.strftime("%Y-%m-%d")
            except Exception:
                fecha_pub = "N/A"
            try:
                fecha_cierre = licitacion.fecha_cierre.strftime("%Y-%m-%d %H:%M")
            except Exception:
                fecha_cierre = "N/A"

            if is_simple_view:
                row_items = [
                    score_item,
                    QStandardItem(licitacion.codigo_ca),
                    nombre_item,
                    QStandardItem(nombre_organismo),
                    QStandardItem(licitacion.direccion_entrega or "N/A"),
                    QStandardItem(licitacion.estado_ca_texto or "N/A"),
                    QStandardItem(fecha_pub),
                    QStandardItem(fecha_cierre),
                    prov_item,
                    QStandardItem(str(licitacion.ca_id)),
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
                    score_item,
                    QStandardItem(licitacion.codigo_ca),
                    nombre_item,
                    QStandardItem(licitacion.descripcion or "N/A"),
                    QStandardItem(nombre_organismo),
                    QStandardItem(licitacion.direccion_entrega or "N/A"),
                    QStandardItem(licitacion.estado_ca_texto or "N/A"),
                    QStandardItem(fecha_pub),
                    QStandardItem(fecha_cierre),
                    QStandardItem(fecha_cierre_2),
                    QStandardItem(productos_str),
                    prov_item,
                    QStandardItem(str(licitacion.ca_id)),
                ]


            model.appendRow(row_items)

        active_table = self.sender()
        if isinstance(active_table, QTableView):
             header = active_table.horizontalHeader()
             header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
             if is_simple_view:
                header.setSectionResizeMode(COLUMN_HEADERS_SIMPLE.index("Nombre"), QHeaderView.ResizeMode.Stretch)
                header.setSectionResizeMode(COLUMN_HEADERS_SIMPLE.index("Organismo"), QHeaderView.ResizeMode.Stretch)
             else:
                header.setSectionResizeMode(COLUMN_HEADERS_DETALLADA.index("Nombre"), QHeaderView.ResizeMode.Stretch)
                header.setSectionResizeMode(COLUMN_HEADERS_DETALLADA.index("Descripcion"), QHeaderView.ResizeMode.Stretch)


    def filter_table_view(self, table_view: QTableView, text: str):
        """Filtra las filas de una tabla basado en el texto de búsqueda."""
        model = table_view.model()
        filter_text = text.lower()
        

        is_simple_view = (model.columnCount() == len(COLUMN_HEADERS_SIMPLE))
        idx_codigo = COLUMN_HEADERS_SIMPLE.index("Codigo CA") if is_simple_view else COLUMN_HEADERS_DETALLADA.index("Codigo CA")
        idx_nombre = COLUMN_HEADERS_SIMPLE.index("Nombre") if is_simple_view else COLUMN_HEADERS_DETALLADA.index("Nombre")
        idx_org = COLUMN_HEADERS_SIMPLE.index("Organismo") if is_simple_view else COLUMN_HEADERS_DETALLADA.index("Organismo")


        for row in range(model.rowCount()):
            try:
                codigo_ca = model.item(row, idx_codigo).text().lower()
                nombre = model.item(row, idx_nombre).text().lower()
                organismo = model.item(row, idx_org).text().lower()
            except AttributeError:
                continue

            if (filter_text in codigo_ca or 
                filter_text in nombre or 
                filter_text in organismo):
                table_view.setRowHidden(row, False)
            else:
                table_view.setRowHidden(row, True)

    @Slot(str)
    def on_search_tab1_changed(self, text: str):
        self.filter_table_view(self.table_tab1, text)

    @Slot(str)
    def on_search_tab2_changed(self, text: str):
        self.filter_table_view(self.table_tab2, text)

    @Slot(str)
    def on_search_tab3_changed(self, text: str):
        self.filter_table_view(self.table_tab3, text)

    @Slot(str)
    def on_search_tab4_changed(self, text: str):
        self.filter_table_view(self.table_tab4, text)