"""
repositorio_consultas_mysql_mariadb.py — Implementación para ejecutar consultas y SP en MySQL/MariaDB
Ubicación: repositorios/repositorio_consultas_mysql_mariadb.py

Equivalente a: ApiGenericaCsharp/Repositorios/RepositorioConsultasMysqlMariaDB.cs

Propósito: Implementar IRepositorioConsultas para MySQL/MariaDB.
Expone consultas parametrizadas, validación de consulta, ejecución
de procedimientos/funciones y obtención de metadatos.
"""

from typing import Any
from datetime import datetime, date
import aiomysql

from servicios.abstracciones.i_proveedor_conexion import IProveedorConexion


class RepositorioConsultasMysqlMariaDB:
    """
    Implementación de IRepositorioConsultas para MySQL/MariaDB.

    Usa aiomysql como driver asíncrono.
    """

    def __init__(self, proveedor_conexion: IProveedorConexion):
        """
        Constructor que recibe el proveedor de conexión.

        Args:
            proveedor_conexion: Proveedor que suministra la cadena de conexión
        """
        if proveedor_conexion is None:
            raise ValueError("proveedor_conexion no puede ser None")
        self._proveedor_conexion = proveedor_conexion

    # ================================================================
    # MÉTODO AUXILIAR: Parsea la cadena de conexión MySQL
    # ================================================================
    def _parsear_cadena_conexion(self, cadena: str) -> dict[str, Any]:
        """
        Parsea una cadena de conexión MySQL al formato requerido por aiomysql.

        Formatos soportados:
        - mysql://user:password@host:port/database
        - Server=host;Port=port;Database=db;User=user;Password=pass;
        """
        config: dict[str, Any] = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "",
            "db": ""
        }

        # Formato URI: mysql://user:password@host:port/database
        if cadena.startswith("mysql://"):
            from urllib.parse import urlparse
            parsed = urlparse(cadena)
            config["host"] = parsed.hostname or "localhost"
            config["port"] = parsed.port or 3306
            config["user"] = parsed.username or "root"
            config["password"] = parsed.password or ""
            config["db"] = parsed.path.lstrip("/") if parsed.path else ""
        else:
            # Formato ADO.NET: Server=host;Port=port;Database=db;User=user;Password=pass;
            partes = cadena.split(";")
            for parte in partes:
                if "=" in parte:
                    clave, valor = parte.split("=", 1)
                    clave = clave.strip().lower()
                    valor = valor.strip()

                    if clave in ("server", "host"):
                        config["host"] = valor
                    elif clave == "port":
                        config["port"] = int(valor)
                    elif clave in ("database", "db"):
                        config["db"] = valor
                    elif clave in ("user", "uid", "username"):
                        config["user"] = valor
                    elif clave in ("password", "pwd"):
                        config["password"] = valor

        return config

    # ================================================================
    # MÉTODO AUXILIAR: Convierte DateTime con hora 00:00:00 a date
    # ================================================================
    def _convertir_valor(self, valor: Any) -> Any:
        """
        Convierte valores especiales para MySQL.
        """
        if valor is None:
            return None

        # DateTime con hora 00:00:00 -> date
        if isinstance(valor, datetime):
            if valor.hour == 0 and valor.minute == 0 and valor.second == 0:
                return valor.date()

        return valor

    # ================================================================
    # MÉTODO: Ejecuta consulta SQL parametrizada
    # ================================================================
    async def ejecutar_consulta_parametrizada_con_dictionary(
        self,
        consulta_sql: str,
        parametros: dict[str, Any] | None,
        maximo_registros: int = 10000,
        esquema: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta una consulta SQL parametrizada con Dictionary.

        Args:
            consulta_sql: Consulta SQL parametrizada
            parametros: Diccionario de parámetros
            maximo_registros: Límite de registros (por defecto 10000)
            esquema: Esquema opcional

        Returns:
            Lista de diccionarios con los resultados
        """
        if not consulta_sql or not consulta_sql.strip():
            raise ValueError("La consulta SQL no puede estar vacía.")

        resultados: list[dict[str, Any]] = []
        config = self._parsear_cadena_conexion(self._proveedor_conexion.obtener_cadena_conexion())

        conexion = await aiomysql.connect(**config)
        try:
            async with conexion.cursor(aiomysql.DictCursor) as cursor:
                # Preparar parámetros - MySQL usa %s o %(name)s
                valores: list[Any] = []
                consulta_final = consulta_sql

                for nombre_param, valor in (parametros or {}).items():
                    # Normalizar nombre del parámetro
                    nombre = nombre_param if nombre_param.startswith("@") else f"@{nombre_param}"

                    # Convertir valor
                    valor_convertido = self._convertir_valor(valor)

                    # Reemplazar @param con %s
                    consulta_final = consulta_final.replace(nombre, "%s")
                    valores.append(valor_convertido)

                await cursor.execute(consulta_final, valores)
                rows = await cursor.fetchall()

                for row in rows[:maximo_registros]:
                    resultados.append(dict(row))

        finally:
            conexion.close()

        return resultados

    # ================================================================
    # MÉTODO: Valida si una consulta SQL es sintácticamente correcta
    # ================================================================
    async def validar_consulta_con_dictionary(
        self,
        consulta_sql: str,
        parametros: dict[str, Any] | None
    ) -> tuple[bool, str | None]:
        """
        Valida si una consulta SQL es sintácticamente correcta sin ejecutarla.

        Usa EXPLAIN para validar consultas SELECT.

        Args:
            consulta_sql: Consulta SQL a validar
            parametros: Diccionario de parámetros

        Returns:
            Tupla (es_valida, mensaje_error)
        """
        if not consulta_sql or not consulta_sql.strip():
            return (False, "La consulta SQL está vacía.")

        try:
            config = self._parsear_cadena_conexion(self._proveedor_conexion.obtener_cadena_conexion())

            conexion = await aiomysql.connect(**config)
            try:
                async with conexion.cursor() as cursor:
                    # Preparar parámetros
                    valores: list[Any] = []
                    consulta_final = consulta_sql

                    for nombre_param, valor in (parametros or {}).items():
                        nombre = nombre_param if nombre_param.startswith("@") else f"@{nombre_param}"
                        consulta_final = consulta_final.replace(nombre, "%s")
                        valores.append(self._convertir_valor(valor))

                    # Usar EXPLAIN para validar SELECT
                    es_select = consulta_sql.strip().upper().startswith("SELECT")
                    if es_select:
                        consulta_validacion = f"EXPLAIN {consulta_final}"
                        await cursor.execute(consulta_validacion, valores)
                        await cursor.fetchall()

                    return (True, None)

            finally:
                conexion.close()

        except Exception as ex:
            return (False, str(ex))

    # ================================================================
    # MÉTODO: Ejecuta procedimiento almacenado
    # ================================================================
    async def ejecutar_procedimiento_almacenado_con_dictionary(
        self,
        nombre_sp: str,
        parametros: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta un procedimiento almacenado con parámetros Dictionary.

        MySQL usa: CALL nombre_sp(@param1, @param2, ...)

        Args:
            nombre_sp: Nombre del procedimiento almacenado
            parametros: Diccionario de parámetros

        Returns:
            Lista de diccionarios con los resultados
        """
        if not nombre_sp or not nombre_sp.strip():
            raise ValueError("El nombre del procedimiento no puede estar vacío.")

        resultados: list[dict[str, Any]] = []
        config = self._parsear_cadena_conexion(self._proveedor_conexion.obtener_cadena_conexion())

        conexion = await aiomysql.connect(**config)
        try:
            async with conexion.cursor(aiomysql.DictCursor) as cursor:
                # Construir placeholders
                valores: list[Any] = []
                placeholders: list[str] = []

                for nombre_param, valor in (parametros or {}).items():
                    placeholders.append("%s")
                    valores.append(self._convertir_valor(valor))

                # MySQL: CALL nombreSP(%s, %s, ...)
                placeholders_str = ", ".join(placeholders) if placeholders else ""
                sql_call = f"CALL {nombre_sp}({placeholders_str})"

                await cursor.execute(sql_call, valores)

                # Obtener resultados
                rows = await cursor.fetchall()
                for row in rows:
                    resultados.append(dict(row))

        finally:
            conexion.close()

        return resultados

    # ================================================================
    # MÉTODOS DE METADATOS
    # ================================================================

    async def obtener_esquema_tabla(
        self,
        nombre_tabla: str,
        esquema_predeterminado: str | None = None
    ) -> str | None:
        """
        Obtiene el esquema real donde existe una tabla.

        En MySQL, el esquema es el nombre de la base de datos.
        """
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío.")

        config = self._parsear_cadena_conexion(self._proveedor_conexion.obtener_cadena_conexion())

        conexion = await aiomysql.connect(**config)
        try:
            async with conexion.cursor() as cursor:
                # Buscar primero en el esquema indicado
                esquema_buscar = esquema_predeterminado if esquema_predeterminado else config.get("db", "")

                if esquema_buscar:
                    sql1 = """
                        SELECT TABLE_SCHEMA
                        FROM INFORMATION_SCHEMA.TABLES
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                        LIMIT 1
                    """
                    await cursor.execute(sql1, (esquema_buscar, nombre_tabla))
                    resultado = await cursor.fetchone()
                    if resultado:
                        return resultado[0]

                # Si no está, buscar en cualquier esquema visible
                sql2 = """
                    SELECT TABLE_SCHEMA
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_NAME = %s
                    ORDER BY TABLE_SCHEMA
                    LIMIT 1
                """
                await cursor.execute(sql2, (nombre_tabla,))
                resultado = await cursor.fetchone()
                return resultado[0] if resultado else None

        finally:
            conexion.close()

    async def obtener_estructura_tabla(
        self,
        nombre_tabla: str,
        esquema: str
    ) -> list[dict[str, Any]]:
        """
        Obtiene la estructura detallada de una tabla incluyendo constraints.

        Incluye: PK, FK, UNIQUE, CHECK (MySQL 8.0.16+), DEFAULT, AUTO_INCREMENT
        """
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío.")

        resultados: list[dict[str, Any]] = []
        config = self._parsear_cadena_conexion(self._proveedor_conexion.obtener_cadena_conexion())

        conexion = await aiomysql.connect(**config)
        try:
            async with conexion.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT
                        c.COLUMN_NAME AS column_name,
                        c.DATA_TYPE AS data_type,
                        c.CHARACTER_MAXIMUM_LENGTH AS character_maximum_length,
                        c.NUMERIC_PRECISION AS numeric_precision,
                        c.NUMERIC_SCALE AS numeric_scale,
                        c.IS_NULLABLE AS is_nullable,
                        c.COLUMN_DEFAULT AS column_default,
                        c.ORDINAL_POSITION AS ordinal_position,
                        CASE WHEN c.COLUMN_KEY = 'PRI' THEN 'YES' ELSE 'NO' END AS is_primary_key,
                        CASE WHEN c.COLUMN_KEY = 'UNI' THEN 'YES' ELSE 'NO' END AS is_unique,
                        CASE WHEN c.EXTRA LIKE '%%auto_increment%%' THEN 'YES' ELSE 'NO' END AS is_identity,
                        fk.REFERENCED_TABLE_NAME AS foreign_table_name,
                        fk.REFERENCED_COLUMN_NAME AS foreign_column_name,
                        fk.CONSTRAINT_NAME AS fk_constraint_name
                    FROM INFORMATION_SCHEMA.COLUMNS c
                    LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE fk
                        ON c.TABLE_SCHEMA = fk.TABLE_SCHEMA
                        AND c.TABLE_NAME = fk.TABLE_NAME
                        AND c.COLUMN_NAME = fk.COLUMN_NAME
                        AND fk.REFERENCED_TABLE_NAME IS NOT NULL
                    WHERE c.TABLE_SCHEMA = %s
                      AND c.TABLE_NAME = %s
                    ORDER BY c.ORDINAL_POSITION
                """

                esquema_usar = esquema if esquema else config.get("db", "")
                await cursor.execute(sql, (esquema_usar, nombre_tabla))
                rows = await cursor.fetchall()

                for row in rows:
                    resultados.append(dict(row))

        finally:
            conexion.close()

        return resultados

    async def obtener_estructura_base_datos(self) -> list[dict[str, Any]]:
        """
        Obtiene la estructura básica de todas las tablas de la base de datos.
        """
        resultados: list[dict[str, Any]] = []
        config = self._parsear_cadena_conexion(self._proveedor_conexion.obtener_cadena_conexion())

        conexion = await aiomysql.connect(**config)
        try:
            async with conexion.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT
                        c.TABLE_NAME AS table_name,
                        c.COLUMN_NAME AS column_name,
                        c.DATA_TYPE AS data_type,
                        c.CHARACTER_MAXIMUM_LENGTH AS character_maximum_length,
                        c.IS_NULLABLE AS is_nullable
                    FROM INFORMATION_SCHEMA.COLUMNS c
                    WHERE c.TABLE_SCHEMA = DATABASE()
                    ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
                """

                await cursor.execute(sql)
                rows = await cursor.fetchall()

                for row in rows:
                    resultados.append(dict(row))

        finally:
            conexion.close()

        return resultados

    async def obtener_estructura_completa_base_datos(self) -> dict[str, Any]:
        """
        Obtiene la estructura completa de la base de datos incluyendo:
        - Tablas con columnas y constraints
        - Vistas
        - Procedimientos almacenados
        - Funciones
        - Triggers
        - Índices
        - Eventos (MySQL scheduler)
        """
        resultado: dict[str, Any] = {}
        config = self._parsear_cadena_conexion(self._proveedor_conexion.obtener_cadena_conexion())

        conexion = await aiomysql.connect(**config)
        try:
            esquema_actual = config.get("db", "")

            # 1. Tablas con columnas y constraints
            resultado["tablas"] = await self._obtener_tablas_con_columnas(conexion, esquema_actual)

            # 2. Vistas
            resultado["vistas"] = await self._obtener_vistas(conexion, esquema_actual)

            # 3. Procedimientos almacenados
            resultado["procedimientos"] = await self._obtener_procedimientos(conexion, esquema_actual)

            # 4. Funciones
            resultado["funciones"] = await self._obtener_funciones(conexion, esquema_actual)

            # 5. Triggers
            resultado["triggers"] = await self._obtener_triggers(conexion, esquema_actual)

            # 6. Índices
            resultado["indices"] = await self._obtener_indices(conexion, esquema_actual)

            # 7. Eventos (MySQL scheduler)
            resultado["eventos"] = await self._obtener_eventos(conexion, esquema_actual)

        finally:
            conexion.close()

        return resultado

    # ================================================================
    # MÉTODOS AUXILIARES PARA ESTRUCTURA COMPLETA DE BD
    # ================================================================

    async def _obtener_tablas_con_columnas(
        self,
        conexion,
        esquema: str
    ) -> list[dict[str, Any]]:
        """Obtiene todas las tablas con sus columnas, FK e índices."""
        tablas: list[dict[str, Any]] = []

        async with conexion.cursor(aiomysql.DictCursor) as cursor:
            sql_tablas = """
                SELECT
                    TABLE_SCHEMA,
                    TABLE_NAME,
                    TABLE_COMMENT,
                    ENGINE,
                    TABLE_ROWS,
                    AUTO_INCREMENT,
                    TABLE_COLLATION
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """

            await cursor.execute(sql_tablas, (esquema,))
            rows_tablas = await cursor.fetchall()

            for row in rows_tablas:
                tabla_dict: dict[str, Any] = {
                    "schema": row['TABLE_SCHEMA'],
                    "nombre": row['TABLE_NAME'],
                    "comentario": row['TABLE_COMMENT'],
                    "engine": row['ENGINE'],
                    "filas_estimadas": row['TABLE_ROWS'],
                    "auto_increment": row['AUTO_INCREMENT'],
                    "collation": row['TABLE_COLLATION'],
                    "columnas": await self._obtener_columnas_tabla(conexion, row['TABLE_SCHEMA'], row['TABLE_NAME']),
                    "foreign_keys": await self._obtener_foreign_keys_tabla(conexion, row['TABLE_SCHEMA'], row['TABLE_NAME']),
                    "indices": await self._obtener_indices_tabla(conexion, row['TABLE_SCHEMA'], row['TABLE_NAME'])
                }
                tablas.append(tabla_dict)

        return tablas

    async def _obtener_columnas_tabla(
        self,
        conexion,
        schema: str,
        tabla: str
    ) -> list[dict[str, Any]]:
        """Obtiene las columnas de una tabla específica."""
        columnas: list[dict[str, Any]] = []

        async with conexion.cursor(aiomysql.DictCursor) as cursor:
            sql = """
                SELECT
                    c.COLUMN_NAME,
                    c.DATA_TYPE,
                    c.COLUMN_TYPE,
                    c.CHARACTER_MAXIMUM_LENGTH,
                    c.NUMERIC_PRECISION,
                    c.NUMERIC_SCALE,
                    c.IS_NULLABLE,
                    c.COLUMN_DEFAULT,
                    c.ORDINAL_POSITION,
                    c.COLUMN_KEY,
                    c.EXTRA,
                    c.COLUMN_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS c
                WHERE c.TABLE_SCHEMA = %s AND c.TABLE_NAME = %s
                ORDER BY c.ORDINAL_POSITION
            """

            await cursor.execute(sql, (schema, tabla))
            rows = await cursor.fetchall()

            for row in rows:
                column_key = row['COLUMN_KEY'] or ""
                extra = row['EXTRA'] or ""

                columnas.append({
                    "nombre": row['COLUMN_NAME'],
                    "tipo": row['DATA_TYPE'],
                    "tipo_completo": row['COLUMN_TYPE'],
                    "longitud_maxima": row['CHARACTER_MAXIMUM_LENGTH'],
                    "precision": row['NUMERIC_PRECISION'],
                    "escala": row['NUMERIC_SCALE'],
                    "nullable": row['IS_NULLABLE'] == "YES",
                    "valor_default": row['COLUMN_DEFAULT'],
                    "posicion": row['ORDINAL_POSITION'],
                    "es_primary_key": column_key == "PRI",
                    "es_unique": column_key == "UNI",
                    "es_auto_increment": "auto_increment" in extra.lower(),
                    "comentario": row['COLUMN_COMMENT']
                })

        return columnas

    async def _obtener_foreign_keys_tabla(
        self,
        conexion,
        schema: str,
        tabla: str
    ) -> list[dict[str, Any]]:
        """Obtiene las foreign keys de una tabla."""
        fks: list[dict[str, Any]] = []

        async with conexion.cursor(aiomysql.DictCursor) as cursor:
            sql = """
                SELECT
                    kcu.CONSTRAINT_NAME,
                    kcu.COLUMN_NAME,
                    kcu.REFERENCED_TABLE_SCHEMA,
                    kcu.REFERENCED_TABLE_NAME,
                    kcu.REFERENCED_COLUMN_NAME,
                    rc.UPDATE_RULE,
                    rc.DELETE_RULE
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                    ON kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
                    AND kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                WHERE kcu.TABLE_SCHEMA = %s
                  AND kcu.TABLE_NAME = %s
                  AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
                ORDER BY kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION
            """

            await cursor.execute(sql, (schema, tabla))
            rows = await cursor.fetchall()

            for row in rows:
                fks.append({
                    "constraint_name": row['CONSTRAINT_NAME'],
                    "column_name": row['COLUMN_NAME'],
                    "foreign_schema": row['REFERENCED_TABLE_SCHEMA'],
                    "foreign_table_name": row['REFERENCED_TABLE_NAME'],
                    "foreign_column_name": row['REFERENCED_COLUMN_NAME'],
                    "on_update": row['UPDATE_RULE'],
                    "on_delete": row['DELETE_RULE']
                })

        return fks

    async def _obtener_indices_tabla(
        self,
        conexion,
        schema: str,
        tabla: str
    ) -> list[dict[str, Any]]:
        """Obtiene los índices de una tabla."""
        indices: list[dict[str, Any]] = []

        async with conexion.cursor(aiomysql.DictCursor) as cursor:
            sql = """
                SELECT
                    INDEX_NAME,
                    INDEX_TYPE,
                    NON_UNIQUE,
                    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ', ') AS columns,
                    NULLABLE
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                GROUP BY INDEX_NAME, INDEX_TYPE, NON_UNIQUE, NULLABLE
                ORDER BY INDEX_NAME
            """

            await cursor.execute(sql, (schema, tabla))
            rows = await cursor.fetchall()

            for row in rows:
                indices.append({
                    "nombre": row['INDEX_NAME'],
                    "tipo": row['INDEX_TYPE'],
                    "es_unique": row['NON_UNIQUE'] == 0,
                    "columnas": row['columns'],
                    "nullable": row['NULLABLE']
                })

        return indices

    async def _obtener_vistas(
        self,
        conexion,
        esquema: str
    ) -> list[dict[str, Any]]:
        """Obtiene todas las vistas de la base de datos."""
        vistas: list[dict[str, Any]] = []

        async with conexion.cursor(aiomysql.DictCursor) as cursor:
            sql = """
                SELECT
                    TABLE_SCHEMA,
                    TABLE_NAME,
                    VIEW_DEFINITION,
                    CHECK_OPTION,
                    IS_UPDATABLE,
                    SECURITY_TYPE
                FROM INFORMATION_SCHEMA.VIEWS
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME
            """

            await cursor.execute(sql, (esquema,))
            rows = await cursor.fetchall()

            for row in rows:
                vistas.append({
                    "schema": row['TABLE_SCHEMA'],
                    "nombre": row['TABLE_NAME'],
                    "definicion": row['VIEW_DEFINITION'],
                    "check_option": row['CHECK_OPTION'],
                    "es_actualizable": row['IS_UPDATABLE'] == "YES",
                    "tipo_seguridad": row['SECURITY_TYPE']
                })

        return vistas

    async def _obtener_procedimientos(
        self,
        conexion,
        esquema: str
    ) -> list[dict[str, Any]]:
        """Obtiene todos los procedimientos almacenados."""
        procedimientos: list[dict[str, Any]] = []

        async with conexion.cursor(aiomysql.DictCursor) as cursor:
            sql = """
                SELECT
                    ROUTINE_SCHEMA,
                    ROUTINE_NAME,
                    ROUTINE_DEFINITION,
                    DATA_TYPE,
                    CREATED,
                    LAST_ALTERED,
                    ROUTINE_COMMENT,
                    SECURITY_TYPE,
                    SQL_MODE,
                    DEFINER
                FROM INFORMATION_SCHEMA.ROUTINES
                WHERE ROUTINE_SCHEMA = %s
                  AND ROUTINE_TYPE = 'PROCEDURE'
                ORDER BY ROUTINE_NAME
            """

            await cursor.execute(sql, (esquema,))
            rows = await cursor.fetchall()

            for row in rows:
                proc_dict: dict[str, Any] = {
                    "schema": row['ROUTINE_SCHEMA'],
                    "nombre": row['ROUTINE_NAME'],
                    "definicion": row['ROUTINE_DEFINITION'],
                    "tipo_retorno": row['DATA_TYPE'],
                    "fecha_creacion": row['CREATED'],
                    "fecha_modificacion": row['LAST_ALTERED'],
                    "comentario": row['ROUTINE_COMMENT'],
                    "tipo_seguridad": row['SECURITY_TYPE'],
                    "sql_mode": row['SQL_MODE'],
                    "definer": row['DEFINER'],
                    "parametros": await self._obtener_parametros_rutina(conexion, row['ROUTINE_SCHEMA'], row['ROUTINE_NAME'])
                }
                procedimientos.append(proc_dict)

        return procedimientos

    async def _obtener_funciones(
        self,
        conexion,
        esquema: str
    ) -> list[dict[str, Any]]:
        """Obtiene todas las funciones de la base de datos."""
        funciones: list[dict[str, Any]] = []

        async with conexion.cursor(aiomysql.DictCursor) as cursor:
            sql = """
                SELECT
                    ROUTINE_SCHEMA,
                    ROUTINE_NAME,
                    ROUTINE_DEFINITION,
                    DATA_TYPE,
                    CREATED,
                    LAST_ALTERED,
                    ROUTINE_COMMENT,
                    SECURITY_TYPE,
                    IS_DETERMINISTIC,
                    DEFINER
                FROM INFORMATION_SCHEMA.ROUTINES
                WHERE ROUTINE_SCHEMA = %s
                  AND ROUTINE_TYPE = 'FUNCTION'
                ORDER BY ROUTINE_NAME
            """

            await cursor.execute(sql, (esquema,))
            rows = await cursor.fetchall()

            for row in rows:
                func_dict: dict[str, Any] = {
                    "schema": row['ROUTINE_SCHEMA'],
                    "nombre": row['ROUTINE_NAME'],
                    "definicion": row['ROUTINE_DEFINITION'],
                    "tipo_retorno": row['DATA_TYPE'],
                    "fecha_creacion": row['CREATED'],
                    "fecha_modificacion": row['LAST_ALTERED'],
                    "comentario": row['ROUTINE_COMMENT'],
                    "tipo_seguridad": row['SECURITY_TYPE'],
                    "es_deterministica": row['IS_DETERMINISTIC'] == "YES",
                    "definer": row['DEFINER'],
                    "parametros": await self._obtener_parametros_rutina(conexion, row['ROUTINE_SCHEMA'], row['ROUTINE_NAME'])
                }
                funciones.append(func_dict)

        return funciones

    async def _obtener_parametros_rutina(
        self,
        conexion,
        schema: str,
        rutina: str
    ) -> list[dict[str, Any]]:
        """Obtiene los parámetros de un procedimiento o función."""
        parametros: list[dict[str, Any]] = []

        async with conexion.cursor(aiomysql.DictCursor) as cursor:
            sql = """
                SELECT
                    PARAMETER_NAME,
                    DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE,
                    PARAMETER_MODE,
                    ORDINAL_POSITION
                FROM INFORMATION_SCHEMA.PARAMETERS
                WHERE SPECIFIC_SCHEMA = %s
                  AND SPECIFIC_NAME = %s
                  AND PARAMETER_NAME IS NOT NULL
                ORDER BY ORDINAL_POSITION
            """

            await cursor.execute(sql, (schema, rutina))
            rows = await cursor.fetchall()

            for row in rows:
                parametros.append({
                    "nombre": row['PARAMETER_NAME'],
                    "tipo": row['DATA_TYPE'],
                    "longitud_maxima": row['CHARACTER_MAXIMUM_LENGTH'],
                    "precision": row['NUMERIC_PRECISION'],
                    "escala": row['NUMERIC_SCALE'],
                    "direccion": row['PARAMETER_MODE'],
                    "posicion": row['ORDINAL_POSITION']
                })

        return parametros

    async def _obtener_triggers(
        self,
        conexion,
        esquema: str
    ) -> list[dict[str, Any]]:
        """Obtiene todos los triggers de la base de datos."""
        triggers: list[dict[str, Any]] = []

        async with conexion.cursor(aiomysql.DictCursor) as cursor:
            sql = """
                SELECT
                    TRIGGER_SCHEMA,
                    TRIGGER_NAME,
                    EVENT_MANIPULATION,
                    EVENT_OBJECT_SCHEMA,
                    EVENT_OBJECT_TABLE,
                    ACTION_TIMING,
                    ACTION_STATEMENT,
                    CREATED,
                    DEFINER
                FROM INFORMATION_SCHEMA.TRIGGERS
                WHERE TRIGGER_SCHEMA = %s
                ORDER BY EVENT_OBJECT_TABLE, TRIGGER_NAME
            """

            await cursor.execute(sql, (esquema,))
            rows = await cursor.fetchall()

            for row in rows:
                triggers.append({
                    "schema": row['TRIGGER_SCHEMA'],
                    "nombre": row['TRIGGER_NAME'],
                    "evento": row['EVENT_MANIPULATION'],
                    "schema_tabla": row['EVENT_OBJECT_SCHEMA'],
                    "tabla": row['EVENT_OBJECT_TABLE'],
                    "timing": row['ACTION_TIMING'],
                    "cuerpo": row['ACTION_STATEMENT'],
                    "fecha_creacion": row['CREATED'],
                    "definer": row['DEFINER']
                })

        return triggers

    async def _obtener_indices(
        self,
        conexion,
        esquema: str
    ) -> list[dict[str, Any]]:
        """Obtiene todos los índices de la base de datos."""
        indices: list[dict[str, Any]] = []

        async with conexion.cursor(aiomysql.DictCursor) as cursor:
            sql = """
                SELECT
                    TABLE_SCHEMA,
                    TABLE_NAME,
                    INDEX_NAME,
                    INDEX_TYPE,
                    NON_UNIQUE,
                    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ', ') AS columns,
                    NULLABLE
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s
                GROUP BY TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, INDEX_TYPE, NON_UNIQUE, NULLABLE
                ORDER BY TABLE_NAME, INDEX_NAME
            """

            await cursor.execute(sql, (esquema,))
            rows = await cursor.fetchall()

            for row in rows:
                indices.append({
                    "schema": row['TABLE_SCHEMA'],
                    "tabla": row['TABLE_NAME'],
                    "nombre": row['INDEX_NAME'],
                    "tipo": row['INDEX_TYPE'],
                    "es_unique": row['NON_UNIQUE'] == 0,
                    "columnas": row['columns'],
                    "nullable": row['NULLABLE']
                })

        return indices

    async def _obtener_eventos(
        self,
        conexion,
        esquema: str
    ) -> list[dict[str, Any]]:
        """Obtiene todos los eventos (MySQL scheduler) de la base de datos."""
        eventos: list[dict[str, Any]] = []

        async with conexion.cursor(aiomysql.DictCursor) as cursor:
            sql = """
                SELECT
                    EVENT_SCHEMA,
                    EVENT_NAME,
                    EVENT_DEFINITION,
                    EVENT_TYPE,
                    EXECUTE_AT,
                    INTERVAL_VALUE,
                    INTERVAL_FIELD,
                    STARTS,
                    ENDS,
                    STATUS,
                    ON_COMPLETION,
                    CREATED,
                    LAST_ALTERED,
                    EVENT_COMMENT,
                    DEFINER
                FROM INFORMATION_SCHEMA.EVENTS
                WHERE EVENT_SCHEMA = %s
                ORDER BY EVENT_NAME
            """

            await cursor.execute(sql, (esquema,))
            rows = await cursor.fetchall()

            for row in rows:
                eventos.append({
                    "schema": row['EVENT_SCHEMA'],
                    "nombre": row['EVENT_NAME'],
                    "definicion": row['EVENT_DEFINITION'],
                    "tipo": row['EVENT_TYPE'],
                    "ejecutar_en": row['EXECUTE_AT'],
                    "intervalo_valor": row['INTERVAL_VALUE'],
                    "intervalo_campo": row['INTERVAL_FIELD'],
                    "inicio": row['STARTS'],
                    "fin": row['ENDS'],
                    "estado": row['STATUS'],
                    "al_completar": row['ON_COMPLETION'],
                    "fecha_creacion": row['CREATED'],
                    "fecha_modificacion": row['LAST_ALTERED'],
                    "comentario": row['EVENT_COMMENT'],
                    "definer": row['DEFINER']
                })

        return eventos
