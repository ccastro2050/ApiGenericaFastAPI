"""Abstracciones de servicios."""
from .i_politica_tablas_prohibidas import IPoliticaTablasProhibidas
from .i_proveedor_conexion import IProveedorConexion
from .i_servicio_crud import IServicioCrud
from .i_servicio_consultas import IServicioConsultas

__all__ = [
    "IPoliticaTablasProhibidas",
    "IProveedorConexion", 
    "IServicioCrud",
    "IServicioConsultas"
]
