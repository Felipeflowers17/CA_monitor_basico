# -*- coding: utf-8 -*-
"""
Configuración del Motor de Puntuación (Score Engine).

(Versión 5.3 - Se han movido UMBRALES a config.py)
"""



# --- Puntuaciones Asignadas ---
# (Mantenemos estas aquí, ya que solo el ScoreEngine las usa)
#
PUNTOS_ORGANISMO = 5
PUNTOS_SEGUNDO_LLAMADO = 4
PUNTOS_KEYWORD_TITULO = 2
PUNTOS_ALERTA_URGENCIA = 3 
PUNTOS_KEYWORD_PRODUCTO = 5

# --- Listas de Texto para el Scoring (Estáticas) ---
#
# (Estas listas ya no se usan porque el motor es dinámico,
# pero las dejamos como referencia de la lógica antigua)

ORGANISMOS_PRIORITARIOS = {
    "i municipalidad de canela",
    "departamento provincial de educación arauco",
    # ... etc
}

KEYWORDS_TITULO = {
    "adquisicion", "ferreteria", "vacunas",
    # ... etc
}

# Palabras clave en PRODUCTOS SOLICITADOS (para Fase 2) 
# (Esta sí se usa en la lógica de Fase 2 que aún es estática)
KEYWORDS_PRODUCTOS_ALTO_VALOR = {
    "" 
}