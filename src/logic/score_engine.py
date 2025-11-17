# -*- coding: utf-8 -*-
"""
Motor de Puntuación (Score Engine)

"""

from src.utils.logger import configurar_logger
from src.db.db_models import (
    CaKeyword, 
    CaOrganismoRegla,      
    TipoReglaOrganismo,  
    CaOrganismo,
)

from config.config import UMBRAL_FASE_1
from config.score_config import (
    PUNTOS_SEGUNDO_LLAMADO,
    PUNTOS_ALERTA_URGENCIA,
)

from typing import Dict, List, TYPE_CHECKING, Set, Optional

if TYPE_CHECKING:
    from src.db.db_service import DbService

logger = configurar_logger(__name__)


class ScoreEngine:
    """
    Clase de servicio que maneja toda la lógica de puntuación.
    """

    def __init__(self, db_service: "DbService"):
        self.db_service = db_service
        logger.info("ScoreEngine inicializado (MODO DINÁMICO).")

        self.reglas_keywords: Dict[str, List[CaKeyword]] = {}
        self.reglas_prioritarias: Dict[int, int] = {}
        self.reglas_no_deseadas: Set[int] = set()
        
        # Mapa de traducción: { "nombre normalizado": organismo_id }
        self.organismo_name_to_id_map: Dict[str, int] = {}
        
        try:
            self.recargar_reglas()
        except Exception as e:
            logger.critical(f"Error fatal al cargar reglas iniciales desde la BD: {e}", exc_info=True)


    def recargar_reglas(self):
        """
        Recarga todas las reglas (Keywords, Organismos y Mapa de Nombres) desde la BD.
        """
        logger.info("ScoreEngine: Recargando reglas desde la Base de Datos...")
        
        self.reglas_keywords = {}
        self.reglas_prioritarias = {}
        self.reglas_no_deseadas = set()
        self.organismo_name_to_id_map = {}

        # 1. Cargar Keywords
        try:
            keywords_db = self.db_service.get_all_keywords()
            for kw in keywords_db:
                tipo = kw.tipo
                if tipo not in self.reglas_keywords:
                    self.reglas_keywords[tipo] = []
                self.reglas_keywords[tipo].append(kw)
            logger.info(f"Cargadas {len(keywords_db)} keywords dinámicas.")
        except Exception as e:
            logger.error(f"Error al cargar keywords desde la BD: {e}", exc_info=True)

        # 2. Cargar Reglas de Organismos (por ID)
        try:
            organismos_reglas_db = self.db_service.get_all_organismo_reglas()
            
            for regla in organismos_reglas_db:
                if not regla.organismo_id:
                    continue
                
                if regla.tipo == TipoReglaOrganismo.PRIORITARIO:
                    self.reglas_prioritarias[regla.organismo_id] = regla.puntos
                elif regla.tipo == TipoReglaOrganismo.NO_DESEADO:
                    self.reglas_no_deseadas.add(regla.organismo_id)

            logger.info(f"Cargadas {len(self.reglas_prioritarias)} reglas de organismos prioritarios.")
            logger.info(f"Cargadas {len(self.reglas_no_deseadas)} reglas de organismos no deseados.")
            
        except Exception as e:
            logger.error(f"Error al cargar reglas de organismos desde la BD: {e}", exc_info=True)

        # 3. Cargar Mapa de Nombres de Organismos
        try:
            all_organismos = self.db_service.get_all_organisms()
            for org in all_organismos:
                if org.nombre and org.organismo_id:
                    nombre_norm = self._normalizar_texto(org.nombre)
                    if nombre_norm:
                        self.organismo_name_to_id_map[nombre_norm] = org.organismo_id
            logger.info(f"Cargado mapa de {len(self.organismo_name_to_id_map)} nombres de organismos.")
        except Exception as e:
            logger.error(f"Error al cargar mapa de nombres de organismos: {e}", exc_info=True)


    def _normalizar_texto(self, texto: str | None) -> str:
        if not texto:
            return ""
        return texto.lower().strip()


    def calcular_puntuacion_fase_1(self, licitacion_raw: dict) -> int:
        """
        Calcula el puntaje Fase 1.
        Acepta un 'dict' crudo y usa el mapa 'organismo_name_to_id_map'.
        """
        
        organismo_nombre_norm = self._normalizar_texto(licitacion_raw.get("organismo_comprador"))
        
        organismo_id: Optional[int] = None
        if organismo_nombre_norm:
            organismo_id = self.organismo_name_to_id_map.get(organismo_nombre_norm)

        if organismo_id is not None and organismo_id in self.reglas_no_deseadas:
            logger.debug(f"Fase 1 SKIP (No Deseado): '{licitacion_raw.get('nombre')}' | Org: {organismo_nombre_norm}")
            return -9999
        
        puntaje = 0
        
        nombre_norm = self._normalizar_texto(licitacion_raw.get("nombre"))
        estado_norm = self._normalizar_texto(licitacion_raw.get("estado_ca_texto"))
        
        if not nombre_norm:
            return 0

        if organismo_id is not None and organismo_id in self.reglas_prioritarias:
            puntaje += self.reglas_prioritarias[organismo_id]
            
        if "segundo llamado" in estado_norm:
            puntaje += PUNTOS_SEGUNDO_LLAMADO
        if "alerta urgencia" in estado_norm:
            puntaje += PUNTOS_ALERTA_URGENCIA
            
        for kw_obj in self.reglas_keywords.get('titulo_pos', []):
            if kw_obj.keyword in nombre_norm:
                puntaje += kw_obj.puntos
                
        for kw_obj in self.reglas_keywords.get('titulo_neg', []):
            if kw_obj.keyword in nombre_norm:
                puntaje += kw_obj.puntos
        
        puntaje_final = max(0, puntaje)
        
        if puntaje_final >= UMBRAL_FASE_1:
            logger.debug(f"Fase 1 OK (Dinámico): '{nombre_norm}' | Score: {puntaje_final}")
        
        return puntaje_final

    def calcular_puntuacion_fase_2(self, datos_ficha: dict) -> int:
        """
        Calcula el puntaje de Fase 2 (Descripción y Productos).
        Ahora usa las keywords dinámicas de la BD.
        """
        puntaje = 0
        
        # --- 1. Lógica de Productos ---
        productos_raw = datos_ficha.get("productos_solicitados", [])
        texto_productos = ""
        if productos_raw:
            texto_productos = " ".join(
                self._normalizar_texto(item.get("nombre", "") + " " + item.get("descripcion", ""))
                for item in productos_raw
            )
        
        # --- 2. Lógica de Descripción Principal ---
        descripcion_norm = self._normalizar_texto(datos_ficha.get("descripcion"))
        
        # --- 3. Aplicar Keywords Dinámicas ---
        
        # Aplicar Keywords 'titulo_pos' a la descripción
        if descripcion_norm:
            for kw_obj in self.reglas_keywords.get('titulo_pos', []):
                if kw_obj.keyword in descripcion_norm:
                    puntaje += kw_obj.puntos
            
            # Aplicar Keywords 'titulo_neg' a la descripción
            for kw_obj in self.reglas_keywords.get('titulo_neg', []):
                if kw_obj.keyword in descripcion_norm:
                    puntaje += kw_obj.puntos

        # Aplicar Keywords 'producto' al texto de los productos
        if texto_productos:
            for kw_obj in self.reglas_keywords.get('producto', []):
                if kw_obj.keyword in texto_productos:
                    puntaje += kw_obj.puntos
        
        logger.debug(f"Fase 2 | Desc: '{descripcion_norm[:50]}...', Prod: '{texto_productos[:50]}...' | Score: {puntaje}")
        # El puntaje de Fase 2 SÍ puede ser negativo si encuentra muchas keywords negativas.
        # El puntaje final se suma al de Fase 1 en el EtlService.
        return puntaje