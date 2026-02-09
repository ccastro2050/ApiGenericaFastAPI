"""
Paquete de repositorios.
Contiene implementaciones de acceso a datos para diferentes proveedores.
"""

from .repositorio_lectura_sqlserver import RepositorioLecturaSqlServer

__all__ = ["RepositorioLecturaSqlServer"]
