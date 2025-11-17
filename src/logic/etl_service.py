import time
import json
from datetime import datetime
from pathlib import Path
from typing import Callable, TYPE_CHECKING, Dict, Optional
from playwright.sync_api import sync_playwright

if TYPE_CHECKING:
    from src.db.db_service import DbService
    from src.scraper.scraper_service import ScraperService
    from src.logic.score_engine import ScoreEngine
    from src.db.db_models import CaLicitacion

from config.config import MODO_HEADLESS, HEADERS_API
from src.utils.logger import configurar_logger

from src.utils.exceptions import (
    ScrapingFase1Error, DatabaseLoadError, DatabaseTransformError,
    ScrapingFase2Error, RecalculoError, ScraperHealthError
)

logger = configurar_logger(__name__)
BASE_DIR = Path(__file__).resolve().parents[2]
EXPORTS_DIR = BASE_DIR / "data" / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


class EtlService:
    def __init__( self, db_service: "DbService", scraper_service: "ScraperService", score_engine: "ScoreEngine", ):
        self.db_service = db_service
        self.scraper_service = scraper_service
        self.score_engine = score_engine
        logger.info("EtlService inicializado (dependencias inyectadas).")

    def _create_progress_emitters(
        self,
        progress_callback_text: Optional[Callable[[str], None]],
        progress_callback_percent: Optional[Callable[[int], None]]
    ):
        def emit_text(msg: str):
            if progress_callback_text: progress_callback_text(msg)
        def emit_percent(val: int):
            if progress_callback_percent: progress_callback_percent(val)
        return emit_text, emit_percent

    def _transform_puntajes_fase_1(
        self, 
        progress_callback_text: Optional[Callable[[str], None]] = None,
        progress_callback_percent: Optional[Callable[[int], None]] = None
    ):
        logger.info("Iniciando (Transform) Fase 1...")
        emit_text, emit_percent = self._create_progress_emitters( progress_callback_text, progress_callback_percent )
        try:
            licitaciones_a_puntuar = ( self.db_service.obtener_todas_candidatas_fase_1_para_recalculo() )
            total = len(licitaciones_a_puntuar)
            if not licitaciones_a_puntuar:
                logger.info("No hay CAs nuevas para puntuar (Fase 1).")
                return
            emit_text(f"Puntuando {total} CAs nuevas...")
            logger.info(f"Se puntuarán {total} CAs nuevas...")
            lista_para_actualizar = []
            for i, licitacion in enumerate(licitaciones_a_puntuar):
                item_raw = { 
                    'codigo': licitacion.codigo_ca,
                    'nombre': licitacion.nombre, 
                    'estado_ca_texto': licitacion.estado_ca_texto, 
                    'organismo_comprador': licitacion.organismo.nombre if licitacion.organismo else "" 
                }
                puntaje = self.score_engine.calcular_puntuacion_fase_1(item_raw)
                lista_para_actualizar.append((licitacion.ca_id, puntaje))
                percent = int(((i + 1) / total) * 100)
                if i % 100 == 0 or (i + 1) == total:
                    emit_percent(percent)
            self.db_service.actualizar_puntajes_fase_1_en_lote(lista_para_actualizar)
            logger.info("Transformación (T) Fase 1 completada. Puntajes actualizados.")
        except Exception as e:
            logger.error(f"Error en (Transform) Fase 1: {e}", exc_info=True)
            raise DatabaseTransformError(f"Error al calcular puntajes (Transform): {e}") from e

    def run_etl_live_to_db(
        self,
        progress_callback_text: Optional[Callable[[str], None]] = None,
        progress_callback_percent: Optional[Callable[[int], None]] = None,
        config: dict = None,
    ):
        emit_text, emit_percent = self._create_progress_emitters(
            progress_callback_text, progress_callback_percent
        )
        
        date_from = config["date_from"]
        date_to = config["date_to"]
        max_paginas = config["max_paginas"]

        logger.info(f"Iniciando ETL (Playwright)... Rango: {date_from} a {date_to}")
        emit_text("Iniciando Fase 1 (Listado - Playwright)...")
        emit_percent(5)

        # --- 1. EXTRACT (Fase 1 - Playwright) ---
        try:
            filtros_fase_1 = {
                'date_from': date_from.strftime('%Y-%m-%d'),
                'date_to': date_to.strftime('%Y-%m-%d')
            }
            # --- ¡CORRECCIÓN AQUÍ! Llamamos a run_scraper_listado ---
            datos_crudos = self.scraper_service.run_scraper_listado(
                emit_text, filtros_fase_1, max_paginas
            )
        except Exception as e:
            logger.critical(f"ETL (Playwright) falló en (Extract): {e}")
            emit_text(f"Error Crítico en Fase 1: {e}")
            raise ScrapingFase1Error(f"Fallo el scraping de listado (Fase 1): {e}") from e

        if not datos_crudos:
            logger.info("Fase 1 (Extract) no retornó datos. Terminando.")
            emit_text("Fase 1 no encontró CAs.")
            emit_percent(100)
            return
            
        emit_percent(20)

        # --- 2. LOAD (Fase 1) ---
        try:
            emit_text(f"Cargando {len(datos_crudos)} CAs crudas a la BD...")
            self.db_service.insertar_o_actualizar_licitaciones_raw(datos_crudos)
        except Exception as e:
            logger.critical(f"ETL (Playwright) falló en (Load): {e}")
            emit_text(f"Error Crítico al cargar en BD: {e}")
            raise DatabaseLoadError(f"Fallo al guardar en BD (Load): {e}") from e
            
        emit_percent(30)
            
        # --- 3. TRANSFORM (Fase 1) ---
        self._transform_puntajes_fase_1(emit_text, emit_percent) 
        emit_percent(40)

        # --- 4. OBTENER CANDIDATAS PARA FASE 2 ---
        emit_text("Obteniendo candidatas para Fase 2...")
        try:
            candidatas = self.db_service.obtener_candidatas_para_fase_2()
        except Exception as e:
            logger.error(f"Error al obtener candidatas de la BD: {e}")
            emit_text(f"Error de BD: {e}")
            raise e

        if not candidatas:
            logger.info("ETL (Playwright) finalizado. No hay candidatas nuevas para Fase 2.")
            emit_text("Proceso finalizado. No hay CAs nuevas para Fase 2.")
            emit_percent(100)
            return

        # --- 5. ELT (Fase 2 - Playwright) ---
        logger.info(f"Iniciando Fase 2 (Playwright) para {len(candidatas)} CAs.")
        emit_text(f"Iniciando Fase 2 (Scraping). {len(candidatas)} CAs por procesar...")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=MODO_HEADLESS, slow_mo=500)
                context = browser.new_context( user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit(537.36', viewport={'width': 1920, 'height': 1080}, locale='es-CL' )
                page = context.new_page()
                page.set_extra_http_headers(HEADERS_API)
                exitosas = 0
                total = len(candidatas)
                for i, licitacion in enumerate(candidatas):
                    codigo_ca = licitacion.codigo_ca
                    percent = 40 + int(((i + 1) / total) * 55)
                    emit_percent(percent)
                    
                    logger.info(f"--- [Fase 2] Procesando {i+1}/{total}: {codigo_ca} ---")
                    
                    datos_ficha = self.scraper_service.scrape_ficha_detalle_api(
                        page, codigo_ca, emit_text
                    )
                    
                    if datos_ficha is None:
                        logger.error(f"No se pudieron obtener datos para {codigo_ca}.")
                        continue
                    
                    puntos_fase_2 = self.score_engine.calcular_puntuacion_fase_2(datos_ficha)
                    puntuacion_total = (licitacion.puntuacion_final or 0) + puntos_fase_2
                    
                    self.db_service.actualizar_ca_con_fase_2(
                        codigo_ca, datos_ficha, puntuacion_total
                    )
                    exitosas += 1
                    time.sleep(1) 
                context.close()
                browser.close()
        except Exception as e:
            logger.critical(f"Fallo en el bucle de scraping Fase 2: {e}")
            emit_text(f"Error Crítico en Fase 2: {e}")
            raise ScrapingFase2Error(f"Fallo el scraping de fichas (Fase 2): {e}") from e
        finally:
            logger.info(f"Resumen Fase 2: {exitosas}/{total} procesadas.")

        emit_text("Proceso ETL (Playwright) Completo.")
        emit_percent(100)
        logger.info("Proceso ETL (Playwright) Completo.")

    def run_recalculo_total_fase_1(
        self, 
        progress_callback_text: Optional[Callable[[str], None]] = None,
        progress_callback_percent: Optional[Callable[[int], None]] = None
    ):
        logger.info("--- INICIANDO RECALCULO TOTAL DE PUNTAJES ---")
        emit_text, emit_percent = self._create_progress_emitters( progress_callback_text, progress_callback_percent )
        try:
            emit_text("Recargando reglas desde la BD...")
            self.score_engine.recargar_reglas()
            logger.info("Reglas recargadas en ScoreEngine.")
            emit_percent(10)
            emit_text("Obteniendo todas las CAs de Fase 1...")
            licitaciones_a_puntuar = ( self.db_service.obtener_todas_candidatas_fase_1_para_recalculo() )
            total = len(licitaciones_a_puntuar)
            if not licitaciones_a_puntuar:
                logger.info("No se encontraron CAs para recalcular.")
                emit_text("No hay CAs para recalcular.")
                emit_percent(100)
                return
            logger.info(f"Se recalcularán {total} CAs...")
            emit_text(f"Recalculando {total} CAs...")
            emit_percent(20)
            lista_para_actualizar = []
            for i, licitacion in enumerate(licitaciones_a_puntuar):
                # Filtro de seguimiento comentado para forzar recálculo total
                # if licitacion.seguimiento and ... continue 
                item_raw = { 
                    'codigo': licitacion.codigo_ca,
                    'nombre': licitacion.nombre, 
                    'estado_ca_texto': licitacion.estado_ca_texto, 
                    'organismo_comprador': licitacion.organismo.nombre if licitacion.organismo else "" 
                }
                puntaje = self.score_engine.calcular_puntuacion_fase_1(item_raw)
                lista_para_actualizar.append((licitacion.ca_id, puntaje))
                percent = 20 + int(((i + 1) / total) * 70)
                if i % 100 == 0 or (i + 1) == total:
                    emit_percent(percent)
            emit_text("Guardando nuevos puntajes en la BD...")
            self.db_service.actualizar_puntajes_fase_1_en_lote(lista_para_actualizar)
            logger.info("--- RECALCULO TOTAL COMPLETADO ---")
            emit_text("¡Recálculo completado!")
            emit_percent(100)
        except Exception as e:
            logger.error(f"Error en el Recálculo Total: {e}", exc_info=True)
            emit_text(f"Error en recálculo: {e}")
            raise RecalculoError(f"Fallo el proceso de recálculo: {e}") from e

    def run_fase2_update(
        self, 
        progress_callback_text: Optional[Callable[[str], None]] = None,
        progress_callback_percent: Optional[Callable[[int], None]] = None
    ):
        logger.info("--- INICIANDO ACTUALIZACIÓN DE FICHAS (Playwright) ---")
        emit_text, emit_percent = self._create_progress_emitters(
            progress_callback_text, progress_callback_percent
        )
        try:
            emit_text("Obteniendo CAs de pestañas 2, 3 y 4...")
            cas_tab2 = self.db_service.obtener_datos_tab2_relevantes()
            cas_tab3 = self.db_service.obtener_datos_tab3_seguimiento()
            cas_tab4 = self.db_service.obtener_datos_tab4_ofertadas()
            emit_percent(10)
            cas_a_procesar_map: Dict[int, "CaLicitacion"] = {}
            for cas_list in (cas_tab2, cas_tab3, cas_tab4):
                for ca in cas_list:
                    cas_a_procesar_map[ca.ca_id] = ca
            cas_a_procesar = list(cas_a_procesar_map.values())
            total = len(cas_a_procesar)
            if not cas_a_procesar:
                logger.info("No se encontraron CAs para actualizar.")
                emit_text("No hay CAs para actualizar.")
                emit_percent(100)
                return
            logger.info(f"Se actualizarán {total} CAs.")
            emit_text(f"Iniciando Fase 2. {total} CAs por procesar...")
            emit_percent(20)
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=MODO_HEADLESS, slow_mo=500)
                context = browser.new_context( user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit(537.36', viewport={'width': 1920, 'height': 1080}, locale='es-CL' )
                page = context.new_page()
                page.set_extra_http_headers(HEADERS_API)
                exitosas = 0
                for i, licitacion in enumerate(cas_a_procesar):
                    codigo_ca = licitacion.codigo_ca
                    percent = 20 + int(((i + 1) / total) * 75)
                    emit_percent(percent)
                    item_raw = { 'nombre': licitacion.nombre, 'estado_ca_texto': licitacion.estado_ca_texto, 'organismo_comprador': licitacion.organismo.nombre if licitacion.organismo else "" }
                    puntos_fase_1 = self.score_engine.calcular_puntuacion_fase_1(item_raw)
                    if puntos_fase_1 < 0:
                        logger.warning(f"Omitiendo actualización Fase 2 de {codigo_ca}, puntaje Fase 1 es negativo ({puntos_fase_1}).")
                        continue
                    emit_text(f"({i+1}/{total}) Actualizando: {codigo_ca}...")
                    logger.info(f"--- [Actualización Fase 2] Procesando {i+1}/{total}: {codigo_ca} ---")
                    
                    datos_ficha = self.scraper_service.scrape_ficha_detalle_api(
                        page, codigo_ca, emit_text
                    )
                    if datos_ficha is None:
                        logger.error(f"No se pudieron obtener datos de Fase 2 para {codigo_ca}.")
                        continue
                    
                    puntos_fase_2 = self.score_engine.calcular_puntuacion_fase_2(datos_ficha)
                    puntuacion_total = puntos_fase_1 + puntos_fase_2
                    self.db_service.actualizar_ca_con_fase_2(
                        codigo_ca, datos_ficha, puntuacion_total
                    )
                    exitosas += 1
                    time.sleep(1)
                context.close()
                browser.close()
        
        except Exception as e:
            logger.critical(f"Fallo en el bucle de actualización Fase 2: {e}", exc_info=True)
            emit_text(f"Error Crítico en Fase 2: {e}")
            raise ScrapingFase2Error(f"Fallo el scraping de actualización de fichas: {e}") from e
        finally:
            logger.info(f"Resumen Actualización Fase 2: {exitosas}/{total} procesadas.")
        
        emit_text("¡Actualización de fichas completada!")
        emit_percent(100)
        logger.info("--- ACTUALIZACIÓN DE FICHAS (FASE 2) COMPLETADA ---")

    def run_health_check(
        self, 
        progress_callback_text: Optional[Callable[[str], None]] = None,
        progress_callback_percent: Optional[Callable[[int], None]] = None
    ):
        logger.info("--- INICIANDO CHEQUEO DE SALUD (100% Playwright) ---")
        emit_text, emit_percent = self._create_progress_emitters(
            progress_callback_text, progress_callback_percent
        )
        try:
            emit_text("Probando Fase 1 (Playwright)...")
            emit_percent(10)
            filtros_fase_1 = {
                'date_from': datetime.now().strftime('%Y-%m-%d'),
                'date_to': datetime.now().strftime('%Y-%m-%d')
            }
            # --- ¡CORRECCIÓN AQUÍ! Llamamos a run_scraper_listado ---
            datos_crudos = self.scraper_service.run_scraper_listado(
                emit_text, filtros_fase_1, max_paginas=1
            )
            emit_percent(25)

            if not datos_crudos or not isinstance(datos_crudos, list):
                raise ScraperHealthError("Fase 1 (Listado) no retornó una lista de CAs. ¿Hay CAs publicadas hoy?")
            
            test_ca_fase1 = datos_crudos[0]
            campos_fase1 = ['codigo', 'nombre', 'organismo'] 
            for campo in campos_fase1:
                if campo not in test_ca_fase1:
                    raise ScraperHealthError(f"Fase 1 (Listado) falló. Falta el campo '{campo}' en el JSON.")
            
            logger.info("Chequeo Fase 1 (Playwright) OK.")
            emit_text("Chequeo Fase 1 (Playwright) OK.")
            emit_percent(50)

            codigo_ca_test = test_ca_fase1.get('codigo')
            emit_text(f"Probando Fase 2 (Playwright Ficha {codigo_ca_test})...")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=MODO_HEADLESS, slow_mo=500)
                context = browser.new_context( user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit(537.36', viewport={'width': 1920, 'height': 1080}, locale='es-CL' )
                page = context.new_page()
                page.set_extra_http_headers(HEADERS_API)
                datos_ficha = self.scraper_service.scrape_ficha_detalle_api(
                    page, codigo_ca_test, emit_text
                )
                context.close()
                browser.close()
            
            emit_percent(75)

            if not datos_ficha or not isinstance(datos_ficha, dict):
                raise ScraperHealthError("Fase 2 (Detalle) no retornó un JSON válido.")

            campos_fase2 = ['descripcion', 'productos_solicitados'] 
            for campo in campos_fase2:
                if campo not in datos_ficha:
                    raise ScraperHealthError(f"Fase 2 (Detalle) falló. Falta el campo '{campo}' en el JSON.")

            logger.info("Chequeo Fase 2 (Playwright) OK.")
            emit_text("Chequeo Fase 2 (Playwright) OK.")
            
            logger.info("--- CHEQUEO DE SALUD 100% PLAYWRIGHT COMPLETADO (ÉXITO) ---")
            emit_text("¡Conexión y formato de datos OK!")
            emit_percent(100)
            return True

        except Exception as e:
            logger.error(f"Error en el Chequeo de Salud: {e}", exc_info=True)
            emit_text(f"Error en chequeo: {e}")
            if isinstance(e, ScraperHealthError):
                raise e
            else:
                raise ScraperHealthError(f"Fallo inesperado en el chequeo: {e}") from e