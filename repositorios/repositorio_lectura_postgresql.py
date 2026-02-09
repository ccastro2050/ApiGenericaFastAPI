"""
repositorio_lectura_postgresql.py — Implementación del repositorio para PostgreSQL
Ubicación: repositorios/repositorio_lectura_postgresql.py

Equivalente a: ApiGenericaCsharp/Repositorios/RepositorioLecturaPostgreSQL.cs

Diferencias con SQL Server:
- Identificadores con "comillas dobles" en lugar de [corchetes]
- LIMIT n en lugar de TOP (n)
- Esquema por defecto: 'public' en lugar de 'dbo'
- Case-sensitive en nombres de tablas/columnas
"""

from typing import Any
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from repositorios.abstracciones.i_repositorio_lectura_tabla import IRepositorioLecturaTabla
from servicios.abstracciones.i_proveedor_conexion import IProveedorConexion
from servicios.utilidades.encriptacion_bcrypt import encriptar


class RepositorioLecturaPostgreSQL(IRepositorioLecturaTabla):
    """
    Implementación del repositorio para PostgreSQL.
    
    Usa SQLAlchemy async con asyncpg para conexiones asíncronas.
    Detecta tipos de columnas automáticamente via information_schema.
    """
    
    def __init__(self, proveedor_conexion: IProveedorConexion):
        if proveedor_conexion is None:
            raise ValueError("proveedor_conexion no puede ser None")
        
        self._proveedor_conexion = proveedor_conexion
        self._engine: AsyncEngine | None = None
    
    async def _obtener_engine(self) -> AsyncEngine:
        """Obtiene o crea el engine de SQLAlchemy."""
        if self._engine is None:
            cadena = self._proveedor_conexion.obtener_cadena_conexion()
            self._engine = create_async_engine(cadena, echo=False)
        return self._engine
    
    # =========================================================================
    # DETECCIÓN DE TIPOS
    # =========================================================================
    
    async def _detectar_tipo_columna(
        self, 
        nombre_tabla: str, 
        esquema: str, 
        nombre_columna: str
    ) -> str | None:
        """
        Detecta el tipo de una columna consultando information_schema.
        """
        sql = text("""
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = :esquema
            AND table_name = :tabla
            AND column_name = :columna
        """)
        
        try:
            engine = await self._obtener_engine()
            async with engine.connect() as conn:
                result = await conn.execute(sql, {
                    "esquema": esquema,
                    "tabla": nombre_tabla,
                    "columna": nombre_columna
                })
                row = result.fetchone()
                return row[0].lower() if row else None
        except Exception as ex:
            print(f"Advertencia: No se pudo detectar tipo de {nombre_columna}: {ex}")
            return None
    
    def _convertir_valor(self, valor: str, tipo_destino: str | None) -> Any:
        """Convierte un valor string al tipo Python apropiado."""
        if tipo_destino is None:
            return valor
        
        try:
            # Tipos enteros
            if tipo_destino in ('integer', 'int4', 'bigint', 'int8', 'smallint', 'int2'):
                return int(valor)
            
            # Tipos decimales
            if tipo_destino in ('numeric', 'decimal'):
                return Decimal(valor)
            
            # Tipos flotantes
            if tipo_destino in ('real', 'float4', 'double precision', 'float8'):
                return float(valor)
            
            # Tipo booleano
            if tipo_destino in ('boolean', 'bool'):
                return valor.lower() in ('true', '1', 'yes', 'si', 't')
            
            # UUID
            if tipo_destino == 'uuid':
                return UUID(valor)
            
            # Fechas
            if tipo_destino == 'date':
                return self._extraer_solo_fecha(valor)
            
            if tipo_destino in ('timestamp without time zone', 'timestamp with time zone'):
                return datetime.fromisoformat(valor.replace('Z', '+00:00'))
            
            if tipo_destino == 'time':
                return time.fromisoformat(valor)
            
            # Texto y JSON (no necesitan conversión)
            if tipo_destino in ('character varying', 'varchar', 'character', 'char', 
                               'text', 'json', 'jsonb'):
                return valor
            
            return valor
            
        except (ValueError, TypeError):
            return valor
    
    def _extraer_solo_fecha(self, valor: str) -> date:
        """Extrae solo la fecha de un string."""
        if 'T' in valor:
            return datetime.fromisoformat(valor.replace('Z', '+00:00')).date()
        return date.fromisoformat(valor[:10])
    
    def _es_fecha_sin_hora(self, valor: str) -> bool:
        """Detecta si un valor parece ser solo fecha (YYYY-MM-DD)."""
        return (
            len(valor) == 10 and 
            valor.count('-') == 2 and 
            'T' not in valor and 
            ':' not in valor
        )
    
    def _serializar_valor(self, valor: Any) -> Any:
        """Convierte tipos Python a tipos serializables para JSON."""
        if isinstance(valor, (datetime, date)):
            return valor.isoformat()
        elif isinstance(valor, Decimal):
            return float(valor)
        elif isinstance(valor, UUID):
            return str(valor)
        return valor
    
    # =========================================================================
    # OPERACIONES CRUD
    # =========================================================================
    
    async def obtener_filas(
        self,
        nombre_tabla: str,
        esquema: str | None = None,
        limite: int | None = None
    ) -> list[dict[str, Any]]:
        """Obtiene filas de una tabla."""
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        
        esquema_final = (esquema or "public").strip()
        limite_final = limite or 1000
        
        # PostgreSQL usa LIMIT en lugar de TOP
        sql = text(f'SELECT * FROM "{esquema_final}"."{nombre_tabla}" LIMIT :limite')
        
        try:
            engine = await self._obtener_engine()
            async with engine.connect() as conn:
                result = await conn.execute(sql, {"limite": limite_final})
                columnas = result.keys()
                filas = []
                
                for row in result.fetchall():
                    fila = {
                        col: self._serializar_valor(row[i])
                        for i, col in enumerate(columnas)
                    }
                    filas.append(fila)
                
                return filas
                
        except Exception as ex:
            raise RuntimeError(
                f"Error PostgreSQL al consultar '{esquema_final}.{nombre_tabla}': {ex}"
            ) from ex
    
    async def obtener_por_clave(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor: str,
        esquema: str | None = None
    ) -> list[dict[str, Any]]:
        """Obtiene filas filtradas por una clave."""
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        if not nombre_clave or not nombre_clave.strip():
            raise ValueError("El nombre de la clave no puede estar vacío")
        if not valor or not valor.strip():
            raise ValueError("El valor no puede estar vacío")
        
        esquema_final = (esquema or "public").strip()
        
        try:
            tipo_columna = await self._detectar_tipo_columna(
                nombre_tabla, esquema_final, nombre_clave
            )
            
            # Caso especial: buscar fecha en columna TIMESTAMP
            es_busqueda_fecha_en_timestamp = (
                tipo_columna in ('timestamp without time zone', 'timestamp with time zone') and 
                self._es_fecha_sin_hora(valor)
            )
            
            if es_busqueda_fecha_en_timestamp:
                sql = text(f'''
                    SELECT * FROM "{esquema_final}"."{nombre_tabla}" 
                    WHERE CAST("{nombre_clave}" AS DATE) = :valor
                ''')
                valor_convertido = self._extraer_solo_fecha(valor)
            else:
                sql = text(f'''
                    SELECT * FROM "{esquema_final}"."{nombre_tabla}" 
                    WHERE "{nombre_clave}" = :valor
                ''')
                valor_convertido = self._convertir_valor(valor, tipo_columna)
            
            engine = await self._obtener_engine()
            async with engine.connect() as conn:
                result = await conn.execute(sql, {"valor": valor_convertido})
                columnas = result.keys()
                filas = []
                
                for row in result.fetchall():
                    fila = {
                        col: self._serializar_valor(row[i])
                        for i, col in enumerate(columnas)
                    }
                    filas.append(fila)
                
                return filas
                
        except Exception as ex:
            raise RuntimeError(
                f"Error PostgreSQL al filtrar '{esquema_final}.{nombre_tabla}': {ex}"
            ) from ex
    
    async def crear(
        self,
        nombre_tabla: str,
        datos: dict[str, Any],
        esquema: str | None = None,
        campos_encriptar: str | None = None
    ) -> bool:
        """Inserta una nueva fila en la tabla."""
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        if not datos:
            raise ValueError("Los datos no pueden estar vacíos")
        
        esquema_final = (esquema or "public").strip()
        datos_finales = dict(datos)
        
        # Encriptar campos si se especificaron
        if campos_encriptar:
            campos_a_encriptar = {
                c.strip().lower() for c in campos_encriptar.split(',') if c.strip()
            }
            for campo in list(datos_finales.keys()):
                if campo.lower() in campos_a_encriptar and datos_finales[campo]:
                    datos_finales[campo] = encriptar(str(datos_finales[campo]))
        
        # Construir SQL con comillas dobles para PostgreSQL
        columnas = ", ".join(f'"{k}"' for k in datos_finales.keys())
        parametros = ", ".join(f":{k}" for k in datos_finales.keys())
        sql = text(f'INSERT INTO "{esquema_final}"."{nombre_tabla}" ({columnas}) VALUES ({parametros})')
        
        try:
            valores = {}
            for key, val in datos_finales.items():
                if val is not None and isinstance(val, str):
                    tipo = await self._detectar_tipo_columna(nombre_tabla, esquema_final, key)
                    valores[key] = self._convertir_valor(val, tipo)
                else:
                    valores[key] = val
            
            engine = await self._obtener_engine()
            async with engine.begin() as conn:
                result = await conn.execute(sql, valores)
                return result.rowcount > 0
                
        except Exception as ex:
            raise RuntimeError(
                f"Error PostgreSQL al insertar en '{esquema_final}.{nombre_tabla}': {ex}"
            ) from ex
    
    async def actualizar(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor_clave: str,
        datos: dict[str, Any],
        esquema: str | None = None,
        campos_encriptar: str | None = None
    ) -> int:
        """Actualiza filas en la tabla."""
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        if not nombre_clave or not nombre_clave.strip():
            raise ValueError("El nombre de la clave no puede estar vacío")
        if not valor_clave or not valor_clave.strip():
            raise ValueError("El valor de la clave no puede estar vacío")
        if not datos:
            raise ValueError("Los datos no pueden estar vacíos")
        
        esquema_final = (esquema or "public").strip()
        datos_finales = dict(datos)
        
        if campos_encriptar:
            campos_a_encriptar = {
                c.strip().lower() for c in campos_encriptar.split(',') if c.strip()
            }
            for campo in list(datos_finales.keys()):
                if campo.lower() in campos_a_encriptar and datos_finales[campo]:
                    datos_finales[campo] = encriptar(str(datos_finales[campo]))
        
        clausula_set = ", ".join(f'"{k}" = :{k}' for k in datos_finales.keys())
        sql = text(f'''
            UPDATE "{esquema_final}"."{nombre_tabla}" 
            SET {clausula_set} 
            WHERE "{nombre_clave}" = :valor_clave
        ''')
        
        try:
            valores = {}
            for key, val in datos_finales.items():
                if val is not None and isinstance(val, str):
                    tipo = await self._detectar_tipo_columna(nombre_tabla, esquema_final, key)
                    valores[key] = self._convertir_valor(val, tipo)
                else:
                    valores[key] = val
            
            tipo_clave = await self._detectar_tipo_columna(
                nombre_tabla, esquema_final, nombre_clave
            )
            valores["valor_clave"] = self._convertir_valor(valor_clave, tipo_clave)
            
            engine = await self._obtener_engine()
            async with engine.begin() as conn:
                result = await conn.execute(sql, valores)
                return result.rowcount
                
        except Exception as ex:
            raise RuntimeError(
                f"Error PostgreSQL al actualizar '{esquema_final}.{nombre_tabla}': {ex}"
            ) from ex
    
    async def eliminar(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor_clave: str,
        esquema: str | None = None
    ) -> int:
        """Elimina filas de la tabla."""
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        if not nombre_clave or not nombre_clave.strip():
            raise ValueError("El nombre de la clave no puede estar vacío")
        if not valor_clave or not valor_clave.strip():
            raise ValueError("El valor de la clave no puede estar vacío")
        
        esquema_final = (esquema or "public").strip()
        
        sql = text(f'''
            DELETE FROM "{esquema_final}"."{nombre_tabla}" 
            WHERE "{nombre_clave}" = :valor_clave
        ''')
        
        try:
            tipo_clave = await self._detectar_tipo_columna(
                nombre_tabla, esquema_final, nombre_clave
            )
            valor_convertido = self._convertir_valor(valor_clave, tipo_clave)
            
            engine = await self._obtener_engine()
            async with engine.begin() as conn:
                result = await conn.execute(sql, {"valor_clave": valor_convertido})
                return result.rowcount
                
        except Exception as ex:
            raise RuntimeError(
                f"Error PostgreSQL al eliminar de '{esquema_final}.{nombre_tabla}': {ex}"
            ) from ex
    
    async def obtener_hash_contrasena(
        self,
        nombre_tabla: str,
        campo_usuario: str,
        campo_contrasena: str,
        valor_usuario: str,
        esquema: str | None = None
    ) -> str | None:
        """Obtiene el hash de contraseña de un usuario."""
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        if not campo_usuario or not campo_usuario.strip():
            raise ValueError("El campo de usuario no puede estar vacío")
        if not campo_contrasena or not campo_contrasena.strip():
            raise ValueError("El campo de contraseña no puede estar vacío")
        if not valor_usuario or not valor_usuario.strip():
            raise ValueError("El valor de usuario no puede estar vacío")
        
        esquema_final = (esquema or "public").strip()
        
        sql = text(f'''
            SELECT "{campo_contrasena}" 
            FROM "{esquema_final}"."{nombre_tabla}" 
            WHERE "{campo_usuario}" = :valor_usuario
        ''')
        
        try:
            engine = await self._obtener_engine()
            async with engine.connect() as conn:
                result = await conn.execute(sql, {"valor_usuario": valor_usuario})
                row = result.fetchone()
                return str(row[0]) if row and row[0] else None
                
        except Exception as ex:
            raise RuntimeError(
                f"Error PostgreSQL al obtener hash de '{esquema_final}.{nombre_tabla}': {ex}"
            ) from ex
    
    async def obtener_diagnostico_conexion(self) -> dict[str, Any]:
        """Obtiene información de diagnóstico de la conexión."""
        sql = text("""
            SELECT
                current_database() as nombre_base_datos,
                current_schema() as esquema_actual,
                version() as version_servidor,
                inet_server_addr()::text as direccion_ip,
                inet_server_port() as puerto,
                pg_postmaster_start_time() as hora_inicio,
                current_user as usuario_actual,
                pg_backend_pid() as id_proceso
        """)
        
        try:
            engine = await self._obtener_engine()
            async with engine.connect() as conn:
                result = await conn.execute(sql)
                row = result.fetchone()
                
                if not row:
                    raise RuntimeError("No se pudo obtener diagnóstico")
                
                return {
                    "proveedor": "PostgreSQL",
                    "baseDatos": row[0],
                    "esquema": row[1] or "public",
                    "version": row[2],
                    "direccionIP": row[3] or "localhost",
                    "puerto": row[4],
                    "horaInicio": row[5].isoformat() if row[5] else None,
                    "usuarioConectado": row[6],
                    "idProcesoConexion": row[7]
                }
                
        except Exception as ex:
            raise RuntimeError(f"Error PostgreSQL al obtener diagnóstico: {ex}") from ex
