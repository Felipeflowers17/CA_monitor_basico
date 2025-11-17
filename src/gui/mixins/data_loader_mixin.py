# -*- coding: utf-8 -*-
"""
Mixin para la carga de datos en las pestañas.
"""


from PySide6.QtCore import Slot 
from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)



class DataLoaderMixin:
    """
    Este Mixin maneja la lógica de carga de datos en cadena
    para las 4 pestañas de la aplicación, asegurando que
    se carguen una tras otra y no todas a la vez.
    """

    @Slot()
    def on_load_data_thread(self):
        logger.info("Iniciando cadena de refresco de datos (4 tareas)...")
        self.start_task(
            task=self.db_service.obtener_datos_tab1_candidatas,
            on_result=lambda data: self.poblar_tabla(self.model_tab1, data),
            on_error=self.on_task_error,
            on_finished=self.on_load_tab1_finished,
        )

    @Slot()
    def on_load_tab1_finished(self):
        """Carga la Pestaña 2 al finalizar la 1."""
        if self.last_error:
            self.set_ui_busy(False)
            return
        logger.debug("Hilo Tab 1 OK. Iniciando carga Tab 2...")
        self.start_task(
            task=self.db_service.obtener_datos_tab2_relevantes,
            on_result=lambda data: self.poblar_tabla(self.model_tab2, data),
            on_error=self.on_task_error,
            on_finished=self.on_load_tab2_finished,
        )

    @Slot()
    def on_load_tab2_finished(self):
        """Carga la Pestaña 3 al finalizar la 2."""
        if self.last_error:
            self.set_ui_busy(False)
            return
        logger.debug("Hilo Tab 2 OK. Iniciando carga Tab 3...")
        self.start_task(
            task=self.db_service.obtener_datos_tab3_seguimiento,
            on_result=lambda data: self.poblar_tabla(self.model_tab3, data),
            on_error=self.on_task_error,
            on_finished=self.on_load_tab3_finished,
        )

    @Slot()
    def on_load_tab3_finished(self):
        """Carga la Pestaña 4 al finalizar la 3."""
        if self.last_error:
            self.set_ui_busy(False)
            return
        logger.debug("Hilo Tab 3 OK. Iniciando carga Tab 4...")
        self.start_task(
            task=self.db_service.obtener_datos_tab4_ofertadas,
            on_result=lambda data: self.poblar_tabla(self.model_tab4, data),
            on_error=self.on_task_error,
            on_finished=self.on_load_tab4_finished,
        )

    @Slot()
    def on_load_tab4_finished(self):
        """Finaliza la cadena de carga y desbloquea la GUI."""
        self.set_ui_busy(False)
        if self.last_error:
            logger.warning("Cadena de carga finalizada con errores.")
        else:
            logger.info("Carga de todas las tablas completada.")
            self.statusBar().showMessage("¡Datos refrescados exitosamente!", 5000)