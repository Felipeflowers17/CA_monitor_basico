# -*- coding: utf-8 -*-
"""
Mixin para la carga de datos (Data Loading).
"""
from PySide6.QtCore import Slot
from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)

class DataLoaderMixin:
    """
    Maneja la carga secuencial de las pestañas para no congelar la UI.
    """

    @Slot()
    def on_load_data_thread(self):
        logger.info("Iniciando cadena de refresco de datos (4 tareas)...")
        # Iniciamos con la Tab 1
        self.start_task(
            task=self.db_service.obtener_datos_tab1_candidatas,
            on_result=self.poblar_tab1,
            on_finished=self.on_load_tab1_finished,
            # No pasamos error handler específico, usa el del mixin
        )

    # --- TAB 1 ---
    def poblar_tab1(self, data):
        self.poblar_tabla(self.model_tab1, data)

    @Slot()
    def on_load_tab1_finished(self):
        logger.debug("Hilo Tab 1 OK. Iniciando carga Tab 2...")
        self.start_task(
            task=self.db_service.obtener_datos_tab2_relevantes,
            on_result=self.poblar_tab2,
            on_finished=self.on_load_tab2_finished,
        )

    # --- TAB 2 ---
    def poblar_tab2(self, data):
        self.poblar_tabla(self.model_tab2, data)

    @Slot()
    def on_load_tab2_finished(self):
        logger.debug("Hilo Tab 2 OK. Iniciando carga Tab 3...")
        self.start_task(
            task=self.db_service.obtener_datos_tab3_seguimiento,
            on_result=self.poblar_tab3,
            on_finished=self.on_load_tab3_finished,
        )

    # --- TAB 3 ---
    def poblar_tab3(self, data):
        self.poblar_tabla(self.model_tab3, data)

    @Slot()
    def on_load_tab3_finished(self):
        logger.debug("Hilo Tab 3 OK. Iniciando carga Tab 4...")
        self.start_task(
            task=self.db_service.obtener_datos_tab4_ofertadas,
            on_result=self.poblar_tab4,
            on_finished=self.on_load_tab4_finished,
        )

    # --- TAB 4 ---
    def poblar_tab4(self, data):
        self.poblar_tabla(self.model_tab4, data)

    @Slot()
    def on_load_tab4_finished(self):
        # Fin de la cadena
        logger.info("Carga de todas las tablas completada.")
        # Aquí solía estar: self.statusBar().showMessage(...)