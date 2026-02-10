"""
repositorio_consultas_postgresql.py — Implementación para ejecutar consultas y SP en PostgreSQL
Ubicación: repositorios/repositorio_consultas_postgresql.py

Equivalente a: ApiGenericaCsharp/Repositorios/RepositorioConsultasPostgreSQL.cs

Mejoras:
- Detecta DateTime con hora 00:00:00 y los convierte a date automáticamente en consultas.
- Detecta y asigna tipos correctos al ejecutar procedimientos (json/jsonb, enteros, numéricos, booleanos, fechas).
- Soporte para esquemas personalizados (ventas.mi_funcion).
"""

from typing import Any
from datetime import datetime, date
import asyncpg
import json

from servicios.abstracciones.i_proveedor_conexion import IProveedorConexion


class RepositorioConsultasPostgreSQL:
    """
    Implementación de repositorio para ejecutar consultas y procedimientos almacenados en PostgreSQL.

    Mejoras:
    - Detecta DateTime con hora 00:00:00 y los convierte a date automáticamente en consultas.
    - Detecta y asigna tipos correctos al ejecutar procedimientos (json/jsonb, enteros, numéricos, booleanos, fechas).
    - Soporte para esquemas personalizados en el nombre del SP.
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
    # MÉTODO AUXILIAR: Obtiene metadatos de parámetros de un SP en PostgreSQL
    # ================================================================
    async def _obtener_metadatos_parametros(
        self,
        conexion: asyncpg.Connection,
        nombre_sp: str,
        esquema: str | None = None
    ) -> list[tuple[str, str, str]]:
        """
        Obtiene los metadatos de los parámetros de un procedimiento/función.

        MEJORA: Ahora soporta esquemas personalizados (ventas.mi_funcion).
        Busca primero en el esquema especificado, luego en public, finalmente en todos los esquemas.

        Args:
            conexion: Conexión de base de datos activa
            nombre_sp: Nombre del procedimiento/función
            esquema: Esquema opcional

        Returns:
            Lista de tuplas (nombre, modo, tipo)
        """
        lista: list[tuple[str, str, str]] = []

        # MEJORA: Construir consulta dinámica según si hay esquema o no
        if esquema and esquema.strip():
            # Búsqueda en esquema específico
            sql = """
                SELECT parameter_name, parameter_mode, data_type
                FROM information_schema.parameters
                WHERE specific_name = (
                    SELECT specific_name
                    FROM information_schema.routines
                    WHERE routine_schema = $1
                      AND routine_name = $2
                    LIMIT 1
                )
                ORDER BY ordinal_position
            """
            rows = await conexion.fetch(sql, esquema, nombre_sp)
        else:
            # MEJORA: Búsqueda en public primero, luego en cualquier esquema
            sql = """
                SELECT parameter_name, parameter_mode, data_type
                FROM information_schema.parameters
                WHERE specific_name = (
                    SELECT specific_name
                    FROM information_schema.routines
                    WHERE routine_name = $1
                    ORDER BY CASE
                        WHEN routine_schema = 'public' THEN 1
                        ELSE 2
                    END
                    LIMIT 1
                )
                ORDER BY ordinal_position
            """
            rows = await conexion.fetch(sql, nombre_sp)

        for row in rows:
            nombre = row['parameter_name'] or ""
            modo = row['parameter_mode'] or "IN"
            tipo = row['data_type'] or "text"
            lista.append((nombre, modo, tipo))

        return lista

    # ================================================================
    # MÉTODO AUXILIAR: Detecta si un valor es JSON
    # ================================================================
    def _es_json(
        self,
        tipo: str,
        nombre_param: str,
        valor: Any
    ) -> bool:
        """
        Detecta si un parámetro debería tratarse como JSON.

        Detección de 3 formas:
        1. Por tipo de metadato (json/jsonb)
        2. Por contenido (empieza con { o [)
        3. Por nombre común de parámetro JSON
        """
        tipo_lower = tipo.lower()

        # 1. Por tipo
        if tipo_lower in ("json", "jsonb"):
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
    # MÉTODO AUXILIAR: Convierte valor según tipo de parámetro
    # ================================================================
    def _convertir_valor_segun_tipo(
        self,
        valor: Any,
        tipo: str,
        nombre_param: str
    ) -> Any:
        """
        Convierte el valor al tipo apropiado según los metadatos del parámetro.
        """
        if valor is None:
            return None

        tipo_lower = tipo.lower()

        # JSON/JSONB
        if self._es_json(tipo, nombre_param, valor):
            if isinstance(valor, (dict, list)):
                return json.dumps(valor)
            return str(valor) if valor is not None else "{}"

        # INTEGER
        if tipo_lower in ("integer", "int", "int4"):
            return int(valor) if valor is not None else 0

        # BIGINT
        if tipo_lower in ("bigint", "int8"):
            return int(valor) if valor is not None else 0

        # NUMERIC/DECIMAL
        if tipo_lower in ("numeric", "decimal"):
            return float(valor) if valor is not None else 0.0

        # VARCHAR/TEXT - Convertir a string si no lo es
        if tipo_lower in ("character varying", "varchar", "text"):
            return str(valor) if valor is not None else ""

        # BOOLEAN
        if tipo_lower in ("boolean", "bool"):
            if isinstance(valor, bool):
                return valor
            if isinstance(valor, str):
                return valor.lower() in ("true", "1", "yes", "si")
            return bool(valor)

        # DATE - Manejar DateTime con hora 00:00:00
        if tipo_lower == "date":
            if isinstance(valor, datetime):
                return valor.date()
            return valor

        # Caso por defecto
        return valor

    # ================================================================
    # MÉTODO PRINCIPAL: Ejecuta un procedimiento almacenado genérico
    # ================================================================
    async def ejecutar_procedimiento_almacenado_con_dictionary(
        self,
        nombre_sp: str,
        parametros: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta un procedimiento almacenado o función con parámetros Dictionary.

        MEJORA: Ahora soporta esquemas personalizados en el nombre del SP.

        Formatos soportados:
        - "mi_funcion" → Busca en public primero, luego en otros esquemas
        - "ventas.mi_funcion" → Busca específicamente en el esquema ventas
        - "public.mi_funcion" → Busca específicamente en public

        Args:
            nombre_sp: Nombre del SP o función (puede incluir esquema)
            parametros: Diccionario de parámetros

        Returns:
            Lista de diccionarios con los resultados
        """
        if not nombre_sp or not nombre_sp.strip():
            raise ValueError("El nombre del procedimiento no puede estar vacío.")

        cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()
        resultados: list[dict[str, Any]] = []

        conexion = await asyncpg.connect(cadena_conexion)
        try:
            # MEJORA: Detectar si el nombre incluye esquema (ventas.mi_funcion)
            esquema: str | None = None
            nombre_sp_sin_esquema = nombre_sp

            if '.' in nombre_sp:
                partes = nombre_sp.split('.', 1)
                esquema = partes[0].strip()
                nombre_sp_sin_esquema = partes[1].strip()

            # MEJORA: Detectar si es FUNCTION o PROCEDURE (con soporte de esquemas)
            if esquema and esquema.strip():
                sql_tipo = """
                    SELECT routine_type FROM information_schema.routines
                    WHERE routine_schema = $1 AND routine_name = $2 LIMIT 1
                """
                resultado_tipo = await conexion.fetchval(sql_tipo, esquema, nombre_sp_sin_esquema)
            else:
                sql_tipo = """
                    SELECT routine_type FROM information_schema.routines
                    WHERE routine_name = $1
                    ORDER BY CASE WHEN routine_schema = 'public' THEN 1 ELSE 2 END
                    LIMIT 1
                """
                resultado_tipo = await conexion.fetchval(sql_tipo, nombre_sp_sin_esquema)

            tipo_rutina = resultado_tipo or "PROCEDURE"

            # Obtener metadatos de parámetros
            metadatos = await self._obtener_metadatos_parametros(conexion, nombre_sp_sin_esquema, esquema)

            # Normalizar parámetros (quitar @ del inicio si existe)
            parametros_normalizados: dict[str, Any] = {}
            for clave, valor in (parametros or {}).items():
                clave_normalizada = clave[1:] if clave.startswith("@") else clave
                parametros_normalizados[clave_normalizada.lower()] = valor

            # MEJORA: Incluir parámetros IN e INOUT para la llamada
            parametros_entrada = [m for m in metadatos if m[1] in ("IN", "INOUT")]
            parametros_inout = [m for m in metadatos if m[1] == "INOUT"]

            # Construir placeholders ($1, $2, etc.)
            placeholders = ", ".join(f"${i + 1}" for i in range(len(parametros_entrada)))

            # MEJORA: Construir nombre completo del SP (con esquema si está presente)
            nombre_completo_sp = f"{esquema}.{nombre_sp_sin_esquema}" if esquema else nombre_sp_sin_esquema

            # Construir la llamada SQL
            if tipo_rutina == "FUNCTION":
                sql_llamada = f"SELECT * FROM {nombre_completo_sp}({placeholders})"
            else:
                sql_llamada = f"CALL {nombre_completo_sp}({placeholders})"

            # Construir lista de valores
            valores: list[Any] = []
            for meta in parametros_entrada:
                nombre_param = meta[0]
                tipo_param = meta[2]
                clave_lower = nombre_param.lower()

                valor = parametros_normalizados.get(clave_lower)
                valor_convertido = self._convertir_valor_segun_tipo(valor, tipo_param, nombre_param)
                valores.append(valor_convertido)

            # Ejecutar
            if tipo_rutina == "FUNCTION":
                # FUNCIÓN: Ejecutar y leer resultado directamente
                rows = await conexion.fetch(sql_llamada, *valores)
                for row in rows:
                    fila_dict: dict[str, Any] = dict(row)
                    resultados.append(fila_dict)

            elif parametros_inout:
                # PROCEDURE CON INOUT: Usar fetch para capturar valores INOUT
                rows = await conexion.fetch(sql_llamada, *valores)
                for row in rows:
                    fila_dict: dict[str, Any] = dict(row)
                    resultados.append(fila_dict)
            else:
                # PROCEDURE SIN INOUT: ExecuteNonQuery equivalente
                await conexion.execute(sql_llamada, *valores)

        finally:
            await conexion.close()

        return resultados

    # ================================================================
    # MÉTODO: Ejecuta una consulta SQL parametrizada
    # MEJORA: Convierte DateTime con hora 00:00:00 a date
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

        MEJORA CRÍTICA: Detecta DateTime con hora 00:00:00 y los convierte a date.

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

        conexion = await asyncpg.connect(cadena_conexion)
        try:
            # Preparar parámetros - PostgreSQL usa $1, $2, etc.
            valores: list[Any] = []
            consulta_final = consulta_sql
            param_index = 1

            for nombre_param, valor in (parametros or {}).items():
                # Normalizar nombre del parámetro
                nombre = nombre_param if nombre_param.startswith("@") else f"@{nombre_param}"

                # MEJORA CRÍTICA: Detectar DateTime con hora 00:00:00
                if isinstance(valor, datetime):
                    if valor.hour == 0 and valor.minute == 0 and valor.second == 0:
                        valor = valor.date()

                # Reemplazar @param con $N
                consulta_final = consulta_final.replace(nombre, f"${param_index}")
                valores.append(valor)
                param_index += 1

            # Ejecutar
            rows = await conexion.fetch(consulta_final, *valores)

            for row in rows[:maximo_registros]:
                fila_dict: dict[str, Any] = dict(row)
                resultados.append(fila_dict)

        finally:
            await conexion.close()

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

        Usa EXPLAIN para validar la consulta.

        Args:
            consulta_sql: Consulta SQL a validar
            parametros: Diccionario de parámetros

        Returns:
            Tupla (es_valida, mensaje_error)
        """
        try:
            cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()

            conexion = await asyncpg.connect(cadena_conexion)
            try:
                # Preparar parámetros
                valores: list[Any] = []
                consulta_final = consulta_sql
                param_index = 1

                for nombre_param, valor in (parametros or {}).items():
                    nombre = nombre_param if nombre_param.startswith("@") else f"@{nombre_param}"
                    consulta_final = consulta_final.replace(nombre, f"${param_index}")
                    valores.append(valor)
                    param_index += 1

                # Usar EXPLAIN para validar
                consulta_validacion = f"EXPLAIN {consulta_final}"
                await conexion.fetch(consulta_validacion, *valores)

                return (True, None)

            finally:
                await conexion.close()

        except Exception as ex:
            return (False, str(ex))

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
        Si no, busca primero en 'public', luego en cualquier esquema.
        """
        cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()

        conexion = await asyncpg.connect(cadena_conexion)
        try:
            # Si se proporciona un esquema específico, verificar que la tabla existe
            if esquema_predeterminado and esquema_predeterminado.strip():
                sql_verificar = """
                    SELECT table_schema FROM information_schema.tables
                    WHERE table_name = $1 AND table_schema = $2 LIMIT 1
                """
                resultado = await conexion.fetchval(sql_verificar, nombre_tabla, esquema_predeterminado)
                if resultado:
                    return resultado

            # Buscar primero en 'public', luego en cualquier esquema
            sql = """
                SELECT table_schema FROM information_schema.tables
                WHERE table_name = $1
                ORDER BY CASE WHEN table_schema = 'public' THEN 0 ELSE 1 END
                LIMIT 1
            """
            resultado = await conexion.fetchval(sql, nombre_tabla)
            return resultado

        finally:
            await conexion.close()

    async def obtener_estructura_tabla(
        self,
        nombre_tabla: str,
        esquema: str
    ) -> list[dict[str, Any]]:
        """
        Obtiene la estructura detallada de una tabla incluyendo constraints.

        Incluye: PK, FK, UNIQUE, CHECK, DEFAULT
        """
        resultados: list[dict[str, Any]] = []
        cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()

        conexion = await asyncpg.connect(cadena_conexion)
        try:
            sql = """
                SELECT
                    c.column_name,
                    c.data_type,
                    c.character_maximum_length,
                    c.numeric_precision,
                    c.numeric_scale,
                    c.is_nullable,
                    c.column_default,
                    c.ordinal_position,
                    CASE WHEN pk.column_name IS NOT NULL THEN 'YES' ELSE 'NO' END AS is_primary_key,
                    CASE WHEN uq.column_name IS NOT NULL THEN 'YES' ELSE 'NO' END AS is_unique,
                    fk.foreign_table_name,
                    fk.foreign_column_name,
                    fk.constraint_name AS fk_constraint_name,
                    chk.check_clause
                FROM information_schema.columns c
                LEFT JOIN (
                    SELECT kcu.table_schema, kcu.table_name, kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                ) pk ON c.table_schema = pk.table_schema
                    AND c.table_name = pk.table_name
                    AND c.column_name = pk.column_name
                LEFT JOIN (
                    SELECT kcu.table_schema, kcu.table_name, kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'UNIQUE'
                ) uq ON c.table_schema = uq.table_schema
                    AND c.table_name = uq.table_name
                    AND c.column_name = uq.column_name
                LEFT JOIN (
                    SELECT
                        kcu.table_schema,
                        kcu.table_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name,
                        tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                        AND tc.table_schema = ccu.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                ) fk ON c.table_schema = fk.table_schema
                    AND c.table_name = fk.table_name
                    AND c.column_name = fk.column_name
                LEFT JOIN (
                    SELECT
                        ccu.table_schema,
                        ccu.table_name,
                        ccu.column_name,
                        cc.check_clause
                    FROM information_schema.constraint_column_usage ccu
                    JOIN information_schema.check_constraints cc
                        ON ccu.constraint_name = cc.constraint_name
                        AND ccu.constraint_schema = cc.constraint_schema
                ) chk ON c.table_schema = chk.table_schema
                    AND c.table_name = chk.table_name
                    AND c.column_name = chk.column_name
                WHERE c.table_name = $1
                  AND c.table_schema = $2
                ORDER BY c.ordinal_position
            """

            rows = await conexion.fetch(sql, nombre_tabla, esquema)
            for row in rows:
                resultados.append(dict(row))

        finally:
            await conexion.close()

        return resultados

    async def obtener_estructura_base_datos(self) -> list[dict[str, Any]]:
        """
        Obtiene la estructura básica de todas las tablas de la base de datos.
        """
        resultados: list[dict[str, Any]] = []
        cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()

        conexion = await asyncpg.connect(cadena_conexion)
        try:
            sql = """
                SELECT
                    t.table_name,
                    c.column_name,
                    c.data_type,
                    c.character_maximum_length,
                    c.is_nullable
                FROM information_schema.tables t
                INNER JOIN information_schema.columns c
                    ON t.table_schema = c.table_schema AND t.table_name = c.table_name
                WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name, c.ordinal_position
            """

            rows = await conexion.fetch(sql)
            for row in rows:
                resultados.append(dict(row))

        finally:
            await conexion.close()

        return resultados

    async def obtener_estructura_completa_base_datos(self) -> dict[str, Any]:
        """
        Obtiene la estructura completa de la base de datos incluyendo:
        - Tablas con columnas y constraints
        - Vistas
        - Funciones
        - Procedimientos almacenados (PostgreSQL 11+)
        - Triggers
        - Secuencias
        - Índices
        - Tipos personalizados (ENUMS, COMPOSITES)
        - Extensiones
        """
        resultado: dict[str, Any] = {}
        cadena_conexion = self._proveedor_conexion.obtener_cadena_conexion()

        conexion = await asyncpg.connect(cadena_conexion)
        try:
            # 1. TABLAS con sus columnas y constraints
            resultado["tablas"] = await self._obtener_tablas_con_columnas(conexion)

            # 2. VISTAS
            resultado["vistas"] = await self._obtener_vistas(conexion)

            # 3. FUNCIONES
            resultado["funciones"] = await self._obtener_funciones(conexion)

            # 4. PROCEDIMIENTOS ALMACENADOS (PostgreSQL 11+)
            resultado["procedimientos"] = await self._obtener_procedimientos(conexion)

            # 5. TRIGGERS
            resultado["triggers"] = await self._obtener_triggers(conexion)

            # 6. SECUENCIAS
            resultado["secuencias"] = await self._obtener_secuencias(conexion)

            # 7. ÍNDICES
            resultado["indices"] = await self._obtener_indices(conexion)

            # 8. TIPOS PERSONALIZADOS (ENUMS, COMPOSITES)
            resultado["tipos"] = await self._obtener_tipos_personalizados(conexion)

            # 9. EXTENSIONES
            resultado["extensiones"] = await self._obtener_extensiones(conexion)

        finally:
            await conexion.close()

        return resultado

    # ================================================================
    # MÉTODOS AUXILIARES PARA ESTRUCTURA COMPLETA DE BD
    # ================================================================

    async def _obtener_tablas_con_columnas(self, conexion: asyncpg.Connection) -> list[dict[str, Any]]:
        """Obtiene todas las tablas con sus columnas y FK."""
        tablas: list[dict[str, Any]] = []

        # Obtener tablas
        sql_tablas = """
            SELECT
                t.table_name,
                t.table_type,
                obj_description((quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass) AS table_comment,
                (SELECT COUNT(*) FROM information_schema.columns c WHERE c.table_name = t.table_name AND c.table_schema = t.table_schema) AS column_count
            FROM information_schema.tables t
            WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_name
        """

        rows_tablas = await conexion.fetch(sql_tablas)

        for row in rows_tablas:
            nombre_tabla = row['table_name']
            tabla_dict: dict[str, Any] = {
                "table_name": nombre_tabla,
                "table_type": row['table_type'],
                "table_comment": row['table_comment'],
                "column_count": row['column_count'],
                "columnas": await self._obtener_columnas_tabla(conexion, nombre_tabla),
                "foreign_keys": await self._obtener_foreign_keys_tabla(conexion, nombre_tabla)
            }
            tablas.append(tabla_dict)

        return tablas

    async def _obtener_columnas_tabla(
        self,
        conexion: asyncpg.Connection,
        nombre_tabla: str
    ) -> list[dict[str, Any]]:
        """Obtiene las columnas de una tabla específica."""
        columnas: list[dict[str, Any]] = []

        sql = """
            SELECT
                c.column_name,
                c.data_type,
                c.udt_name,
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                c.is_nullable,
                c.column_default,
                c.ordinal_position,
                CASE WHEN pk.column_name IS NOT NULL THEN 'YES' ELSE 'NO' END AS is_primary_key,
                CASE WHEN uq.column_name IS NOT NULL THEN 'YES' ELSE 'NO' END AS is_unique,
                col_description((quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass, c.ordinal_position) AS column_comment
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.table_schema, kcu.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
            ) pk ON c.table_schema = pk.table_schema AND c.table_name = pk.table_name AND c.column_name = pk.column_name
            LEFT JOIN (
                SELECT kcu.table_schema, kcu.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'UNIQUE'
            ) uq ON c.table_schema = uq.table_schema AND c.table_name = uq.table_name AND c.column_name = uq.column_name
            WHERE c.table_name = $1 AND c.table_schema = 'public'
            ORDER BY c.ordinal_position
        """

        rows = await conexion.fetch(sql, nombre_tabla)
        for row in rows:
            columnas.append(dict(row))

        return columnas

    async def _obtener_foreign_keys_tabla(
        self,
        conexion: asyncpg.Connection,
        nombre_tabla: str
    ) -> list[dict[str, Any]]:
        """Obtiene las foreign keys de una tabla."""
        fks: list[dict[str, Any]] = []

        sql = """
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.update_rule,
                rc.delete_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.table_schema
            JOIN information_schema.referential_constraints rc ON tc.constraint_name = rc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = $1 AND tc.table_schema = 'public'
        """

        rows = await conexion.fetch(sql, nombre_tabla)
        for row in rows:
            fks.append(dict(row))

        return fks

    async def _obtener_vistas(self, conexion: asyncpg.Connection) -> list[dict[str, Any]]:
        """Obtiene todas las vistas de la base de datos."""
        vistas: list[dict[str, Any]] = []

        sql = """
            SELECT
                v.table_name AS view_name,
                v.view_definition,
                v.is_updatable,
                v.is_insertable_into,
                obj_description((quote_ident(v.table_schema) || '.' || quote_ident(v.table_name))::regclass) AS view_comment
            FROM information_schema.views v
            WHERE v.table_schema = 'public'
            ORDER BY v.table_name
        """

        rows = await conexion.fetch(sql)
        for row in rows:
            vistas.append(dict(row))

        return vistas

    async def _obtener_funciones(self, conexion: asyncpg.Connection) -> list[dict[str, Any]]:
        """Obtiene todas las funciones de la base de datos."""
        funciones: list[dict[str, Any]] = []

        sql = """
            SELECT
                p.proname AS function_name,
                pg_get_function_arguments(p.oid) AS arguments,
                pg_get_function_result(p.oid) AS return_type,
                CASE p.prokind
                    WHEN 'f' THEN 'function'
                    WHEN 'p' THEN 'procedure'
                    WHEN 'a' THEN 'aggregate'
                    WHEN 'w' THEN 'window'
                END AS routine_type,
                l.lanname AS language,
                p.prosrc AS source_code,
                CASE p.provolatile
                    WHEN 'i' THEN 'IMMUTABLE'
                    WHEN 's' THEN 'STABLE'
                    WHEN 'v' THEN 'VOLATILE'
                END AS volatility,
                p.proisstrict AS is_strict,
                p.prosecdef AS security_definer,
                obj_description(p.oid) AS function_comment
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            JOIN pg_language l ON p.prolang = l.oid
            WHERE n.nspname = 'public' AND p.prokind = 'f'
            ORDER BY p.proname
        """

        rows = await conexion.fetch(sql)
        for row in rows:
            funciones.append(dict(row))

        return funciones

    async def _obtener_procedimientos(self, conexion: asyncpg.Connection) -> list[dict[str, Any]]:
        """Obtiene todos los procedimientos almacenados (PostgreSQL 11+)."""
        procedimientos: list[dict[str, Any]] = []

        sql = """
            SELECT
                p.proname AS procedure_name,
                pg_get_function_arguments(p.oid) AS arguments,
                l.lanname AS language,
                p.prosrc AS source_code,
                obj_description(p.oid) AS procedure_comment
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            JOIN pg_language l ON p.prolang = l.oid
            WHERE n.nspname = 'public' AND p.prokind = 'p'
            ORDER BY p.proname
        """

        rows = await conexion.fetch(sql)
        for row in rows:
            procedimientos.append(dict(row))

        return procedimientos

    async def _obtener_triggers(self, conexion: asyncpg.Connection) -> list[dict[str, Any]]:
        """Obtiene todos los triggers de la base de datos."""
        triggers: list[dict[str, Any]] = []

        sql = """
            SELECT
                t.trigger_name,
                t.event_manipulation,
                t.event_object_table AS table_name,
                t.action_timing,
                t.action_orientation,
                t.action_statement,
                t.action_condition
            FROM information_schema.triggers t
            WHERE t.trigger_schema = 'public'
            ORDER BY t.event_object_table, t.trigger_name
        """

        rows = await conexion.fetch(sql)
        for row in rows:
            triggers.append(dict(row))

        return triggers

    async def _obtener_secuencias(self, conexion: asyncpg.Connection) -> list[dict[str, Any]]:
        """Obtiene todas las secuencias de la base de datos."""
        secuencias: list[dict[str, Any]] = []

        sql = """
            SELECT
                s.sequence_name,
                s.data_type,
                s.start_value,
                s.minimum_value,
                s.maximum_value,
                s.increment,
                s.cycle_option
            FROM information_schema.sequences s
            WHERE s.sequence_schema = 'public'
            ORDER BY s.sequence_name
        """

        rows = await conexion.fetch(sql)
        for row in rows:
            secuencias.append(dict(row))

        return secuencias

    async def _obtener_indices(self, conexion: asyncpg.Connection) -> list[dict[str, Any]]:
        """Obtiene todos los índices de la base de datos."""
        indices: list[dict[str, Any]] = []

        sql = """
            SELECT
                i.indexname AS index_name,
                i.tablename AS table_name,
                i.indexdef AS index_definition,
                ix.indisunique AS is_unique,
                ix.indisprimary AS is_primary,
                am.amname AS index_type
            FROM pg_indexes i
            JOIN pg_class c ON c.relname = i.indexname
            JOIN pg_index ix ON ix.indexrelid = c.oid
            JOIN pg_am am ON am.oid = c.relam
            WHERE i.schemaname = 'public'
            ORDER BY i.tablename, i.indexname
        """

        rows = await conexion.fetch(sql)
        for row in rows:
            indices.append(dict(row))

        return indices

    async def _obtener_tipos_personalizados(self, conexion: asyncpg.Connection) -> list[dict[str, Any]]:
        """Obtiene los tipos definidos por el usuario (ENUMS, COMPOSITES)."""
        tipos: list[dict[str, Any]] = []

        sql = """
            SELECT
                t.typname AS type_name,
                CASE t.typtype
                    WHEN 'e' THEN 'enum'
                    WHEN 'c' THEN 'composite'
                    WHEN 'd' THEN 'domain'
                    WHEN 'r' THEN 'range'
                END AS type_category,
                CASE
                    WHEN t.typtype = 'e' THEN (
                        SELECT array_agg(e.enumlabel ORDER BY e.enumsortorder)::text
                        FROM pg_enum e WHERE e.enumtypid = t.oid
                    )
                    ELSE NULL
                END AS enum_values,
                obj_description(t.oid) AS type_comment
            FROM pg_type t
            JOIN pg_namespace n ON t.typnamespace = n.oid
            WHERE n.nspname = 'public' AND t.typtype IN ('e', 'c', 'd', 'r')
            ORDER BY t.typname
        """

        rows = await conexion.fetch(sql)
        for row in rows:
            tipos.append(dict(row))

        return tipos

    async def _obtener_extensiones(self, conexion: asyncpg.Connection) -> list[dict[str, Any]]:
        """Obtiene todas las extensiones instaladas en la base de datos."""
        extensiones: list[dict[str, Any]] = []

        sql = """
            SELECT
                e.extname AS extension_name,
                e.extversion AS version,
                n.nspname AS schema_name,
                obj_description(e.oid) AS extension_comment
            FROM pg_extension e
            JOIN pg_namespace n ON e.extnamespace = n.oid
            ORDER BY e.extname
        """

        rows = await conexion.fetch(sql)
        for row in rows:
            extensiones.append(dict(row))

        return extensiones
