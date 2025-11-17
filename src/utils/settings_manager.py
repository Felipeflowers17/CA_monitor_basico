# -*- coding: utf-8 -*-
"""
Gestor de Configuración (SettingsManager).

Maneja la lectura y escritura de un archivo 'settings.json'
para persistir la configuración de la GUI, como los
intervalos de automatización.
"""

import json
from pathlib import Path
from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)

# Define la ruta del archivo (en la raíz del proyecto)
BASE_DIR = Path(__file__).resolve().parents[2] 
SETTINGS_FILE = BASE_DIR / "settings.json"

# Valores por defecto
DEFAULT_SETTINGS = {
    "auto_fase1_intervalo_horas": 0, # Apagado
    "auto_fase2_intervalo_minutos": 0 # Apagado
}

class SettingsManager:
    """Lee y escribe la configuración de la app desde/hacia 'settings.json'."""

    def __init__(self, file_path=SETTINGS_FILE, defaults=DEFAULT_SETTINGS):
        self.file_path = file_path
        self.defaults = defaults
        self.config = self.load_settings()

    def load_settings(self) -> dict:
        """Carga la configuración desde 'settings.json'."""
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Asegurarse de que todas las claves por defecto existan
                    for key, value in self.defaults.items():
                        config.setdefault(key, value)
                    return config
            else:
                logger.info("No se encontró 'settings.json'. Creando con valores por defecto.")
                self.save_settings(self.defaults)
                return self.defaults.copy()
        except Exception as e:
            logger.error(f"Error al cargar 'settings.json': {e}. Usando valores por defecto.")
            return self.defaults.copy()

    def save_settings(self, config: dict):
        """Guarda la configuración en 'settings.json'."""
        try:
            self.config = config
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Configuración guardada en '{self.file_path}'")
        except Exception as e:
            logger.error(f"Error al guardar 'settings.json': {e}")

    def get_setting(self, key: str):
        """Obtiene un valor de la configuración."""
        return self.config.get(key, self.defaults.get(key))

    def set_setting(self, key: str, value):
        """Establece un valor en la configuración (pero no guarda)."""
        self.config[key] = value