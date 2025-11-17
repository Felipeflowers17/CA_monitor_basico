# -*- coding: utf-8 -*-
"""
Servicio de Exportación (Excel y CSV).

(Versión 9.0 - Exportación Flexible)
"""

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Any

import pandas as pd

from src.db.session import SessionLocal
from src.db.db_models import (
    Base, CaLicitacion, CaSector, CaOrganismo, 
    CaSeguimiento, CaKeyword, CaOrganismoRegla
)

if TYPE_CHECKING:
    from src.db.db_service import DbService

from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
EXPORTS_DIR = BASE_DIR / "data" / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ExcelService:
    def __init__(self, db_service: "DbService"):
        self.db_service = db_service
        logger.info("ExcelService (v9.0) inicializado.")

    def _convertir_a_dataframe(self, licitaciones: list[CaLicitacion]) -> pd.DataFrame:
        """Helper para convertir la lista de objetos SQLAlchemy a un DataFrame."""
        datos = []
        for ca in licitaciones:
            
            fecha_cierre_ingenua = None
            if ca.fecha_cierre:
                fecha_cierre_ingenua = ca.fecha_cierre.replace(tzinfo=None)
            
            fecha_cierre_2_ingenua = None
            if ca.fecha_cierre_segundo_llamado:
                fecha_cierre_2_ingenua = ca.fecha_cierre_segundo_llamado.replace(tzinfo=None)

            datos.append(
                {
                    "Score": ca.puntuacion_final,
                    "Código CA": ca.codigo_ca,
                    "Nombre": ca.nombre,
                    "Descripcion": ca.descripcion,
                    "Organismo": ca.organismo.nombre if ca.organismo else "N/A",
                    "Dirección Entrega": ca.direccion_entrega,
                    "Estado": ca.estado_ca_texto,
                    "Fecha Publicación": ca.fecha_publicacion,
                    "Fecha Cierre": fecha_cierre_ingenua,
                    "Fecha Cierre 2do Llamado": fecha_cierre_2_ingenua,
                    "Proveedores": ca.proveedores_cotizando,
                    "Productos": str(ca.productos_solicitados) if ca.productos_solicitados else None,
                    "Favorito": ca.seguimiento.es_favorito if ca.seguimiento else False,
                    "Ofertada": ca.seguimiento.es_ofertada if ca.seguimiento else False,
                }
            )
        
        columnas_detalladas = [
            "Score", "Código CA", "Nombre", "Descripcion", "Organismo",
            "Dirección Entrega", "Estado", "Fecha Publicación", "Fecha Cierre",
            "Fecha Cierre 2do Llamado", "Productos", "Proveedores",
            "Favorito", "Ofertada"
        ]

        if not datos:
            return pd.DataFrame(columns=columnas_detalladas)

        df = pd.DataFrame(datos)
        # Asegurar que todas las columnas existan
        df = df.reindex(columns=columnas_detalladas)
        return df

    def _aplicar_schema_dataframe(self, df: pd.DataFrame, tab_name: str) -> pd.DataFrame:
        """Aplica el schema de columnas correcto según la pestaña."""
        
        # Schema para Pestaña 1 (Candidatas)
        if tab_name.startswith("CAs Candidatas"):
            columnas_tab_1 = [
                "Score", "Código CA", "Nombre", "Organismo", "Dirección Entrega",
                "Estado", "Fecha Publicación", "Fecha Cierre", "Proveedores"
            ]
            # Aseguramos que solo existan estas columnas, si están
            return df.reindex(columns=columnas_tab_1)

        # Schema para Pestañas 2, 3 y 4 (Detalladas)
        columnas_detalladas = [
            "Score", "Código CA", "Nombre", "Descripcion", "Organismo",
            "Dirección Entrega", "Estado", "Fecha Publicación", "Fecha Cierre",
            "Fecha Cierre 2do Llamado", "Productos", "Proveedores",
            "Favorito", "Ofertada"
        ]
        return df.reindex(columns=columnas_detalladas)


    def generar_reporte_pestañas(self, options: dict) -> str:
        """
        Genera un reporte (Excel o CSV) con el contenido de las pestañas
        según las opciones seleccionadas por el usuario.
        """
        logger.info(f"Iniciando generación de reporte de pestañas: {options}")
        
        formato = options.get("format", "excel")
        alcance = options.get("scope", "all")
        tab_name = options.get("tab_name", "")
        
        dfs_to_export: Dict[str, pd.DataFrame] = {}

        try:
            # 1. Obtener los DataFrames a exportar
            if alcance == "all":
                datos_tab1 = self.db_service.obtener_datos_tab1_candidatas()
                datos_tab2 = self.db_service.obtener_datos_tab2_relevantes()
                datos_tab3 = self.db_service.obtener_datos_tab3_seguimiento()
                datos_tab4 = self.db_service.obtener_datos_tab4_ofertadas()
                
                dfs_to_export["Candidatas"] = self._aplicar_schema_dataframe(self._convertir_a_dataframe(datos_tab1), "CAs Candidatas")
                dfs_to_export["Relevantes"] = self._aplicar_schema_dataframe(self._convertir_a_dataframe(datos_tab2), "CAs Relevantes")
                dfs_to_export["Seguimiento"] = self._aplicar_schema_dataframe(self._convertir_a_dataframe(datos_tab3), "CAs en Seguimiento")
                dfs_to_export["Ofertadas"] = self._aplicar_schema_dataframe(self._convertir_a_dataframe(datos_tab4), "CAs Ofertadas")

            elif alcance == "current":
                datos_tab = []
                if tab_name == "CAs Candidatas (Fase 1)":
                    datos_tab = self.db_service.obtener_datos_tab1_candidatas()
                elif tab_name == "CAs Relevantes (Fase 2)":
                    datos_tab = self.db_service.obtener_datos_tab2_relevantes()
                elif tab_name == "CAs en Seguimiento (Favoritos)":
                    datos_tab = self.db_service.obtener_datos_tab3_seguimiento()
                elif tab_name == "CAs Ofertadas":
                    datos_tab = self.db_service.obtener_datos_tab4_ofertadas()
                
                df = self._convertir_a_dataframe(datos_tab)
                dfs_to_export[tab_name] = self._aplicar_schema_dataframe(df, tab_name)

        except Exception as e:
            logger.error(f"Error al obtener datos de la BD para exportar: {e}")
            raise e

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 2. Guardar los DataFrames según el formato
        try:
            if formato == "excel":
                nombre_archivo = f"Reporte_Pestañas_{timestamp}.xlsx"
                ruta_salida = EXPORTS_DIR / nombre_archivo
                with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
                    for sheet_name, df in dfs_to_export.items():
                        # Limpiar nombre para la hoja de Excel
                        sheet_name_clean = sheet_name.split(' ')[0]
                        df.to_excel(writer, sheet_name=sheet_name_clean, index=False)
                
                logger.info(f"Reporte Excel generado exitosamente en: {ruta_salida}")
                return str(ruta_salida)

            elif formato == "csv":
                if alcance == "current":
                    # Exportar un solo archivo CSV
                    sheet_name, df = list(dfs_to_export.items())[0]
                    sheet_name_clean = sheet_name.split(' ')[0]
                    nombre_archivo = f"Reporte_{sheet_name_clean}_{timestamp}.csv"
                    ruta_salida = EXPORTS_DIR / nombre_archivo
                    df.to_csv(ruta_salida, index=False, encoding='utf-8-sig')
                    
                    logger.info(f"Reporte CSV (único) generado exitosamente en: {ruta_salida}")
                    return str(ruta_salida)
                
                elif alcance == "all":
                    # Exportar múltiples CSVs a una carpeta
                    nombre_carpeta = f"Reporte_CSV_{timestamp}"
                    ruta_salida_dir = EXPORTS_DIR / nombre_carpeta
                    os.makedirs(ruta_salida_dir, exist_ok=True)
                    
                    for sheet_name, df in dfs_to_export.items():
                        nombre_archivo_csv = f"{sheet_name}.csv"
                        ruta_csv = ruta_salida_dir / nombre_archivo_csv
                        df.to_csv(ruta_csv, index=False, encoding='utf-8-sig')
                    
                    logger.info(f"Reporte CSV (múltiple) generado exitosamente en: {ruta_salida_dir}")
                    return str(ruta_salida_dir)

        except Exception as e:
            logger.error(f"Error al escribir el archivo de exportación: {e}", exc_info=True)
            raise e

    def generar_reporte_bd_completa(self) -> str:
        """
        Genera un reporte Excel con TODAS las tablas de la base de datos.
        """
        logger.info("Iniciando generación de reporte de BD completa...")

        # Lista de todos los modelos (tablas) que queremos exportar
        tablas_a_exportar = [
            CaLicitacion,
            CaSeguimiento,
            CaOrganismo,
            CaSector,
            CaKeyword,
            CaOrganismoRegla
        ]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"Export_BD_Completa_{timestamp}.xlsx"
        ruta_salida = EXPORTS_DIR / nombre_archivo

        try:
            with SessionLocal() as session:
                connection = session.connection()
                
                with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
                    for model in tablas_a_exportar:
                        table_name = model.__tablename__
                        logger.debug(f"Exportando tabla: {table_name}")
                        try:
                            # pd.read_sql_table es la forma más eficiente
                            df = pd.read_sql_table(table_name, con=connection)
                            df.to_excel(writer, sheet_name=table_name, index=False)
                        except Exception as e:
                            logger.warning(f"No se pudo exportar la tabla {table_name}: {e}")
            
            logger.info(f"Reporte de BD completa generado exitosamente en: {ruta_salida}")
            return str(ruta_salida)

        except Exception as e:
            logger.error(f"Error al escribir el archivo Excel de BD completa: {e}", exc_info=True)
            raise e