"""
Paquete de repositorios.
Contiene implementaciones de acceso a datos para diferentes proveedores.
"""

from .repositorio_lectura_sqlserver import RepositorioLecturaSqlServer
from .repositorio_lectura_postgresql import RepositorioLecturaPostgreSQL

__all__ = ["RepositorioLecturaSqlServer", "RepositorioLecturaPostgreSQL"]
