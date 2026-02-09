"""
encriptacion_bcrypt.py — Módulo de utilidad para encriptación BCrypt
Ubicación: servicios/utilidades/encriptacion_bcrypt.py

Principios SOLID aplicados:
- SRP: Este módulo solo se encarga de operaciones de encriptación/verificación
- OCP: Abierto para extensión (nuevos métodos de hash) cerrado para modificación

Equivalente a: ApiGenericaCsharp/Servicios/Utilidades/EncriptacionBCrypt.cs
"""

import bcrypt

# Costo por defecto de BCrypt (12 es balance entre seguridad y rendimiento)
COSTO_POR_DEFECTO: int = 12


def encriptar(valor_original: str, costo: int = COSTO_POR_DEFECTO) -> str:
    """
    Encripta (hashea) un valor usando BCrypt con salt automático.
    
    El resultado es un string de 60 caracteres que contiene:
    - Identificador del algoritmo ($2b$)
    - Costo utilizado
    - Salt generado
    - Hash resultante
    
    Ejemplo: $2b$12$R9h/cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jWMUW
    
    Args:
        valor_original: Valor a encriptar (contraseña, PIN, etc.)
        costo: Costo computacional del hashing (por defecto 12)
    
    Returns:
        Hash BCrypt de 60 caracteres
    
    Raises:
        ValueError: Si el valor está vacío o el costo está fuera de rango
    """
    if not valor_original or not valor_original.strip():
        raise ValueError("El valor a encriptar no puede estar vacío.")
    
    if not 4 <= costo <= 31:
        raise ValueError(
            f"El costo de BCrypt debe estar entre 4 y 31. Recibido: {costo}. "
            "Recomendado: 10-15."
        )
    
    # bcrypt requiere bytes, no string
    valor_bytes = valor_original.encode('utf-8')
    
    # gensalt() genera el salt con el costo especificado
    salt = bcrypt.gensalt(rounds=costo)
    
    # hashpw() genera el hash final
    hash_bytes = bcrypt.hashpw(valor_bytes, salt)
    
    # Convertir bytes a string para almacenar en BD
    return hash_bytes.decode('utf-8')


def verificar(valor_original: str, hash_existente: str) -> bool:
    """
    Verifica si un valor corresponde a un hash BCrypt específico.
    
    Esta es la única forma de "verificar" datos hasheados con BCrypt, ya que
    el proceso es irreversible. No se puede obtener el valor original.
    
    Args:
        valor_original: Valor a verificar (texto plano)
        hash_existente: Hash BCrypt existente para comparar
    
    Returns:
        True si el valor corresponde al hash, False si no
    
    Raises:
        ValueError: Si algún parámetro está vacío
    """
    if not valor_original or not valor_original.strip():
        raise ValueError("El valor a verificar no puede estar vacío.")
    
    if not hash_existente or not hash_existente.strip():
        raise ValueError("El hash existente no puede estar vacío.")
    
    try:
        # Convertir a bytes para bcrypt
        valor_bytes = valor_original.encode('utf-8')
        hash_bytes = hash_existente.encode('utf-8')
        
        # checkpw() compara de forma segura
        return bcrypt.checkpw(valor_bytes, hash_bytes)
    except Exception:
        # Si ocurre cualquier error, retornar False
        return False


def necesita_rehasheo(hash_existente: str, costo_deseado: int = COSTO_POR_DEFECTO) -> bool:
    """
    Verifica si un hash BCrypt necesita ser re-hasheado debido a cambio de costo.
    Útil para migraciones de seguridad.
    
    Args:
        hash_existente: Hash BCrypt a verificar
        costo_deseado: Nuevo costo deseado
    
    Returns:
        True si el hash debe ser re-generado con el nuevo costo
    """
    if not hash_existente or not hash_existente.strip():
        return True
    
    try:
        # Formato BCrypt: $2b$12$... donde 12 es el costo
        if len(hash_existente) >= 7 and hash_existente.startswith('$2'):
            # Extraer el costo de la posición 4-5
            costo_parte = hash_existente[4:6]
            costo_actual = int(costo_parte)
            return costo_actual < costo_deseado
        
        return True
    except (ValueError, IndexError):
        return True
