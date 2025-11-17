# -*- coding: utf-8 -*-
"""
Worker de Hilos (QRunnable).

"""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)


class WorkerSignals(QObject):
    """
    Define las señales disponibles para un worker.
    ...
    Señales:
        ...
        progress: Se emite para reportar el progreso (pasa un string).
        progress_percent: Se emite para reportar el % (pasa un int).
    """

    finished = Signal()
    error = Signal(Exception)
    result = Signal(object)
    progress = Signal(str)
    progress_percent = Signal(int) 


class Worker(QRunnable):
    """
    Worker genérico que hereda de QRunnable...
    """

    def __init__(
        self,
        task: Callable[..., Any],
        needs_progress_text: bool,  
        needs_progress_percent: bool, 
        *args,
        **kwargs,
    ):
        """
        Inicializa el worker.

        """
        super().__init__()
        self.task = task
        self.needs_progress_text = needs_progress_text
        self.needs_progress_percent = needs_progress_percent
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()  # noqa: F821
    def run(self):
        """
        El método principal que se ejecuta en el hilo secundario.
        ...
        """
        logger.debug(f"Hilo (QRunnable) iniciando tarea: {self.task.__name__}")

        try:
            
            # Convertir tupla de args a lista para poder insertar
            task_args_list = list(self.args)

            # Inyectar callbacks en orden (texto, luego porcentaje)
            # El que se inserta de ÚLTIMO queda PRIMERO en la lista.
            if self.needs_progress_percent:
                task_args_list.insert(0, self.signals.progress_percent.emit)
            
            if self.needs_progress_text:
                task_args_list.insert(0, self.signals.progress.emit)
            
            task_args = tuple(task_args_list)

            # Ejecutar la tarea
            resultado = self.task(*task_args, **self.kwargs)

            if resultado is not None:
                self.signals.result.emit(resultado)

        except Exception as e:
            logger.error(f"Error en el hilo (QRunnable): {e}", exc_info=True)
            self.signals.error.emit(e)
        finally:
            self.signals.finished.emit()
            logger.debug(f"Hilo (QRunnable) finalizó tarea: {self.task.__name__}")