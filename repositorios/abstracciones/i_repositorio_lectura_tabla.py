"""
i_repositorio_lectura_tabla.py — Protocol que define el contrato para lectura genérica de tablas
Ubicación: repositorios/abstracciones/i_repositorio_lectura_tabla.py

Principios SOLID aplicados:
- SRP: Este Protocol solo define operaciones de LECTURA/CRUD, no mezcla responsabilidades
- DIP: Permite que los servicios dependan de esta abstracción, no de implementaciones concretas
- OCP: Abierto para extensión (nuevas implementaciones) pero cerrado para modificación
- ISP: Protocol específico y enfocado, solo contiene métodos de acceso a datos

Equivalente en .NET: IRepositorioLecturaTabla.cs
"""

from typing import Protocol, Optional
from collections.abc import Mapping, Sequence


class IRepositorioLecturaTabla(Protocol):
    """
    Contrato para repositorios que realizan operaciones sobre tablas de base de datos.

    Este Protocol define el "QUÉ" se puede hacer, no el "CÓMO" se hace.
    Cada implementación concreta definirá cómo conectar y ejecutar las consultas
    (asyncpg para Postgres, aioodbc para SQL Server, aiomysql para MySQL, etc.).

    Beneficios de esta abstracción:
    - Permite intercambiar proveedores de base de datos sin cambiar código cliente
    - Facilita testing mediante mocks
    - Desacopla la lógica de negocio del acceso a datos específico
    - Soporta múltiples implementaciones simultáneas

    Equivalente en .NET: interface IRepositorioLecturaTabla
    """

    async def obtener_filas(
        self,
        nombre_tabla: str,
        esquema: Optional[str] = None,
        limite: Optional[int] = None
    ) -> list[dict[str, object]]:
        """
        Obtiene filas de una tabla específica como lista de diccionarios.

        Cada fila se representa como dict[str, object] donde:
        - La clave (str) es el nombre de la columna
        - El valor (object) es el dato de esa columna (puede ser None)

        Esta estructura genérica permite trabajar con CUALQUIER tabla sin necesidad
        de crear modelos/entidades específicas para cada una.

        Args:
            nombre_tabla: Nombre de la tabla a consultar. Obligatorio.
                         Ejemplo: "usuarios", "productos", "pedidos"
            esquema: Esquema/schema de la tabla. Opcional.
                    - SQL Server: "dbo" (por defecto)
                    - PostgreSQL: "public" (por defecto)
                    - MySQL: None (no usa esquemas)
            limite: Máximo número de filas a devolver. Opcional.
                   Si es None, aplicar límite por defecto o sin límite.

        Returns:
            Lista de filas donde cada fila es un diccionario:
            - Clave: nombre de columna (str)
            - Valor: dato de la columna (object, puede ser None)

            Ejemplo:
            [
                {"id": 1, "nombre": "Juan", "email": "juan@test.com", "activo": True},
                {"id": 2, "nombre": "María", "email": "maria@test.com", "activo": False}
            ]

        Raises:
            ValueError: Cuando nombre_tabla es vacío o contiene caracteres inválidos
            RuntimeError: Cuando la tabla no existe o no se puede acceder

        Equivalente en .NET: Task<IReadOnlyList<Dictionary<string, object?>>> ObtenerFilasAsync()
        """
        ...

    async def obtener_por_clave(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor: str,
        esquema: Optional[str] = None
    ) -> list[dict[str, object]]:
        """
        Obtiene filas filtradas por un valor específico en una columna.

        Args:
            nombre_tabla: Nombre de la tabla a consultar
            nombre_clave: Nombre de la columna para filtrar
            valor: Valor a buscar en la columna
            esquema: Esquema de la tabla (opcional)

        Returns:
            Lista de filas que coinciden con el criterio

        Equivalente en .NET: Task<IReadOnlyList<Dictionary<string, object?>>> ObtenerPorClaveAsync()
        """
        ...

    async def crear(
        self,
        nombre_tabla: str,
        datos: dict[str, object],
        esquema: Optional[str] = None,
        campos_encriptar: Optional[str] = None
    ) -> bool:
        """
        Crea un nuevo registro en la tabla especificada.

        Args:
            nombre_tabla: Nombre de la tabla donde insertar
            datos: Datos a insertar como diccionario columna-valor
            esquema: Esquema de la tabla (opcional)
            campos_encriptar: Lista de campos que deben ser encriptados,
                             separados por coma (opcional)

        Returns:
            True si se insertó correctamente

        Equivalente en .NET: Task<bool> CrearAsync()
        """
        ...

    async def actualizar(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor_clave: str,
        datos: dict[str, object],
        esquema: Optional[str] = None,
        campos_encriptar: Optional[str] = None
    ) -> int:
        """
        Actualiza un registro existente en la tabla especificada.

        Args:
            nombre_tabla: Nombre de la tabla donde actualizar
            nombre_clave: Columna que identifica el registro a actualizar
            valor_clave: Valor de la clave para identificar el registro
            datos: Nuevos datos a actualizar
            esquema: Esquema de la tabla (opcional)
            campos_encriptar: Campos que deben ser encriptados (opcional)

        Returns:
            Número de filas afectadas (0 si no se encontró el registro)

        Equivalente en .NET: Task<int> ActualizarAsync()
        """
        ...

    async def eliminar(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor_clave: str,
        esquema: Optional[str] = None
    ) -> int:
        """
        Elimina un registro existente de la tabla especificada.

        Args:
            nombre_tabla: Nombre de la tabla donde eliminar
            nombre_clave: Columna que identifica el registro a eliminar
            valor_clave: Valor de la clave para identificar el registro
            esquema: Esquema de la tabla (opcional)

        Returns:
            Número de filas eliminadas (0 si no se encontró el registro)

        Equivalente en .NET: Task<int> EliminarAsync()
        """
        ...

    async def obtener_hash_contrasena(
        self,
        nombre_tabla: str,
        campo_usuario: str,
        campo_contrasena: str,
        valor_usuario: str,
        esquema: Optional[str] = None
    ) -> Optional[str]:
        """
        Verifica credenciales de usuario obteniendo el hash almacenado para comparación.

        Args:
            nombre_tabla: Nombre de la tabla que contiene usuarios
            campo_usuario: Columna que identifica al usuario (ej: email, username)
            campo_contrasena: Columna que contiene el hash de la contraseña
            valor_usuario: Valor del usuario a buscar
            esquema: Esquema de la tabla (opcional)

        Returns:
            Hash de contraseña almacenado o None si no se encuentra el usuario

        Equivalente en .NET: Task<string?> ObtenerHashContrasenaAsync()
        """
        ...

    async def obtener_diagnostico_conexion(self) -> dict[str, object]:
        """
        Obtiene información de diagnóstico sobre la conexión actual a la base de datos.

        Este método consulta metadatos del sistema del motor de base de datos específico
        para obtener información útil para troubleshooting y diagnóstico:
        - Nombre de la base de datos conectada
        - Versión del motor de base de datos
        - Host/servidor conectado
        - Puerto de conexión
        - Hora de inicio del servidor
        - Usuario de la conexión actual

        IMPLEMENTACIÓN POR MOTOR:
        - PostgreSQL: consulta current_database(), version(), etc.
        - SQL Server: consulta DB_NAME(), @@VERSION, etc.
        - MySQL/MariaDB: consulta DATABASE(), VERSION(), etc.

        NOTA DE SEGURIDAD:
        Este método NO debe devolver credenciales ni la cadena de conexión completa.
        Solo metadatos públicos del servidor para propósitos de diagnóstico.

        Returns:
            Diccionario con información de diagnóstico. Claves comunes:
            - "proveedor": nombre del motor (ej: "PostgreSQL", "SQL Server")
            - "base_datos": nombre de la base de datos actual
            - "version": versión completa del motor
            - "servidor": nombre/host del servidor
            - "puerto": puerto de conexión (si está disponible)

        Equivalente en .NET: Task<Dictionary<string, object?>> ObtenerDiagnosticoConexionAsync()
        """
        ...


