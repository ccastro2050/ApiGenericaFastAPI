"""
i_proveedor_conexion.py — Protocol que define el contrato para obtener conexiones a base de datos
Ubicación: servicios/abstracciones/i_proveedor_conexion.py

Principios SOLID aplicados:
- SRP: Este Protocol solo se encarga de definir operaciones relacionadas con conexiones
- DIP: Permite que otras clases dependan de esta abstracción, no de implementaciones concretas
- ISP: Protocol específico y pequeño, solo métodos relacionados con conexiones
- OCP: Abierto para extensión (nuevas implementaciones) pero cerrado para modificación

Equivalente en .NET: IProveedorConexion.cs
"""

from typing import Protocol


class IProveedorConexion(Protocol):
    """
    Contrato que define cómo obtener información de conexión a base de datos.

    Este Protocol es el "qué" (contrato), no el "cómo" (implementación).
    Permite que cualquier clase que necesite conexiones dependa de esta abstracción
    en lugar de depender de una clase concreta específica.

    Beneficios:
    - Facilita testing (se pueden crear mocks de este Protocol)
    - Permite intercambiar implementaciones sin cambiar código cliente
    - Desacopla la lógica de obtener conexiones de quienes las usan

    Equivalente en .NET: interface IProveedorConexion
    """

    @property
    def proveedor_actual(self) -> str:
        """
        Obtiene el nombre del proveedor de base de datos actualmente configurado.

        Valores esperados:
        - "sqlserver" para Microsoft SQL Server
        - "postgres" para PostgreSQL
        - "mariadb" para MariaDB
        - "mysql" para MySQL

        Returns:
            Nombre del proveedor en minúsculas

        Equivalente en .NET: string ProveedorActual { get; }
        """
        ...

    def obtener_cadena_conexion(self) -> str:
        """
        Obtiene la cadena de conexión correspondiente al proveedor configurado.

        Returns:
            Cadena de conexión lista para usar con el driver correspondiente

        Raises:
            ValueError: Cuando no existe configuración para el proveedor actual

        Equivalente en .NET: string ObtenerCadenaConexion()
        """
        ...


# =============================================================================
# NOTAS PEDAGÓGICAS
# =============================================================================
#
# 1. ¿QUÉ ES UNA PROPERTY EN UN PROTOCOL?
#    - @property define un atributo de solo lectura
#    - Es equivalente a { get; } en C#
#    - La implementación puede ser un atributo o un método
#
# 2. COMPARACIÓN CON C#:
#
#    C#:
#    public interface IProveedorConexion
#    {
#        string ProveedorActual { get; }
#        string ObtenerCadenaConexion();
#    }
#
#    Python:
#    class IProveedorConexion(Protocol):
#        @property
#        def proveedor_actual(self) -> str: ...
#        def obtener_cadena_conexion(self) -> str: ...
#
# 3. ¿POR QUÉ NO ES ASYNC?
#    - Obtener la cadena de conexión es una operación de configuración
#    - No requiere I/O de base de datos
#    - La conexión real (que sí es async) se hace en el repositorio
#
# 4. EJEMPLO DE IMPLEMENTACIÓN FUTURA:
#
#    class ProveedorConexion:
#        def __init__(self, settings: Settings):
#            self._settings = settings
#
#        @property
#        def proveedor_actual(self) -> str:
#            return self._settings.database.provider
#
#        def obtener_cadena_conexion(self) -> str:
#            provider = self.proveedor_actual
#            if provider == "postgres":
#                return self._settings.database.postgres
#            elif provider == "sqlserver":
#                return self._settings.database.sqlserver
#            # ...
