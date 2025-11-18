# -*- coding: utf-8 -*-
"""
Mixin para la gestión de hilos (Threading).
"""
from PySide6.QtCore import Slot
from src.gui.gui_worker import Worker
from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)

class ThreadingMixin:
    """
    Mixin para manejar tareas en segundo plano usando QThreadPool.
    Ahora compatible con Fluent Window y gestión segura de memoria (Fix RuntimeError).
    """

    def start_task(
        self,
        task,
        on_result=None,
        on_error=None,
        on_finished=None,
        on_progress=None,
        on_progress_percent=None,
        task_args=(),
        task_kwargs=None,
    ):
        if task_kwargs is None:
            task_kwargs = {}

        # Bloquear la UI
        self.set_ui_busy(True)

        # Inferir si necesitamos señales de progreso
        needs_text = bool(on_progress)
        needs_percent = bool(on_progress_percent)
        
        try:
            worker = Worker(task, needs_text, needs_percent, *task_args, **task_kwargs)
            
            # Conexión de señales
            if on_result:
                worker.signals.result.connect(on_result)
            if on_error:
                worker.signals.error.connect(on_error)
            
            # --- GESTIÓN DE LIMPIEZA SEGURA ---
            # 1. UI Busy: Liberar la UI cuando termine
            worker.signals.finished.connect(self.on_task_finished_common)
            
            # 2. Garbage Collection: Eliminar referencia de la lista
            # Usamos lambda para capturar ESTA instancia específica de worker
            worker.signals.finished.connect(lambda: self._cleanup_worker(worker))
            
            # 3. Callback del usuario (si existe)
            if on_finished:
                worker.signals.finished.connect(on_finished)
                
            # Progreso
            if on_progress:
                worker.signals.progress.connect(on_progress)
            else:
                worker.signals.progress.connect(self.on_progress_update) 

            if on_progress_percent:
                worker.signals.progress_percent.connect(on_progress_percent)
            else:
                worker.signals.progress_percent.connect(self.on_progress_percent_update) 

            # Iniciar
            self.thread_pool.start(worker)
            self.running_workers.append(worker)
            
        except TypeError as e:
            self.set_ui_busy(False)
            logger.critical(f"Error al iniciar Worker: {e}")
            raise e

    def _cleanup_worker(self, worker):
        """
        Elimina el worker de la lista de referencias de Python.
        Es seguro porque usa comparación de identidad de lista, no métodos C++.
        """
        if worker in self.running_workers:
            self.running_workers.remove(worker)

    @Slot()
    def on_task_finished_common(self):
        """
        Se ejecuta siempre que termina una tarea.
        Solo se encarga de liberar el estado de ocupado de la UI.
        """
        # Ya no tocamos self.running_workers aquí para evitar el RuntimeError
        self.set_ui_busy(False)

    @Slot(str)
    def on_progress_update(self, message: str):
        logger.debug(f"Progreso Tarea: {message}")

    @Slot(int)
    def on_progress_percent_update(self, value: int):
        if self.progress_bar:
            self.progress_bar.setValue(value)
            if value >= 100:
                self.progress_bar.hide()
            else:
                self.progress_bar.show()

    @Slot(tuple)
    def on_task_error(self, error_info):
        self.set_ui_busy(False)
        ex_type, value, tb_str = error_info
        self.last_error = value
        logger.error(f"Error en tarea en segundo plano: {value}\n{tb_str}")