# =============================================================================
# NOTAS PEDAGÓGICAS
# =============================================================================
#
# 1. ¿QUÉ ES UN PROTOCOL?
#    - Es la forma de Python de definir "interfaces" (contratos)
#    - Las clases que implementan el Protocol NO necesitan heredar de él
#    - Python usa "duck typing": si tiene los métodos, cumple el contrato
#
# 2. ¿POR QUÉ "..." EN LOS MÉTODOS?
#    - Los tres puntos (...) indican que el método no tiene implementación
#    - Es equivalente a "pass" pero más idiomático para Protocols
#    - En C# sería simplemente la firma del método sin cuerpo
#
# 3. ¿POR QUÉ USAR dict[str, object]?
#    - Flexibilidad: funciona con cualquier tabla sin crear modelos específicos
#    - Genérico: no necesitas saber las columnas de antemano
#    - Dinámico: las columnas se descubren en tiempo de ejecución
#    - Equivalente a Dictionary<string, object?> en C#
#
# 4. ¿POR QUÉ MÉTODOS ASYNC?
#    - Las operaciones de base de datos son I/O bound
#    - async/await permite no bloquear mientras espera respuesta de BD
#    - Es equivalente a Task<> en C#
#
# 5. COMPARACIÓN CON C#:
#    
#    C#:
#    public interface IRepositorioLecturaTabla
#    {
#        Task<IReadOnlyList<Dictionary<string, object?>>> ObtenerFilasAsync(...);
#    }
#    
#    Python:
#    class IRepositorioLecturaTabla(Protocol):
#        async def obtener_filas(...) -> list[dict[str, object]]:
#            ...
#
# 6. EJEMPLO DE IMPLEMENTACIÓN FUTURA:
#
#    class RepositorioLecturaPostgres:
#        def __init__(self, proveedor_conexion: IProveedorConexion):
#            self._proveedor = proveedor_conexion
#
#        async def obtener_filas(
#            self,
#            nombre_tabla: str,
#            esquema: Optional[str] = None,
#            limite: Optional[int] = None
#        ) -> list[dict[str, object]]:
#            conexion = await self._proveedor.obtener_conexion()
#            # ... lógica específica de PostgreSQL
#
# 7. PRÓXIMO PASO EN main.py:
#    Después de crear las implementaciones, se configurará la inyección:
#
#    def get_repositorio() -> IRepositorioLecturaTabla:
#        if settings.database.provider == "postgres":
#            return RepositorioLecturaPostgres(...)
#        elif settings.database.provider == "sqlserver":
#            return RepositorioLecturaSqlServer(...)
