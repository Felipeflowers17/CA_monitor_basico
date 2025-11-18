# -*- coding: utf-8 -*-
"""
Modelos de la Base de Datos (SQLAlchemy ORM).

Se han agregado campos para soportar:
1. Distinción de "Segundo Llamado" (estado_convocatoria).
2. Notas personalizadas del usuario (notas).
"""

import datetime
import enum  
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    Index,
    Enum,
    Text # Importamos Text para campos de notas largas
)
from typing import Optional, List


class Base(DeclarativeBase):
    type_annotation_map = {
        dict[str, any]: JSON,
        list[dict[str, any]]: JSON,
    }

# --- Tablas de Jerarquía  ---

class CaSector(Base):
    __tablename__ = "ca_sector"
    
    sector_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    organismos: Mapped[List["CaOrganismo"]] = relationship(back_populates="sector")

    def __repr__(self):
        return f"<CaSector(nombre='{self.nombre}')>"

        
class CaOrganismo(Base):
    __tablename__ = "ca_organismo"
    
    organismo_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    
    sector_id: Mapped[int] = mapped_column(ForeignKey("ca_sector.sector_id"))
    
    sector: Mapped["CaSector"] = relationship(back_populates="organismos", lazy="joined")
    
    licitaciones: Mapped[List["CaLicitacion"]] = relationship(back_populates="organismo")

    def __repr__(self):
        return f"<CaOrganismo(nombre='{self.nombre}')>"

        
# --- Tablas de Aplicación ---

class CaLicitacion(Base):
    __tablename__ = "ca_licitacion"
    
    ca_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_ca: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, doc="El código de Mercado Público (ej. 1234-56-COT25)"
    )
    nombre: Mapped[Optional[str]] = mapped_column(String(1000))
    monto_clp: Mapped[Optional[float]] = mapped_column(Float)
    
    fecha_publicacion: Mapped[Optional[datetime.date]] = mapped_column()
    fecha_cierre: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))
    
    fecha_cierre_segundo_llamado: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    estado_ca_texto: Mapped[Optional[str]] = mapped_column(String(255))
    
    # --- NUEVO CAMPO: Estado Convocatoria ---
    # Almacena el código numérico que indica el tipo de llamado.
    # 1 = Publicada (Primer llamado)
    # 2 = Publicada (Segundo llamado)
    estado_convocatoria: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="1=Normal, 2=Segundo Llamado"
    )
    # ----------------------------------------
    
    proveedores_cotizando: Mapped[Optional[int]] = mapped_column(Integer)
    descripcion: Mapped[Optional[str]] = mapped_column(String)
    direccion_entrega: Mapped[Optional[str]] = mapped_column(String(1000))
    productos_solicitados: Mapped[Optional[list[dict[str, any]]]] = mapped_column(
        JSON, nullable=True, doc="Lista de productos solicitados"
    )
    
    puntuacion_final: Mapped[int] = mapped_column(
        Integer, default=0, index=True, doc="El score final (Fase 1 + Fase 2)"
    )
    
    organismo_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ca_organismo.organismo_id")
    )
    
    organismo: Mapped[Optional["CaOrganismo"]] = relationship(
        back_populates="licitaciones", lazy="joined"
    )
    
    seguimiento: Mapped["CaSeguimiento"] = relationship(
        back_populates="licitacion",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    def __repr__(self):
        return f"<CaLicitacion(codigo_ca='{self.codigo_ca}', score={self.puntuacion_final})>"


class CaSeguimiento(Base):
    __tablename__ = "ca_seguimiento"
    
    ca_id: Mapped[int] = mapped_column(
        ForeignKey("ca_licitacion.ca_id", ondelete="CASCADE"), primary_key=True
    )
    
    es_favorito: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    es_ofertada: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    
    # --- NUEVO CAMPO: Notas de Usuario ---
    # Permite al usuario guardar texto libre asociado a una licitación.
    # Se usa Text para permitir descripciones largas.
    notas: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Notas personalizadas del usuario"
    )
    # -------------------------------------
    
    licitacion: Mapped["CaLicitacion"] = relationship(
        back_populates="seguimiento"
    )

    def __repr__(self):
        return f"<CaSeguimiento(ca_id={self.ca_id}, fav={self.es_favorito}, oft={self.es_ofertada})>"


# --- Tablas de Configuración  ---

class CaKeyword(Base):
    __tablename__ = "ca_keyword"
    
    keyword_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(50), index=True)
    puntos: Mapped[int] = mapped_column(Integer)

    def __repr__(self):
        return f"<CaKeyword(keyword='{self.keyword}', tipo='{self.tipo}', puntos={self.puntos})>"


class TipoReglaOrganismo(enum.Enum):
    """Define los tipos de reglas para un organismo."""
    PRIORITARIO = 'prioritario'
    NO_DESEADO = 'no_deseado'


class CaOrganismoRegla(Base):
    """
    Almacena las reglas de puntuación para un organismo.
    Un organismo puede ser Prioritario (suma puntos) o No Deseado (resta o filtra).
    Si un organismo no está en esta tabla, es 'No Prioritario'.
    """
    __tablename__ = "ca_organismo_regla"
    
    regla_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    organismo_id: Mapped[int] = mapped_column(
        ForeignKey("ca_organismo.organismo_id", ondelete="CASCADE"),
        unique=True, # Un organismo solo puede tener una regla
        index=True
    )
    
    # Define si es 'prioritario' o 'no_deseado'
    tipo: Mapped[TipoReglaOrganismo] = mapped_column(
        Enum(TipoReglaOrganismo, name='tipo_regla_organismo_enum', native_enum=False), 
        nullable=False,
        index=True
    )
    
    # Los puntos solo aplican a 'prioritario'.
    # Será NULL para 'no_deseado'.
    puntos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relación para fácil acceso al nombre del organismo
    organismo: Mapped["CaOrganismo"] = relationship(lazy="joined")

    def __repr__(self):
        return (
            f"<CaOrganismoRegla(org_id={self.organismo_id}, "
            f"tipo='{self.tipo.value}', puntos={self.puntos})>"
        )