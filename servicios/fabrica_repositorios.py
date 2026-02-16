"""
fabrica_repositorios.py — Fábrica centralizada de repositorios
Ubicación: servicios/fabrica_repositorios.py

Equivalente en .NET: Program.cs líneas 154-194 (switch de proveedores)

Este es el ÚNICO lugar donde se mapea proveedor → implementación concreta.
Para agregar un nuevo proveedor de BD, solo se agregan entradas a los diccionarios.
Los controladores NUNCA saben qué implementación concreta se usa (Open/Closed Principle).
"""

from servicios.conexion.proveedor_conexion import ProveedorConexion
from servicios.servicio_crud import ServicioCrud
from servicios.servicio_consultas import ServicioConsultas
from servicios.politicas.politica_tablas_prohibidas import PoliticaTablasProhibidas
from repositorios import (
    RepositorioLecturaSqlServer,
    RepositorioLecturaPostgreSQL,
    RepositorioLecturaMysqlMariaDB,
    RepositorioConsultasSqlServer,
    RepositorioConsultasPostgreSQL,
    RepositorioConsultasMysqlMariaDB,
)


# ================================================================
# REGISTRO DE IMPLEMENTACIONES (equivalente al switch en Program.cs)
# ================================================================
#
# Equivalente a:
#   switch (proveedorBD.ToLower()) {
#       case "postgres":
#           builder.Services.AddScoped<IRepositorioLecturaTabla, RepositorioLecturaPostgreSQL>();
#           builder.Services.AddScoped<IRepositorioConsultas, RepositorioConsultasPostgreSQL>();
#           break;
#       case "mysql": case "mariadb":
#           builder.Services.AddScoped<IRepositorioLecturaTabla, RepositorioLecturaMysqlMariaDB>();
#           ...
#   }
#
# Para agregar un nuevo proveedor (ej: Oracle, SQLite):
#   1. Crear RepositorioLecturaOracle y RepositorioConsultasOracle
#   2. Agregar UNA línea a cada diccionario aquí
#   3. Agregar cadena de conexión en .env
#   4. NO se modifica ningún controlador

# Diccionario proveedor → clase de repositorio de lectura (CRUD)
_REPOSITORIOS_LECTURA = {
    "sqlserver":        RepositorioLecturaSqlServer,
    "sqlserverexpress": RepositorioLecturaSqlServer,
    "localdb":          RepositorioLecturaSqlServer,
    "postgres":         RepositorioLecturaPostgreSQL,
    "mysql":            RepositorioLecturaMysqlMariaDB,
    "mariadb":          RepositorioLecturaMysqlMariaDB,
}

# Diccionario proveedor → clase de repositorio de consultas (SQL parametrizado, SPs)
_REPOSITORIOS_CONSULTAS = {
    "sqlserver":        RepositorioConsultasSqlServer,
    "sqlserverexpress": RepositorioConsultasSqlServer,
    "localdb":          RepositorioConsultasSqlServer,
    "postgres":         RepositorioConsultasPostgreSQL,
    "mysql":            RepositorioConsultasMysqlMariaDB,
    "mariadb":          RepositorioConsultasMysqlMariaDB,
}


# ================================================================
# FUNCIONES FACTORY (equivalente a la resolución del DI container)
# ================================================================

def crear_repositorio_lectura():
    """
    Crea el repositorio de lectura según DB_PROVIDER.

    Equivalente a: serviceProvider.GetService<IRepositorioLecturaTabla>()
    """
    proveedor = ProveedorConexion()
    clase = _REPOSITORIOS_LECTURA.get(proveedor.proveedor_actual)
    if not clase:
        raise ValueError(
            f"Proveedor '{proveedor.proveedor_actual}' no tiene repositorio de lectura registrado. "
            f"Proveedores disponibles: {list(_REPOSITORIOS_LECTURA.keys())}"
        )
    return clase(proveedor)


def crear_repositorio_consultas():
    """
    Crea el repositorio de consultas según DB_PROVIDER.

    Equivalente a: serviceProvider.GetService<IRepositorioConsultas>()
    """
    proveedor = ProveedorConexion()
    clase = _REPOSITORIOS_CONSULTAS.get(proveedor.proveedor_actual)
    if not clase:
        raise ValueError(
            f"Proveedor '{proveedor.proveedor_actual}' no tiene repositorio de consultas registrado. "
            f"Proveedores disponibles: {list(_REPOSITORIOS_CONSULTAS.keys())}"
        )
    return clase(proveedor)


def crear_servicio_crud() -> ServicioCrud:
    """
    Crea ServicioCrud con sus dependencias resueltas.
    Usado por: entidades_controller, autenticacion_controller.

    Equivalente a: serviceProvider.GetService<IServicioCrud>()
    """
    return ServicioCrud(crear_repositorio_lectura(), PoliticaTablasProhibidas())


def crear_servicio_consultas() -> ServicioConsultas:
    """
    Crea ServicioConsultas con sus dependencias resueltas.
    Usado por: consultas_controller, procedimientos_controller.

    Equivalente a: serviceProvider.GetService<IServicioConsultas>()
    """
    return ServicioConsultas(crear_repositorio_consultas())
