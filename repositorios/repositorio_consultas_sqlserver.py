"""
repositorio_consultas_sqlserver.py — Implementación para ejecutar consultas y SP en SQL Server
Ubicación: repositorios/repositorio_consultas_sqlserver.py

Equivalente a: ApiGenericaCsharp/Repositorios/RepositorioConsultasSqlServer.cs

MEJORA IMPLEMENTADA:
Detecta DateTime con hora 00:00:00 y los convierte a Date automáticamente
tanto en consultas como en procedimientos almacenados.
"""

from typing import Any
from datetime import datetime, date, time
import aioodbc

from servicios.abstracciones.i_proveedor_conexion import IProveedorConexion


class RepositorioConsultasSqlServer:
    """
    Implementación de repositorio para ejecutar consultas y procedimientos almacenados en SQL Server.

    MEJORA IMPLEMENTADA:
    Detecta DateTime con hora 00:00:00 y los convierte a DateOnly automáticamente
    tanto en consultas como en procedimientos almacenados.
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
    # MÉTODO AUXILIAR: Mapea tipos de datos de SQL Server a pyodbc types
    # ================================================================
    def _mapear_tipo(self, tipo: str) -> str:
        """
        Mapea tipos de datos de SQL Server para validación y procesamiento.

        Args:
            tipo: Nombre del tipo SQL Server

        Returns:
            Tipo normalizado en minúsculas
        """
        return tipo.lower()

    # ================================================================
    # MÉTODO AUXILIAR: Obtiene metadatos de parámetros de un SP en SQL Server
    # ================================================================
    async def _obtener_metadatos_parametros(
        self,
        cursor,
        nombre_sp: str
    ) -> list[tuple[str, bool, str, int | None]]:
        """
        Obtiene los metadatos de los parámetros de un procedimiento almacenado.

        Args:
            cursor: Cursor de base de datos activo
            nombre_sp: Nombre del procedimiento almacenado

        Returns:
            Lista de tuplas (nombre, es_output, tipo, max_length)
        """
        lista: list[tuple[str, bool, str, int | None]] = []

        sql = """
            SELECT
                PARAMETER_NAME,
                CASE WHEN PARAMETER_MODE = 'OUT' OR PARAMETER_MODE = 'INOUT' THEN 1 ELSE 0 END AS IsOutput,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.PARAMETERS
            WHERE SPECIFIC_NAME = ?
            ORDER BY ORDINAL_POSITION
        """

        await cursor.execute(sql, nombre_sp)
        rows = await cursor.fetchall()

        for row in rows:
            nombre = row[0] if row[0] else ""
            es_output = row[1] == 1 if row[1] is not None else False
            tipo = row[2] if row[2] else "nvarchar"
            max_length = row[3] if row[3] is not None else None
            lista.append((nombre, es_output, tipo, max_length))

        return lista

    # ================================================================
    # MÉTODO AUXILIAR: Detecta si un valor es JSON
    # ================================================================
    def _es_json(
        self,
        tipo: str,
        max_length: int | None,
        nombre_param: str,
        valor: Any
    ) -> bool:
        """
        Detecta si un parámetro debería tratarse como JSON.

        Detección de 3 formas:
        1. Por tipo (nvarchar(max) es el tipo JSON en SQL Server)
        2. Por contenido (empieza con { o [)
        3. Por nombre común de parámetro JSON
        """
        # 1. Por tipo: nvarchar(max) = max_length -1
        if tipo.lower() == "nvarchar" and max_length == -1:
            return True

        # 2. y 3. Por contenido y nombre
        if isinstance(valor, str) and valor.strip():
            nombre_lower = nombre_param.lower() if nombre_param else ""
            valor_trim = valor.strip()

            # Detectar por contenido
            if valor_trim.startswith("{") or valor_trim.startswith("["):
                return True

            # Detectar por nombre común de parámetros JSON
            if any(x in nombre_lower for x in ["roles", "detalles", "json", "data"]):
                if valor_trim.startswith("{") or valor_trim.startswith("["):
                    return True

        return False

    # ================================================================
    # MÉTODO AUXILIAR: Convierte DateTime con hora 00:00:00 a date
    # ================================================================
    def _convertir_datetime_a_date_si_aplica(
        self,
        valor: Any,
        tipo_columna: str
    ) -> Any:
        """
        Si el valor es datetime con hora 00:00:00 y el tipo de columna es date,
        convierte a date para evitar problemas de comparación.
        """
        if isinstance(valor, datetime):
            if valor.hour == 0 and valor.minute == 0 and valor.second == 0:
                if tipo_columna.lower() == "date":
                    return valor.date()
        return valor

    # ================================================================
    # MÉTODO AUXILIAR: Convierte valor según tipo de parámetro
    # ================================================================
    def _convertir_valor_segun_tipo(
        self,
        valor: Any,
        tipo: str,
        max_length: int | None,
        nombre_param: str
    ) -> Any:
        """
        Convierte el valor al tipo apropiado según los metadatos del parámetro.
        """
        if valor is None:
            return None

        tipo_lower = tipo.lower()

        # JSON
        if self._es_json(tipo, max_length, nombre_param, valor):
            return str(valor) if valor is not None else None

        # VARCHAR/NVARCHAR/CHAR/NCHAR - Convertir a string
        if tipo_lower in ("varchar", "nvarchar", "char", "nchar"):
            return str(valor)

        # DATE - Manejar DateTime con hora 00:00:00
        if tipo_lower == "date":
            if isinstance(valor, datetime):
                if valor.hour == 0 and valor.minute == 0 and valor.second == 0:
                    return valor.date()
            elif isinstance(valor, date):
                return valor
            return valor

        # INT
        if tipo_lower == "int":
            return int(valor)

        # BIGINT
        if tipo_lower == "bigint":
            return int(valor)

        # DECIMAL/NUMERIC
        if tipo_lower in ("decimal", "numeric"):
            return float(valor)

        # BIT (boolean)
        if tipo_lower == "bit":
            if isinstance(valor, bool):
                return valor
            if isinstance(valor, str):
                return valor.lower() in ("true", "1", "yes", "si")
            return bool(valor)

        # Caso por defecto
        return valor

    # ================================================================
    # MÉTODO PRINCIPAL: Ejecuta un procedimiento almacenado genérico
    # MEJORA CRÍTICA: Convierte DateTime con hora 00:00:00 a Date
    # DETECTA SI ES FUNCTION O PROCEDURE
    # ================================================================
    async def ejecutar_procedimiento_almacenado_con_dictionary(
        self,
        nombre_sp: str,
        parametros: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta un procedimiento almacenado o función con parámetros Dictionary.

        MEJORA CRÍTICA: Detecta si es FUNCTION o PROCEDURE y ejecuta apropiadamente.

        Args:
            nombre_sp: Nombre del SP o función
            parametros: Diccionario de parámetros

        Returns:
            Lista de diccionarios con los resultados
        """
        if not nombre_sp or not nombre_sp.strip():
            raise ValueError("El nombre del procedimiento no puede estar vacío.")

        cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()
        resultados: list[dict[str, Any]] = []

        async with aioodbc.connect(dsn=cadena_conexion) as conexion:
            async with conexion.cursor() as cursor:
                # Detectar si es FUNCTION o PROCEDURE
                sql_tipo = "SELECT ROUTINE_TYPE FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_NAME = ?"
                await cursor.execute(sql_tipo, nombre_sp)
                resultado_tipo = await cursor.fetchone()
                tipo_rutina = resultado_tipo[0] if resultado_tipo else "PROCEDURE"

                # Obtener metadatos de parámetros
                metadatos = await self._obtener_metadatos_parametros(cursor, nombre_sp)

                # Normalizar parámetros (quitar @ del inicio si existe)
                parametros_normalizados: dict[str, Any] = {}
                for clave, valor in (parametros or {}).items():
                    clave_normalizada = clave[1:] if clave.startswith("@") else clave
                    parametros_normalizados[clave_normalizada.lower()] = valor

                if tipo_rutina == "FUNCTION":
                    # ============================================================
                    # MANEJO DE FUNCIONES
                    # ============================================================
                    parametros_entrada = [m for m in metadatos if not m[1]]  # No output
                    params_query = ", ".join(f"?" for _ in parametros_entrada)
                    sql_llamada = f"SELECT dbo.{nombre_sp}({params_query}) AS Resultado"

                    # Construir lista de valores
                    valores: list[Any] = []
                    for meta in parametros_entrada:
                        nombre_param = meta[0]
                        clave = nombre_param[1:] if nombre_param.startswith("@") else nombre_param
                        clave_lower = clave.lower()

                        valor = parametros_normalizados.get(clave_lower)
                        valor_convertido = self._convertir_valor_segun_tipo(
                            valor, meta[2], meta[3], nombre_param
                        )
                        valores.append(valor_convertido)

                    await cursor.execute(sql_llamada, valores)

                else:
                    # ============================================================
                    # MANEJO DE PROCEDIMIENTOS
                    # ============================================================
                    # Construir la llamada EXEC con parámetros nombrados
                    params_call: list[str] = []
                    valores: list[Any] = []

                    for meta in metadatos:
                        nombre_param = meta[0]
                        es_output = meta[1]
                        tipo = meta[2]
                        max_length = meta[3]

                        clave = nombre_param[1:] if nombre_param.startswith("@") else nombre_param
                        clave_lower = clave.lower()

                        if not es_output:
                            valor = parametros_normalizados.get(clave_lower)
                            valor_convertido = self._convertir_valor_segun_tipo(
                                valor, tipo, max_length, nombre_param
                            )
                            params_call.append(f"@{clave} = ?")
                            valores.append(valor_convertido)

                    if params_call:
                        sql_exec = f"EXEC {nombre_sp} {', '.join(params_call)}"
                    else:
                        sql_exec = f"EXEC {nombre_sp}"

                    await cursor.execute(sql_exec, valores)

                # Obtener resultados
                try:
                    columns = [column[0] for column in cursor.description] if cursor.description else []
                    rows = await cursor.fetchall()

                    for row in rows:
                        fila_dict: dict[str, Any] = {}
                        for i, columna in enumerate(columns):
                            fila_dict[columna] = row[i]
                        resultados.append(fila_dict)
                except Exception:
                    # El SP no devolvió resultados (INSERT/UPDATE/DELETE)
                    pass

        return resultados

    # ================================================================
    # MÉTODO: Ejecuta una consulta SQL parametrizada
    # MEJORA: Convierte DateTime con hora 00:00:00 a Date
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

        MEJORA CRÍTICA: Detecta DateTime con hora 00:00:00 y los convierte a Date.

        Args:
            consulta_sql: Consulta SQL parametrizada
            parametros: Diccionario de parámetros
            maximo_registros: Límite de registros (por defecto 10000)
            esquema: Esquema opcional

        Returns:
            Lista de diccionarios con los resultados
        """
        resultados: list[dict[str, Any]] = []
        cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()

        async with aioodbc.connect(dsn=cadena_conexion) as conexion:
            async with conexion.cursor() as cursor:
                # Preparar parámetros
                valores: list[Any] = []
                consulta_final = consulta_sql

                for nombre_param, valor in (parametros or {}).items():
                    # Normalizar nombre del parámetro
                    nombre = nombre_param if nombre_param.startswith("@") else f"@{nombre_param}"

                    # MEJORA CRÍTICA: Detectar DateTime con hora 00:00:00
                    if isinstance(valor, datetime):
                        if valor.hour == 0 and valor.minute == 0 and valor.second == 0:
                            # Si la hora es 00:00:00, probablemente es una fecha sin hora
                            # Convertir a Date para que SQL Server lo trate como DATE
                            valor = valor.date()

                    # Reemplazar el parámetro nombrado con ?
                    consulta_final = consulta_final.replace(nombre, "?")
                    valores.append(valor)

                await cursor.execute(consulta_final, valores)

                # Obtener resultados
                columns = [column[0] for column in cursor.description] if cursor.description else []
                rows = await cursor.fetchall()

                for row in rows[:maximo_registros]:
                    fila_dict: dict[str, Any] = {}
                    for i, columna in enumerate(columns):
                        fila_dict[columna] = row[i]
                    resultados.append(fila_dict)

        return resultados

    # ================================================================
    # MÉTODO: Valida si una consulta SQL con parámetros es sintácticamente correcta
    # ================================================================
    async def validar_consulta_con_dictionary(
        self,
        consulta_sql: str,
        parametros: dict[str, Any] | None
    ) -> tuple[bool, str | None]:
        """
        Valida si una consulta SQL es sintácticamente correcta sin ejecutarla.

        Usa SET PARSEONLY ON para validar sin ejecución.

        Args:
            consulta_sql: Consulta SQL a validar
            parametros: Diccionario de parámetros

        Returns:
            Tupla (es_valida, mensaje_error)
        """
        try:
            cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()

            async with aioodbc.connect(dsn=cadena_conexion) as conexion:
                async with conexion.cursor() as cursor:
                    # Activar modo PARSEONLY para validación sin ejecución
                    await cursor.execute("SET PARSEONLY ON")

                    # Preparar parámetros
                    valores: list[Any] = []
                    consulta_final = consulta_sql

                    for nombre_param, valor in (parametros or {}).items():
                        nombre = nombre_param if nombre_param.startswith("@") else f"@{nombre_param}"
                        consulta_final = consulta_final.replace(nombre, "?")
                        valores.append(valor)

                    await cursor.execute(consulta_final, valores)

                    # Desactivar modo PARSEONLY
                    await cursor.execute("SET PARSEONLY OFF")

                    return (True, None)

        except Exception as ex:
            error_str = str(ex)

            # Mapear códigos de error comunes
            if "102" in error_str:
                return (False, "Error de sintaxis SQL: revise la estructura de la consulta")
            elif "207" in error_str:
                return (False, "Nombre de columna inválido: verifique que las columnas existan")
            elif "208" in error_str:
                return (False, "Objeto no válido: tabla o vista no existe en la base de datos")
            elif "156" in error_str:
                return (False, "Palabra clave SQL incorrecta o en posición incorrecta")
            elif "170" in error_str:
                return (False, "Error de sintaxis cerca de palabra reservada")
            else:
                return (False, f"Error de validación SQL Server: {error_str}")

    # ================================================================
    # MÉTODOS: Consultas de metadatos de base de datos/tablas
    # ================================================================
    async def obtener_esquema_tabla(
        self,
        nombre_tabla: str,
        esquema_predeterminado: str | None = None
    ) -> str | None:
        """
        Obtiene el esquema real donde existe una tabla.

        Si se proporciona un esquema específico, verifica que la tabla exista en ese esquema.
        Si no, busca primero en 'dbo', luego en cualquier esquema.
        """
        cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()

        async with aioodbc.connect(dsn=cadena_conexion) as conexion:
            async with conexion.cursor() as cursor:
                # Si se proporciona un esquema específico, verificar que la tabla existe
                if esquema_predeterminado and esquema_predeterminado.strip():
                    sql_verificar = """
                        SELECT TABLE_SCHEMA
                        FROM INFORMATION_SCHEMA.TABLES
                        WHERE TABLE_NAME = ? AND TABLE_SCHEMA = ?
                    """
                    await cursor.execute(sql_verificar, nombre_tabla, esquema_predeterminado)
                    resultado = await cursor.fetchone()
                    if resultado:
                        return resultado[0]

                # Buscar primero en 'dbo', luego en cualquier esquema
                sql = """
                    SELECT TOP 1 TABLE_SCHEMA
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_NAME = ?
                    ORDER BY CASE WHEN TABLE_SCHEMA = 'dbo' THEN 0 ELSE 1 END
                """
                await cursor.execute(sql, nombre_tabla)
                resultado = await cursor.fetchone()
                return resultado[0] if resultado else None

    async def obtener_estructura_tabla(
        self,
        nombre_tabla: str,
        esquema: str
    ) -> list[dict[str, Any]]:
        """
        Obtiene la estructura detallada de una tabla incluyendo constraints.

        Incluye: PK, FK, UNIQUE, CHECK, DEFAULT, IDENTITY
        """
        resultados: list[dict[str, Any]] = []
        cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()

        async with aioodbc.connect(dsn=cadena_conexion) as conexion:
            async with conexion.cursor() as cursor:
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
                        CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 'YES' ELSE 'NO' END AS is_primary_key,
                        CASE WHEN uq.COLUMN_NAME IS NOT NULL THEN 'YES' ELSE 'NO' END AS is_unique,
                        CASE WHEN COLUMNPROPERTY(OBJECT_ID(QUOTENAME(c.TABLE_SCHEMA) + '.' + QUOTENAME(c.TABLE_NAME)), c.COLUMN_NAME, 'IsIdentity') = 1 THEN 'YES' ELSE 'NO' END AS is_identity,
                        fk.foreign_table_name,
                        fk.foreign_column_name,
                        fk.fk_constraint_name,
                        chk.check_clause
                    FROM INFORMATION_SCHEMA.COLUMNS c
                    LEFT JOIN (
                        SELECT kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.COLUMN_NAME
                        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                            AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                        WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                    ) pk ON c.TABLE_SCHEMA = pk.TABLE_SCHEMA
                        AND c.TABLE_NAME = pk.TABLE_NAME
                        AND c.COLUMN_NAME = pk.COLUMN_NAME
                    LEFT JOIN (
                        SELECT kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.COLUMN_NAME
                        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                            AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                        WHERE tc.CONSTRAINT_TYPE = 'UNIQUE'
                    ) uq ON c.TABLE_SCHEMA = uq.TABLE_SCHEMA
                        AND c.TABLE_NAME = uq.TABLE_NAME
                        AND c.COLUMN_NAME = uq.COLUMN_NAME
                    LEFT JOIN (
                        SELECT
                            kcu.TABLE_SCHEMA,
                            kcu.TABLE_NAME,
                            kcu.COLUMN_NAME,
                            ccu.TABLE_NAME AS foreign_table_name,
                            ccu.COLUMN_NAME AS foreign_column_name,
                            tc.CONSTRAINT_NAME AS fk_constraint_name
                        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                            AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                        JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE ccu
                            ON tc.CONSTRAINT_NAME = ccu.CONSTRAINT_NAME
                            AND tc.TABLE_SCHEMA = ccu.TABLE_SCHEMA
                        WHERE tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
                    ) fk ON c.TABLE_SCHEMA = fk.TABLE_SCHEMA
                        AND c.TABLE_NAME = fk.TABLE_NAME
                        AND c.COLUMN_NAME = fk.COLUMN_NAME
                    LEFT JOIN (
                        SELECT
                            ccu.TABLE_SCHEMA,
                            ccu.TABLE_NAME,
                            ccu.COLUMN_NAME,
                            cc.CHECK_CLAUSE AS check_clause
                        FROM INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE ccu
                        JOIN INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
                            ON ccu.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
                            AND ccu.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA
                    ) chk ON c.TABLE_SCHEMA = chk.TABLE_SCHEMA
                        AND c.TABLE_NAME = chk.TABLE_NAME
                        AND c.COLUMN_NAME = chk.COLUMN_NAME
                    WHERE c.TABLE_NAME = ? AND c.TABLE_SCHEMA = ?
                    ORDER BY c.ORDINAL_POSITION
                """

                await cursor.execute(sql, nombre_tabla, esquema)
                columns = [column[0] for column in cursor.description]
                rows = await cursor.fetchall()

                for row in rows:
                    fila_dict: dict[str, Any] = {}
                    for i, columna in enumerate(columns):
                        fila_dict[columna] = row[i]
                    resultados.append(fila_dict)

        return resultados

    async def obtener_estructura_base_datos(self) -> list[dict[str, Any]]:
        """
        Obtiene la estructura básica de todas las tablas de la base de datos.
        """
        resultados: list[dict[str, Any]] = []
        cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()

        async with aioodbc.connect(dsn=cadena_conexion) as conexion:
            async with conexion.cursor() as cursor:
                sql = """
                    SELECT
                        t.TABLE_NAME AS table_name,
                        c.COLUMN_NAME AS column_name,
                        c.DATA_TYPE AS data_type,
                        c.CHARACTER_MAXIMUM_LENGTH AS character_maximum_length,
                        c.IS_NULLABLE AS is_nullable
                    FROM INFORMATION_SCHEMA.TABLES t
                    INNER JOIN INFORMATION_SCHEMA.COLUMNS c
                        ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
                    WHERE t.TABLE_TYPE = 'BASE TABLE'
                    ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, c.ORDINAL_POSITION
                """

                await cursor.execute(sql)
                columns = [column[0] for column in cursor.description]
                rows = await cursor.fetchall()

                for row in rows:
                    fila_dict: dict[str, Any] = {}
                    for i, columna in enumerate(columns):
                        fila_dict[columna] = row[i]
                    resultados.append(fila_dict)

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
        - Secuencias
        - Tipos definidos por usuario
        - Sinónimos
        """
        resultado: dict[str, Any] = {}
        cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()

        async with aioodbc.connect(dsn=cadena_conexion) as conexion:
            async with conexion.cursor() as cursor:
                # 1. Tablas con columnas y constraints
                resultado["tablas"] = await self._obtener_tablas_con_columnas(cursor)

                # 2. Vistas
                resultado["vistas"] = await self._obtener_vistas(cursor)

                # 3. Procedimientos almacenados
                resultado["procedimientos"] = await self._obtener_procedimientos(cursor)

                # 4. Funciones
                resultado["funciones"] = await self._obtener_funciones(cursor)

                # 5. Triggers
                resultado["triggers"] = await self._obtener_triggers(cursor)

                # 6. Índices
                resultado["indices"] = await self._obtener_indices(cursor)

                # 7. Secuencias
                resultado["secuencias"] = await self._obtener_secuencias(cursor)

                # 8. Tipos definidos por usuario
                resultado["tipos"] = await self._obtener_tipos_personalizados(cursor)

                # 9. Sinónimos
                resultado["sinonimos"] = await self._obtener_sinonimos(cursor)

        return resultado

    # ================================================================
    # MÉTODOS AUXILIARES PARA ESTRUCTURA COMPLETA DE BD
    # ================================================================

    async def _obtener_tablas_con_columnas(self, cursor) -> list[dict[str, Any]]:
        """Obtiene todas las tablas con sus columnas, FK e índices."""
        tablas: list[dict[str, Any]] = []

        # Obtener lista de tablas
        sql_tablas = """
            SELECT
                s.name AS schema_name,
                t.name AS table_name,
                ep.value AS table_comment
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = t.object_id
                AND ep.minor_id = 0
                AND ep.name = 'MS_Description'
            WHERE t.is_ms_shipped = 0
            ORDER BY s.name, t.name
        """

        await cursor.execute(sql_tablas)
        rows_tablas = await cursor.fetchall()

        lista_tablas: list[tuple[str, str, str | None]] = []
        for row in rows_tablas:
            lista_tablas.append((row[0], row[1], row[2]))

        for schema, tabla, comentario in lista_tablas:
            tabla_dict: dict[str, Any] = {
                "schema": schema,
                "nombre": tabla,
                "comentario": comentario,
                "columnas": await self._obtener_columnas_tabla(cursor, schema, tabla),
                "foreign_keys": await self._obtener_foreign_keys_tabla(cursor, schema, tabla),
                "indices": await self._obtener_indices_tabla(cursor, schema, tabla)
            }
            tablas.append(tabla_dict)

        return tablas

    async def _obtener_columnas_tabla(
        self,
        cursor,
        schema: str,
        tabla: str
    ) -> list[dict[str, Any]]:
        """Obtiene las columnas de una tabla específica."""
        columnas: list[dict[str, Any]] = []

        sql = """
            SELECT
                c.name AS column_name,
                tp.name AS data_type,
                c.max_length AS character_maximum_length,
                c.precision AS numeric_precision,
                c.scale AS numeric_scale,
                c.is_nullable,
                dc.definition AS column_default,
                c.column_id AS ordinal_position,
                CASE WHEN pk.column_id IS NOT NULL THEN 1 ELSE 0 END AS is_primary_key,
                CASE WHEN uq.column_id IS NOT NULL THEN 1 ELSE 0 END AS is_unique,
                c.is_identity,
                ep.value AS column_comment
            FROM sys.columns c
            INNER JOIN sys.tables t ON c.object_id = t.object_id
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            INNER JOIN sys.types tp ON c.user_type_id = tp.user_type_id
            LEFT JOIN sys.default_constraints dc ON c.default_object_id = dc.object_id
            LEFT JOIN (
                SELECT ic.object_id, ic.column_id
                FROM sys.index_columns ic
                INNER JOIN sys.indexes i ON ic.object_id = i.object_id AND ic.index_id = i.index_id
                WHERE i.is_primary_key = 1
            ) pk ON c.object_id = pk.object_id AND c.column_id = pk.column_id
            LEFT JOIN (
                SELECT ic.object_id, ic.column_id
                FROM sys.index_columns ic
                INNER JOIN sys.indexes i ON ic.object_id = i.object_id AND ic.index_id = i.index_id
                WHERE i.is_unique = 1 AND i.is_primary_key = 0
            ) uq ON c.object_id = uq.object_id AND c.column_id = uq.column_id
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = c.object_id
                AND ep.minor_id = c.column_id
                AND ep.name = 'MS_Description'
            WHERE s.name = ? AND t.name = ?
            ORDER BY c.column_id
        """

        await cursor.execute(sql, schema, tabla)
        rows = await cursor.fetchall()

        for row in rows:
            columnas.append({
                "nombre": row[0],
                "tipo": row[1],
                "longitud_maxima": row[2],
                "precision": row[3],
                "escala": row[4],
                "nullable": row[5],
                "valor_default": row[6],
                "posicion": row[7],
                "es_primary_key": row[8] == 1,
                "es_unique": row[9] == 1,
                "es_identity": row[10],
                "comentario": row[11]
            })

        return columnas

    async def _obtener_foreign_keys_tabla(
        self,
        cursor,
        schema: str,
        tabla: str
    ) -> list[dict[str, Any]]:
        """Obtiene las foreign keys de una tabla."""
        fks: list[dict[str, Any]] = []

        sql = """
            SELECT
                fk.name AS constraint_name,
                COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS column_name,
                OBJECT_SCHEMA_NAME(fkc.referenced_object_id) AS referenced_schema,
                OBJECT_NAME(fkc.referenced_object_id) AS referenced_table,
                COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS referenced_column,
                fk.update_referential_action_desc AS on_update,
                fk.delete_referential_action_desc AS on_delete
            FROM sys.foreign_keys fk
            INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN sys.tables t ON fk.parent_object_id = t.object_id
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = ? AND t.name = ?
            ORDER BY fk.name
        """

        await cursor.execute(sql, schema, tabla)
        rows = await cursor.fetchall()

        for row in rows:
            fks.append({
                "constraint_name": row[0],
                "column_name": row[1],
                "foreign_schema_name": row[2],
                "foreign_table_name": row[3],
                "foreign_column_name": row[4],
                "on_update": row[5],
                "on_delete": row[6]
            })

        return fks

    async def _obtener_indices_tabla(
        self,
        cursor,
        schema: str,
        tabla: str
    ) -> list[dict[str, Any]]:
        """Obtiene los índices de una tabla."""
        indices: list[dict[str, Any]] = []

        sql = """
            SELECT
                i.name AS index_name,
                i.type_desc AS index_type,
                i.is_unique,
                i.is_primary_key,
                STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
            FROM sys.indexes i
            INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            INNER JOIN sys.tables t ON i.object_id = t.object_id
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = ? AND t.name = ? AND i.name IS NOT NULL
            GROUP BY i.name, i.type_desc, i.is_unique, i.is_primary_key
            ORDER BY i.name
        """

        await cursor.execute(sql, schema, tabla)
        rows = await cursor.fetchall()

        for row in rows:
            indices.append({
                "nombre": row[0],
                "tipo": row[1],
                "es_unique": row[2],
                "es_primary_key": row[3],
                "columnas": row[4]
            })

        return indices

    async def _obtener_vistas(self, cursor) -> list[dict[str, Any]]:
        """Obtiene todas las vistas de la base de datos."""
        vistas: list[dict[str, Any]] = []

        sql = """
            SELECT
                s.name AS schema_name,
                v.name AS view_name,
                m.definition AS view_definition,
                ep.value AS view_comment
            FROM sys.views v
            INNER JOIN sys.schemas s ON v.schema_id = s.schema_id
            LEFT JOIN sys.sql_modules m ON v.object_id = m.object_id
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = v.object_id
                AND ep.minor_id = 0
                AND ep.name = 'MS_Description'
            WHERE v.is_ms_shipped = 0
            ORDER BY s.name, v.name
        """

        await cursor.execute(sql)
        rows = await cursor.fetchall()

        for row in rows:
            vistas.append({
                "schema": row[0],
                "nombre": row[1],
                "definicion": row[2],
                "comentario": row[3]
            })

        return vistas

    async def _obtener_procedimientos(self, cursor) -> list[dict[str, Any]]:
        """Obtiene todos los procedimientos almacenados."""
        procedimientos: list[dict[str, Any]] = []

        sql = """
            SELECT
                s.name AS schema_name,
                p.name AS procedure_name,
                m.definition AS procedure_definition,
                p.create_date,
                p.modify_date,
                ep.value AS procedure_comment
            FROM sys.procedures p
            INNER JOIN sys.schemas s ON p.schema_id = s.schema_id
            LEFT JOIN sys.sql_modules m ON p.object_id = m.object_id
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = p.object_id
                AND ep.minor_id = 0
                AND ep.name = 'MS_Description'
            WHERE p.is_ms_shipped = 0
            ORDER BY s.name, p.name
        """

        await cursor.execute(sql)
        rows = await cursor.fetchall()

        lista_procs: list[tuple] = []
        for row in rows:
            lista_procs.append((row[0], row[1], row[2], row[3], row[4], row[5]))

        for schema, nombre, definicion, created, modified, comentario in lista_procs:
            proc_dict: dict[str, Any] = {
                "schema": schema,
                "nombre": nombre,
                "definicion": definicion,
                "fecha_creacion": created,
                "fecha_modificacion": modified,
                "comentario": comentario,
                "parametros": await self._obtener_parametros_rutina(cursor, schema, nombre)
            }
            procedimientos.append(proc_dict)

        return procedimientos

    async def _obtener_funciones(self, cursor) -> list[dict[str, Any]]:
        """Obtiene todas las funciones de la base de datos."""
        funciones: list[dict[str, Any]] = []

        sql = """
            SELECT
                s.name AS schema_name,
                o.name AS function_name,
                o.type_desc AS function_type,
                m.definition AS function_definition,
                o.create_date,
                o.modify_date,
                ep.value AS function_comment
            FROM sys.objects o
            INNER JOIN sys.schemas s ON o.schema_id = s.schema_id
            LEFT JOIN sys.sql_modules m ON o.object_id = m.object_id
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = o.object_id
                AND ep.minor_id = 0
                AND ep.name = 'MS_Description'
            WHERE o.type IN ('FN', 'IF', 'TF', 'FS', 'FT')
            AND o.is_ms_shipped = 0
            ORDER BY s.name, o.name
        """

        await cursor.execute(sql)
        rows = await cursor.fetchall()

        lista_funcs: list[tuple] = []
        for row in rows:
            lista_funcs.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6]))

        for schema, nombre, tipo, definicion, created, modified, comentario in lista_funcs:
            func_dict: dict[str, Any] = {
                "schema": schema,
                "nombre": nombre,
                "tipo": tipo,
                "definicion": definicion,
                "fecha_creacion": created,
                "fecha_modificacion": modified,
                "comentario": comentario,
                "parametros": await self._obtener_parametros_rutina(cursor, schema, nombre)
            }
            funciones.append(func_dict)

        return funciones

    async def _obtener_parametros_rutina(
        self,
        cursor,
        schema: str,
        rutina: str
    ) -> list[dict[str, Any]]:
        """Obtiene los parámetros de un procedimiento o función."""
        parametros: list[dict[str, Any]] = []

        sql = """
            SELECT
                p.name AS parameter_name,
                TYPE_NAME(p.user_type_id) AS data_type,
                p.max_length,
                p.precision,
                p.scale,
                p.is_output,
                p.has_default_value,
                p.default_value
            FROM sys.parameters p
            INNER JOIN sys.objects o ON p.object_id = o.object_id
            INNER JOIN sys.schemas s ON o.schema_id = s.schema_id
            WHERE s.name = ? AND o.name = ?
            ORDER BY p.parameter_id
        """

        await cursor.execute(sql, schema, rutina)
        rows = await cursor.fetchall()

        for row in rows:
            nombre_param = row[0]
            if not nombre_param:  # Saltar return value
                continue

            parametros.append({
                "nombre": nombre_param,
                "tipo": row[1],
                "longitud_maxima": row[2],
                "precision": row[3],
                "escala": row[4],
                "es_output": row[5],
                "tiene_default": row[6],
                "valor_default": row[7]
            })

        return parametros

    async def _obtener_triggers(self, cursor) -> list[dict[str, Any]]:
        """Obtiene todos los triggers de la base de datos."""
        triggers: list[dict[str, Any]] = []

        sql = """
            SELECT
                s.name AS schema_name,
                tr.name AS trigger_name,
                OBJECT_NAME(tr.parent_id) AS table_name,
                tr.is_disabled,
                tr.is_instead_of_trigger,
                m.definition AS trigger_definition,
                CASE
                    WHEN te.type_desc = 'INSERT' THEN 'INSERT'
                    WHEN te.type_desc = 'UPDATE' THEN 'UPDATE'
                    WHEN te.type_desc = 'DELETE' THEN 'DELETE'
                    ELSE te.type_desc
                END AS trigger_event,
                tr.create_date,
                tr.modify_date
            FROM sys.triggers tr
            INNER JOIN sys.objects o ON tr.parent_id = o.object_id
            INNER JOIN sys.schemas s ON o.schema_id = s.schema_id
            LEFT JOIN sys.sql_modules m ON tr.object_id = m.object_id
            LEFT JOIN sys.trigger_events te ON tr.object_id = te.object_id
            WHERE tr.is_ms_shipped = 0
            ORDER BY s.name, tr.name
        """

        await cursor.execute(sql)
        rows = await cursor.fetchall()

        for row in rows:
            triggers.append({
                "schema": row[0],
                "nombre": row[1],
                "tabla": row[2],
                "deshabilitado": row[3],
                "es_instead_of": row[4],
                "definicion": row[5],
                "evento": row[6],
                "fecha_creacion": row[7],
                "fecha_modificacion": row[8]
            })

        return triggers

    async def _obtener_indices(self, cursor) -> list[dict[str, Any]]:
        """Obtiene todos los índices de la base de datos."""
        indices: list[dict[str, Any]] = []

        sql = """
            SELECT
                s.name AS schema_name,
                t.name AS table_name,
                i.name AS index_name,
                i.type_desc AS index_type,
                i.is_unique,
                i.is_primary_key,
                i.is_unique_constraint,
                STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns,
                i.filter_definition
            FROM sys.indexes i
            INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            INNER JOIN sys.tables t ON i.object_id = t.object_id
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE i.name IS NOT NULL AND t.is_ms_shipped = 0
            GROUP BY s.name, t.name, i.name, i.type_desc, i.is_unique, i.is_primary_key, i.is_unique_constraint, i.filter_definition
            ORDER BY s.name, t.name, i.name
        """

        await cursor.execute(sql)
        rows = await cursor.fetchall()

        for row in rows:
            indices.append({
                "schema": row[0],
                "tabla": row[1],
                "nombre": row[2],
                "tipo": row[3],
                "es_unique": row[4],
                "es_primary_key": row[5],
                "es_unique_constraint": row[6],
                "columnas": row[7],
                "filtro": row[8]
            })

        return indices

    async def _obtener_secuencias(self, cursor) -> list[dict[str, Any]]:
        """Obtiene todas las secuencias de la base de datos."""
        secuencias: list[dict[str, Any]] = []

        sql = """
            SELECT
                s.name AS schema_name,
                seq.name AS sequence_name,
                TYPE_NAME(seq.user_type_id) AS data_type,
                seq.start_value,
                seq.increment,
                seq.minimum_value,
                seq.maximum_value,
                seq.is_cycling,
                seq.current_value
            FROM sys.sequences seq
            INNER JOIN sys.schemas s ON seq.schema_id = s.schema_id
            ORDER BY s.name, seq.name
        """

        await cursor.execute(sql)
        rows = await cursor.fetchall()

        for row in rows:
            secuencias.append({
                "schema": row[0],
                "nombre": row[1],
                "tipo": row[2],
                "valor_inicial": row[3],
                "incremento": row[4],
                "valor_minimo": row[5],
                "valor_maximo": row[6],
                "es_ciclica": row[7],
                "valor_actual": row[8]
            })

        return secuencias

    async def _obtener_tipos_personalizados(self, cursor) -> list[dict[str, Any]]:
        """Obtiene los tipos definidos por el usuario."""
        tipos: list[dict[str, Any]] = []

        sql = """
            SELECT
                s.name AS schema_name,
                t.name AS type_name,
                CASE
                    WHEN t.is_table_type = 1 THEN 'TABLE TYPE'
                    WHEN t.is_user_defined = 1 THEN 'USER DEFINED TYPE'
                    ELSE 'ALIAS TYPE'
                END AS type_category,
                bt.name AS base_type,
                t.max_length,
                t.precision,
                t.scale,
                t.is_nullable
            FROM sys.types t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            LEFT JOIN sys.types bt ON t.system_type_id = bt.user_type_id AND bt.is_user_defined = 0
            WHERE t.is_user_defined = 1
            ORDER BY s.name, t.name
        """

        await cursor.execute(sql)
        rows = await cursor.fetchall()

        for row in rows:
            tipos.append({
                "schema": row[0],
                "nombre": row[1],
                "categoria": row[2],
                "tipo_base": row[3],
                "longitud_maxima": row[4],
                "precision": row[5],
                "escala": row[6],
                "nullable": row[7]
            })

        return tipos

    async def _obtener_sinonimos(self, cursor) -> list[dict[str, Any]]:
        """Obtiene todos los sinónimos de la base de datos."""
        sinonimos: list[dict[str, Any]] = []

        sql = """
            SELECT
                s.name AS schema_name,
                syn.name AS synonym_name,
                syn.base_object_name AS target_object,
                syn.create_date
            FROM sys.synonyms syn
            INNER JOIN sys.schemas s ON syn.schema_id = s.schema_id
            ORDER BY s.name, syn.name
        """

        await cursor.execute(sql)
        rows = await cursor.fetchall()

        for row in rows:
            sinonimos.append({
                "schema": row[0],
                "nombre": row[1],
                "objeto_destino": row[2],
                "fecha_creacion": row[3]
            })

        return sinonimos
