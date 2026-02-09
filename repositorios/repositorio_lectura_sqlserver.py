"""
repositorio_lectura_sqlserver.py — Implementación del repositorio para SQL Server
Ubicación: repositorios/repositorio_lectura_sqlserver.py

Equivalente a: ApiGenericaCsharp/Repositorios/RepositorioLecturaSqlServer.cs

Características:
- Detección automática de tipos via INFORMATION_SCHEMA
- Conversión inteligente de strings a tipos apropiados
- Soporte para búsquedas DATE vs DATETIME
- Encriptación BCrypt de campos sensibles
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


class RepositorioLecturaSqlServer(IRepositorioLecturaTabla):
    """
    Implementación del repositorio para SQL Server.
    
    Usa SQLAlchemy async con aioodbc para conexiones asíncronas.
    Detecta tipos de columnas automáticamente via INFORMATION_SCHEMA.
    """
    
    def __init__(self, proveedor_conexion: IProveedorConexion):
        """
        Inicializa el repositorio con el proveedor de conexión.
        
        Args:
            proveedor_conexion: Proveedor que entrega la cadena de conexión
        """
        if proveedor_conexion is None:
            raise ValueError("proveedor_conexion no puede ser None")
        
        self._proveedor_conexion = proveedor_conexion
        self._engine: AsyncEngine | None = None
    
    async def _obtener_engine(self) -> AsyncEngine:
        """
        Obtiene o crea el engine de SQLAlchemy (lazy initialization).
        
        Returns:
            AsyncEngine configurado para SQL Server
        """
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
        Detecta el tipo de una columna consultando INFORMATION_SCHEMA.
        
        Args:
            nombre_tabla: Nombre de la tabla
            esquema: Esquema (ej: 'dbo')
            nombre_columna: Nombre de la columna
        
        Returns:
            Tipo de dato como string (ej: 'int', 'varchar') o None si no existe
        """
        sql = text("""
            SELECT DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :esquema
            AND TABLE_NAME = :tabla
            AND COLUMN_NAME = :columna
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
        """
        Convierte un valor string al tipo Python apropiado.
        
        Args:
            valor: Valor como string
            tipo_destino: Tipo SQL detectado
        
        Returns:
            Valor convertido al tipo apropiado
        """
        if tipo_destino is None:
            return valor
        
        try:
            # Tipos enteros
            if tipo_destino in ('int', 'bigint', 'smallint', 'tinyint'):
                return int(valor)
            
            # Tipos decimales
            if tipo_destino in ('decimal', 'numeric', 'money', 'smallmoney'):
                return Decimal(valor)
            
            # Tipos flotantes
            if tipo_destino in ('float', 'real'):
                return float(valor)
            
            # Tipo booleano
            if tipo_destino == 'bit':
                return valor.lower() in ('true', '1', 'yes', 'si')
            
            # UUID
            if tipo_destino == 'uniqueidentifier':
                return UUID(valor)
            
            # Fechas
            if tipo_destino == 'date':
                return self._extraer_solo_fecha(valor)
            
            if tipo_destino in ('datetime', 'datetime2', 'smalldatetime'):
                return datetime.fromisoformat(valor.replace('Z', '+00:00'))
            
            if tipo_destino == 'time':
                return time.fromisoformat(valor)
            
            # Texto (no necesita conversión)
            if tipo_destino in ('varchar', 'char', 'text', 'nvarchar', 'nchar', 'ntext'):
                return valor
            
            return valor
            
        except (ValueError, TypeError):
            return valor
    
    def _extraer_solo_fecha(self, valor: str) -> date:
        """
        Extrae solo la fecha de un string.
        
        Args:
            valor: String con fecha (puede incluir hora)
        
        Returns:
            Objeto date
        """
        # Si tiene 'T', es formato ISO con hora
        if 'T' in valor:
            return datetime.fromisoformat(valor.replace('Z', '+00:00')).date()
        
        # Intentar parsear como fecha
        return date.fromisoformat(valor[:10])
    
    def _es_fecha_sin_hora(self, valor: str) -> bool:
        """
        Detecta si un valor parece ser solo fecha (YYYY-MM-DD).
        
        Args:
            valor: String a evaluar
        
        Returns:
            True si es formato fecha sin hora
        """
        return (
            len(valor) == 10 and 
            valor.count('-') == 2 and 
            'T' not in valor and 
            ':' not in valor
        )
    
    # =========================================================================
    # OPERACIONES CRUD
    # =========================================================================
    
    async def obtener_filas(
        self,
        nombre_tabla: str,
        esquema: str | None = None,
        limite: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Obtiene filas de una tabla.
        
        Args:
            nombre_tabla: Nombre de la tabla
            esquema: Esquema (default: 'dbo')
            limite: Máximo de filas (default: 1000)
        
        Returns:
            Lista de diccionarios con los datos
        """
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        
        esquema_final = (esquema or "dbo").strip()
        limite_final = limite or 1000
        
        # SQL Server usa TOP (n) en lugar de LIMIT
        sql = text(f"SELECT TOP ({limite_final}) * FROM [{esquema_final}].[{nombre_tabla}]")
        
        try:
            engine = await self._obtener_engine()
            async with engine.connect() as conn:
                result = await conn.execute(sql)
                columnas = result.keys()
                filas = []
                
                for row in result.fetchall():
                    fila = {}
                    for i, columna in enumerate(columnas):
                        valor = row[i]
                        # Convertir tipos especiales para JSON
                        if isinstance(valor, (datetime, date)):
                            valor = valor.isoformat()
                        elif isinstance(valor, Decimal):
                            valor = float(valor)
                        elif isinstance(valor, UUID):
                            valor = str(valor)
                        fila[columna] = valor
                    filas.append(fila)
                
                return filas
                
        except Exception as ex:
            raise RuntimeError(
                f"Error SQL al consultar '{esquema_final}.{nombre_tabla}': {ex}"
            ) from ex
    
    async def obtener_por_clave(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor: str,
        esquema: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Obtiene filas filtradas por una clave.
        
        Args:
            nombre_tabla: Nombre de la tabla
            nombre_clave: Nombre de la columna clave
            valor: Valor a buscar
            esquema: Esquema (default: 'dbo')
        
        Returns:
            Lista de diccionarios con los datos encontrados
        """
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        if not nombre_clave or not nombre_clave.strip():
            raise ValueError("El nombre de la clave no puede estar vacío")
        if not valor or not valor.strip():
            raise ValueError("El valor no puede estar vacío")
        
        esquema_final = (esquema or "dbo").strip()
        
        try:
            # Detectar tipo de la columna
            tipo_columna = await self._detectar_tipo_columna(
                nombre_tabla, esquema_final, nombre_clave
            )
            
            # Caso especial: buscar fecha en columna DATETIME
            es_busqueda_fecha_en_datetime = (
                tipo_columna in ('datetime', 'datetime2') and 
                self._es_fecha_sin_hora(valor)
            )
            
            if es_busqueda_fecha_en_datetime:
                sql = text(f"""
                    SELECT * FROM [{esquema_final}].[{nombre_tabla}] 
                    WHERE CAST([{nombre_clave}] AS DATE) = :valor
                """)
                valor_convertido = self._extraer_solo_fecha(valor)
            else:
                sql = text(f"""
                    SELECT * FROM [{esquema_final}].[{nombre_tabla}] 
                    WHERE [{nombre_clave}] = :valor
                """)
                valor_convertido = self._convertir_valor(valor, tipo_columna)
            
            engine = await self._obtener_engine()
            async with engine.connect() as conn:
                result = await conn.execute(sql, {"valor": valor_convertido})
                columnas = result.keys()
                filas = []
                
                for row in result.fetchall():
                    fila = {}
                    for i, columna in enumerate(columnas):
                        val = row[i]
                        if isinstance(val, (datetime, date)):
                            val = val.isoformat()
                        elif isinstance(val, Decimal):
                            val = float(val)
                        elif isinstance(val, UUID):
                            val = str(val)
                        fila[columna] = val
                    filas.append(fila)
                
                return filas
                
        except Exception as ex:
            raise RuntimeError(
                f"Error SQL al filtrar '{esquema_final}.{nombre_tabla}': {ex}"
            ) from ex
    
    async def crear(
        self,
        nombre_tabla: str,
        datos: dict[str, Any],
        esquema: str | None = None,
        campos_encriptar: str | None = None
    ) -> bool:
        """
        Inserta una nueva fila en la tabla.
        
        Args:
            nombre_tabla: Nombre de la tabla
            datos: Diccionario con los datos a insertar
            esquema: Esquema (default: 'dbo')
            campos_encriptar: Campos a encriptar separados por coma
        
        Returns:
            True si se insertó correctamente
        """
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        if not datos:
            raise ValueError("Los datos no pueden estar vacíos")
        
        esquema_final = (esquema or "dbo").strip()
        
        # Copiar datos para no modificar el original
        datos_finales = dict(datos)
        
        # Encriptar campos si se especificaron
        if campos_encriptar:
            campos_a_encriptar = {
                c.strip().lower() 
                for c in campos_encriptar.split(',') 
                if c.strip()
            }
            
            for campo in list(datos_finales.keys()):
                if campo.lower() in campos_a_encriptar and datos_finales[campo]:
                    datos_finales[campo] = encriptar(str(datos_finales[campo]))
        
        # Construir SQL
        columnas = ", ".join(f"[{k}]" for k in datos_finales.keys())
        parametros = ", ".join(f":{k}" for k in datos_finales.keys())
        sql = text(f"INSERT INTO [{esquema_final}].[{nombre_tabla}] ({columnas}) VALUES ({parametros})")
        
        try:
            # Convertir valores según tipos detectados
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
                f"Error SQL al insertar en '{esquema_final}.{nombre_tabla}': {ex}"
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
        """
        Actualiza filas en la tabla.
        
        Args:
            nombre_tabla: Nombre de la tabla
            nombre_clave: Columna clave para el WHERE
            valor_clave: Valor de la clave
            datos: Datos a actualizar
            esquema: Esquema (default: 'dbo')
            campos_encriptar: Campos a encriptar
        
        Returns:
            Número de filas afectadas
        """
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        if not nombre_clave or not nombre_clave.strip():
            raise ValueError("El nombre de la clave no puede estar vacío")
        if not valor_clave or not valor_clave.strip():
            raise ValueError("El valor de la clave no puede estar vacío")
        if not datos:
            raise ValueError("Los datos no pueden estar vacíos")
        
        esquema_final = (esquema or "dbo").strip()
        
        # Copiar y encriptar campos
        datos_finales = dict(datos)
        
        if campos_encriptar:
            campos_a_encriptar = {
                c.strip().lower() 
                for c in campos_encriptar.split(',') 
                if c.strip()
            }
            
            for campo in list(datos_finales.keys()):
                if campo.lower() in campos_a_encriptar and datos_finales[campo]:
                    datos_finales[campo] = encriptar(str(datos_finales[campo]))
        
        # Construir SQL
        clausula_set = ", ".join(f"[{k}] = :{k}" for k in datos_finales.keys())
        sql = text(f"""
            UPDATE [{esquema_final}].[{nombre_tabla}] 
            SET {clausula_set} 
            WHERE [{nombre_clave}] = :valor_clave
        """)
        
        try:
            # Convertir valores
            valores = {}
            for key, val in datos_finales.items():
                if val is not None and isinstance(val, str):
                    tipo = await self._detectar_tipo_columna(nombre_tabla, esquema_final, key)
                    valores[key] = self._convertir_valor(val, tipo)
                else:
                    valores[key] = val
            
            # Convertir valor de la clave
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
                f"Error SQL al actualizar '{esquema_final}.{nombre_tabla}': {ex}"
            ) from ex
    
    async def eliminar(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor_clave: str,
        esquema: str | None = None
    ) -> int:
        """
        Elimina filas de la tabla.
        
        Args:
            nombre_tabla: Nombre de la tabla
            nombre_clave: Columna clave para el WHERE
            valor_clave: Valor de la clave
            esquema: Esquema (default: 'dbo')
        
        Returns:
            Número de filas eliminadas
        """
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        if not nombre_clave or not nombre_clave.strip():
            raise ValueError("El nombre de la clave no puede estar vacío")
        if not valor_clave or not valor_clave.strip():
            raise ValueError("El valor de la clave no puede estar vacío")
        
        esquema_final = (esquema or "dbo").strip()
        
        sql = text(f"""
            DELETE FROM [{esquema_final}].[{nombre_tabla}] 
            WHERE [{nombre_clave}] = :valor_clave
        """)
        
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
                f"Error SQL al eliminar de '{esquema_final}.{nombre_tabla}': {ex}"
            ) from ex
    
    async def obtener_hash_contrasena(
        self,
        nombre_tabla: str,
        campo_usuario: str,
        campo_contrasena: str,
        valor_usuario: str,
        esquema: str | None = None
    ) -> str | None:
        """
        Obtiene el hash de contraseña de un usuario.
        
        Args:
            nombre_tabla: Tabla de usuarios
            campo_usuario: Columna del nombre de usuario
            campo_contrasena: Columna de la contraseña hasheada
            valor_usuario: Nombre del usuario a buscar
            esquema: Esquema (default: 'dbo')
        
        Returns:
            Hash de la contraseña o None si no existe
        """
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío")
        if not campo_usuario or not campo_usuario.strip():
            raise ValueError("El campo de usuario no puede estar vacío")
        if not campo_contrasena or not campo_contrasena.strip():
            raise ValueError("El campo de contraseña no puede estar vacío")
        if not valor_usuario or not valor_usuario.strip():
            raise ValueError("El valor de usuario no puede estar vacío")
        
        esquema_final = (esquema or "dbo").strip()
        
        sql = text(f"""
            SELECT [{campo_contrasena}] 
            FROM [{esquema_final}].[{nombre_tabla}] 
            WHERE [{campo_usuario}] = :valor_usuario
        """)
        
        try:
            engine = await self._obtener_engine()
            async with engine.connect() as conn:
                result = await conn.execute(sql, {"valor_usuario": valor_usuario})
                row = result.fetchone()
                return str(row[0]) if row and row[0] else None
                
        except Exception as ex:
            raise RuntimeError(
                f"Error SQL al obtener hash de '{esquema_final}.{nombre_tabla}': {ex}"
            ) from ex
    
    async def obtener_diagnostico_conexion(self) -> dict[str, Any]:
        """
        Obtiene información de diagnóstico de la conexión.
        
        Returns:
            Diccionario con información del servidor
        """
        sql = text("""
            SELECT
                DB_NAME() AS nombre_base_datos,
                SCHEMA_NAME() AS esquema_actual,
                @@VERSION AS version_servidor,
                @@SERVERNAME AS nombre_servidor,
                SUSER_SNAME() AS usuario_actual,
                @@SPID AS id_proceso
        """)
        
        try:
            engine = await self._obtener_engine()
            async with engine.connect() as conn:
                result = await conn.execute(sql)
                row = result.fetchone()
                
                if not row:
                    raise RuntimeError("No se pudo obtener diagnóstico")
                
                return {
                    "proveedor": "SQL Server",
                    "baseDatos": row[0],
                    "esquema": row[1] or "dbo",
                    "version": row[2],
                    "servidor": row[3],
                    "usuarioConectado": row[4],
                    "idProcesoConexion": row[5]
                }
                
        except Exception as ex:
            raise RuntimeError(f"Error SQL al obtener diagnóstico: {ex}") from ex
