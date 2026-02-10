# ApiGenericaFastAPI - API REST Generica Multi-Base de Datos

![Python Version](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![Database](https://img.shields.io/badge/DB-SQL_Server_%7C_Postgres_%7C_MySQL-brightgreen?logo=databricks)
![Auth](https://img.shields.io/badge/Auth-JWT_&_BCrypt-gold?logo=jsonwebtokens)
![Architecture](https://img.shields.io/badge/Architecture-Clean_%26_SOLID-orange)
![License](https://img.shields.io/badge/License-Educativo-lightgrey)

API REST generica para operaciones CRUD sobre cualquier tabla de base de datos. Soporta multiples motores con una sola configuracion.

**Version Python/FastAPI del proyecto [ApiGenericaCsharp](https://github.com/ccastro2050/ApiGenericaCsharp)**

---

## Tabla de Contenidos

- [Caracteristicas](#caracteristicas)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalacion](#instalacion)
- [Configuracion](#configuracion)
- [Bases de Datos Soportadas](#bases-de-datos-soportadas)
- [Endpoints](#endpoints)
- [Autenticacion JWT](#autenticacion-jwt)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Principios SOLID](#principios-solid)
- [Equivalencias C# vs Python](#equivalencias-c-vs-python)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Solucion de Problemas Comunes](#solucion-de-problemas-comunes)

---

## Caracteristicas

- **CRUD Generico**: Operaciones Create, Read, Update, Delete sobre cualquier tabla
- **Multi-Base de Datos**: SQL Server, PostgreSQL, MySQL, MariaDB
- **Autenticacion JWT**: Tokens seguros con expiracion configurable
- **Swagger UI**: Documentacion interactiva automatica de la API
- **ReDoc**: Documentacion alternativa de solo lectura
- **Consultas Parametrizadas**: Ejecucion segura de SQL con parametros
- **Stored Procedures**: Ejecucion dinamica de procedimientos almacenados
- **Introspeccion de BD**: Consultar estructura de tablas y base de datos
- **Encriptacion BCrypt**: Hash seguro de contrasenas
- **CORS Configurado**: Listo para consumir desde frontend
- **Async/Await**: Operaciones asincronas para mejor rendimiento
- **Arquitectura Limpia**: Separacion de responsabilidades (Controllers, Services, Repositories)

---

## Arquitectura

```
+-------------------------------------------------------------+
|                        CONTROLLERS                          |
|  entidades_controller | consultas_controller | autenticacion|
|  diagnostico_controller | estructuras_controller | procedimientos |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                         SERVICIOS                           |
|         ServicioCrud           |      ServicioConsultas     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                       REPOSITORIOS                          |
|  +-------------+  +-------------+  +---------------------+  |
|  |  SQL Server |  |  PostgreSQL |  |  MySQL / MariaDB    |  |
|  |  (aioodbc)  |  |  (asyncpg)  |  |    (aiomysql)       |  |
|  +-------------+  +-------------+  +---------------------+  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                      BASE DE DATOS                          |
+-------------------------------------------------------------+
```

---

## Requisitos

| Requisito | Version |
|-----------|---------|
| Python | 3.11 o superior |
| pip | Ultima version |
| Visual Studio Code | Ultima version (recomendado) |
| Base de datos | SQL Server, PostgreSQL, MySQL o MariaDB |

> **Nota sobre drivers async**: Esta API utiliza drivers asincronos nativos:
> - **asyncpg**: Driver PostgreSQL ultrarapido
> - **aiomysql**: Driver MySQL/MariaDB asincrono
> - **aioodbc**: Driver SQL Server via ODBC asincrono
>
> A diferencia de ORMs pesados, estos drivers trabajan directamente con SQL, ideal para APIs genericas donde el rendimiento es critico.

---

## Instalacion

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd ApiGenericaFastAPI
```

### 2. Crear entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
# Copiar plantilla
cp .env.example .env

# Editar .env con tus valores
# (ver seccion Configuracion)
```

### 5. Ejecutar la API

```bash
# Desarrollo (con auto-reload)
uvicorn main:app --reload --port 8000

# O directamente
python main.py
```

### 6. Abrir documentacion

| Documentacion | URL |
|---------------|-----|
| Swagger UI | http://localhost:8000/swagger |
| ReDoc | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/swagger/v1/swagger.json |

---

## Configuracion

### Archivo .env (Produccion)

```env
# Entorno
ENVIRONMENT=production
DEBUG=false

# JWT
JWT_KEY=MiClaveSecretaMuyLargaDeAlMenos32Caracteres!
JWT_ISSUER=MiApp
JWT_AUDIENCE=MiAppUsers
JWT_DURACION_MINUTOS=60

# Seguridad
TABLAS_PROHIBIDAS=

# Base de datos activa
DB_PROVIDER=sqlserver

# Cadenas de conexion
DB_SQLSERVER=Server=MI_SERVIDOR;Database=mi_bd;User Id=usuario;Password=password;TrustServerCertificate=True;
DB_POSTGRES=Host=localhost;Port=5432;Database=mi_bd;Username=postgres;Password=postgres;
DB_MYSQL=Server=localhost;Port=3306;Database=mi_bd;User=root;Password=mysql;CharSet=utf8mb4;
DB_MARIADB=Server=localhost;Port=3306;Database=mi_bd;User=root;Password=;
```

### Archivo .env.development (Desarrollo)

```env
ENVIRONMENT=development
DEBUG=true
DB_PROVIDER=postgres
# ... resto de configuracion para desarrollo local
```

### Cambiar de base de datos

Solo modifica el valor de `DB_PROVIDER`:

| Valor | Base de datos |
|-------|---------------|
| `sqlserver` | Microsoft SQL Server |
| `sqlserverexpress` | SQL Server Express |
| `localdb` | SQL Server LocalDB (desarrollo) |
| `postgres` | PostgreSQL |
| `mysql` | MySQL |
| `mariadb` | MariaDB |

> **Nota sobre LocalDB**: Es una version ligera de SQL Server para desarrollo. Viene incluida con Visual Studio. No requiere instalar SQL Server completo.

### Jerarquia de configuracion

| Entorno | Archivos cargados |
|---------|-------------------|
| Production | Solo `.env` |
| Development | `.env` + `.env.development` (sobrescribe) |

Equivalente a `appsettings.json` + `appsettings.Development.json` en C#.

---

## Bases de Datos Soportadas

| Base de Datos | Driver Python | Puerto Default | Uso |
|---------------|---------------|----------------|-----|
| SQL Server | aioodbc | 1433 | Produccion |
| SQL Server Express | aioodbc | 1433 | Desarrollo/Produccion |
| SQL Server LocalDB | aioodbc | - | Solo desarrollo |
| PostgreSQL | asyncpg | 5432 | Produccion |
| MySQL | aiomysql | 3306 | Produccion |
| MariaDB | aiomysql | 3306 | Produccion |

---

## Endpoints

### entidades_controller - CRUD Generico

| Metodo | Ruta | Descripcion | Auth |
|--------|------|-------------|------|
| GET | `/api/{tabla}` | Obtener todos los registros | Si |
| GET | `/api/{tabla}/{clave}/{valor}` | Obtener por clave | Si |
| POST | `/api/{tabla}` | Crear registro | Si |
| PUT | `/api/{tabla}/{clave}/{valor}` | Actualizar registro | Si |
| DELETE | `/api/{tabla}/{clave}/{valor}` | Eliminar registro | Si |

### consultas_controller - SQL Parametrizado

| Metodo | Ruta | Descripcion | Auth |
|--------|------|-------------|------|
| POST | `/api/consultas/ejecutarconsultaparametrizada` | Ejecutar consulta SQL | Si |

### autenticacion_controller - JWT

| Metodo | Ruta | Descripcion | Auth |
|--------|------|-------------|------|
| POST | `/api/autenticacion/login` | Iniciar sesion | No |

### diagnostico_controller - Estado del Sistema

| Metodo | Ruta | Descripcion | Auth |
|--------|------|-------------|------|
| GET | `/api/diagnostico/salud` | Verificar estado de la API | No |
| GET | `/api/diagnostico/conexion` | Verificar conexion a BD | No |

### estructuras_controller - Introspeccion

| Metodo | Ruta | Descripcion | Auth |
|--------|------|-------------|------|
| GET | `/api/estructuras/{tabla}/modelo` | Estructura de una tabla | No |
| GET | `/api/estructuras/basedatos` | Estructura completa de la BD | No |

### procedimientos_controller - Stored Procedures

| Metodo | Ruta | Descripcion | Auth |
|--------|------|-------------|------|
| POST | `/api/procedimientos/ejecutarsp` | Ejecutar procedimiento almacenado | Si |

---

## Autenticacion JWT

### 1. Obtener token

```http
POST /api/autenticacion/login
Content-Type: application/json

{
  "tabla": "usuarios",
  "campo_usuario": "email",
  "campo_contrasena": "password",
  "usuario": "admin@ejemplo.com",
  "contrasena": "miPassword123"
}
```

### 2. Respuesta exitosa

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expira": "2024-01-15T12:00:00Z",
  "usuario": "admin@ejemplo.com"
}
```

### 3. Usar token en peticiones

```http
GET /api/productos
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Ejemplos de Uso

### Obtener todos los productos

```http
GET /api/productos?limite=100
Authorization: Bearer {token}
```

### Obtener producto por ID

```http
GET /api/productos/id/42
Authorization: Bearer {token}
```

### Crear un producto

```http
POST /api/productos
Authorization: Bearer {token}
Content-Type: application/json

{
  "nombre": "Laptop HP",
  "precio": 1500.00,
  "stock": 25
}
```

### Actualizar un producto

```http
PUT /api/productos/id/42
Authorization: Bearer {token}
Content-Type: application/json

{
  "precio": 1399.99,
  "stock": 30
}
```

### Eliminar un producto

```http
DELETE /api/productos/id/42
Authorization: Bearer {token}
```

### Ejecutar consulta SQL

```http
POST /api/consultas/ejecutarconsultaparametrizada
Authorization: Bearer {token}
Content-Type: application/json

{
  "consulta": "SELECT * FROM productos WHERE precio > @precio",
  "parametros": {
    "precio": 100.00
  }
}
```

### Ejecutar procedimiento almacenado

```http
POST /api/procedimientos/ejecutarsp
Authorization: Bearer {token}
Content-Type: application/json

{
  "nombreSP": "sp_obtener_ventas_mes",
  "mes": 12,
  "anio": 2024
}
```

---

## Estructura del Proyecto

```
ApiGenericaFastAPI/
|-- controllers/
|   |-- __init__.py
|   |-- autenticacion_controller.py   # Login y JWT
|   |-- consultas_controller.py       # SQL parametrizado
|   |-- diagnostico_controller.py     # Estado del sistema
|   |-- entidades_controller.py       # CRUD generico
|   |-- estructuras_controller.py     # Introspeccion BD
|   +-- procedimientos_controller.py  # Stored procedures
|
|-- servicios/
|   |-- __init__.py
|   |-- abstracciones/
|   |   |-- i_servicio_crud.py        # Protocolo CRUD
|   |   +-- i_repositorio_consultas.py
|   |-- conexion/
|   |   +-- proveedor_conexion.py     # Proveedor de conexion
|   |-- utilidades/
|   |   +-- encriptacion_bcrypt.py    # Hash de contrasenas
|   |-- servicio_crud.py              # Logica CRUD
|   +-- servicio_consultas.py         # Logica consultas
|
|-- repositorios/
|   |-- __init__.py
|   |-- abstracciones/
|   |   |-- i_repositorio_lectura.py
|   |   +-- i_repositorio_consultas.py
|   |-- repositorio_lectura_sqlserver.py
|   |-- repositorio_lectura_postgresql.py
|   |-- repositorio_lectura_mysql_mariadb.py
|   |-- repositorio_consultas_sqlserver.py
|   |-- repositorio_consultas_postgresql.py
|   +-- repositorio_consultas_mysql_mariadb.py
|
|-- config.py                         # Configuracion con pydantic-settings
|-- main.py                           # Punto de entrada (equivale a Program.cs)
|-- requirements.txt                  # Dependencias (equivale a .csproj)
|-- .env                              # Configuracion produccion (NO subir a Git)
|-- .env.development                  # Configuracion desarrollo (NO subir a Git)
|-- .env.example                      # Plantilla de configuracion
|-- .gitignore
+-- README.md                         # Este archivo
```

---

## Principios SOLID Aplicados

| Principio | Aplicacion |
|-----------|------------|
| **S** - Single Responsibility | Cada clase tiene una sola responsabilidad (Controller -> coordina, Service -> logica, Repository -> datos) |
| **O** - Open/Closed | Agregar nueva BD sin modificar codigo existente (solo nuevo repositorio) |
| **L** - Liskov Substitution | Cualquier repositorio puede sustituir a otro que implemente el mismo Protocol |
| **I** - Interface Segregation | Protocols especificos (IRepositorioLectura, IRepositorioConsultas) |
| **D** - Dependency Inversion | Controllers dependen de abstracciones (Protocol), no de implementaciones concretas |

---

## Equivalencias C# vs Python

### Conceptos Generales

| Concepto | C# (.NET) | Python (FastAPI) |
|----------|-----------|------------------|
| Framework | ASP.NET Core | FastAPI |
| Punto de entrada | `Program.cs` | `main.py` |
| Configuracion | `appsettings.json` | `.env` |
| Dependencias | `.csproj` (NuGet) | `requirements.txt` (pip) |
| Interfaces | `interface` | `Protocol` (typing) |
| Inyeccion DI | `AddScoped<>()` | `Depends()` |
| Decoradores/Atributos | `[HttpGet]` | `@router.get()` |
| Async | `async Task<T>` | `async def` |

### Archivos Equivalentes

| C# | Python |
|----|--------|
| `Program.cs` | `main.py` |
| `appsettings.json` | `.env` |
| `appsettings.Development.json` | `.env.development` |
| `Controllers/*.cs` | `controllers/*.py` |
| `Servicios/*.cs` | `servicios/*.py` |
| `Repositorios/*.cs` | `repositorios/*.py` |
| `IServicio.cs` | `i_servicio.py` (Protocol) |

### Inyeccion de Dependencias

```csharp
// C# - Registro global en Program.cs
builder.Services.AddScoped<IServicioCrud, ServicioCrud>();

// Uso en Controller
public class MiController(IServicioCrud servicio) { }
```

```python
# Python - Por endpoint con Depends()
def obtener_servicio() -> ServicioCrud:
    return ServicioCrud(repositorio)

@router.get("/")
async def endpoint(servicio = Depends(obtener_servicio)):
    ...
```

### Atributos vs Decoradores

| Aspecto | C# (Atributos) | Python (Decoradores) |
|---------|----------------|---------------------|
| Sintaxis | `[HttpGet]` | `@router.get()` |
| Mecanismo | Metadatos + Reflexion | Funcion que envuelve funcion |
| Modifican codigo? | No (solo etiquetas) | Si (envuelven) |

---

## Tecnologias Utilizadas

| Tecnologia | Version | Proposito |
|------------|---------|-----------|
| Python | 3.11+ | Lenguaje principal |
| FastAPI | 0.100+ | Framework web async |
| Uvicorn | 0.22+ | Servidor ASGI |
| Pydantic | 2.0+ | Validacion de datos |
| pydantic-settings | 2.0+ | Configuracion desde .env |
| python-jose | 3.3+ | Tokens JWT |
| passlib + bcrypt | 1.7+ | Hash de contrasenas |
| asyncpg | 0.28+ | Driver PostgreSQL async |
| aiomysql | 0.2+ | Driver MySQL/MariaDB async |
| aioodbc | 0.5+ | Driver SQL Server async |

---

## Dependencias (requirements.txt)

```txt
# Framework web
fastapi>=0.100.0
uvicorn[standard]>=0.22.0

# Configuracion
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0

# Autenticacion JWT
python-jose[cryptography]>=3.3.0
python-multipart>=0.0.6

# Seguridad
passlib[bcrypt]>=1.7.4
bcrypt>=4.0.0

# Drivers de base de datos (async)
asyncpg>=0.28.0
aiomysql>=0.2.0
aioodbc>=0.5.0
```

---

## Probar la API

1. Activar entorno virtual: `venv\Scripts\activate`
2. Ejecutar: `uvicorn main:app --reload`
3. Abrir: `http://localhost:8000/swagger`
4. Probar endpoint de diagnostico: `GET /api/diagnostico/salud`
5. Hacer login para obtener token
6. Usar token en endpoints protegidos (boton "Authorize" en Swagger)

---

## Solucion de Problemas Comunes

### 1. Error de Conexion a la Base de Datos

**Sintoma**: `Connection refused` o `timeout`

**Solucion**:
- Verifica que el servicio de la base de datos este corriendo
- Revisa que `DB_PROVIDER` coincida con una cadena de conexion configurada
- Para SQL Server, asegurate de tener ODBC Driver 17 instalado

### 2. El Token JWT no funciona (401 Unauthorized)

**Sintoma**: Recibes error 401 incluso con el token.

**Solucion**:
- Incluye `Bearer ` (con espacio) antes del token
- Verifica que `JWT_KEY` tenga al menos 32 caracteres
- Comprueba que el token no haya expirado

### 3. ModuleNotFoundError

**Sintoma**: `ModuleNotFoundError: No module named 'fastapi'`

**Solucion**:
```bash
# Verificar que el entorno virtual este activo
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Reinstalar dependencias
pip install -r requirements.txt
```

### 4. Error de Puerto en Uso

**Sintoma**: `Address already in use`

**Solucion**:
```bash
# Cambiar puerto
uvicorn main:app --reload --port 8001

# O encontrar proceso usando el puerto
netstat -ano | findstr :8000
```

### 5. Errores de Importacion Circular

**Sintoma**: `ImportError: cannot import name 'X' from partially initialized module`

**Solucion**:
- Verifica que los `__init__.py` esten correctos
- Usa imports relativos dentro de paquetes: `from .modulo import Clase`

---

## Comandos Utiles

```bash
# Activar entorno virtual
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar en desarrollo
uvicorn main:app --reload --port 8000

# Ejecutar en produccion
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Verificar sintaxis
python -m py_compile main.py

# Generar requirements.txt desde entorno
pip freeze > requirements.txt
```

---

## Licencia

Este proyecto es de uso educativo.

---

## Autor

Basado en el tutorial ApiGenericaCsharp de Carlos Arturo Castro Castro.

Adaptacion a Python/FastAPI como ejercicio de aprendizaje para comparar ambos ecosistemas.
