"""
Paquete de repositorios.
Contiene implementaciones de acceso a datos para diferentes proveedores.
"""

from .repositorio_lectura_sqlserver import RepositorioLecturaSqlServer
from .repositorio_lectura_postgresql import RepositorioLecturaPostgreSQL
from .repositorio_lectura_mysql_mariadb import RepositorioLecturaMysqlMariaDB
from .repositorio_consultas_sqlserver import RepositorioConsultasSqlServer
from .repositorio_consultas_postgresql import RepositorioConsultasPostgreSQL
from .repositorio_consultas_mysql_mariadb import RepositorioConsultasMysqlMariaDB

__all__ = [
    "RepositorioLecturaSqlServer",
    "RepositorioLecturaPostgreSQL",
    "RepositorioLecturaMysqlMariaDB",
    "RepositorioConsultasSqlServer",
    "RepositorioConsultasPostgreSQL",
    "RepositorioConsultasMysqlMariaDB"
]
