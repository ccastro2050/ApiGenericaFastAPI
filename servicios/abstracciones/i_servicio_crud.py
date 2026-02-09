"""
i_servicio_crud.py — Protocol que define el contrato para operaciones de lógica de negocio
Ubicación: servicios/abstracciones/i_servicio_crud.py

Equivalente a: ApiGenericaCsharp/Servicios/Abstracciones/IServicioCrud.cs

Principios SOLID aplicados:
- SRP: Solo define operaciones de lógica de negocio
- DIP: Permite que el controlador dependa de esta abstracción
- ISP: Protocol específico y pequeño
"""

from typing import Protocol, Any


class IServicioCrud(Protocol):
    """
    Protocol que define el contrato para un servicio CRUD genérico.
    
    La capa de servicios aplica la lógica de negocio:
    - Validaciones específicas del dominio
    - Coordinación entre repositorios
    - Transformación de datos
    - Aislamiento de la lógica de negocio
    
    Analogía del restaurante:
    - Repositorio = Bodega: "Dame todos los tomates"
    - Servicio = Chef: "Dame tomates maduros, máximo 10"
    - Controlador = Mesero: "El cliente pidió ensalada"
    """
    
    async def listar(
        self,
        nombre_tabla: str,
        esquema: str | None = None,
        limite: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Lista registros de una tabla aplicando reglas de negocio.
        
        Args:
            nombre_tabla: Tabla a consultar (con validaciones de dominio)
            esquema: Esquema (con reglas de negocio aplicadas)
            limite: Límite (con políticas empresariales)
        
        Returns:
            Lista de diccionarios con los datos
        
        Raises:
            ValueError: Si parámetros violan reglas de negocio
            PermissionError: Si la tabla está prohibida
        """
        ...
    
    async def obtener_por_clave(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor: str,
        esquema: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Obtiene registros filtrados por una clave.
        
        Args:
            nombre_tabla: Tabla a consultar
            nombre_clave: Columna para filtrar
            valor: Valor a buscar
            esquema: Esquema (opcional)
        
        Returns:
            Lista de registros que coinciden
        """
        ...
    
    async def crear(
        self,
        nombre_tabla: str,
        datos: dict[str, Any],
        esquema: str | None = None,
        campos_encriptar: str | None = None
    ) -> bool:
        """
        Crea un nuevo registro.
        
        Args:
            nombre_tabla: Tabla donde crear
            datos: Datos a insertar
            esquema: Esquema (opcional)
            campos_encriptar: Campos a encriptar separados por coma
        
        Returns:
            True si se creó correctamente
        """
        ...
    
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
        Actualiza un registro existente.
        
        Args:
            nombre_tabla: Tabla donde actualizar
            nombre_clave: Columna clave para el WHERE
            valor_clave: Valor de la clave
            datos: Nuevos datos
            esquema: Esquema (opcional)
            campos_encriptar: Campos a encriptar
        
        Returns:
            Número de filas afectadas
        """
        ...
    
    async def eliminar(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor_clave: str,
        esquema: str | None = None
    ) -> int:
        """
        Elimina un registro.
        
        Args:
            nombre_tabla: Tabla donde eliminar
            nombre_clave: Columna clave
            valor_clave: Valor de la clave
            esquema: Esquema (opcional)
        
        Returns:
            Número de filas eliminadas
        """
        ...
    
    async def verificar_contrasena(
        self,
        nombre_tabla: str,
        campo_usuario: str,
        campo_contrasena: str,
        valor_usuario: str,
        valor_contrasena: str,
        esquema: str | None = None
    ) -> tuple[int, str]:
        """
        Verifica credenciales de usuario con BCrypt.
        
        Args:
            nombre_tabla: Tabla de usuarios
            campo_usuario: Columna del usuario
            campo_contrasena: Columna del hash
            valor_usuario: Usuario a verificar
            valor_contrasena: Contraseña en texto plano
            esquema: Esquema (opcional)
        
        Returns:
            Tupla (código, mensaje):
            - (200, "Éxito") si es correcta
            - (404, "Usuario no encontrado")
            - (401, "Contraseña incorrecta")
        """
        ...
