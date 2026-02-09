"""
configuracion_jwt.py — Clase de configuración para tokens JWT
Ubicación: modelos/configuracion_jwt.py

Equivalente a: ApiGenericaCsharp/Modelos/ConfiguracionJwt.cs

Se asocia directamente con las variables JWT_* en el archivo .env

Principios:
- SRP: Se encarga solo de representar datos de configuración JWT.
- OCP: Puede ampliarse si se agregan más parámetros, sin afectar el resto del sistema.
- DIP: Es usada por los controladores a través de get_settings().

Ejemplo de configuración en .env:

JWT_KEY=ClaveSuperSecreta123456
JWT_ISSUER=ApiGenericaFastAPI
JWT_AUDIENCE=clientes
JWT_DURACION_MINUTOS=60
"""

from pydantic import BaseModel, Field


class ConfiguracionJwt(BaseModel):
    """
    Representa los valores de configuración JWT.
    Estos valores son cargados desde .env y usados para firmar los tokens.
    """
    
    # Clave secreta usada para firmar los tokens JWT.
    # Debe ser larga y segura. Nunca se comparte públicamente.
    key: str = Field(default="", description="Clave secreta para firmar tokens")
    
    # Emisor del token (Issuer). Normalmente el nombre o dominio de la API.
    issuer: str = Field(default="", description="Emisor del token")
    
    # Audiencia del token (Audience). Indica quién puede usar este token.
    audience: str = Field(default="", description="Audiencia del token")
    
    # Duración del token en minutos.
    # Si no se establece en .env, se aplica el valor por defecto (30 minutos).
    duracion_minutos: int = Field(default=30, description="Duración en minutos")
