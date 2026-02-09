"""
servicio_crud.py — Implementación de la lógica de negocio que coordina operaciones CRUD
Ubicación: servicios/servicio_crud.py

Equivalente a: ApiGenericaCsharp/Servicios/ServicioCrud.cs

Principios SOLID aplicados:
- SRP: Solo lógica de negocio, delega acceso a datos al repositorio
- DIP: Depende de abstracciones (Protocol), no de implementaciones concretas
- OCP: Se puede cambiar el repositorio sin modificar este servicio
"""

from typing import Any

from repositorios.abstracciones.i_repositorio_lectura_tabla import IRepositorioLecturaTabla
from servicios.abstracciones.i_politica_tablas_prohibidas import IPoliticaTablasProhibidas
from servicios.utilidades.encriptacion_bcrypt import verificar


class ServicioCrud:
    """
    Implementación del servicio CRUD que aplica reglas de negocio.
    
    Actúa como coordinador entre Controllers y Repositorios.
    
    Responsabilidades:
    - Validar parámetros según reglas de negocio
    - Normalizar datos antes de enviarlos al repositorio
    - Aplicar límites y políticas de seguridad
    - Verificar tablas prohibidas
    """
    
    def __init__(
        self,
        repositorio_lectura: IRepositorioLecturaTabla,
        politica_tablas: IPoliticaTablasProhibidas
    ):
        """
        Constructor que recibe dependencias mediante inyección.
        
        Args:
            repositorio_lectura: Repositorio para acceso a datos
            politica_tablas: Política de tablas permitidas/prohibidas
        """
        if repositorio_lectura is None:
            raise ValueError(
                "repositorio_lectura no puede ser None. "
                "Verificar la configuración de dependencias."
            )
        
        if politica_tablas is None:
            raise ValueError(
                "politica_tablas no puede ser None. "
                "Verificar la configuración de dependencias."
            )
        
        self._repositorio = repositorio_lectura
        self._politica_tablas = politica_tablas
    
    def _validar_tabla_permitida(self, nombre_tabla: str) -> None:
        """
        Valida que la tabla esté permitida según la política.
        
        Args:
            nombre_tabla: Nombre de la tabla a validar
        
        Raises:
            PermissionError: Si la tabla está prohibida
        """
        if not self._politica_tablas.es_tabla_permitida(nombre_tabla):
            raise PermissionError(
                f"Acceso denegado: La tabla '{nombre_tabla}' está restringida "
                f"y no puede ser consultada. Verifique los permisos de acceso."
            )
    
    async def listar(
        self,
        nombre_tabla: str,
        esquema: str | None = None,
        limite: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Lista registros aplicando reglas de negocio.
        
        Proceso:
        1. Validación de parámetros
        2. Verificación de tabla permitida
        3. Normalización de parámetros
        4. Delegación al repositorio
        """
        # FASE 1: VALIDACIONES
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío.")
        
        # FASE 2: VERIFICAR TABLA PERMITIDA
        self._validar_tabla_permitida(nombre_tabla)
        
        # FASE 3: NORMALIZACIÓN
        esquema_normalizado = esquema.strip() if esquema and esquema.strip() else None
        limite_normalizado = limite if limite and limite > 0 else None
        
        # FASE 4: DELEGACIÓN AL REPOSITORIO
        return await self._repositorio.obtener_filas(
            nombre_tabla=nombre_tabla,
            esquema=esquema_normalizado,
            limite=limite_normalizado
        )
    
    async def obtener_por_clave(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor: str,
        esquema: str | None = None
    ) -> list[dict[str, Any]]:
        """Obtiene registros filtrados por clave."""
        # VALIDACIONES
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío.")
        if not nombre_clave or not nombre_clave.strip():
            raise ValueError("El nombre de la clave no puede estar vacío.")
        if not valor or not valor.strip():
            raise ValueError("El valor no puede estar vacío.")
        
        # VERIFICAR TABLA PERMITIDA
        self._validar_tabla_permitida(nombre_tabla)
        
        # NORMALIZACIÓN
        esquema_normalizado = esquema.strip() if esquema and esquema.strip() else None
        
        # DELEGACIÓN
        return await self._repositorio.obtener_por_clave(
            nombre_tabla=nombre_tabla,
            nombre_clave=nombre_clave.strip(),
            valor=valor.strip(),
            esquema=esquema_normalizado
        )
    
    async def crear(
        self,
        nombre_tabla: str,
        datos: dict[str, Any],
        esquema: str | None = None,
        campos_encriptar: str | None = None
    ) -> bool:
        """Crea un nuevo registro."""
        # VALIDACIONES
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío.")
        if not datos:
            raise ValueError("Los datos no pueden estar vacíos.")
        
        # VERIFICAR TABLA PERMITIDA
        self._validar_tabla_permitida(nombre_tabla)
        
        # NORMALIZACIÓN
        esquema_normalizado = esquema.strip() if esquema and esquema.strip() else None
        campos_encriptar_norm = campos_encriptar.strip() if campos_encriptar and campos_encriptar.strip() else None
        
        # DELEGACIÓN
        return await self._repositorio.crear(
            nombre_tabla=nombre_tabla,
            datos=datos,
            esquema=esquema_normalizado,
            campos_encriptar=campos_encriptar_norm
        )
    
    async def actualizar(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor_clave: str,
        datos: dict[str, Any],
        esquema: str | None = None,
        campos_encriptar: str | None = None
    ) -> int:
        """Actualiza un registro existente."""
        # VALIDACIONES
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío.")
        if not nombre_clave or not nombre_clave.strip():
            raise ValueError("El nombre de la clave no puede estar vacío.")
        if not valor_clave or not valor_clave.strip():
            raise ValueError("El valor de la clave no puede estar vacío.")
        if not datos:
            raise ValueError("Los datos no pueden estar vacíos.")
        
        # VERIFICAR TABLA PERMITIDA
        self._validar_tabla_permitida(nombre_tabla)
        
        # NORMALIZACIÓN
        esquema_normalizado = esquema.strip() if esquema and esquema.strip() else None
        campos_encriptar_norm = campos_encriptar.strip() if campos_encriptar and campos_encriptar.strip() else None
        
        # DELEGACIÓN
        return await self._repositorio.actualizar(
            nombre_tabla=nombre_tabla,
            nombre_clave=nombre_clave.strip(),
            valor_clave=valor_clave.strip(),
            datos=datos,
            esquema=esquema_normalizado,
            campos_encriptar=campos_encriptar_norm
        )
    
    async def eliminar(
        self,
        nombre_tabla: str,
        nombre_clave: str,
        valor_clave: str,
        esquema: str | None = None
    ) -> int:
        """Elimina un registro."""
        # VALIDACIONES
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío.")
        if not nombre_clave or not nombre_clave.strip():
            raise ValueError("El nombre de la clave no puede estar vacío.")
        if not valor_clave or not valor_clave.strip():
            raise ValueError("El valor de la clave no puede estar vacío.")
        
        # VERIFICAR TABLA PERMITIDA
        self._validar_tabla_permitida(nombre_tabla)
        
        # NORMALIZACIÓN
        esquema_normalizado = esquema.strip() if esquema and esquema.strip() else None
        
        # DELEGACIÓN
        return await self._repositorio.eliminar(
            nombre_tabla=nombre_tabla,
            nombre_clave=nombre_clave.strip(),
            valor_clave=valor_clave.strip(),
            esquema=esquema_normalizado
        )
    
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
        
        Returns:
            Tupla (código, mensaje)
        """
        # VALIDACIONES
        if not nombre_tabla or not nombre_tabla.strip():
            raise ValueError("El nombre de la tabla no puede estar vacío.")
        if not campo_usuario or not campo_usuario.strip():
            raise ValueError("El campo de usuario no puede estar vacío.")
        if not campo_contrasena or not campo_contrasena.strip():
            raise ValueError("El campo de contraseña no puede estar vacío.")
        if not valor_usuario or not valor_usuario.strip():
            raise ValueError("El valor de usuario no puede estar vacío.")
        if not valor_contrasena:
            raise ValueError("La contraseña no puede estar vacía.")
        
        # VERIFICAR TABLA PERMITIDA
        self._validar_tabla_permitida(nombre_tabla)
        
        # NORMALIZACIÓN
        esquema_normalizado = esquema.strip() if esquema and esquema.strip() else None
        
        # OBTENER HASH DE LA BD
        hash_almacenado = await self._repositorio.obtener_hash_contrasena(
            nombre_tabla=nombre_tabla,
            campo_usuario=campo_usuario.strip(),
            campo_contrasena=campo_contrasena.strip(),
            valor_usuario=valor_usuario.strip(),
            esquema=esquema_normalizado
        )
        
        # VERIFICAR SI EXISTE EL USUARIO
        if hash_almacenado is None:
            return (404, f"Usuario '{valor_usuario}' no encontrado.")
        
        # VERIFICAR CONTRASEÑA CON BCRYPT
        if verificar(valor_contrasena, hash_almacenado):
            return (200, "Credenciales válidas.")
        else:
            return (401, "Contraseña incorrecta.")
