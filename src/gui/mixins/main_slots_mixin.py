# -*- coding: utf-8 -*-
"""
Mixin para los Slots (acciones) de los botones principales.

"""

from PySide6.QtWidgets import QMessageBox, QSystemTrayIcon, QDialog
from PySide6.QtCore import Slot 
import datetime 

from src.gui.gui_scraping_dialog import ScrapingDialog
from src.gui.gui_settings_dialog import GuiSettingsDialog
from src.gui.gui_export_dialog import GuiExportDialog 
from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)


class MainSlotsMixin:
    """
    Este Mixin maneja las acciones disparadas por los
    botones principales de la barra de herramientas
    (Scraping, Exportar, Recalcular, Configuración).
    """


    def _show_task_completion_notification(self, title: str, message: str, is_auto: bool = False, is_error: bool = False):
        if self.tray_icon:
            icon = QSystemTrayIcon.MessageIcon.Warning if is_error else QSystemTrayIcon.MessageIcon.Information
            self.tray_icon.showMessage(title, message, icon, 4000)
        if not is_auto:
            if not is_error:
                QMessageBox.information(self, title, message)


    
    @Slot()
    def on_scraping_completed(self):
        self.set_ui_busy(False)
        if self.last_error:
            logger.warning("Proceso de Scraping finalizado con errores.")
            self._show_task_completion_notification( "Error de Scraping", f"La tarea falló: {self.last_error}", is_auto=False, is_error=True )
        else:
            msg = "La tarea de scraping ha finalizado exitosamente."
            self._show_task_completion_notification( "Proceso Completado", msg, is_auto=False, is_error=False )
        self.on_load_data_thread()

    @Slot()
    def on_export_report_completed(self): 
        self.set_ui_busy(False)
        if self.last_error:
            logger.error(f"La exportación falló: {self.last_error}")
            self._show_task_completion_notification( "Error de Exportación", f"La exportación falló: {self.last_error}", is_auto=False, is_error=True )
        elif self.last_export_path:
            logger.info("Exportación finalizada.")
            msg = f"Reporte guardado en:\n{self.last_export_path}"
            self._show_task_completion_notification( "Exportación Exitosa", msg, is_auto=False, is_error=False )

    @Slot()
    def on_recalculate_finished(self):
        self.set_ui_busy(False)
        if self.last_error:
            logger.warning(f"Proceso de Recálculo finalizado con errores: {self.last_error}")
            self._show_task_completion_notification( "Error de Recálculo", f"El recálculo falló: {self.last_error}", is_auto=False, is_error=True )
        else:
            msg = "Se han recalculado todos los puntajes exitosamente."
            self._show_task_completion_notification( "Recálculo Completado", msg, is_auto=False, is_error=False )
        self.on_load_data_thread()

    @Slot()
    def on_fase2_update_finished(self):
        self.set_ui_busy(False)
        is_auto = getattr(self, 'is_task_running_auto', False) 
        if self.last_error:
            logger.warning(f"Proceso de Actualización de Fichas finalizado con errores: {self.last_error}")
            self._show_task_completion_notification( "Error de Actualización", f"La actualización falló: {self.last_error}", is_auto=is_auto, is_error=True )
        else:
            msg = "Se han actualizado las fichas seleccionadas."
            self._show_task_completion_notification( "Actualización Completada", msg, is_auto=is_auto, is_error=False )
        self.on_load_data_thread()
        
    @Slot()
    def on_auto_task_finished(self):
        self.set_ui_busy(False)
        if self.last_error:
            logger.warning(f"PILOTO AUTOMÁTICO: Tarea finalizada con errores: {self.last_error}")
            self._show_task_completion_notification( "Error de Piloto Automático", f"La tarea automática falló: {self.last_error}", is_auto=True, is_error=True )
        else:
            logger.info("PILOTO AUTOMÁTICO: Tarea finalizada exitosamente.")
        self.on_load_data_thread()

    @Slot()
    def on_health_check_finished(self):
        self.set_ui_busy(False)
        if self.last_error:
            logger.warning(f"Chequeo de salud finalizado con errores: {self.last_error}")
            msg = ( "Falló el chequeo de salud.\n\n" f"Error: {self.last_error}\n\n" "Es posible que el sitio de Mercado Público haya cambiado, " "que no haya CAs hoy, o que no haya conexión a internet." )
            self._show_task_completion_notification("Chequeo Fallido", str(self.last_error), is_auto=False, is_error=True)
            QMessageBox.critical(self, "Chequeo Fallido", msg)
        elif self.last_health_check_ok:
            logger.info("Chequeo de salud finalizado con ÉXITO.")
            msg = ( "¡Chequeo de salud completado!\n\n" "La conexión a Mercado Público y el formato de datos " "(Fase 1 y Fase 2) parecen estar correctos." )
            self._show_task_completion_notification("Chequeo Exitoso", "Conexión y formato de datos OK.", is_auto=False, is_error=False)
            QMessageBox.information(self, "Chequeo Exitoso", msg)
        else:
            logger.error("Chequeo de salud finalizó en un estado desconocido (sin error, pero sin éxito).")
            

    
    @Slot()
    def on_open_scraping_dialog(self):
        if self.is_task_running:
            return
        dialog = ScrapingDialog(self)
        dialog.start_scraping.connect(self.on_start_full_scraping)
        dialog.exec()

    @Slot(dict)
    def on_start_full_scraping(self, config: dict):
        logger.info(f"Recibida configuración de scraping: {config}")
        task_to_run = None
        if config["mode"] == "to_db":
            task_to_run = self.etl_service.run_etl_live_to_db
        elif config["mode"] == "to_json":
            task_to_run = self.etl_service.run_etl_live_to_json
        if task_to_run is None:
            return
        
        self.start_task(
            task=task_to_run,
            on_result=lambda: logger.info("Proceso ETL completo OK"),
            on_error=self.on_task_error,
            on_finished=self.on_scraping_completed,
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
            task_args=(config,),
        )


    @Slot()
    def on_open_export_pestañas_dialog(self):
        """
        Abre el diálogo de opciones de exportación de pestañas.
        La exportación real se dispara por 'on_run_export_report_task'.
        """
        if self.is_task_running:
            return
        
        # Obtener el nombre de la pestaña actual
        try:
            current_tab_index = self.tabs.currentIndex()
            current_tab_name = self.tabs.tabText(current_tab_index)
        except Exception:
            current_tab_name = "Actual" # Fallback

        dialog = GuiExportDialog(current_tab_name, self)
        
        # Si el usuario presiona "Aceptar", obtenemos las opciones y lanzamos la tarea
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            self.on_run_export_report_task(options)

    @Slot(dict)
    def on_run_export_report_task(self, options: dict):
        """
        Inicia la tarea de exportación de pestañas con las opciones dadas.
        """
        if self.is_task_running: # Doble chequeo por si acaso
            return
        logger.info(f"Solicitud de exportar reporte de pestañas (con hilos) y opciones: {options}")
        self.last_export_path = None
        
        self.start_task(
            task=self.excel_service.generar_reporte_pestañas,
            on_result=lambda path: setattr(self, 'last_export_path', path),
            on_error=self.on_task_error,
            on_finished=self.on_export_report_completed, 
            task_args=(options,), # Pasa las opciones
            # Esta tarea es rápida, no necesita barra de progreso
        )

    @Slot()
    def on_export_full_db_thread(self):
        """
        Inicia la tarea de exportación de la BD completa.
        """
        if self.is_task_running:
            return
            
        confirm = QMessageBox.question(
            self, "Confirmar Exportación Completa",
            "Esto exportará TODAS las tablas de la base de datos (Licitaciones, "
            "Organismos, Keywords, etc.) a un único archivo Excel.\n\n"
            "Puede tardar unos segundos.\n\n¿Desea continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.No:
            return
            
        logger.info("Solicitud de exportar BD completa (con hilos)...")
        self.last_export_path = None
        
        self.start_task(
            task=self.excel_service.generar_reporte_bd_completa,
            on_result=lambda path: setattr(self, 'last_export_path', path),
            on_error=self.on_task_error,
            on_finished=self.on_export_report_completed, # <-- Reutiliza el mismo slot
            # Esta tarea es rápida, no necesita barra de progreso
        )



    @Slot()
    def on_open_settings_dialog(self):

        if self.is_task_running:
            return
        logger.debug("Abriendo diálogo de configuración...")
        dialog = GuiSettingsDialog(self.db_service, self.settings_manager, self)
        dialog.settings_changed.connect(self.on_settings_changed)
        dialog.exec()

    @Slot()
    def on_settings_changed(self):

        logger.info("Configuración actualizada por el usuario.")
        try:
            self.score_engine.recargar_reglas()
            logger.info("Reglas de ScoreEngine recargadas.")
            self.reload_timers_config() 
            QMessageBox.information(
                self, "Configuración Actualizada",
                "La configuración de reglas y/o automatización se ha guardado.\n"
                "Actualiza los puntajes en configuracion."
            )
        except Exception as e:
            logger.error(f"Error al aplicar nueva configuración: {e}")
            QMessageBox.critical(self, "Error", f"No se pudieron aplicar los cambios:\n{e}")

    @Slot()
    def on_run_recalculate_thread(self):
        # ... (Lógica de confirmación sin cambios)
        if self.is_task_running:
            return
        confirm = QMessageBox.question( self, "Confirmar Recálculo", "Esto recalculará los puntajes de Fase 1 para todas las CAs...", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No, )
        if confirm == QMessageBox.StandardButton.No:
            return
        logger.info("Iniciando recálculo total de puntajes (con hilo)...")
        
        self.start_task(
            task=self.etl_service.run_recalculo_total_fase_1,
            on_result=lambda: logger.info("Recálculo completado OK"),
            on_error=self.on_task_error,
            on_finished=self.on_recalculate_finished,
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
        )

    @Slot()
    def on_run_fase2_update_thread(self, skip_confirm=False):
        if self.is_task_running:
            return
        if not skip_confirm:
            confirm = QMessageBox.question( self, "Confirmar Actualización de Fichas", "Esto buscará en la web las fichas de todas las CAs en las pestañas...", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No, )
            if confirm == QMessageBox.StandardButton.No:
                return
        logger.info("Iniciando actualización de Fichas Fase 2 (con hilo)...")
        
        self.start_task(
            task=self.etl_service.run_fase2_update,
            on_result=lambda: logger.info("Actualización de Fichas completada OK"),
            on_error=self.on_task_error,
            on_finished=self.on_fase2_update_finished,
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
        )
    
    @Slot()
    def on_start_full_scraping_auto(self):
        logger.info("PILOTO AUTOMÁTICO: Disparado Timer (Fase 1 - Búsqueda Diaria)")
        if self.is_task_running:
            logger.warning("PILOTO AUTOMÁTICO (Fase 1): Omitido. Otra tarea ya está en ejecución.")
            return
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        config = { "mode": "to_db", "date_from": yesterday, "date_to": today, "max_paginas": 100 }
        logger.info("PILOTO AUTOMÁTICO (Fase 1): Iniciando tarea...")
        
        self.start_task(
            task=self.etl_service.run_etl_live_to_db,
            on_result=lambda: logger.info("PILOTO AUTOMÁTICO (Fase 1): Proceso ETL completo OK"),
            on_error=self.on_task_error,
            on_finished=self.on_auto_task_finished, 
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
            task_args=(config,),
        )

    @Slot()
    def on_run_fase2_update_thread_auto(self):

        logger.info("PILOTO AUTOMÁTICO: Disparado Timer (Fase 2 - Actualización Fichas)")
        if self.is_task_running:
            logger.warning("PILOTO AUTOMÁTICO (Fase 2): Omitido. Otra tarea ya está en ejecución.")
            return
        logger.info("PILOTO AUTOMÁTICO (Fase 2): Iniciando tarea...")
        
        self.start_task(
            task=self.etl_service.run_fase2_update,
            on_result=lambda: logger.info("PILOTO AUTOMÁTICO (Fase 2): Actualización de Fichas OK"),
            on_error=self.on_task_error,
            on_finished=self.on_auto_task_finished,
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
        )
        
    @Slot()
    def on_run_health_check_thread(self):
        # ... (Lógica sin cambios) ...
        if self.is_task_running:
            QMessageBox.warning(self, "Tarea en Curso", "Ya hay otra tarea ejecutándose. Espere a que termine.")
            return
        logger.info("Iniciando chequeo de salud (con hilo)...")
        self.last_health_check_ok = False 
        
        self.start_task(
            task=self.etl_service.run_health_check,
            on_result=lambda result: setattr(self, 'last_health_check_ok', result),
            on_error=self.on_task_error,
            on_finished=self.on_health_check_finished,
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
        )
