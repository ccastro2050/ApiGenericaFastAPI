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
# FUNCIONES FACTORY CON SINGLETON
# (equivalente a builder.Services.AddSingleton<> en C#)
#
# Antes se creaba un repositorio + engine NUEVO por cada request,
# lo que costaba ~30ms. Ahora se reutiliza la misma instancia.
# ================================================================

_repo_lectura_singleton = None
_repo_consultas_singleton = None
_servicio_crud_singleton = None
_servicio_consultas_singleton = None


def crear_repositorio_lectura():
    """
    Obtiene el repositorio singleton de lectura según DB_PROVIDER.

    Equivalente a: serviceProvider.GetService<IRepositorioLecturaTabla>()
    """
    global _repo_lectura_singleton
    if _repo_lectura_singleton is None:
        proveedor = ProveedorConexion()
        clase = _REPOSITORIOS_LECTURA.get(proveedor.proveedor_actual)
        if not clase:
            raise ValueError(
                f"Proveedor '{proveedor.proveedor_actual}' no tiene repositorio de lectura registrado. "
                f"Proveedores disponibles: {list(_REPOSITORIOS_LECTURA.keys())}"
            )
        _repo_lectura_singleton = clase(proveedor)
    return _repo_lectura_singleton


def crear_repositorio_consultas():
    """
    Obtiene el repositorio singleton de consultas según DB_PROVIDER.

    Equivalente a: serviceProvider.GetService<IRepositorioConsultas>()
    """
    global _repo_consultas_singleton
    if _repo_consultas_singleton is None:
        proveedor = ProveedorConexion()
        clase = _REPOSITORIOS_CONSULTAS.get(proveedor.proveedor_actual)
        if not clase:
            raise ValueError(
                f"Proveedor '{proveedor.proveedor_actual}' no tiene repositorio de consultas registrado. "
                f"Proveedores disponibles: {list(_REPOSITORIOS_CONSULTAS.keys())}"
            )
        _repo_consultas_singleton = clase(proveedor)
    return _repo_consultas_singleton


def crear_servicio_crud() -> ServicioCrud:
    """
    Obtiene el ServicioCrud singleton con sus dependencias resueltas.
    Usado por: entidades_controller, autenticacion_controller.

    Equivalente a: serviceProvider.GetService<IServicioCrud>()
    """
    global _servicio_crud_singleton
    if _servicio_crud_singleton is None:
        _servicio_crud_singleton = ServicioCrud(
            crear_repositorio_lectura(), PoliticaTablasProhibidas()
        )
    return _servicio_crud_singleton


def crear_servicio_consultas() -> ServicioConsultas:
    """
    Obtiene el ServicioConsultas singleton con sus dependencias resueltas.
    Usado por: consultas_controller, procedimientos_controller.

    Equivalente a: serviceProvider.GetService<IServicioConsultas>()
    """
    global _servicio_consultas_singleton
    if _servicio_consultas_singleton is None:
        _servicio_consultas_singleton = ServicioConsultas(crear_repositorio_consultas())
    return _servicio_consultas_singleton
