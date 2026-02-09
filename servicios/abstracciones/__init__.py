"""Paquete de abstracciones (Protocols) para servicios."""

from .i_proveedor_conexion import IProveedorConexion
from .i_politica_tablas_prohibidas import IPoliticaTablasProhibidas
from .i_servicio_crud import IServicioCrud

__all__ = ["IProveedorConexion", "IPoliticaTablasProhibidas", "IServicioCrud"]
